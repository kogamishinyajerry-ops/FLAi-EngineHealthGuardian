# ADR 0006 — MRO findings 作为 actual_finding 来源

- 状态:Accepted
- 日期:2026-08-12

## 背景
gold-label 闭环(ADR-0004)有了人工判定,但缺**真实物理 ground truth** 的供给口。报告要求把「拆换 / 孔探 / NFF / 修理 disposition」这类 MRO 工单结果接成标签来源,让 `actual_finding` 有真实依据,而非仅靠工程师主观判定。

## 决策
- **MRO finding 是标签侧数据**(不是发动机观测),放在 `ehm.feedback`,**不**放进 `data_brain.ingestion`,也不实现 `IngestionAdapter`(那个协议产出 `EngineSnapshot`)。
- **`MroFinding`** 模型记录结构化字段:`esn / finding_date / finding_type / finding_text / disposition / component / source`;`MroJsonAdapter` 读 JSONL。真实部署若列名不同,加一个字段 map(类比 `ParameterMap`,此处 deferred)。
- **复用 ADR-0004 的事件溯源**:每个 finding 经 `findings_to_adjudications` 转成一条带 `actual_finding` 的 `Adjudication`,进同一个 `LabelStore`,走同一个 `GoldLabel` join 与 metrics。**不**新建 FindingStore/join。
- **finding → outcome 用结构化启发式**(`derive_outcome`,由 `finding_type`/`disposition` 驱动,不做文本挖掘):REMOVAL/REPAIR→TRUE_FAULT;NFF/RTV→NFF;BORESCOPE 按 disposition 判真假;TEST/SHOP_VISIT→INCONCLUSIVE。
- **匹配规则**:finding 附到同 ESN、`finding_date` 当天或之前、**最新且优先非 NOMINAL** 的 Evidence(即「还开着的告警」);无匹配前置 Evidence 的 finding 为 orphan,跳过。
- **Evidence 新增 `timestamp`(事件时间)**字段。时间匹配必须用事件发生时间,**不能**用 `provenance.generated_at`(那是管线运行时刻,会把所有 finding 误判成 orphan)。pipeline 用该 ESN 最新快照时间填 `timestamp`。

## 后果
- 好:`actual_finding` 现在有真实 shop 依据;precision proxy / confusion 能反映物理真相,不只是主观判定;整套机器消费链路复用,零新存储。
- 代价:finding→outcome 是有损启发式(物理真相 vs 判定类别本就非一一对应);MroFinding 的富元数据(component/ATA/disposition)目前只进 `human_response` 文本,未做结构化分析(未来若需要再加 FindingStore)。
- 边界:`Evidence.subject` 必须遵循 `ehm:ESN:<esn>` 约定才能被 finding 匹配(`evidence_esn` 解析)。
