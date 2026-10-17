# A-Closure 静态审阅记录

审阅范围：冻结的诊断补丁和请求 harness；未编译、未启动游戏、未运行 native server。此记录不构成原生运行或 NPC 行为 PASS。

## 冻结输入

- Veloren official GitLab source: `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248`
- Native patch SHA-256: `19caffe6962c6b5e094fd1344c2b84b8eb5a737943a8d0ac865d9c0b39708cf8`
- Harness SHA-256: `6a0f07a3934baf6899030deb305aec4e3063087477f0e172a62da93bd1f9416b`

## 有界结论

- NPC small-talk 的 `random_bool(0.2)` 仍在原短路分支位置调用一次；外部请求诊断记录该次实际结果，不额外抽样。无 request ID 的原生路径仍调同一 native talk helper。
- 路由诊断匹配活动 lease 且只报告一次。Say provenance 仅由显式 request ID、匹配目标及当前 action index 建立；队列过滤后按保留动作重建索引，server 只将该位置的 Say ID 传入 Agent 队列。普通 Say 不按相同 NPC/目标推断关联。
- 当前 native patch 的 `simulate_npcs` 保留动作过滤条件和遍历顺序；添加的 filtered 事件只对有显式外部 ID 的 Say 记录。Agent 分支保留原有 `allowed_to_speak`、utterance、chat 和控制动作顺序，遥测跟在既有原生处理之后。
- Harness 候选资格按实际 ECS 三维坐标、Loaded/alive/SPEAK、样本新鲜度及 5 秒连续资格核验；偏好既定 UID 对，不合格时对目录候选按实时距离和 UID 回退排序。server catalog 的 XY 粗筛不是最终 3D 资格判定。
- 请求输入受空前缀及逐次前缀校验、一次 cancel 负控、最多六次正向提交、单次追加不重试、单次正向 80 秒无终态即停止、每次正向后的 20 秒原生活动观察约束。helper 的汇总布尔不是独立验收结论。

## 验收边界

本静态审阅未发现上述限定范围内需修改代码的阻断项，可进入冻结后的 build/test 与原生证据阶段。真实请求资格、每个 ID 的事件归因、Agent 结果、取消负控、观测预算完整性和 post-run native continuation，仍须根据被冻结的原始输入、JSONL、stdout/stderr逐项验收；不得从静态代码、脚本测试或汇总字段推断 A = PASS。
