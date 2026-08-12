# ADR 0007 — 场景即消费者边界(压测结论)

- 状态:Accepted
- 日期:2026-08-12

## 背景
报告的 MVP 要 3–5 个健康场景。架构声称「场景是平台的消费者,加场景不应改库」(`scenarios/` 只用 `src/ehm/` 的通用原语 + 自带特征工程)。需要真做一个第二场景来**压测**这个边界,而不是只靠架构图自证。

## 做法
构建第二个场景 `scenarios/vibration/`(振动异常趋势),刻意只从 `scenarios/` 写代码,看哪里被库卡住。

## 发现:三处「写着通用、实则绑死 EGT」的库耦合
压测立刻暴露了三处,各做一次最小通用化(一次性清理):

1. **`egt_residual_trend`** —— 逻辑本就参数无关(对任意残差序列算最小二乘斜率),只是名字带 egt、且 `detail` 硬编码了 `°C/flight` 单位。→ **改名 `residual_trend`,detail 改为与单位无关**(单位由调用方在 observation 文本里写)。
2. **`PeerGroup`** —— 原来 `from ehm.data_brain.features.egt import residual` 硬编码算 EGT 残差,根本不通用。→ **构造器接受 `residual_fn` 参数**,由调用方传入(EGT 传 EGT 残差,振动传振动残差)。

(单位泄漏是 #1 的一部分,单列为一条以示警惕。)

## 结论:边界成立
完成上述一次性清理后,**振动场景完全在 `scenarios/` 内完成,零进一步库改动**。干净复用的通用原语:

`EngineSnapshot` · `Evidence` · `dq.assess` · `PeerGroup`(已通用)· `residual_trend`(已通用)· `uncertainty.from_signals` · `policy.gate` · `AuditLog` · `run_agent` · 整个 `feedback`(labels/findings/mro)· `ontology.FAILURE_MODE` 命名空间。

场景自带(不进库):特征工程(振动残差 baseline)、失效模式词汇、编排逻辑、合成数据。

→ **加第 3、4 个场景预期接近零库改动**(可能只需再次警惕类似的「EGT 泄漏」)。

## 剩余摩擦(已记录,非阻塞)
- **agent FIM 表是 EGT 专属**:振动的 `BearingDegradation` 走 `lookup_fim_task` 返回 `FIM TBD`(优雅降级)。未来应让 failure-mode→FIM 映射可扩展/可配置。
- **DQ `_KEY_PARAMS` 偏 EGT**(oat/n1/n2/egt/fuel,不含 vibration):振动场景把这几个都填了以过 completeness。未来可让 key-params 按场景配置。
- **场景编排重复**:振动 pipeline 与 EGT pipeline 结构高度相似(~60 行)。若后续场景继续同构,再抽共享的「残差-趋势场景运行器」;现在刻意不抽,避免过早泛化。

## 后果
- 好:边界被真实场景验证而非架构图自证;三处隐性耦合被清掉,库现在是诚实地通用;`make demo-vib` 跑通同样的 NOMINAL/ADVISORY/ABSTAIN 三态,且与 EGT 共用同一 Evidence 脊柱 / 闸门 / gold-label 回路。
- 教训:凡命名或常量带具体参数(egt、°C)的「通用」代码,几乎一定是泄漏 —— 加场景压测是发现它们的最快方式。
