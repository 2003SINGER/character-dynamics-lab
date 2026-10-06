# 父代理独立验收｜第 1—3 步与剩余证据

日期：2026-10-07。结论：开发比较已独立复跑并逐项核对；正式状态保留 `READY_FOR_INDEPENDENT_REVIEW`，不自行 CLOSED。第 4 步仍缺玩家意义与具体机制缺口证据，完整 thread goal 不因此完成。

## 最终复跑

- 父代理重新运行旧 pilot **11/11**、最终 comparison **13/13** tests。
- 最终 runner SHA-256：`b3c16ebbdbd06cd937649e186682e9f124354e5b21e9a03662edf9b51db054f8`。
- 独立 fresh runs：`parent-final-comparison-20261007-02` 与 `parent-final-comparison-20261007-03`，项目内 `outputs/praxish_utility_comparison_v0/runs/`。除时间/run ID manifest 外，**31 个 artifacts 逐字节相同**；父代理重新计算七项输入/依赖哈希，与 manifest 一致。两次均为提交前的 worktree 执行。
- 12 cases / 32 tie seeds / 三个实际负控；仅两个已诊断取消差异，workspace 行为审计通过。最终 gate 会拒绝 raw cancel 后续回合的新错误；两侧同时删除关闭条件，即使 parity 通过，也被行为 contract 拒绝。
- `git diff --check`、workflow YAML 解析通过；repo health return 0，三个既有警告保留，未扩大清理范围。新增独立 Node CI job 会从 pin 下载原件，运行旧/新 tests 与 fresh comparison；CI artifact 只上传比较结果，不包含 source-cache。

执行提交：`df0c7ac46f97aa88e7787228d46d526804245387`。提交后 fresh run `parent-exact-head-df0c7ac-20261007-01` 成功，父代理用 `git show <revision>:<path>` 重新计算七项执行输入哈希，与 manifest 一致；结果与最终提交前 artifacts 相同。受保护 main 读回仍为 `e9ad2ebf329e8259b35f3ee0ef0492485d85c3ff`。

[该执行提交的 exact-head CI](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/37500083388) 已核验 `success`：`praxish-contract` 真正下载/验证 pin、运行旧/新 tests 与 fresh comparison；`regression` 的 Configure/Build/CTest/Reference verification/Repository health 全绿；`source-ranking-contract` 也 success。这是执行提交的证据，不自动证明以后文档或代码提交的 CI 状态。

复跑：`node 02_实验/Praxish_Utility_Comparison_v0/tools/compare.mjs run --run-id <fresh-id>`。每次使用新 ID；精确执行版本与输入 bytes 以 manifest 核对，不能用本地 tests 代替远端 exact-head CI。

## 已直接核对的证据

- 第 1 步：AIIDE 2023 attachment pin、原始三脚本运行、deterministic 原始日志、完整论文/源码机制审读沿用[原实验 owner](../Praxish_Activity_Pilot_v0/README.md)，本轮旧 pilot 的 11 条 tests 重新通过。Praxish 一步绝对后状态 utility 不是活动方法天然优于 utility 的证据。
- 第 2 步：共同全信息离散 turn 场景，有限工作 phase 与独立请求状态；两边事件在相同 turn 生效，角色顺序、候选效果、目标与 RNG 相同。它不是 ContinuousRuntime、局部观察或分钟级长动作实验。
- 第 3 步：父代理读完独立 native utility 与对照 runner、配置、case 输入和 tests；native 选择不调用 Praxish、不读取 Praxish 轨迹。两侧复用相同能力，并非模块化活动对手写角色专用 if/else。
- 父代理在 `/private/tmp` 调用绝对 runner 路径，fresh run `parent-final-comparison-20261007-01` 成功。相应 manifest 是旧 HEAD `7d4e46b` 上的 worktree 执行，精确文件哈希另记，不能冒称已提交的代码结果。
- 父代理另写一次性检查、**不调用评分 helper**：逐候选手算状态替换及目标分数，核对普通请求 Answer=11 / Finish=5，低优先级 Answer=2 / Finish=5，服务 multiplicity、12-case 状态和同义条件 workaround；全部通过。
- 父代理读取全部案例的 actions/issues 和九组配置差异。两个 workaround 的 native baseline 完全不变；闭合修复实际把 Finish 延迟到 turn 6。两个 raw cancel 的 parity false 保留，不将 `exit 0` 偷换成全部 parity 通过。
- 原件别名直接 VM 证据不加载观察器：`getAllPossibleActions(visitor)` 的两个 entry 对象相同；显式 Status 绑定后分开。不是 observer 改写原件而制造差异。
- 所有公开 timeline frame 只含 turn/actor/action；其中 11 对序列相同，唯一不同的是原件负取消权重 bug。完整因果数值证据在 typed trace，不靠解释性文案给人物加分。

## 公平性与结论边界

新增公共投影的父审：完整读取 exporter/template/tests，要求补全动作 target/actor 绑定校验，拒绝同 key 冲突状态，去掉由全局 roster 推断“在场”的文案。以已提交比较 run `parent-exact-head-df0c7ac-20261007-01` 为输入，投影 tests **7/7**，fresh bundle `outputs/praxish_utility_comparison_v0/presentation/parent-review-20261007-01/`，input/generator/template hashes 留在 manifest。12 组含目标与公共状态的轨迹仍为 **11 相同 / 1 上游 bug 分歧**，共 97 相同 / 7 不同回合对。

父代理另作不调用快照/动作归一化 helper 的 raw-fact/target 读回，**208 side-turns** 的工作状态、请求状态和目标一致。父代理在本机 in-app browser 通过仅监听 loopback 的临时 HTTP 服务真正打开，核对默认匿名、空动作、前后翻页、自动播放到末回合停止、场景切换、来源揭示/隐藏，以及窄窗口 A/B 堆叠与下滚可读。截图留在该 bundle 的 `browser-review.jpg`；服务和临时 tab 已关闭。应用不允许 `file:` 导航，所以直接双击离线文件未作该浏览器的实测；生成 HTML 无网络资源依赖。未把 DOM fake smoke 代替真实浏览器验收；没有真人偏好、成本或可置信性结果。viewer 是阶段 4 的证据呈现，不是阶段 4 完成。

传统 utility 本身可模块化。参考[Game AI Pro 原始章节](https://www.gameaipro.com/GameAIPro/GameAIPro_Chapter09_An_Introduction_to_Utility_Theory.pdf)的方法基座，此处 baseline 使用可复用角色绑定、前置条件、效果和目标因子；它不是该章节所有响应曲线、惯性或商业系统的复现。匹配的是 Praxish 当前一步 goal-based law，不能推广为击败/覆盖所有 utility、BT 或 GOAP。

世界关闭 hard constraint 是独立审计规则；raw 两侧违规仍执行并记录，不偷偷回滚成正确 trajectory。适配是内容前置条件，不是新增 runtime validator。

结果只支持[RESULTS](RESULTS.md)的窄结论：本场景未显出活动组织的行为优势；源实现 bug 不是机制优势。作者工时未知，未招募玩家、未确认测量效度，不将 trace 相同说成所有玩家体验都相同。

## 保护边界

旧 pilot runner SHA-256 `b4cb9ec07ff2c9f2e337389c70e7b644aa5a2cfb388717acd7482a3cf397b34e`；旧 scenario `d2bc5148d38341e701c7932745f24dd448ceb41219629d2139f21b335175f6f8`，均未变。

已有 dirty CMake SHA-256 `b13f01bdea84a4a34694406a063079ebba735b387090a3adfaf371f4d6212788`，未修改/暂存。本次只提交比较目录、CI 的独立 Node job 和相应入口/状态文档；Runtime、Dynamics、Theory-S、Paper-0、旧 NPC paired 文件与 `main` 不进入改动。
