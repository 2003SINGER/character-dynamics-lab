# 后置机制候选｜AU 考古

原始依据：[2026-09-06 WebGPT 原文](../90_原始材料/2026-09-06_WebGPT_AU机制考古与反事实Replay/原文.txt)。本页只保存候选，不把它们写成已实现机制或当前 Paper-0 主张。

## B1 Action Quality / Engagement

- 候选链：`O/S/commitment → quality/engagement/duration/interruption → action payload → W settlement`
- 价值：PowerWash、AGAIN、FarmQuest 等数据可能包含持续时间、投入、操作模式和完成度，不止 action type。
- 状态：保存，对应 Q06；只有数据证明 action type 不够时再重新评估。
- 当前禁止：不新增 quality/effort/duration 状态或自由参数。

## B2 主观误解转化为客观社会事实

- 候选链：`wrong/stale O_i → X_i/S_i → action_i → W changes → other agents observe`。
- 价值：未来多人版本的动态因果链，不压缩成普通 ToM 标签。
- 状态：保存，多人阶段再研究；Paper-0 不进入。
- 当前禁止：不接入单人 Forward loop。

## B3 Forward–Inverse 对偶

- Forward：latent/persistent state → behavior distribution。
- Inverse：revealed behavior → revise estimate of latent state。
- 状态：Paper-0 只做 Forward；inverse learner 后置。
- 当前禁止：不把角色真实改变与系统修正估计混为一谈。

## B4 P drift / personality plasticity

- 候选链：`long-term S/history → sparse P change`。
- 状态：当前 `P` frozen，后置保存。
- 当前禁止：不在 mechanism v1 引入 P 更新。

## B5 Multi-agent / relationship dynamics / second-order runtime

保留 `R_i[j]`、misconception、second-order knowledge 和 interaction consequences 的概念边界；当前不接入 Paper-0 mechanism loop，不扩展为运行时多人系统。

## B6 Action preparation / incubation

保存早期的 preparation/pending action tendency 想法；不与 `S/D` 混写，没有外部证据前不实现。

## B7 Specialized learned semantic model

若未来积累高质量 `raw O/ΔO → X` 数据，可评估专门语义模型；当前不做训练计划，不影响接口。

## 升格条件

以上候选只有在对应外部数据、明确 estimand、最小对照和可复核失败证据出现后，才能从“保存”进入新的设计决策；不得直接写入当前 TODO 主链。
