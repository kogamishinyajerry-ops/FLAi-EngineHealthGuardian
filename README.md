# FLAi — Engine Health Guardian (EHM 智能体)

中国商飞「发动机健康管理（EHM）智能体」项目的工程实现仓。**当前状态：脚手架 v0（scaffold）** —— 只搭骨架 + 一个端到端可跑的垂直切片,验证「四脑 + Evidence 脊柱」架构,不包含任何真实数据接入或可上线能力。

> 本仓的顶层设计依据是一份独立战略研究报告(强参考,非圣经)。该报告出于敏感性**仅本地保留**(docs/strategy-report.md,已 gitignore,不纳入公开仓库)。对其的可执行性评估见 [`docs/exec-assessment.md`](docs/exec-assessment.md)。项目级真实约束源是 [`CODEBUDDY.md`](CODEBUDDY.md)。

## 这个项目是什么

不是「重新做一个 EHM 系统」,而是在 COMAC 现有「云诊/云析」数据底座之上,建设一个**发动机专项的、以本体和证据链为核心**的智能诊断/预测/决策支持层。核心立场:

- **「工程师副驾驶」,不是「自动维修放行官」** —— 前 18 个月 advisory-only,不自动改变放行/MEL/维修方案/适航状态。
- **LLM 只负责编排和解释,绝不自己计算发动机状态** —— 数值判断由 PHM 模型/规则/物理残差执行。
- **小数据路线**:本体 + 物理残差 + self-supervised + active learning,不和 GE/CFM 拼 fleet-scale 深度学习。

详见 `docs/architecture.md`。

## 技术栈(已锁)

Python 3.12 · uv · Pydantic v2 · Polars · DuckDB+Parquet · rdflib(单层本体) · LangGraph(agent 状态机) · OpenTelemetry · ruff/mypy/pytest。MVP 不上 Kafka/K8s。

## 快速开始

```bash
make install   # uv sync,创建 venv 并 editable 安装 ehm
make demo      # 跑 EGT-margin 垂直切片(合成数据,离线)
make demo-vib  # 跑第二个场景:振动异常趋势(验证「加场景不动库」)
make dashboard # 生成自包含 HTML 看板并在浏览器打开(三态/置信/溯源/混淆矩阵/precision)
make gold      # 跑 demo + 种子判定 + 反馈报告(gold-label 闭环演示)
make test      # pytest
make lint      # ruff
make type      # mypy (src/ehm)
```

`make demo` 会用合成数据端到端跑通:`ingest → DQ → EGT 残差特征 → peer 归一化 → 趋势规则 → 不确定性 → advisory 策略闸门 → Evidence → agent → 审计日志`,并打印三类输出(NOMINAL / ADVISORY / ABSTAIN)。

### Gold-label 闭环(工程师判定回路)

报告的头号资产:每个告警最终得到工程师结论,并反哺模型。Evidence 不可变,判定以 append-only `Adjudication` 事件记录(见 `docs/adr/0004-gold-label-loop.md`)。

```bash
uv run python -m scripts.adjudicate list                          # 列出待判定 Evidence
uv run python -m scripts.adjudicate apply <id> <outcome> [--finding ...]  # 记录判定
uv run python -m scripts.adjudicate import-mro <mro_jsonl>        # MRO findings 接成 actual_finding 真实标签
uv run python -m scripts.adjudicate report                         # 反馈统计(coverage / precision / confusion)
uv run python -m scripts.adjudicate seed-demo                      # 给 demo 写示例判定(非真实标签)
```

**真实标签供给**:`import-mro` 把拆换/孔探/NFF 等工单结果(MRO JSONL)转成带 `actual_finding` 的判定事件,经同一套 gold-label 机器产出 shop 确认的 precision/confusion(见 `docs/adr/0006-mro-findings-as-actual-finding.md`)。`make gold-mro` 一键演示。

`outcome` ∈ `true_fault | conditional_anomaly | operational | sensor_issue | nff | inconclusive`。

### 真实格式 ingestion(QAR-CSV / ACARS-JSON)

平台不再 synthetic-only:`QarCsvAdapter` / `AcarsJsonAdapter` 走现有 `IngestionAdapter` 协议,经 `ParameterMap`(源列名→canonical 字段 + 单位转换)确定性译码,相位由有状态 `PhaseTracker` 从高度/空速序列推出。加新航司/新源 = 新建一个 map,不改代码(见 `docs/adr/0005-real-format-ingestion.md`)。

```bash
uv run python -m scripts.inspect_ingestion qar     # 解码 QAR fixture
uv run python -m scripts.inspect_ingestion acars   # 解码 ACARS fixture
```

样例数据见 `tests/fixtures/`(提交进仓,自文档化格式 + 可复现)。真实数据准入落地后,换字典/换样本即可切换,代码不动。

### 可视化看板(任务控制台)

深色「任务控制台」式看板:**渐进式披露**(默认只露异常,正常折叠)、**残差波形 SVG**(波动直观传达是否在恶化)、4 维**置信雷达**、点击引擎出**详情抽屉**、以及一个动画**航线流水**视图(一个航班如何被消化成可审计 Evidence)。三视图:机队总览 / 航线流水 / 模型表现。

```bash
make dashboard   # 重生成 demo 数据 → 渲染 data/dashboard/index.html → 浏览器打开
```

EGT 跑过 `import-mro` 后,异常卡上会带 `MRO:true_fault` shop 真相标签。看板是库的**只读消费者**,绝不成为数据源(见 `docs/adr/0008`、`docs/adr/0009-dashboard-v2-mission-console.md`)。

## 目录结构

```
src/ehm/
  core/          共享内核:Canonical Data Model、Evidence 对象(脊柱)、telemetry、errors
  data_brain/    ingestion / quality / features / phm
  knowledge_brain/  本体(rdflib)+ 规则
  safety_brain/  uncertainty / advisory 策略闸门 / append-only 审计
  agent/         LangGraph 2-node 图(assess→respond),LLM 插入点 documented
  feedback/      gold-label 闭环:Adjudication 事件 / LabelStore / join / 反馈指标
scenarios/egt_margin/   首个垂直切片:EGT 裕度异常趋势(合成数据)
scenarios/vibration/    第二个垂直切片:振动异常趋势(压测「加场景不动库」)
scripts/run_egt_demo.py `make demo` 入口
scripts/adjudicate.py   gold-label 判定 CLI(list / apply / report / seed-demo)
scripts/inspect_ingestion.py  真实格式 fixture 解码演示(qar / acars)
tests/                    单元 + 切片测试
tests/fixtures/           真实格式样例(qar_sample.csv / acars_sample.jsonl)
docs/                     策略报告、评估、架构、ADR
```

## 范围边界(v0 显式不做)

真实 ACARS/QAR/MRO adapter、双层图数据库、Kafka/K8s、LLM 实调、ClickHouse、适航认证证据包。这些都在架构里留了接口/插入点,但不在 v0 实现 —— 详见 `docs/architecture.md` 的「显式 stub / deferred」清单。

## 约束

改动本仓前必读 [`CODEBUDDY.md`](CODEBUDDY.md)。
