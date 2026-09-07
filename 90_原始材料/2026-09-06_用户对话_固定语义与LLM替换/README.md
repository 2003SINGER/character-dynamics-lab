# 用户对话｜固定语义与 LLM 替换

- 来源：`C:\Users\2003SINGER\.codex\attachments\acc7a67b-1a45-46d5-88e9-c3e7156fc425\pasted-text.txt`
- 来源修改时间：2026-09-06 12:11:07
- 归档副本：[原文](原文.txt)
- SHA-256：`B875C9BE8FA0FD6C5A67FAF8A2EA40720444FD8AB38B6AF8E6A34CE16A4C60D5`

用户确认的执行顺序：先用人工/离线 AI 形成版本化 compiled semantic rules，运行时关闭 LLM；在多数据集 dev 循环中同时修语义规则与显式动力学；冻结后再将 fixed semantic frontend 替换为 live LLM，并与 fixed semantics、LLM-direct/no-dynamics 进行对照。规则不得按单条真人动作或未来信息打补丁。
