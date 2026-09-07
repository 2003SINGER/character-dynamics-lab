# LIGHT Run 2：frozen-base incremental probe

## 运行边界

- Development diagnostic only；未更换数据集、split、feature、S、eta、appraisal 或 semantic rules。
- `theta_0` 直接读取 Run 1 的 `retrained_no_s.model.json`；`means`、`scales` 也直接读取该模型。
- 每个 condition 只拟合 `w`；每个 condition 独立选择 lambda。
- replay 使用 Run 1 manifest 指定的 `light_mechanism_dev.replay.jsonl`，SHA 与 Run 1 完全一致。
- trajectory split：`5079 / 1088 / 1089`；每个 condition `24999` rows；intervention paired rows `3771`。

## Invariant checks

- zero-`w` 与 Run 1 no-S：dev holdout NLL `2.1546767058575305`，绝对差 `0`。
- zero-`w` 逐行概率最大绝对差：`0`（tolerance `1e-12`）。
- 所有 condition 的 `zeroed-S − base-no-S`（paired subset）：`0`。
- `theta_0`、normalization 均未重新拟合；artifact manifest 标记 `theta_fitted=false`、`normalization_fitted=false`、`learnable_parameters=["w"]`。

## Primary result

主比较使用同一 paired intervention subset 的 base NLL 与 correct-S NLL；全 dev holdout base NLL 另列为参照。

| condition | selected λ | base NLL (paired) | correct NLL | incremental gain | incremental bits | permuted − correct |
|---|---:|---:|---:|---:|---:|---:|
| Activity-S | `0.0001` | `2.154765066` | `2.152338373` | `+0.002426693` | `+0.003500978` | `+0.000834690` |
| ActionSupport-S | `0.0001` | `2.154765066` | `2.154706592` | `+0.000058474` | `+0.000084361` | `−0.001065189` |
| Theory-S | `0.001` | `2.154765066` | `2.154749709` | `+0.000015357` | `+0.000022156` | `+0.004105825` |

全 dev holdout 的 Run 1 no-S base NLL 为 `2.154676706`。三个 condition 的 correct NLL 都只在 paired subset 上报告，以保证增量比较同样本。

## Ranking metrics and coverage

| condition | top-1 | MRR | mean rank | state mean | state std | nonzero fraction | ‖w‖₂ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Activity-S | `0.207902` | `0.404841` | `5.114558` | `0.407629` | `0.329172` | `0.683457` | `0.236416` |
| ActionSupport-S | `0.207372` | `0.403928` | `5.161496` | `0.235186` | `0.251918` | `0.551432` | `0.263095` |
| Theory-S | `0.208433` | `0.404582` | `5.177937` | `0.048535` | `0.112104` | `0.199629` | `0.567374` |

Candidate-count stratified NLL (`2 / 3 / 4 / 5+`)：

- Activity-S: `0.679730 / 1.043119 / 1.337968 / 2.323096`
- ActionSupport-S: `0.679336 / 1.034898 / 1.332710 / 2.326706`
- Theory-S: `0.678314 / 1.037129 / 1.335171 / 2.326479`

## Optimizer diagnostics

All conditions used L-BFGS-B, zero initialization, max 1000 iterations, `gtol=1e-8`, and converged successfully.

| condition | iterations | nfev | njev | final gradient norm | final data NLL |
|---|---:|---:|---:|---:|---:|
| Activity-S | `29` | `31` | `31` | `2.806e-6` | `2.184125263` |
| ActionSupport-S | `20` | `23` | `23` | `1.548e-5` | `2.186049466` |
| Theory-S | `11` | `13` | `13` | `8.519e-7` | `2.185308745` |

Top five absolute `w` entries (numeric description only):

- Activity-S: `repeated_acquire −0.148394`; `target_in_inventory +0.099124`; `environment_control −0.086920`; `stimulation +0.083968`; `target_visible_in_O −0.073662`.
- ActionSupport-S: `repeated_acquire −0.155095`; `target_visible_in_O −0.131746`; `target_in_inventory +0.099551`; `context_relevance +0.082427`; `recovery +0.050046`.
- Theory-S: `target_visible_in_O +0.404464`; `stimulation −0.234723`; `environment_control +0.215733`; `target_in_scene +0.175546`; `recovery +0.080262`.

## 当前读法

在共同 frozen base 上，Activity-S 是唯一显示出清楚的正向增量（约 `0.00243` NLL）；ActionSupport-S 与 Theory-S 的正向增量都接近零。Theory-S 仍显示明显的错误历史敏感性（permuted − correct `+0.00411`），但正确 Theory-S 尚未形成有实质量级的净增量收益。以上仍是 development evidence，不触发机制修改。

结果 artifact：`outputs/experiments/T14_T20_LIGHT_frozen_base_run2_20260907/`。
