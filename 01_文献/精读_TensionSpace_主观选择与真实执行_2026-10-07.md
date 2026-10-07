# 精读：Tension Space 的主观选择、真实执行与草图拟合

日期：2026-10-07。Luna 全文审读 14 页公开稿，主代理复核 §IV 定义/Algorithms 1–4、§VI 草图拟合/A*；未运行 Unity 工具。另对 Force Dynamic 2021 的状态/Algorithms/见证者方法作定向核读，不记作第二篇全文精读。

原文：Kybartas、Verbrugge、Lessard，*Tension Space Analysis for Emergent Narrative*，IEEE Transactions on Games 13(2), 146–159 (2021)，[DOI](https://doi.org/10.1109/TG.2020.2989072)；阅读的是 [arXiv v1（2020-04-22）](https://arxiv.org/pdf/2004.10808v1)。以下页码按 14 页公开稿，不冒称已逐字比对正式排版。

## 结论先行

**[论文证据]** 这不是“只有叙事命题向量、没有可执行世界”。它有实际世界、可错误的主观世界、动作前提/效果、主观筛选和实际执行校验。世界状态是否用命题向量，不能作为“可执行/不可执行”的分界。

**[项目推论]** `W≠O`、局部 belief 下选动作、真实世界最后验动作都有强先例。本项目应比较具体观测与后果传播，不从这些接口名宣布创新。

## 1. 表示与公式

**[论文证据｜§IV-A/B，PDF pp.4–5]** 系统 `N=⟨P,T,wa,C,A,r⟩`；实际世界 `wa` 是命题赋值向量。角色 `c=⟨wp,Wv,Ac⟩`：`wp` 为认知世界，`Wv` 为按主题组织的固定理想世界，`Ac` 为动作子集。`⊥` 表示不关心；实际世界每命题需有确定值。

动作 `a=⟨wδ,wε⟩` 分别表示前提和效果。`⊥` 在前提中不约束该项，在效果中不改变该项。

```text
dist(x,y) = 0                 若任一项为 ⊥
          = |x-y|             否则
D(w1,w2) = Σ命题 dist(w1[p],w2[p])
主观目标张力 T(c) = Σ理想世界 v D(v, c.wp)
score(c,a) = T(c) - Σv D(v, Apply(a.effect,c.wp))
```

这是非负距离与预期减张力，不是 DiriGent 的 signed challenge/satisfy；不能把两套公式混在一起。

## 2. 真正执行的算法

**[论文证据｜§IV-C，Algorithms 1–4，PDF p.6]**

```text
for character c:
    按 c.wp 匹配动作前提，计算各合法候选的 score
    若最大 score >= 0：提出该动作；否则不动作
    再按 wa 匹配真实前提
    若不满足：失败，不 Apply
    若满足：Apply 效果到 wa
            同一效果 Apply 到所有角色 wp
```

例如 `wp(door_open)=true`、`wa(door_open)=false`，角色可能认为穿门可行，真实执行却失败。这是从原算法构造的说明例，不是论文的运行样本。基础模型对成功效果统一广播给所有角色，不含本项目的感知权限投影与 typed rejection 学习；不能一边认前例存在，一边夸它已经等于本项目全部信息语义。

角色单步贪心，没有多步 intention/plan。论文明确指出即时张力下降可能妨碍更好的未来路径，lookahead 是未来工作（§VII）。不把草图阶段的 A* 误写成角色在 runtime 规划。

## 3. 草图究竟生成什么

**[论文证据｜§V–VI，PDF pp.7–12]** 热图遍历可能实际世界，坐标是对两个理想世界的距离；全部可能世界的图不等于动作可达图。

作者先画张力空间，拟合命题真值；再画动作路径，将边拆为单位移动。动作拟合先找一个符合起点的实际世界，使用 A* 搜索命题移动到下一节点，再生成动作的前提/效果，顺序 Apply 后拟合下一边。无法拟合世界观的移动会忽略；动作路径失败后停止并标红。

这是**内容生成时拟合一条可能执行的 trace**，不是固定世界中、任意玩家扰动后保证作者节点，也不是一般可达性分析。作者约一分钟、五幅草图重建功能相近的 Fanny 设计是工具示范，不是作者成本受控研究或玩家活人感结果。工具是 C# Unity Editor 扩展；本轮未找到其公开执行代码入口。

## 4. Force Dynamic 2021：只作方法补充

原文：[A Force Dynamic Model of Narrative Agents](https://ojs.aaai.org/index.php/AIIDE/article/download/18890/18655/22656)，AIIDE 17，50–57。DiriGent 的 2021a/2021b 分别指 TSA/本篇，不是同一套方法。

**[定向论文证据｜PDF pp.2–4，Algorithms 1–5]** satisfaction filter 将 `wp` 映射到满足度；`conflict=1-satisfaction`，重力 `fg=-conflict`。动作以角色 condition/effect filters 与 instigator 绑定；有效角色映射后，按自身重力与动作移动、对其他参与者的关系力与其移动的 similarity 评分。人际力每步乘 `1-σ`，观察者反应按 `α` 缩放。它不是简单给动作加一句“有张力”。

这个扩展的 condition/effect 主要作用于角色 perceived worlds，不能从其名称推成 TSA 的同一权威实际世界执行器；当前把所有角色当 witness，真实视觉/听觉权限是未来工作。探索性谈判模拟比较冲突曲线，未证玩家体验或心理真实性。

## 5. 项目判断

应吸收：明确区分理想状态与相信的现实；候选评分采用对动作后状态的比较；预期可行与真实成功分开；作者工具可展示张力与动作可达区域的差异。固定理想、广播认知、贪心与工具扩展性仍有限。

TSA **未被本项目复现、未选为方法**。它否定了贴文中“命题向量所以不可执行”的差异；并没有自动否定世界中心 NPC 方向。唯一下一动作见[综合复核](专题调研_世界引导直接近邻复核_2026-10-07.md)。
