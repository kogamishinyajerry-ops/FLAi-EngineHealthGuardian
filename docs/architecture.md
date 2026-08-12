# 架构(v0)

本文件描述当前脚手架的实际实现,以及对报告建议的**取舍**。报告是强参考(独立战略研究报告,出于敏感性仅本地保留、不纳入公开仓库),不是逐字蓝图 —— 偏离处都在下面写明理由。

## 顶层原则(来自报告,严格对齐)

1. **advisory-only** —— 不自动改变放行/MEL/维修方案/适航状态。
2. **LLM 只编排与解释**,不算发动机状态。
3. **小数据路线** —— 本体 + 物理残差 + self-supervised + active learning。
4. **Evidence 对象是脊柱** —— 每条输出都带完整 provenance,可从建议追溯到原始参数/航段/算法/规则/资料版本/人员确认。
5. **ABSTAIN 是一等结果** —— 置信度/适用性不足时拒答转人工。

## 四脑架构

```
                         ┌───────────────┐
  ACARS/QAR/MRO/... ──►  │  data_brain   │  ingest→DQ→features→phm
                         └──────┬────────┘
                                │ (Evidence 候选)
   AMM/FIM/SB/本体  ──►  ┌──────┴────────┐
                         │ knowledge_brain│  本体 + 规则
                         └──────┬────────┘
                                │
                         ┌──────┴────────┐
                         │  safety_brain  │  uncertainty → advisory 策略闸门 → audit
                         └──────┬────────┘
                                │ (Evidence,已 gate)
                         ┌──────┴────────┐
                         │     agent     │  LangGraph(assess→respond),工具 allow-list
                         └──────┬────────┘
                                ▼
                   MCC/工程师工作台 + MRO/企业系统
```

- **不允许反向依赖**。各脑只产出 Evidence/dataclass 结果;agent 是消费者。
- 跨脑通信一律走 **Evidence 对象**,不互调内部函数。

## 模块映射

| 报告概念 | 本仓落点 | 状态 |
|---|---|---|
| 数据接入(ACARS/QAR/MRO) | `data_brain.ingestion`(`IngestionAdapter` 协议) | 协议 + 合成适配器;真实 adapter deferred |
| 数据质量 | `data_brain.quality.checks` | 基础 completeness/range;OEM 限值 deferred |
| 特征/工况归一化 | `data_brain.features.egt` / `peer` | EGT 残差 + peer z;真热力学模型 deferred |
| 异常检测/PHM | `data_brain.phm.anomaly` | 趋势规则;ensemble/ML/数字孪生 deferred |
| 发动机本体 | `knowledge_brain.ontology`(rdflib 单层) | 命名空间 + 核心类/关系 v0 |
| 规则/因果 | `knowledge_brain.rules` | 失效模式词汇 + version;FMEA/fault tree deferred |
| 不确定性 | `safety_brain.uncertainty` | 四类置信度 + peer 惩罚 |
| 权限/安全策略 | `safety_brain.policy` | **advisory-only 硬闸门** |
| 审计/证据链 | `safety_brain.audit` | append-only JSONL;WORM/PROV-O deferred |
| Agent | `agent.graph`(LangGraph) | 2-node 图;LLM 插入点 documented |
| Canonical Data Model | `core.schemas` | `EngineSnapshot` v0 |
| Evidence 脊柱 | `core.evidence` | v0,含 NOMINAL/ADVISORY/ABSTAIN 状态 |

## 关键数据结构

### Evidence 对象(`core/evidence.py`)
直接落地报告要求的链:
```
raw → cleaned → feature → model/rule version → ontology entities
    → manual citation → confidence → recommendation → human response → finding
```
- `Provenance`:每一段引用都留 ref/version
- `Confidence`:四类独立维度 `data / model / knowledge / applicability`,`overall()` 取**最弱链**
- `status`:`NOMINAL`(分析完无事)/ `ADVISORY`(建议,advisory-only)/ `ABSTAIN`(置信不足转人工)

### Canonical Data Model(`core/schemas.py`)
`EngineSnapshot(esn, flight_id, phase, timestamp, oat_c, n1_pct, n2_pct, egt_c, fuel_flow_kg_h, thrust_ref_pct, vibration_ips, config_tag)`。
单位用 QUDT-aware 字段名/注释(v0 不绑定完整 QUDT 本体)。`config_tag` 支撑「时间化构型」。

## 对报告的取舍(偏离处)

1. **单层图,不做双层**:报告建议「OWL/RDF 权威 + 属性图视图」双层。v0 只用 rdflib 单层。理由:避免「完美本体」陷阱(报告自己也警告了「漂亮 Dashboard」风险)。等第一个场景证明查询性能需要时,再加属性图作为物化视图。→ ADR 待补。
2. **垂直切片优先于水平分层**:v0 用 EGT-margin 一个场景端到端打通(合成数据),而不是先把四脑全铺开。架构被真实切片验证,而非被架构图验证。
3. **具体选型先锁**:报告技术栈表是菜单;v0 锁定一套(Python-first / DuckDB+Parquet / rdflib / LangGraph),可换处都做了接口抽象。
4. **Evidence 加显式 `status` 字段**:报告只讲「拒答」。v0 区分 NOMINAL/ADVISORY/ABSTAIN,避免把「没事」和「不敢说」混为一谈。

## 显式 stub / deferred 清单(v0 不做)

- 真实 ACARS/QAR/MRO adapter(只有协议 + 合成适配器)
- 双层图数据库(单层 rdflib)
- Kafka / K8s(文件/JSONL ingestion)
- LLM 实调(agent `respond` 默认确定性格式化,离线可跑;LLM 插入点 documented)
- ClickHouse(DuckDB+Parquet;storage 接口抽象)
- OEM 工程限值、真热力学 gas-path 模型、FMEA/fault tree、ensemble ML、数字孪生
- 适航认证证据包、WORM 不可篡改存储、PROV-O 正式绑定
- 跨航司联邦/匿名 benchmark

每项都留了**接口或插入点**,在对应模块 docstring 里标明。

## 验证策略(v0)

- `make demo`:合成数据端到端跑通,产出含 Evidence(含完整 provenance + 至少一条 ABSTAIN)的审计 JSONL。
- `make test`:单元(Evidence/Confidence/策略闸门/Canonical Model)+ 切片(EGT 三类输出齐全)。
- 合入门槛:`make lint`、`make type`、`make test` 全绿。

未来的离线→在线验证流程(历史回放 → 时间/ESN 隔离测试 → 工程师盲评 → shadow mode → stepped-wedge)在进入真实数据阶段后再落地,数据结构现在就按那个方向建。
