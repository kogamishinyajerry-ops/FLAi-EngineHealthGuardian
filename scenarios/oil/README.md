# 场景:滑油消耗 / 泄漏检测(第三个垂直切片)

第三个 PHM 场景,把 MVP 推到 3 场景,并**第三次压测「加场景不动库」**。这次刻意用一个**不同的特征形状**来更狠地压边界。

## 这次为什么不同(压测价值)
EGT/振动都是「单快照残差 vs 物理 baseline」(适配通用 `PeerGroup`)。滑油**消耗**是个**速率**(从油箱液位差分 `level[i-1]-level[i]` 得来),**不适配**逐快照的 `PeerGroup` —— 所以本场景自带「机队速率 peer」,而不是硬套通用件。这正是边界压测想暴露的差异。

## 数据(合成)
| ESN | 构型 | 设定 | 期望输出 |
|---|---|---|---|
| `ESN_OIL_HEALTHY` | OIL-A | 稳定低消耗 ~0.10 L/flight | **NOMINAL** |
| `ESN_OIL_LEAK` | OIL-A | 消耗率 ~0.06 L/flight² 上升 | **ADVISORY**(泄漏) |
| `ESN_OIL_LOWDATA` | OIL-B(独占) | 仅 4 个航班 | **ABSTAIN** |

油箱液位由累积消耗反推;管线再把速率算回来(数据形态的闭环)。

## 压测结论(见 ADR-0011)
- **唯一库改动**:`EngineSnapshot` 加了 3 个滑油字段(`oil_temp_c` / `oil_pressure_kpa` / `oil_level_l`)—— 新物理域需要**共享词缀扩展**,这是预期且合理的(不是边界违规)。
- **除此之外零库逻辑改动**:复用 `residual_trend` / `uncertainty` / `policy.gate` / `Evidence` / `run_agent` / `AuditLog`;特征工程 + 机队速率 peer 全在场景内。
- 边界成立的真义:**场景逻辑留在场景;共享词缀扩展是协调式改动**。

## 运行
```bash
make demo-oil                    # 单独跑
make dashboard                   # 三场景 tab 一起渲染
```

## 剩余摩擦(同前,非阻塞)
- 场景编排与 EGT/振动 pipeline 结构相似(可未来抽共享运行器)。

> 原先两处摩擦(agent FIM 表无 `OilLeak` → `FIM TBD`;DQ `_KEY_PARAMS` 偏 EGT)已在 ADR-0012 消除:FIM 改读 `provenance.manual_citations`,DQ `key_params` 按域可配置。滑油 pipeline 现传自己的 key_params。
