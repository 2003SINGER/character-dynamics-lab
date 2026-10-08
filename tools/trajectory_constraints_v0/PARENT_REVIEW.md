# 父代理验收｜Typed Trajectory Contracts V0

日期：2026-10-08。交付状态：`READY_FOR_INDEPENDENT_REVIEW`。这是父代理对 Luna 所写参考实现的审阅及执行记录，不是独立人类验收，不是作者轨迹 Pilot 已运行。

系统设计 owner：[AuthorialTrajectoryPilotV0](../../00_研究设计/AuthorialTrajectoryPilotV0.md)。原算法和项目语义的区别见[正式定义核读](../../01_文献/语义核读_轨迹约束与在线监测_2026-10-08.md)。

## 1. 实际执行证据

父代理在稳定 checkpoint 执行 stdlib unittest：**27/27 PASS**。`acceptance_manifest.json` 引用的 test ID 必须真实存在；两份存储的 JSON golden 会反序列化并求值，不只是检查文件存在。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B \
  -m unittest discover -s tools/trajectory_constraints_v0/tests -v
```

另外独立构造七次求值/拒绝检查，不复用测试方法：

| 输入 | 期待与实得 |
|---|---|
| now=0，F holding 的窗口 [5,10] | PENDING，不是历史缺证据 |
| 连续 x 只有 x(0)=x(2)=0，要求窗内 x≥1/2 | INDETERMINATE，不能从端点判无见证 |
| 精确 x=t，窗口 (0,1]，要求存在 x≤0 | VIOLATED，不使用被排除的 t=0 |
| holding(0)=true，G_[0,10]，没有完整变化流声明 | INDETERMINATE，不假定保持 |
| 同一输入显式 seal_values_through(ref,10) | SATISFIED，依赖该完整性输入承诺 |
| holding(0)=true，实体在 t=1 删除，检查 AT@0 | SATISFIED，tombstone 不重写过去 |
| belief_revision 事件缺少注册要求的 actor 参数 | 拒绝输入，不算一次已发生事件 |

## 2. 原文八类准入反例落点

| 要求 | 可执行位置 |
|---|---|
| 未注册 trust 不得执行 | `test_admission_rejections_unknown_owner_types_units_enum_pin_time_interpolation` |
| 错误 belief 不得冒充 factive knows | `test_projectors_are_pure_and_fact_bound` |
| 未到截止的目标不能误判失败 | `test_eventually_pending_then_inclusive_deadline_witness_and_open_endpoint` |
| 唯一钥匙毁坏的可达性与时序违背分开 | `test_dispatch_runs_only_typed_pure_projector_and_monitor_stays_separate_from_reachability`；不实现 planner |
| 端点安全但内段越界必须抓到 | `test_polynomial_interior_extremum_and_generic_bounds_uncertainty` |
| 版本变化需要显式迁移、重放准入 | `test_explicit_migration_replay_gate`；回调不是生产重放证据 |
| 同窗硬冲突给局部证明，未知不冒充兼容 | `test_conflict_proof_is_narrow_and_eventuals_are_not_mistaken_for_always` |
| stable ID 删除不绑定同名新人/物品 | `test_stable_deleted_identity_is_indeterminate_unless_exists_false_registered` |

其余 coverage、event payload、三值组合、seal、加权均值、编辑器、枚举序列、时间平移和 split invariance 对照见 manifest 与测试源码。测试数量不等于独立心理学证据。

## 3. 审查导致的实质修正

首次“全绿”后，反例发现并修正：未来窗口被算历史缺失；只有端点的连续存在目标被误判；开端点零根被拿来当见证；删除对象重写过去；有界事件计数未验完整流；稀疏 step 值没有完整性声明仍被保持；实际 event payload 未验 schema；AT 非单点、包络单位、变量 band 冲突证明过宽。修复均进入可重跑测试，不靠测试总 PASS 掩盖数据流缺口。

## 4. 必须保留的非声称

- 仅 Registry、closed AST、synthetic finite-trace monitor、editor compilation 和纯 projector dispatch；没有 Director、搜索器、NPC、生产 C++ adapter 或新实验。
- points/segments/seals 是合成证据抽象的受信输入。数学及 coverage 校验不证明生产者的多项式来自真实 Dynamics；生产接入另验 oracle/commit 路径。
- 完整性 seal 是生产者承诺，不是自动证据发现；支持模式之外拒绝，不偷偷降级端点判断。
- 连续 Boolean 任意求根、全 PDDL3/STL、全局 satisfiability 均未实现。兼容性无窄证明时返回 UNKNOWN。
- `MonitorSession` checkpoint 只有 monitor bookkeeping，不能当完整 World/scheduler/RNG/cassette fork。
- 合成 quest phase 只验证枚举契约，不提供信任/关系动力学。ACTOR_S 值须 model pin；原始数值不是人类心理量表。
- 未修改 Runtime、Dynamics、coefficients、S/P/action schema 或原有 paired 实验。仓库已有的外来 CMake/paired 工作不纳入本提交。

正式下一步是人工审核设计及作者语义，再决定 E0 domain/executor/fork 与预算；这次不自动开跑。
