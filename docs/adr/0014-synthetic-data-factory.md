# ADR 0014 — 物理驱动合成数据工厂(`data_brain.synth`)

- 状态:Accepted
- 日期:2026-08-13
- 配套:`docs/synthetic-data-plan.md`

## 背景
报告 P1「数字孪生合成 > GAN」要求高质量合成数据,但现有 `scenarios/*/synthetic.py`
只是「baseline + 线性斜率 + 均匀噪声」,只产单 cruise 快照,退化没走物理
(`egt_degraded()` 从未被调用),且无混淆项/传感器故障/真实格式产出。需要一个配置驱动、
可复现、产出真实格式、带诚实标签的数据工厂。

## 决策
新增 **库原语包 `src/ehm/data_brain/synth/`**,以 `data_brain.physics`(含新增
`vibration.py` / `oil.py`)为物理主干,配置驱动地产出:

- **QAR-CSV**(一航段一文件,全相位,单位逆向 `°C→°F`/`kg/h→lb/h`)→ 走现有 `QarCsvAdapter`
  + `PhaseTracker`,相位可回环解码;
- **snapshots.jsonl**(一航段一巡航 canonical `EngineSnapshot`,含滑油质量平衡);
- **manifest.jsonl**(ground-truth:注入了什么;`truth_label = true_fault|sensor_fault|no_fault`);
- **config.json / config_hash.txt / README.txt**(可复现:`(config_hash, factory_version, seed)`)。

退化**接回物理旋钮**(不再加线性斜率):`hpc_efficiency_decay`/`turbine_distress`→gas-path,
`bearing_wear`→振动,`oil_leak`→滑油。混淆项(`hot_day` 等)**改环境不改健康**,
`truth_label` 保持 `no_fault`——这是误报压测的关键。传感器故障 drift/stuck/bias 与发动机
故障**分两个标签类**。

## 模块归属(为何进库)
工厂是「产 canonical `EngineSnapshot` 的通用数据生产设施」,复用 `physics`、对接 `core.schemas`
+ ingestion adapter,与现有 `ingestion/synthetic.py`(`SyntheticAdapter`)同域。它**不是**
某场景专属逻辑(EGT/振动/滑油逻辑留在 `scenarios/`),因此不违反 ADR-0007/0011
(那两条管的是场景逻辑不进库;新物理域的共享词缀扩展是协调式改动)。场景专属的「退化故事」
以**配置数据**形式存在,不是库代码。

## 诚实边界(继承 ADR-0010/0013)
- 系数是公开涡扇占位值、**非 LEAP OEM**;绝对 EGT 示意量级;**残差校准不变**——所以监控
  价值不受影响。
- 稳态循环模型只在持续功率段有效;地面慢车 EGT 用 `OAT + 温升` 下限钳位(只影响非巡航,
  巡航 EGT 远高于下限)。
- 全程 `source=synthetic`,不与真实数据混;标签只在 manifest;advisory-only。

## 验证
- `tests/test_synth_physics.py`:振动↗转速/不平衡、滑油温↗EGT、油压↗N2、泄漏↗消耗、退化↗EGT、
  全相位 EGT 落 DQ 区间。
- `tests/test_synth_factory.py`:产物齐全;QAR-CSV 经 `QarCsvAdapter` 回环(六相位全现 + 单位
  算术逆);ACARS-JSONL 经 `AcarsJsonAdapter` 回环;MRO-JSONL 经 `MroJsonAdapter` 回环且携带
  注入真相(退化机→removal、其余→borescope);manifest 真相标签正确;`(seed,config)` 复跑
  字节一致;snapshots.jsonl 可还原 `EngineSnapshot`。
- `tests/test_synth_gold_label.py`(P3):工厂快照 → EGT pipeline → Evidence → 合成 MRO finding
  → `findings_to_adjudications` → 断言注入真相(退化机=TRUE_FAULT,传感器漂移/混淆项/健康=NFF)。
- `tests/test_synth_cmapss.py`(P4):复现 C-MAPSS FD001 退化模型,断言退化机 EGT 残差上行斜率与
  健康机干净分离、轨迹末端高于始端——方法定性签名,不宣称等于 LEAP。

## 后果
- 好:合成数据从「线性占位」升级为「物理驱动、可注入、可溯源、产三种真实格式 + 接入 gold-label
  回路」的资产;`make synth` 一键重放;端到端压测真实数据接入(A1)落地后的路径;C-MAPSS 方法
  验证守护「方法没退化」。
- 代价:仍是占位校准(非 LEAP);MRO finding 是每引擎一条(shop visit 粒度),非逐航段。
- 仍是占位/deferred:按 ESN/时间拆分的训练/评估数据集产物(P5);真实 C-MAPSS 数据 ingest
  (格式适配器)与 OEM 校准。
