# ADR 0002 — 技术栈选型

- 状态:Accepted
- 日期:2026-08-12

## 背景
报告的技术栈表是「菜单」(Kafka/Pulsar、ClickHouse/Timescale、Neo4j/JanusGraph、MLflow/Kubeflow 并列)。真实项目必须锁定一套。

## 决策
| 维度 | 选型 | 理由 |
|---|---|---|
| 语言/版本 | Python 3.12 | PHM/ML 生态;团队小,单语言降低复杂度 |
| 依赖/环境 | uv | 快、单一工具;src layout 单包 `ehm` |
| schema | Pydantic v2 | 运行时校验 + mypy 友好;Evidence 对象就是 Pydantic model |
| 数据处理 | Polars | 比 pandas 快、内存友好、lazy |
| 列存 | DuckDB + Parquet | **零基础设施**,MVP 合成数据足够;经 storage 接口抽象,日后可换 ClickHouse |
| 本体 | rdflib(单层) | Python 原生、无 JVM;双层图 deferred |
| agent | LangGraph | 状态机式编排,契合「LLM 只编排」;工具 allow-list |
| 可观测 | OpenTelemetry | 从 day1 打 span,避免事后补 |
| 质量 | ruff + mypy(strict) + pytest + pre-commit | |

**不上**:Kafka(用文件/JSONL)、K8s(MVP 不需要编排)。

## 后果
- 好:零基础设施即可跑 demo;每个可换点都有接口;CI 轻。
- 风险:langgraph/rdflib 类型 stub 不全 → mypy `ignore_missing_imports`(已配)。LangGraph API 演进快 → agent 层尽量薄、只依赖稳定原语(StateGraph/add_node/add_edge/invoke)。
