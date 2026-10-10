# Native Platform P5 — Author Bundle

状态：**READY_FOR_INDEPENDENT_REVIEW**，未 CLOSED。本页定义本阶段范围与复现入口；实际运行结论只维护在 [RESULTS](RESULTS.md)，公开证据入口见其 reviewer summary / manifest。代码/API 说明见 [P5 core README](../../tools/native_platform_v0/p5/README.md)。

## 固定开发范围

在既有 Evennia 场景与 Ensemble 原生人物行为上，两个 NPC 在同一个真实 W 中运行并共享可竞争的物品资源；加载受限 JSON Author Bundle，通过复用 TypedIR 的事件计数/顺序与有限状态条件评估约束，并枚举有限作者世界机会。当前仅有两个可授权机会：开放 main 或 side passage；最多一次，物理成本预算上限为 2。规划输出是依赖、下界和条件性候选，不是完整 DM，也不保证 NPC 会执行任务、相遇或回应。

开发矩阵位于 [`bundles/dev-matrix-v1.json`](bundles/dev-matrix-v1.json)，引用同目录版本化作者包。场景覆盖 main/side 路线、原生社交回应的接受/拒绝、director-off、玩家短暂取得并归还共享物品、未来 bundle 编辑与 stale-version CAS、越权机会拒绝、零预算和截止冲突。该矩阵定义固定运行配置；实际结果见 [RESULTS](RESULTS.md)，配置本身不是证据。

## 组件复用与新增边界

| 能力 | 复用 / 本项目新增 | 边界 |
|---|---|---|
| NPC 原生任务规划 | GTPyhop HTN | 每个 NPC 的既有任务计划；不是 P5 新规划算法 |
| 社交选择/回应 | 原生 Ensemble | NPC 可拒绝；作者包不能强制回应 |
| 约束表达与判定 | 现有 trajectory TypedIR；P5 注册有限事件/状态 evaluator | 未注册语义为 gap/unknown，不执行任意作者代码 |
| 作者机会候选 | P5 小型有限 AND/OR 条件枚举、NO_OP 与预算/截止诊断 | 项目 glue；预测条件性，不承诺未来状态 |
| storylet | 作者包中的分支说明文本 | content-only，不是可执行剧情或世界效果 |
| bundle 编辑 | 稳定 ID、版本 CAS 与未来要求检查 | 编辑计划/身份，不代表持久目标进度；旧判定保留 |

## 运行与停止条件

真实场景运行需要本地初始化的 Evennia DB、项目 venv、fresh loopback 服务进程（quota 上限 16；固定 12 场矩阵需 12 个空余配额）；公共 checkout 不自带该本机环境。若当前进程已消耗配额，使用既有 [stop_loopback](../../tools/native_platform_v0/evennia/stop_loopback.sh) / [start_loopback](../../tools/native_platform_v0/evennia/start_loopback.sh) 在同一实例重启；不删除场景/DB，也不另建服务器。只跑 Python 单测不会启动服务器。固定矩阵命令和审计解释见 [core README](../../tools/native_platform_v0/p5/README.md) 与 [RESULTS](RESULTS.md)。MCP reset/step/get_trace 的 1 分钟控制链 smoke 已验证；完整 12 场矩阵使用同认证 RPC runner，并非 MCP stdio 场景套件。旧阶段回归与审阅材料已收口；当前为 `READY_FOR_INDEPENDENT_REVIEW`，不自动开启 P5 后续阶段。此阶段不是生产就绪、玩家/心理效度或新颖性结论。
