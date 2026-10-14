# LLM-Admission v0：Luna真实调用与语义绑定

工作批次2026-10-14，基准webgpt-sync@90ee524；实际UTC时刻以运行记录为准。
只做一次极简准入、E/G各一次正式语义推理，0格式重试，最多一次依据合格E绑定的原版执行。完成停止，不做B1逐步行动排名、模型比较、换模型或第二游戏。

## 信息和模型边界

1. 从冻结domain直接导出全部14房间、初始先验、326操作实例及来源，按同一前提/效果合并输入别名；反向展开必须逐实例等同B0。完整shared_rules及manifest留存；给模型的压缩说明须逐项核对同等规则，不带GOALS、搜索计划、历史结果或walkthrough。
2. 新原版会话只收集启动n、seed20261014与当前START文字；这两条实际观察不称模型决策或任务成功。隐藏NPC位置/随机游标等未知。静态初值不是实时全知状态。
3. 模型为当前可选gpt-6-luna，fork_turns=none，新子Agent分别做准入/E/G；不继承主控对话。reasoning不强改，实际值读取turn_context；每个正式子Agent只有一条实验用户请求，无followup修正。
4. spawn接口没有禁用工具/替换系统指令参数；要求不使用工具，并核查完整子Agent调用记录。不能据无工具调用推断没有工具权限。所有有效记录仍为AGENT_CONFOUNDED/Luna-in-Codex。执行模型标识以本地runtime turn_context为证，后端权重、不可见系统指令不伪称可知。
5. 若真实模型标识不可核或非Luna，停止；若调用了工具(本协议完全禁用实验工具使用)，按INVALID_LEAKAGE保守拒绝，不将该候选投入游戏。保留证据，不修改系统提示绕过限制。

## 两次固定请求与独立判据

- E作者原话：“让探险者建立裂隙晶桥，安全抵达西岸，最后仍持有钥匙与点亮的灯，并且整个过程中不能死亡。”
- G作者原话：“让海盗因为过去受到探险者帮助而逐渐产生持续信任，并使这种信任真正影响之后的互动。”
- 输出单个oa-author-binding-v0 JSON；goal.required/forbidden为已注册原子数组，trajectory_obligations、bindings及其来源、assumptions、residual_obligations、missing_capabilities分开。不要求输出命令解答，禁止额外文件/搜索工具。
- E验收原位置、桥、keys、lamp、亮灯与no_death_ever六义务；检查器持有答案但不发给模型。遗漏/额外硬条件/未注册原子/硬残留拒绝；不人工补全。no_death_ever不伪造为静态dead谓词，由冻结原生账本判据核验。
- 合格模型原子直接构造Goal交给冻结UCS，不按E选择人工GOALS。E仅作为独立证据判定器的选择标签。控制器只加最薄external_goal参数，原默认分支、domain/UCS/observe/verify及历史证据不改。
- G不是按ID回预存答案：模型真实分析规则目录；主控定性逐项审阅生产、归因、更新、消费者与证据范围。不能把有限模型缺字段当全游戏绝对不存在；新增机制只候选，不执行、不修改游戏。

保存实际完整请求、原样最终输出、runtime来源、工具调用、可得token事件及不可观测项；不公开完整原会话、凭证或自动注入的私有指令。研究结果只支持探索性Agent系统/接口绑定，不能主张纯模型优势、泛化或完整Character Dynamics完成。
