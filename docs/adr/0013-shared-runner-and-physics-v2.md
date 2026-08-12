# ADR 0013 — 共享场景运行器 + 物理模型 v2(双转子/BPR/冷却空气)

- 状态:Accepted
- 日期:2026-08-12

## A. 共享残差-趋势运行器
EGT 与振动 pipeline 有 ~60 行近乎逐行重复的编排(ingest→DQ→peer→逐 ESN 残差序列→趋势→uncertainty→policy→Evidence→audit)。抽取 `scenarios/_runner.py`:

- `ResidualTrendConfig`(声明式:residual_fn、signal label/unit、阈值、失效模式、FIM、key_params、model_score_fn)+ `run_residual_trend_scenario(...)`。
- EGT/振动 pipeline 收缩成「配置 + 薄 `run`」(~20 行)。
- **放在 `scenarios/` 而非库**:这是场景编排,不是库原语(库保持原语-only,见 ADR-0007/0011)。
- 滑油(速率型)结构不同,保持 bespoke —— 不过度泛化;若第 4 个速率场景出现再抽 rate-runner。

## B. 物理模型 v2(双转子 + BPR + 冷却空气)
单转子草图升级为**双转子涡扇**:压缩链 fan→LPC→HPC(T13/T25/T3),BPR 驱动风扇功,冷却空气引气混合进涡轮。

- 多转子:HPC 在 HP 转子(HPT 驱动),fan+LPC 在 LP 转子(LPT 驱动);HPC_PR = OPR/(FPR·LPC_PR)。
- BPR:风扇功 = BPR·cp·(T13−T2),进入 LPT 功平衡。
- 冷却空气:引气 ε 在 T3 混入热燃气 → T4_mix = (1−ε)T4 + ε·T3 → EGT 降低。
- EGT(T5)由**功平衡**算(T45 = T4_mix − HPC 功;T5 = T45 − 风扇+LPC 功),而非旧的单 P 比。

新增定性测试:压缩链递进升温(T2<T13<T25<T3)、冷却空气↘EGT、BPR↗↘EGT;原有方向(↗OAT、↗推力、退化↗、η_c↓→T3↑)全部保留。

## 诚实声明(同 ADR-0010)
系数仍是公开涡扇占位值、**非 LEAP OEM**;绝对 EGT 示意量级;**残差校准不变**所以监控价值不受影响。v2 让功能形式更物理(冷却/BPR/多转子各有可测效应),为 OEM 校准留了更细的结构接口。

## 后果
- 好:EGT/振动重复消除(-~80 行),加场景成本下降;物理模型更讲道理、可测效应更多。
- 代价:物理模型复杂度上升(更多假设,更多潜在误差面);仍是占位校准。
- 仍是占位:LEAP 校准、变几何、真实引气分配、N1/N2 修正转速驱动(现仍用 thrust_frac)。
