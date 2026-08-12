# ADR 0004 — Gold-label loop(event-sourced adjudication)

- 状态:Accepted
- 日期:2026-08-12

## 背景
报告称 gold-label factory 是「最稀缺、最有价值的资产」:每个告警最终要得到工程师结论(真实故障 / 条件异常 / 操作因素 / 传感器问题 / NFF / 无法判断),并反哺模型/规则层。实现必须不打断 advisory-only 与 append-only 审计原则。

## 决策
- **Evidence 在审计日志里不可变**。人工判定作为 **append-only `Adjudication` 事件**,按 `Evidence.id` 关联(事件溯源),绝不回写已记录的 Evidence。
- **「有效判定」** = 同一 Evidence 上 `adjudicated_at` 最新的事件;`supersedes` 字段保留溯源。后到的拆检结果可细化早先的现场判断,且不抹除历史。
- **「标注后的 Evidence」** = audit × labels 的 join(`GoldLabel`)。训练 / 评估 / precision proxy 全部从这一视图派生,不直接读原始日志。
- outcome 词汇固定六类;`TRUE_FAULT` / `CONDITIONAL_ANOMALY` 计为「告警为真」;`INCONCLUSIVE` 不计入 precision 分母(既非对也非错)。
- `ehm.feedback` 仅依赖 `ehm.core`,是各脑的 peer,不构成反向依赖。

## 后果
- 好:审计完整性 100% 保留(契合报告 WORM / PROV-O 方向);重判有完整历史;标签可被机器消费,直接驱动 KPI(coverage、actionable-alert precision、系统状态 × 人工真相 confusion)。
- 代价:查「最新判定」需 replay/聚合;v0 数据量小无性能问题,量大时加物化视图(同本体的「属性图视图」一道 deferred)。
- 与 `Evidence.human_response` / `actual_finding` 的关系:那两个字段留给「可变 / 内存中」场景;在 append-only 模式下,人工输入由 `Adjudication` 承载,经 `GoldLabel` 暴露 —— 两者不冲突。
