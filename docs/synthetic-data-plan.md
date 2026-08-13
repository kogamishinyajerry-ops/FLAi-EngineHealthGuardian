# 模拟数据生产方案(Synthetic Data Plan)

> 配套 ADR-0014。本文是设计文档;实现见 `src/ehm/data_brain/synth/`。当前实现到 **P2**。
> 立场对齐 `docs/strategy-report.md` 的 P1「数字孪生合成 > GAN」与 `CODEBUDDY.md` §5。

## 0. 北极星

机队小、阳性事件极少,无法靠大样本监督学习竞争。**高质量物理合成数据**是
战略报告的 P1 之一。但报告同时给了两条硬警告:*「合成数据只能增强,不可作为唯一
验收证据」* 与 *「禁止用生成式 AI 虚构真实故障标签」*。

> 把 `data_brain.physics` 气路模型升级为**配置驱动、可注入故障、带诚实标签、直接产
> 真实格式、seed 可复现的数据工厂**,使其成为可追溯的训练/评估/架构验证资产——而不
> 是又一堆散落的 `synthetic.py`。

**价值定位(不越界)**:架构验证 + 方法验证 + 数据增强 + 误报压测。它**不是** LEAP-1C
真值的替代,也**不是**唯一验收证据。

## 1. 「高质量」七维度 + 度量

| # | 维度 | 目标 | 度量 |
|---|---|---|---|
| 1 | 物理保真度 | 功能依赖(热力气路因果)对,绝对值占位 | `gas_path`/振动/滑油定性测试全绿;退化走物理旋钮 |
| 2 | 工况真实性 | 真实航班剖面 + 航季 OAT 分布 + duty-cycle | 全相位生成;OAT 按航季采样;`PhaseTracker` 可回环解码 |
| 3 | 传感器真实性 | 噪声/采样率/丢点/单位/传感器故障 | AR(1) 噪声、按相位采样率、丢点、drift/stuck/bias |
| 4 | 机队真实性 | 多 ESN/构型/peer/构型随时间 | peer 群 ≥ 2;`config_tag` 可区分 |
| 5 | 故障多样性 | 渐变 + 混淆项 | 每类显式 label;混淆项标 `no_fault` |
| 6 | 标签完整性 | ground-truth = 「注入了什么」 | 每条数据回溯 manifest;`source=synthetic` |
| 7 | 可验证 + 可复现 | seed + 版本 + 配置 → 重放 | `(config_hash, factory_version, seed)` 复跑一致 |

## 2. 物理驱动 vs 生成式(核心取舍)

**决策:以 `gas_path` + 显式退化注入为唯一主干;GAN/扩散/LLM 不进数值/标签链路。**

- 气路物理模型 + 退化旋钮 = **主干**(功能依赖真、可审计;OEM 系数将来直接换 `EngineDesign`)。
- 标签来自「注入了什么」,诚实可溯源(`CODEBUDDY.md` §5)。
- 生成式仅在 P3「扩充 NLP 测试文本」边界,且**绝不虚构故障标签**。
- **绝对值准不准不重要,功能依赖/故障特征对才重要**——残差校准不变(ADR-0010)。

升级前最大问题:`scenarios/*/synthetic.py` 把退化写成 `baseline + 线性斜率`,
**`egt_degraded()` 造好却从没被调用**。工厂把退化重新接回物理旋钮。

## 3. 标签诚实性

每批数据配 `manifest.jsonl`(ground-truth,与数据物理分离,全程 `source=synthetic`):

- 每航段一条:`{esn, flight_id, cycle, 注入退化/混淆项/传感器故障, truth_label}`。
- `truth_label`:`true_fault`(退化激活)> `sensor_fault`(传感器故障)> `no_fault`。
- 拆分按 ESN + 时间(`CODEBUDDY.md` §3),manifest 记录 cycle。

## 4. 工况真实性

- **全相位剖面**:`ground→takeoff→climb→cruise→descent→approach→ground`,相位采样率不同
  (巡航稀疏、起降密集),OAT 按 ISA 递减率随高度下降。
- **航季 OAT**:summer/winter/ISA 的地面 OAT 分布采样(非 iid 均匀)。
- **航线 duty-cycle**:short_haul / long_haul 的巡航高度与时长不同。
- **peer 群**:多 ESN 同构型;`config_tag` 区分构型。

## 5. 传感器真实性

AR(1) 自相关噪声(非白噪声)、按相位采样率、概率丢点(触发 DQ `completeness`/ABSTAIN)、
单位逆向产出(EGT 存 °F、FF 存 lb/h,走 adapter 的 `convert` 端到端压测)、传感器故障
drift/stuck/bias(label=`sensor_fault`,与发动机故障分开)。

## 6. 故障多样性 + 混淆项(误报压测关键)

**故障族**(每类带物理签名):
- `hpc_efficiency_decay`(η_c↘ + 多烧油 → EGT↑)、`turbine_distress`(EGT↑强)、
  `bearing_wear`(振动↑)、`oil_leak`(消耗↑)。

**混淆项**(真实物理、非故障、`truth_label=no_fault`):`hot_day`(OAT↑→EGT↑,最易误报)、
`cold_day`、`high_alt_airport`。混淆项让 **false-alert budget 可测**。

## 7. 输出格式(走现有 adapter,端到端验证)

| 格式 | 产物 | adapter |
|---|---|---|
| QAR-CSV | 一航段一文件,全相位时间序列 | `QarCsvAdapter` + `PhaseTracker` |
| snapshots.jsonl | 一航段一巡航 canonical 快照(含滑油) | `SyntheticAdapter` |
| acars_json/reports.jsonl | 一航段一巡航 ACARS 报告( canonical 单位) | `AcarsJsonAdapter` |
| mro_json/findings.jsonl | 一 ESN 一 shop-visit finding(注入真相) | `MroJsonAdapter` → `findings_to_adjudications` |
| manifest.jsonl | per-flight ground-truth | (标签侧) |

> 单位逆向:QAR 存 `°F`/`lb/h`,QarCsvAdapter 转回验证算术逆;ACARS 存 canonical 单位。
> MRO finding 的真相 = 注入退化是否曾激活:曾激活→`removal/repair`(→TRUE_FAULT);否则
> →`borescope/rtv`(→NFF,含传感器漂移/混淆项/健康——shop visit 找不到发动机故障,即 NFF)。

## 8. 方法验证(NASA C-MAPSS)—— P4(未实现)

复现 C-MAPSS 退化设置(HPC 效率衰减 + 传感器漂移),断言定性形状一致;**验证方法对,不宣称
等于 LEAP-1C**。C-MAPSS 也可作公开真实格式数据集喂 adapter(仅方法/管道验证)。

## 9. 可复现 + 资产化

声明式 `SynthConfig`(frozen dataclass)+ 分层 seed(per-engine 子 seed)+ `(config_hash,
factory_version, seed)` 写入每批 README。`make synth` 重放。配置驱动,加故障类 = 加配置项。

## 10. 当前实现(P2 + P3)结构

```
src/ehm/data_brain/
  physics/{cycle,vibration,oil}.py        # 三域物理主干(诚实占位)
  synth/
    config.py     # SynthConfig + specs + config_hash
    mission.py    # 全相位航班剖面 + ISA OAT
    engine.py     # 物理真值 + 退化演化(接回 gas_path 旋钮)
    sensor.py     # AR(1) 噪声 + 丢点 + 传感器故障
    confounders.py# hot_day/cold_day/high_alt(改环境不改健康)
    manifest.py   # FlightTruth + truth_label
    mro.py        # 注入退化 -> MRO finding 诚实映射(EngineRunSummary)
    factory.py    # 编排 → QAR-CSV + snapshots + ACARS + MRO + manifest + config/hash/README
```

默认 fleet(6 台):2 healthy peer / 1 HPC decay(`true_fault`)/ 1 EGT drift(`sensor_fault`)
/ 1 hot-day(`no_fault` 混淆项)/ 1 low-data 跨构型。

## 11. 诚实边界(必须随数据传播)

- 系数是公开涡扇占位值,**非 LEAP-1C OEM**;绝对 EGT 示意量级;**残差校准不变**。
- 稳态循环模型只在持续功率段有效;地面慢车 EGT 用 `OAT + 温升` 下限钳位(只影响非巡航)。
- `source=SYNTHETIC`,不与真实数据混;标签只在 manifest;advisory-only。

## 12. 路线图

- ✅ **P0** 退化接通物理旋钮 + 振动/滑油子模型
- ✅ **P1** 全相位剖面 → QAR-CSV → `QarCsvAdapter`/`PhaseTracker` 回环
- ✅ **P2** 多 ESN fleet + peer + 混淆项 + manifest + seed/版本
- ✅ **P3** ACARS-JSONL + MRO-JSONL;合成 MRO finding 经 `findings_to_adjudications` 接入 gold-label 回路
- ⏳ **P4** C-MAPSS 方法验证回归测试
- ⏳ **P5** 按 ESN/时间拆分的训练/评估数据集产物

## 13. 风险

| 风险 | 缓解 |
|---|---|
| 误当 LEAP 真值 | README/manifest 全程标 `source=synthetic` + 占位声明 |
| 混淆项误标 | 混淆项与故障注入正交;回归测试校验 label |
| 物理模型仍是占位校准 | 继承 ADR-0010/0013 诚实声明;OEM 数据到位换 `EngineDesign` 即可 |
| 标签泄漏 | manifest 物理分离;按 ESN+时间拆(P5) |
| 过度工程化 | 配置驱动、分阶段、复用物理;拒绝 scope creep |
