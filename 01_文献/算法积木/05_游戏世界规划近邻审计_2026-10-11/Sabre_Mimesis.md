# 传统强近邻：Sabre 的人物解释搜索与 Mimesis 的执行中介

阅读日期：2026-10-11。主代理全文审读；未运行或复现。以下严格分开 2021 Sabre 与 2003 Mimesis，不以新版本代码倒推旧论文。两篇均读完整正文、算法/实例、评测或结论与参考文献，视觉核对 Sabre PDF p.6 Algorithm 1 与 Mimesis PDF p.4 §3.3。

## 来源与可核位置

| 原件 | 版本 / 公开入口 | 本地 PDF（Git ignored；不公开再分发） / SHA-256 |
|---|---|---|
| Ware & Siler, **Sabre: A Narrative Planner Supporting Intention and Deep Theory of Mind** | AIIDE 2021, pp.99–106，8页；[作者 PDF](https://cs.engr.uky.edu/~sgware/reading/papers/ware2021sabre.pdf)；[正式记录](https://doi.org/10.1609/aiide.v17i1.18896) | `90_原始材料/_private/2026-10-11_规划近邻原件/Sabre/ware2021sabre.pdf`；`0bc3e2179ad08f5ad4cd377d15b1de39764214f36fd9d82fc64e23eb2bace6c5` |
| Riedl, C.J. Saretto & R. Michael Young, **Managing Interaction Between Users and Agents in a Multi-agent Storytelling Environment** | AAMAS 2003，作者 PDF 9页（末两页空白）；[作者 PDF](https://sites.cc.gatech.edu/fac/riedl/pubs/riedl-young-aamas03.pdf) | `90_原始材料/_private/2026-10-11_规划近邻原件/Mimesis/riedl-young-aamas03.pdf`；`85ad393a66064814e358400724929b5df3c917b2d26d597fed4a98491b1d1de9` |

原文提取与本地原件同目录。原件相对路径是本机证据定位，不是公开仓库下载链接。旧卡[01](../01_叙事修复与导演.md)与[02](../02_人物意图与约束规划.md)仍维护其他版本/方法；本卡只增强这两篇在当前问题下的机制证据。

## 结论先行

- **论文证据**：传统方法早已把作者目标、人物解释、非人物世界规则、用户干扰与真实引擎执行纳入研究；不能把这些模块的存在当本项目创新。
- **项目决定**：Sabre 是统一作者/人物符号规划的强对手；Mimesis 是因果威胁检测与执行后改未来的机制对手，二者不是可以不经适配就组合运行的一个软件。
- **未验证**：二者在我们的原生游戏、权限、时间与在线修复预算下的性能；尚无本项目比较结果。

## 1. Sabre：不是“给 NPC 排任务”，而是带解释义务的集中式世界搜索

### 1.1 输入与可改变对象（论文证据，pp.100–102）

作者提供有限实体、nominal/numeric fluents、初态、角色错误信念、各角色与作者 utility，以及两类事件：

1. **action**：`PRE / EFF / CON / OBS`。`CON` 指需要解释为何同意该动作的角色，不是所有受影响者；被攻击者无需同意。`OBS(a,c)` 定义谁能观察，观察者才获得相应信念更新。
2. **trigger**：前提满足便自动发生的确定性世界规则，无 consenting character；动作推进离散时间，trigger 本身即时发生。多个 trigger 的效果必须由域作者避免顺序依赖；它不是连续天气/物理积分器。

信念可任意深嵌套，但角色必须确定地相信某个值，不表示概率/未知集合。未显式写错的初始信念默认与真实值一致；这是该域的建模选择，不能无条件搬进本项目的局部观察权限。

`RES` 由显式效果与 `OBS` 推导的信念效果组成；预处理只展开所有可能被前提/utility 查询到的有限相关结果。状态按事件历史保存，查询 fluent 时追溯最近修改；这不等于原生游戏已提交历史的事务接口。

### 1.2 怎样让每一个动作“有理由”（论文证据，pp.103–104）

令 `β(c,s)` 是角色 c 所相信的状态，`α(actions,s)` 是动作及自动触发规则的结果。动作 a 的解释不是一段 LLM 理由，而是一个存在性证据：

- 在 `β(c,s)` 中存在以 a 开头的可执行计划；
- 该计划能提高 c 的 utility；
- 后续动作涉及的其他 consenting characters 也各有可成立的解释；
- 不靠可删除的冗余动作凑解释。

因此主计划实际可执行与“角色认为有用的解释计划”是两个对象。角色的解释可能因错误信念而最终失败；人物行动不能仅因作者希望它发生便自动合格。

**机制释义伪代码（不是原件逐字复制或已实现代码）：**

```text
从作者初态展开真实可执行 action
  对 action 的 consenting characters:
    取该角色 belief-state
    查以此 action 开头、utility 上升的解释续篇
    续篇如依赖别人合作，再递归承担别人的解释义务
  解释成立后，主搜索应用 action + trigger closure
  作者 utility 上升、所有动作有解释且不冗余 → 接受
```

Search 的公开实现评测使用 A* 与论文注明的 h+ heuristic；实际有最大深度保护，无解搜索未必终止。输出是一个集中式计划，不是多个 NPC 独立决策的证明，也不是完整的外部扰动在线 policy。

### 1.3 可以搬在哪里 / 不能搬成什么

| 机制 | 具体可借用途（项目推断） | 不成立的替换 |
|---|---|---|
| `CON + β + utility improvement` | 检查高层作者计划中人物行动是否存在域内理由；解释需绑定动作/状态 | 不能只输出一句“他想避雨”就算证明，也不要求所有游戏采用 Sabre belief schema |
| action / trigger | 将人物选择与非人物规则放进同一因果搜索；例如雨由规则触发而非 NPC 选择 | 把原生数分钟降雨过程当零时 trigger，会改变时间语义 |
| `OBS → belief effects` | 防止人物凭未观察事件行动 | 初始默认知道真值不等于一般合法知识权限 |
| 作者 utility 与解释计划 | 作者可集中编排，同时承担人物合理性义务 | 不等于作者只能间接引导；不等于独立角色自治 |

### 1.4 实际评价与失败（论文证据，Table 1 与 Limitations）

七类 narrative benchmark domains；Lovers 随机生成10个已知可解实例、解出9个。Table 1 从毫秒到 Grandma 平均6.2小时，说明信念/解释搜索成本不可忽略；不能把不同域规模的耗时当公平算法排名。

消融是 full / intention-only / belief-only 在固定长度内的合法解集合比较。论文明确说明，功能/问题假设不一致，不能由此宣称胜过所有旧 planner。正文引用2018年用户证据，不是本篇新增玩家试验；形式 utility 解释仍不覆盖全部情感、人格或玩家感知可信度。作者仍手写 fluents/actions/triggers/utilities；domain debugging、uncertainty 与搜索成本是明确限制。

## 2. Mimesis：不是回滚，而是按因果链区分“执行后改未来”与“执行前拦截”

### 2.1 输入、层次与真实执行（论文证据，§3.2–3.3.3，Fig.1）

上层 Controller 使用 Longbow hierarchical partial-order causal-link planning：plan 包含动作、偏序以及 `producer --condition--> consumer`。下层是修改过的 Unreal Tournament Server，procedural operations 与上层 declarative operators 对应。XML 传 plan / mediation policy；下层 Execution Manager 将顺序约束变成 DAG，只执行前驱已完成的节点；玩家节点不能直接强制执行，采用待玩家满足成功条件的 placeholder。

**这是真实引擎/声明模型接缝的先例**，不是文字 narrator。但本篇没有给完整模型一致性证明、可移植适配器或详尽 re-planner 源码。

### 2.2 威胁检测与两种修复的精确次序（§3.3–4.2）

```text
计划中每条 producer --p--> consumer
  枚举区间内玩家可能执行、effects 能否定 p 的动作
  为每个匹配动作建立 mediation-policy entry
玩家命令执行前送 Mediator
  constituent: 对应计划动作
  consistent: 不破坏未执行部分的因果支持
  exceptional: 命中当前区间的 causal threat
exceptional:
  accommodation → 允许真实执行；换未执行计划/政策
  intervention  → 换成预置合法 failure-mode；执行替代动作
```

例如玩家提前开金库，保留已发生的开门，删除未来多余开门并重连支持链。玩家过早射杀必须开库的人时，可在执行前换成 shoot-and-miss。后者的失败结果来自开发者预置 operator，不是 LLM 临时声称“没打中”，也不是已杀死后复活。

§4.1 的响应排序接口明确是 `heuristic(history, candidate action, future)`：history 为已经执行的片段；候选为 exceptional act 或 failure-mode；future 为旧或修复计划后缀。选 accommodation / intervention 的完整质量函数与高效重规划内部过程**未在此篇充分给出**，不能补造成标准已复现算法。

§4.2 在空闲计算时预建 policy tree：节点是 plan+policy，边是 exception→新plan/policy；可选 breadth-first（较近异常先处理）或 best-first（较可能异常先处理）。这是提前计算分支以减少临场延迟，不是任意未来扰动的完备策略证明。

### 2.3 评价与边界

本篇给系统架构、银行场景及 Table 1 policy，未提供受控玩家质量实验或完整运行性能比较。结论明确留下 heuristic / 计算需求研究，并承认只看单次异常、不识别玩家较长意图；单步 failure-mode 也有限。不能把叙事连贯与控制感的动机陈述当实测增益。

**项目决定**：保留 future accommodation 与 pre-execution intervention 为不同权限条件；控制可强可弱，但即使选择强控制，也不能把已结算成功偷偷改成失败。天气若能威胁因果支持，可用同一检测结构表述（项目推断），论文自身枚举的是用户行动，不是已经展示动态天气修复。

## 3. 对统一问题的实际影响

已存在的成熟能力：作者目标+解释搜索、action与trigger统一因果域、跨层模型/执行映射、威胁定位、未来修订、权限化拦截。当前项目不能以“世界中心、作者稀疏节点、LLM之前没有这些”立新颖性主张。

仍需比较而非先宣称不足：给同一固定游戏域和同一实际扰动，符号搜索、LLM候选+独立检查、自然语言直接规划在有界成本与修复质量上怎样不同。人物形式解释与玩家判断另记，SAT/utility 不代替人类评价。

用户新理解（留白，不以 AI 判断代填）：
