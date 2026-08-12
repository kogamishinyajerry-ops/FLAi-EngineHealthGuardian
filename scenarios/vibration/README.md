# 场景:振动异常趋势(第二个垂直切片)

这是 v0 的**第二个 PHM 场景**,主要目的不是预报精度,而是**压测「加场景不动库」**的架构边界 —— 证明在 `scenarios/` 加一个新场景,只需自带特征工程,复用库里的通用原语,不改 `src/ehm/`。结论见 `docs/adr/0007-scenario-as-consumer-boundary.md`。

## 压测发现了两处库耦合(已通用化)

加这个场景时发现库里有两处「名字/实现写着通用、实则绑死 EGT」的地方,各做了一次最小通用化:

1. `egt_residual_trend` —— 逻辑本就参数无关(对任意残差序列算斜率),只是名字带 egt。**改名 `residual_trend`**。
2. `PeerGroup` —— 原本 `from ehm.data_brain.features.egt import residual` 硬编码算 EGT 残差。**改为接受 `residual_fn` 参数**,由调用方传入(EGT 传 EGT 残差,振动传振动残差)。

通用化之后,本场景**零库改动**即完成(除上面这两次一次性清理)。

## 数据(合成)

与 EGT 切片同构(便于对比),信号换成振动(ips),baseline 按转速(N1/N2)算:

| ESN | 构型 | 设定 | 期望输出 |
|---|---|---|---|
| `ESN_VIB_HEALTHY` | LEAP1C-VIB-A | 振动 = baseline + 噪声 | **NOMINAL** |
| `ESN_VIB_DEGRADE` | LEAP1C-VIB-A | 残差以 ~0.08 ips/航班 上升 | **ADVISORY** |
| `ESN_VIB_LOWDATA` | LEAP1C-VIB-B(独占) | 仅 4 个航班,小 cohort | **ABSTAIN** |

## 管线(`pipeline.run`)

```
ingest → DQ → 振动残差(对 N1/N2 归一化) → peer(通用 PeerGroup,residual_fn=振动残差)
  → residual_trend(通用规则,小阈值 0.05 ips/flight) → uncertainty → policy.gate
  → Evidence → agent → audit
```

与 EGT 共用 `Evidence` 脊柱、`policy.gate` advisory 闸门、`AuditLog`、`run_agent`、以及整个 gold-label/feedback/MRO 回路 —— 跨场景的判定与标签机制天然兼容。

## 运行

```bash
make demo-vib   # = uv run python -m scripts.run_vibration_demo
```

## 已记录的剩余摩擦(非阻塞)

- **agent FIM 表是 EGT 专属**:振动的 `BearingDegradation` 走 `lookup_fim_task` 返回 `FIM TBD`(优雅降级,不报错)。未来应让 failure-mode→FIM 映射可扩展/可配置。
- **DQ `_KEY_PARAMS` 偏 EGT**:completeness 按 (oat,n1,n2,egt,fuel) 计,不含 vibration;振动场景把这几个参数都填了以通过。未来可让 key-params 按场景配置。
- **场景编排有重复**:本 pipeline 与 EGT pipeline 结构高度相似(~60 行)。若第 3、4 个场景继续同构,可抽出共享的「残差-趋势场景运行器」(目前刻意不抽,避免过早泛化)。
