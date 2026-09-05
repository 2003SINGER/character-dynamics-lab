# T0b｜SOTOPIA 外部轨迹可行性 pilot

目的：导出一个小、可追溯的 SOTOPIA-π episode 切片，验证它是否实际包含 Replay 所需的 actor、回合顺序、动作、私有/公开信息和 provenance。它不是 baseline，也不是关于人物心理的实验。

`export_slice.py` 只读已经由本地 Redis Stack 加载的官方 RDB。导出记录必须保留：原始 dump 的 SHA-256、dataset license、Redis key、以及 `unknown_within_dump` provenance；不得把来源未知的 agent 轨迹改写成人类行为。

原始 dump、Redis runtime 与导出的 JSONL 放在被 Git 忽略的 `outputs/sotopia_t0b_*/`。只有导出器和本说明纳入版本控制。

通过条件：30 条均有两名 actor、顺序 messages、非空 action trace、可取 agent/environment profile；并能从每名 actor 的 initial context 读出“自身目标可见、对方目标 unknown”的信息边界。

失败条件：若 episode-level generator provenance 无法恢复，或无法在不泄露对方私有目标/未来消息的前提下冻结输入 schema，则该数据只能作为工程格式参考，不能进入 T14–T17。

## 2026-09-05 结果

结果是**结构通过、研究数据准入未通过**。

- 官方 `cmu-lti/sotopia-pi` dump 成功取得并校验；原始 SOTOPIA dump URL 当日返回 404。
- 从 32,663 个 `EpisodeLog` 中按 Redis key 的 SHA-256 稳定排序抽出 30 条；导出到 `outputs/sotopia_t0b_2026-09-05/slice/`，其中有 25 个 agent profile、26 个 environment profile。
- 30/30 条均有两名 actor、顺序化 messages、至少一条非 idle actor 行动；30/30 条的初始 prompt 显式呈现自身目标、将另一角色的目标写为 `Unknown`。这证明 SOTOPIA 的 episode 格式可承载 `O` 的信息边界。
- 但 episode log 没有记录每条轨迹究竟来自 human、expert policy 还是 self-play，故 provenance 必须保持 `unknown_within_dump`。
- 491 个 actor action surface 中，279 条是 `did nothing`、187 条是 `said`、17 条 `left the conversation`，仅 8 条是零散自由文本行动/非言语行为。直接压缩为这些标签会丢掉对话决策语义；保留原句则不再是当前离散 `A^O` / NLL 协议。

因此这个切片可以作为**外部合成轨迹的 O/trace 格式测试资产**，不能直接启动 T14–T17。下一步必须先决定：另找带有限行为本体且有来源记录的数据、建立并审计独立的 dialogue-act 标注协议，或将首篇研究暂时限为小房间受控 intervention fixture。
