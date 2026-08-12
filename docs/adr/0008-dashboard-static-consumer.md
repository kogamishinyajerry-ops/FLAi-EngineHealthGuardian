# ADR 0008 — 看板:静态、自包含、库的只读消费者

- 状态:Accepted
- 日期:2026-08-12

## 背景
需要一个直观好看的 UI 看板,把 Evidence 脊柱、三态、置信度、溯源链、gold-label 指标可视化。有三种走法:静态 HTML / 本地实时服务(FastAPI)/ Streamlit。

## 决策
**Python 生成自包含静态 HTML**(`src/ehm/dashboard/` + `scripts/build_dashboard.py` + `make dashboard`)。理由:

- 当前数据是**批处理/合成**,没有「实时」可言 → live server 是空的,徒增常驻进程 + FastAPI 依赖。
- 项目铁律 lean / 离线 / Python-first / 不加重依赖 → Streamlit 重且长相通用,做不到「极其好看」。
- 手写 HTML/CSS 才能完全控外观,做出真正精致的看板;且可复现、CI 友好、零部署。

## 设计
- `dashboard` 是 `ehm.core` + `ehm.feedback` 的**叶子消费者**:读 audit + label store,进程内复用 `build_gold_labels`/`compute` 算指标,渲染 HTML。**不新增反向依赖**,不持久化任何新真相。
- **自包含**:CSS + 原生 JS 全部内联,无外部 CDN/字体/框架 → 离线可开,测试断言「不含 http(s) 外链」。
- 原生 JS 只做三件事:场景 tab 切换、状态过滤、`<details>` 溯源展开(其实 details 原生就够)。
- 数据可视化用**置信度条 + 混淆热力网格**(逐点残差趋势未持久化,折线图 deferred)。

## 约束(写进 CODEBUDDY)
- **看板永远只读**:它只是 Evidence/指标的视图,**绝不能成为数据源或真相源**。任何「在 UI 里编辑数据」的需求都要回流到库 + 持久化层,而不是看板自己存。
- 看板不引入新的运行时依赖。

## 后果
- 好:架构价值「被看见」而非埋在 JSON;零部署、离线、可复现;复用库的指标计算,看板与 CLI/报告口径一致。
- 代价:静态快照(改数据要 `make dashboard` 重生成);无逐点趋势图(待残差持久化)。
