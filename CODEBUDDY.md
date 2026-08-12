# CODEBUDDY.md — FLAi Engine Health Guardian 项目规则

> 这是本项目的**真实约束源**(全局 `~/AGENTS.md` 指定:每个项目的 `CODEBUDDY.md` 才是真实约束)。改本仓前必读。破坏性操作(rm/force-push/删配置)前必须确认,其余按本文件。

## 0. 项目立场(不可动摇)

- **「工程师副驾驶」,不是「自动维修放行官」**。前 18 个月所有输出 **advisory-only**,不自动改变放行 / MEL / 维修方案 / 适航状态。
- **LLM 只编排和解释,绝不计算发动机状态**。数值判断由 PHM 模型 / 规则 / 物理残差 / 确定性程序执行。LLM 不解析二进制 QAR、不自己算 EGT margin、不创造维修阈值。
- **小数据路线**:本体 + 物理残差 + self-supervised + active learning。不追求和 OEM 拼 fleet-scale 监督学习。
- **Evidence 对象是脊柱**。任何告警/建议/标签都必须是带完整 provenance 的 Evidence,否则不许离开管线。`safety_brain.policy.gate` 是 advisory-only 的唯一硬闸门。
- **ABSTAIN 是一等结果**。置信度/适用性不足时拒答转人工,比强行给概率更安全。

## 1. 技术栈(已锁,改前先开 ADR)

- Python 3.12;uv 管依赖;单包 `ehm`(src layout,**不做多包 monorepo**)
- Pydantic v2(所有 schema/Evidence)、Polars(数据)、DuckDB+Parquet(列存,经 storage 接口抽象,日后可换 ClickHouse)
- rdflib(**单层**本体;报告里的「双层图(OWL 权威 + 属性图视图)」deferred,等场景证明需要再做)
- LangGraph(agent 状态机)、OpenTelemetry(从 day1 打 span)
- ruff(lint+format)、mypy(strict,覆盖 src/ehm)、pytest、pre-commit
- MVP **不上 Kafka/K8s**;ingestion 走文件/JSONL + 适配器协议

新增运行时依赖需在 PR/commit 里说明理由。

## 2. 模块边界

```
core          共享内核(schemas/evidence/telemetry/errors)。不依赖其他脑。
data_brain    ingestion→quality→features→phm。依赖 core。
knowledge_brain  本体 + 规则。依赖 core。
safety_brain  uncertainty/policy/audit。依赖 core。
agent         LangGraph 编排。依赖 core + 各脑的只读结果(Evidence)。
```

- **不允许反向依赖**(各脑不依赖 agent;core 不依赖任何脑)。
- 跨脑通信走 **Evidence 对象 / 明确的 dataclass 结果**,不直接互调内部。
- 场景代码(`scenarios/`)是平台能力的**消费者**,不把场景逻辑塞进 `ehm` 包。

## 3. 数据与正确性

- **不在没有真实数据时卡死工程**:ingestion 走 `IngestionAdapter` 协议 + 合成适配器,让管线在数据准入(假设 A1/A2/A3)落地前就能验证。
- **译码/数值计算永远确定性**,不交给 LLM。
- **配置与版本化从 day1 强制**:规则、模型、本体、资料引用都要带 version;`EngineSnapshot.config_tag` 支撑「时间化构型」(某航段当时的构型/SB 状态必须可重建)。
- **训练/测试按时间、ESN、航司隔离**(禁止同发动机相邻航段随机 split)。本仓尚未进入建模阶段,但任何未来数据集构造必须遵守。
- 误报治理以 **false-alert budget** 为硬 KPI;稀有故障报 **precision-recall / event-level**,不报 ROC-AUC;RUL 同时报 **interval coverage**,不只 RMSE。

## 4. 测试与可复现

- 所有合成数据**带 seed**,测试/demo 必须可复现。
- 任何新管线步骤都要有最小单测;场景改动加切片测试。
- `make test` / `make lint` / `make type` 必须全绿才能合入。

## 5. 合规与安全(任何阶段都适用)

- 数据原则上**境内存储/训练/推理**;跨境、海外模型/云访问按数据域逐项审批,不在架构层默认开放。
- 用真实运营数据前必须确认 owner / purpose / 授权 / 保留策略。
- 不引用未获授权或失效版本的维修资料(AMM/FIM/TSM/SB/ICA)。
- 不用生成式 AI 虚构真实故障标签。

## 6. 提交约定

- commit message 用中文或英文均可,但要写清「做了什么/为什么」。
- 多步任务收尾时简述 做了/没做/风险/下一步/产物路径。
- 破坏性操作(rm/force-push/删配置/改锁定选型)前必须人工确认。
