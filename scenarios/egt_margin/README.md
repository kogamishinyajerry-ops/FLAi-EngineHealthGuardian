# 场景:EGT 裕度异常趋势(首个垂直切片)

这是 v0 脚手架用来**端到端验证架构**的垂直切片,全程使用合成数据、离线可跑。它不追求预报精度,只验证「四脑 + Evidence 脊柱」能否真正组合起来产出可审计的结论。

## 数据(合成)

`synthetic.generate(seed)` 造一个小机队,刻意覆盖三种 Evidence 分支:

| ESN | 构型 | 设定 | 期望输出 |
|---|---|---|---|
| `ESN_HEALTHY_01` | LEAP1C-A | EGT = healthy baseline + 噪声 | **NOMINAL** |
| `ESN_DEGRADE_02` | LEAP1C-A | EGT 残差以 ~2.5 °C/航班 上升 | **ADVISORY** |
| `ESN_LOWDATA_03` | LEAP1C-B(独占) | 只有 4 个航班,小 cohort | **ABSTAIN** |

不带真实 LEAP-1C 数值;幅度仅作示意;带 seed,可复现。

## 管线(`pipeline.run`)

```
ingest(SyntheticAdapter) → DQ 门控 → EGT 残差特征(对 OAT/thrust 归一化)
  → peer((phase,config) 归一化) → 趋势规则(滑动窗最小二乘斜率)
  → uncertainty(四类置信) → policy.gate(advisory-only 硬闸门)
  → Evidence(含完整 provenance) → agent(LangGraph 格式化) → audit(JSONL)
```

关键设计点:

- **EGT 残差** = `observed EGT − physics_baseline(phase, thrust, oat)`。baseline 是占位线性模型(真热力学模型 deferred),接口稳定。
- **ABSTAIN 触发**:`ESN_LOWDATA_03` 同构型 cohort 只有自身 4 个样本 → peer_size<5 → Knowledge/Applicability 置信被惩罚 → overall 低于门槛建 ABSTAIN,清空 recommendation。比强行给概率安全。
- **Evidence 三态**:NOMINAL(分析完无事)/ ADVISORY(建议,advisory-only)/ ABSTAIN(置信不足转人工),避免把「没事」和「不敢说」混为一谈。

## 运行

```bash
make demo   # = uv run python -m scripts.run_egt_demo
```

输出每台发动机一行 `[NOMINAL/ADVISORY/ABSTAIN]` 消息,并把 3 条 Evidence 写入 `data/audit/egt_demo.jsonl`。

## 这个切片证明了什么 / 不证明什么

- ✅ 四脑能围绕 Evidence 脊柱组合,produce 带完整 provenance、可区分三态的结论。
- ✅ advisory-only 闸门、ABSTAIN、peer 归一化、趋势规则都在最小闭环里跑通。
- ❌ **不**证明任何真实发动机诊断能力 —— 物理模型、阈值、peer 全是占位/合成。真实数据接入和验证流程(历史回放→隔离测试→工程师盲评→shadow)在后续阶段落地。
