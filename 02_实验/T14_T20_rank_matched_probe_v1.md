# T14/T20：raw-feature conditional probe v1

这是 v0 rank-matched 设计的参数化升级候选，不是正式 test 结果。v0 文档保留为设计历史。

## Policy

使用 [compiled_semantics_v1.json](T0c_LIGHT/compiled_semantics_v1.json) 与 [replay_features_v1.py](Replay/replay_features_v1.py) 生成有序 raw feature vector：

```text
[goal_progress, stimulation, recovery, hunger_relief, bathroom_relief,
 short_term_reward, environment_control, context_relevance, has_target,
 target_in_scene, target_visible_in_O, target_in_inventory, repeated_acquire]
```

前 7 个语义字段只表达 binary topology；`context_relevance` 保持冻结的 lexical-overlap 连续值；scene 字段是独立 boolean。没有 `scene_bias`、预加权 heuristic、全局 intercept 或可学习 temperature（固定 `T=1`）。

```text
z(t,a) = theta^T f(t,a) + S_t * w^T f(t,a)
pi(a) = softmax(z(t,a))
```

唯一 learnable parameters 是 `{theta,w}`。训练器位于 Python `Replay/replay_probe_v1.py`，使用 conditional multinomial NLL + 不惩罚 intercept 的 L2（本模型无 intercept）、L-BFGS、零向量初始化、`max_iter=1000`、`gtol=1e-8`；`seed=20260907` 只用于 split/permutation（优化器本身 deterministic）。lambda 网格 `{1e-4,1e-3,1e-2,1e-1,1}`，只由 train/validation 选择。train-only means/std（零方差 std=1）与 weights 一起写入 model/manifest。

## Fair comparison

Theory-S、Activity-S、ActionSupport-S 使用同一 1D EMA、`eta=0.35`、transition compiler、历史权限、feature version、split、lambda 规则和 probe family。当前 LIGHT 140-step slice 只能做 dev/synthetic smoke；正式实验必须 trajectory/episode-disjoint train/validation/test，并审计 persona grouping。

分别报告：retrained-no-S；训练好的 Theory probe 在 test 置零 `S`；同一 probe 在 test 替换同 horizon 的 trajectory-permuted `S`。后两者不重新训练，分别检验 state consumption 与正确历史归属。

## Frozen boundaries

梯度不得进入 ReplayRecord/source candidate support、W→O/SceneSnapshot、transition compiler、expected-effect templates、X 定义、三种 `x_t` 定义或 gold reveal/evaluation boundary。RoomDemo 的 hand-designed policy 不改；本 v1 只服务 external/replay research path。

## Acceptance

先跑 synthetic regression：A* 改写不改变 pre-reveal feature/S/logit；feature 不含 `scene_bias`；scene flags 不改 semantic tags；三种 state 的 EMA 形式相同；所有 candidate logit 加同一常数时概率不变；zeroed/permuted 只改输入 S，不改 model weights；v0 artifact 不覆盖。未通过独立行为真值准入前，不启动正式 test。
