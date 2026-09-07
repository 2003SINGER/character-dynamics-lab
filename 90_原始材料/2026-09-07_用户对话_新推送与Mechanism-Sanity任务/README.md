# 用户对话｜新推送核对与 Mechanism Sanity v1 任务

- 来源：`C:\Users\2003SINGER\.codex\attachments\dd729fb0-58fb-497b-8b87-cd683e82059a\pasted-text.txt`
- 来源修改时间：2026-09-07 20:37:47
- 归档副本：[原文](原文.txt)
- SHA-256：`57C2D5BA71512D288DE154FCDCDF1579ACB7CDBDA2E74C03B74FB7B347D1C69E`

## 阅读与归属

该文件包含一次先误读、后纠正的仓库复核对话。最终有效指令是：不要把旧 `intents-research` 课题嫁接进当前项目；Terra 继续保持 strict-v2 数据准入不变；由 Codex/Luna 在当前 `character-dynamics` 仓库执行受控的 `Mechanism Sanity v1`。

## 执行边界

- 先检查并复用现有机制、SceneSnapshot、affordance、Replay 与 C++ 参考实现，不另起平行架构。
- Theory-S v1 需有现有文献依据、字段职责、各字段 dynamics 及 `S → π(A)` coupling；当前一维 confirmed-effect EMA 只保留为历史 probe。
- `dataset → SceneSnapshot → objects/agents/possessions/known facts → affordances → generated A^O`；候选生成绝不读取当步 `A*`。
- 从外部数据选 3–5 个信息充分、候选有竞争的 sandbox fixture；若 LIGHT 不适合 persistent-S，记录不适合，不硬造。
- 只做 S-intervention engineering sanity，不启动新的正式 NLL/Experiment B，不根据 Run1–4 追调 Theory-S。
- 验收后提交并推送到 `webgpt-sync`；汇报改动、Theory-S、S 是否明显影响行为、候选是否独立于 A*、场景适配性和下一步。
