# ADR 0010 — 物理气路模型(EGT baseline 升级)

- 状态:Accepted
- 日期:2026-08-12

## 背景
EGT baseline 原本是 `scenarios/egt_margin/features.py` 里拍脑袋的线性公式(`_BASE[phase] + 1.2*thrust - 1.5*oat`),系数无物理依据。需要换成「更讲道理」的物理模型。

## 诚实前提(重要)
LEAP-1C 的 OEM 设计数据(假设 A3)未取得,**不可能做到 LEAP 真值**。所以本模型不是「真实 LEAP 模型」,而是:
- **功能形式是真的热力气路**(进气总温→多变压缩→燃烧室 TIT→涡轮膨胀→EGT),系数是**公开涡扇级别的占位值**。
- 绝对 EGT 是示意量级;**但监控用的残差(observed − baseline)是校准不变的** —— 常数偏移在相减中抵消 —— 所以只要功能依赖正确,残差就准。这才是监控价值所在。

## 决策
- 新增 `ehm.data_brain.physics`(库资产,可复用):
  - `EngineDesign`(OPR/FPR/TIT/η_comp/η_turb 等,通用占位)+ `default_design()`
  - `OperatingPoint` / `GasPathPoint` / `Degradation`
  - `gas_path(design, op, degradation)` —— 计算各站位 T/P
  - `egt_healthy` / `egt_degraded` —— baseline 与退化态 EGT(K)
  - 相位→(mach, altitude) 近似表 + ISA 大气压
- EGT 场景 `features.baseline` 改为调用 `egt_healthy`(`baseline()`/`residual()` 接口不变)。
- **顺带修正一处历史不一致**:EGT 的特征工程原本在库 `data_brain/features/egt.py`,与 ADR-0007(场景自带特征、振动已在 `scenarios/vibration/features.py`)不一致。现迁到 `scenarios/egt_margin/features.py`,删除库里的 `egt.py`,`features/__init__` 只保留通用的 `PeerGroup`。pipeline / synthetic 改从场景本地 import。
- 换 baseline 后 EGT demo 仍出 NOMINAL/ADVISORY/ABSTAIN 三态(残差校准不变的实证)。

## 物理建模要点
- T2 = OAT·(1+ram)(进气总温)
- T3 = T2·OPR^((γ−1)/(γ·η_c))(多变压缩,η 低 → T3 高)
- T4 = TIT_design·(0.55+0.45·thrust)·(1+退化惩罚)·(T2/标准日)(推力/气温/退化驱动)
- T5(EGT)= T4·(1−η_t·(1−(P_amb/P3)^((γ_g−1)/γ_g)))(涡轮等熵-效率膨胀)
- **退化**:`thrust_penalty` 抬高同推力所需 T4 → EGT 升高(EGT 裕度损失的典型特征);`eta_comp_factor` 降低压气机效率 → T3 升高。

## 验证(定性物理,非绝对值)
测试只断言**方向性**:压缩升温(T3>T2)、涡轮降温(T5<T4)、EGT↗OAT、EGT↗推力、退化↗EGT、η_c↓→T3↑。换到新 baseline 后 EGT demo 仍出 NOMINAL/ADVISORY/ABSTAIN 三态(残差校准不变的实证)。

## 后果
- 好:baseline 有了物理依据和结构;OEM 系数将来直接替换 `EngineDesign` 即可,结构不动;退化有物理签名(为数字孪生/迁移学习铺路)。
- 代价:绝对值非 LEAP 真值(明确标注);简化模型省略了 BPR/多转子/冷却空气等细节;相位→mach/alt 是粗近似。
- 仍是占位的:真热力学 gas-path 模型、LEAP 校准、多转子分解、冷却空气修正 —— 待 OEM 数据或工程投入。
