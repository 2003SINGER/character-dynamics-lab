# 用户对话｜Theory-S 结果边界与机制主线纠偏

- 来源：`C:\Users\2003SINGER\.codex\attachments\f0d4f18c-1e7b-4b4a-9c76-77193da731c3\pasted-text.txt`
- 来源修改时间：2026-09-07 20:26:29
- 归档副本：[原文](原文.txt)
- SHA-256：`B49C370CE8FEDAD3C5E03BE2DB79B454D613DB91FC2004CF4169026885FEF7CD`

## 归属与证据边界

该长段按项目规则保存为用户粘贴的 WebGPT 仓库复核/研究讨论原件；其中开头与中段的直接指令、纠正和边界是用户一手意见，后续展开部分是可供执行的复核提案。模型提出的心理学来源、机制解释和“可行/有价值”判断仍需逐篇核验，不能仅凭本原件写成已证实结论。

## 本次维护出的用户确认方向

1. Run1–4 目前只能叫 **development identifiability diagnostics**；`correct Theory-S ≈ zero` 不能推出 Theory-S 有效或无效，正式实验尚未开始。
2. Theory-S 不能继续以当前一维 EMA 探针冒充正式理论；正式 v1 需要先参考并核验心理学、计算情绪与游戏 AI 文献，再形成可证伪版本。
3. 先做机制 sandbox 的工程验收：固定 `W/O/P/A^O`，只干预 `S` 时，行为分布应出现预期且非微小变化；这证明的是 causal expressive capacity，不是现实数据上的 predictive validity。
4. 由 scene/object/affordance 独立生成合理合法的 `A^O`，再揭晓外部 `A*`；`A* ∉ A^O` 应记录为 support miss，不得为了覆盖 gold action 倒塞候选。
5. LIGHT 只承担它实际能支持的能力；建立 dataset→capability matrix，不强迫单一数据集覆盖完整 `W/O/X/S/P/A`。
6. 首阶段运行时关闭 LLM：由人工/离线 AI 形成版本化 compiled semantic rules，固定运行后再循环修改语义规则与显式动力学；冻结后才做 fixed-semantics / live-LLM / direct-LLM 替换比较。

## 尚未确认

- Theory-S v1 的具体字段、文献依据、更新函数、候选动作生成器和 sandbox 场景尚未拍板或实现。
- LIGHT 是否适合 persistent-S identification 尚未由独立准入和跨数据集比较确认。
- 文中提及的 EMA、MAMID、FAtiMA、Chain-of-Emotion 等来源及任何新颖性判断需要独立文献核验。
