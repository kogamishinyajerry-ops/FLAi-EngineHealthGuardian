# ADR 0012 — 消除残留摩擦:FIM 走 provenance + DQ key_params 可配置

- 状态:Accepted
- 日期:2026-08-12

## 背景
ADR-0007 / 0011 记录了两处非阻塞摩擦:
1. agent 的 FIM 表是 EGT 专属,非 EGT 场景(振动/滑油)返回 `FIM TBD`。
2. DQ `_KEY_PARAMS` 偏 EGT,非 EGT 场景的 completeness 被按 EGT 参数错算。

## 发现 + 决策

### 1. FIM 表是冗余且错误的 —— 删除,改读 provenance
每个场景**早就**把自己的 FIM 写进了 `Evidence.provenance.manual_citations`(EGT `FIM 72-00-00`、振动 `FIM 79-00-00`、滑油 `FIM 79-21-00`)。agent 里那张 `_FIM_TABLE` + `lookup_fim_task(hypothesis)` 是**重复且错误**的二次推导(还只认 EGT 的失效模式)。

- 删除 `_FIM_TABLE` / `lookup_fim_task`;agent `respond` 直接用 `"; ".join(ev.provenance.manual_citations) or "FIM TBD"`。
- FIM 接地回归到**证据自己的 provenance**(场景从授权资料设的),agent 只负责呈现,不重新推断。这更诚实,也天然支持任意场景。
- 效果:振动/滑油的 advisory 现在显示真实 FIM 引用,不再 `FIM TBD`。

### 2. DQ key_params 改为按域可配置
`assess(snapshot, *, min_completeness=0.6, key_params=_DEFAULT_KEY_PARAMS)`。
- 默认仍是 EGT 导向(向后兼容);振动/滑油 pipeline 各传自己的域参数集。
- completeness 不再被 EGT 参数错算。

## 后果
- 好:两处「优雅降级」变成「正确」;agent 更简单(少一张错表);DQ 按域诚实。
- 边界:`assess` 的签名扩展是库的合理通用化(不是场景逻辑泄漏)。
- 这两条摩擦从 ADR-0007/0011 的「已记录」变成「已消除」。
