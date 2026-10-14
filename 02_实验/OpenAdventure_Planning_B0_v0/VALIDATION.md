# 父级核验记录

2026-10-14，代码实现与父级核验分工；均为AI开发核验，不代替人的独立审阅。

## 原生规则对照（评价运行前）

- 未读取上游 walkthrough。固定原版 YAML 词汇组映射到 travel 的 `verbs`，逐项核对 B0 `MOVE_ROWS` 中输入别名和目的地。
- 实际检查 **14房间、45移动行、174输入别名**，不合法的源边为 **0**。只检查已建模部分，不据此声称全部游戏建模完备。
- 条件另核：格栅前后需open，裂隙跨越需bridge；lamp/keys是HERE条件；桥切换互斥；安全灯光约束不是原版动作合法性的同义词。
- 初次核验脚本误以 YAML 枚举名而非上游 `buildtravel` 的词汇组匹配 travel verbs，错误拒绝了一批真实别名；在运行游戏评价前修正。不是游戏失败或 Planner失败，不用这次误报否定模型。
- 代码草稿中的域外目的地映成自环、HERE条件遗漏、桥双向效果同时可用，均在原生运行前按源规则修正；未把草稿当实验结果。

原生运行、单测与证据哈希由本目录 RESULTS 与各非覆盖 run 维护；不会用本页的静态审查替代运行结果。

## 首次开发运行与适配错误

- [首次D结果](development_first.json)：10任务输入、8次搜索，原生最终look/inventory通过独立判定。父级命令在程序完成后误将zsh只读变量`status`用于保存shell退出码，外层返回错误；游戏运行及JSON已经完成，stderr为空。后续包装改用任务专用变量，不把外层错误当规划失败，也不重写第一次记录。
- [首次反馈负控](development_feedback_first.json)：14任务输入，状态`MODEL_MISMATCH`；真正的`You have no keys!`后同时出现原生`Are you trying to get into the cave?`。控制器未认出这是回答窗口，后续look/inventory被原版以`Please answer the question.`拒绝。这是控制器输入模式遗漏，不是不可达证明。
- 两段首运行及源码hash均保留。只修已知hint输入处理，在评价E之前重跑开发/负控；不改动作效果、任务、seed或预算，不以修正后结果覆盖首个失败。
