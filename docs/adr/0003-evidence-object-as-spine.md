# ADR 0003 — Evidence 对象作为脊柱

- 状态:Accepted
- 日期:2026-08-12

## 背景
报告的核心要求:任何 safety-relevant 输出都必须能复现完整证据链
`raw → cleaned → feature → model/rule version → ontology entities → manual citation → confidence → recommendation → human response → finding`。
如果每种输出各自设计数据结构,长期会出现「不可追溯」的孤岛。

## 决策
- **所有输出统一为 `Evidence` 对象**(`core/evidence.py`),无论来自规则、模型还是 agent。
- `Provenance` 字段对应证据链每一段。
- `Confidence` 为四类独立维度(data/model/knowledge/applicability),`overall()` 取**最弱链**(木桶原则)。
- 新增显式 `status`:`NOMINAL` / `ADVISORY` / `ABSTAIN`,区分「没事 / 建议行动 / 不敢说转人工」。
- **`safety_brain.policy.gate` 是 advisory-only 唯一硬闸门**:任何 Evidence 离开管线前必须过 gate;低于门槛建 ABSTAIN 并清空 recommendation。

## 后果
- 好:审计、未来认证证据包、人工 adjudication 闭环都围绕同一结构;「拒答」被显式建模。
- 代价:简单统计告警也要包成 Evidence,略重。可接受 —— 一致性 > 简洁,尤其在安全关键领域。
- 与报告的差异:报告只讲「拒答」;v0 把状态拆成三态,避免 NOMINAL 被误当 ABSTAIN。
