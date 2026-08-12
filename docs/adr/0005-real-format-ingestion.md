# ADR 0005 — 真实格式 ingestion(ParameterMap + 确定性译码)

- 状态:Accepted
- 日期:2026-08-12

## 背景
v0 只有合成适配器,平台无法证明能吃真实格式。需要为 QAR / ACARS 这类导出加适配器,且要为「多航司、多源、字段名/单位各异」留出扩展位,同时严守「译码绝不交给 LLM」。

## 决策
- **新增 `QarCsvAdapter`(QAR 导出 CSV,逐行时间序列)和 `AcarsJsonAdapter`(ACARS 报文 JSONL,一消息一快照)**,都实现现有 `IngestionAdapter` 协议 —— 各脑仍只依赖 `EngineSnapshot`,不感知来源。
- **`ParameterMap` 是参数字典的雏形**:源列名/字段名 → canonical 属性 + 源单位。加新航司/新源 = 新建一个 map(配置),不改代码。
- **确定性单位转换**(`mapping.convert`):K/°F→°C、psi/hPa/bar→kPa、lb/h→kg/h 等;未知单位**直接报错**,绝不静默错单位(报告反复警告的 °C/K、psi/kPa、lb/h/kg/h 类错误)。`ParameterMap.validate()` 还会校验「from_unit 的目标单位 == 该属性 canonical 单位」,在配置阶段就拦住错配。
- **译码用 stdlib(`csv`/`json`)逐行做**;Polars 留给批量特征/分析路径,不用于逐行 model 构造。LLM 在译码链路里没有任何角色。
- **相位识别补一个有状态 `PhaseTracker`**(从高度/空速序列推 ground→takeoff→climb→cruise→descent→approach→ground),把 scaffold 里 deferred 的「真实 QAR 需相位检测」往前推一步。阈值是占位启发式,非 OEM 值。
- 时间戳缺 tz 时按 UTC 处理(QAR 惯例),满足 DQ 的 tz 校验。

## 后果
- 好:平台不再 synthetic-only;真实数据准入(A1)落地后,把 map 换成真实字典、把 fixture 换成真实样本即可切换,代码不动。fixture 提交进仓,格式自文档化、测试可复现。
- 代价:`PhaseTracker` 阈值是占位,真实相位边界需 OEM/工程校准;`ParameterMap.validate` 只覆盖已知 canonical 单位的属性,新参数要补 `_CANONICAL_UNIT` 表项。
- 仍是 stub 的:真实 OEM 参数字典/ICD、ACARS 报文版本协商、流式(实时)ACARS 接入(MVP 走文件/JSONL)。
