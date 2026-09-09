# T0d｜OPeRA model-estimated observable candidate reconstruction feasibility v0

状态：**LIMITED-GO（grounding 已可行；Terra 语义候选生成与 canonical readout 仍未验证）**

本页是一个独立 feasibility spike，不改写已冻结的 [OPeRA pilot protocol v0](OPeRA_pilot_protocol_v0.md)。没有启动训练，也没有把任何候选集写入 Theory-S 或正式 pilot。这里的 `Ahat^O_t` 只指 **model-estimated observable candidate set**，不声称是真实用户主观的 `A^O_t`。

## 1. 结论

从 OPeRA 的合法 prediction-time 输入中，构造一个**有页面 grounding 的候选生成流程**是可行的：

```text
pre-action simplified_html_t + url_t + legal H_obs_<t
    -> deterministic interactive-element grounding
    -> Terra semantic filtering / grouping / normalization
    -> frozen Ahat^O_t artifact
    -> reveal A*_t only in a separate evaluator
```

但本轮环境没有可调用的 Terra 推理工具，因此没有生成或评估真正的 Terra `Ahat^O_t`。只有 deterministic HTML grounding smoke，不能把其 lexical proxy 结果写成 support recall。故本轮不能给 candidate reconstruction `GO`。

当前 OPeRA 总体 **仍为 LIMITED-GO**。原先“release 没有 source-provided exact candidate set”的限制没有被推翻，只能更精确地改写为：

1. source 没有提供逐步枚举的 gold candidate set；
2. model-estimated candidate set 原则上可以从合法 O 生成，但尚未在 gold-blind Terra fixture 上验证稳定性与 recall；
3. 即使候选 support 成立，OPeRA click-type / exact UI target 仍不能自然投影到冻结的 Replay 13D action readout。

因此没有理由现在升级 OPeRA，也没有理由启动真实 gradient training。

## 2. 当前 source grounding 事实

本地 pinned parquet 的 action schema 包含 `simplified_html`、`url`、时间戳和真实 action 标签；`simplified_html` 是非空的页面结构文本，常见页面含导航、search box、link、button、select/option 等可交互节点。样例 HTML 规模约 8.6–149 KB，且具有大量重复导航/商品/推荐节点。

本轮做了一个**不按 gold action 选样本**的 deterministic fixture：按 session SHA-256 排序取前 10 条满足当前冻结长度门槛（至少 20 actions）的 session，每条取首步、中间步和倒数第二步，共 30 steps。候选生成阶段只读取：

- 当前 `simplified_html_t`；
- 当前 `url_t`；
- 可在当前时点取得的过去 history（本次 parser smoke 没有把 gold 字段注入 generator）。

HTML parser 仅抽取显式可交互标签（如 `a/button/input/select/option/textarea`）和显式 interactive ARIA role，并保存 tag、可见文本、`name/id/href/aria-label/value` 以及 source-location identity。之后按完整 identity 去重。

### 2.1 deterministic grounding smoke（不是 candidate recall）

| 指标 | 30-step fixture 结果 |
|---|---:|
| steps / sessions | 30 / 10 |
| raw interactive elements | 37–522；均值约 179.3 |
| unique grounded elements | 37–350；中位数约 155 |
| non-empty grounding rate | 30/30（100%） |
| parser-level duplicate fraction | 均值约 10.6% |

这说明 OPeRA 的 HTML 足以提供候选的**页面锚点和 provenance**，但 raw set 太大，不能直接当合理 candidate set。必须经过冻结的 semantic filtering/grouping，并保留每个 canonical candidate 对 raw elements 的 provenance。

另做了一个仅在 candidate artifact 生成之后才读取 gold 的 lexical sanity check：用 `semantic_id` 与 grounded element 文本/属性做事后 token overlap，30 steps 中约 26/30 达到预设的粗 lexical overlap 阈值（约 86.7%）。这不是 `P(A*_t ∈ Ahat^O_t)`：它没有 canonicalize action target，也没有运行 Terra，因此不报告为 support recall，只作为说明 source HTML 与部分 gold target 存在可见词汇联系的弱 sanity check。

## 3. 合法输入与禁止字段

### 3.1 Terra generator 允许输入

- 当前 action 发生前的 `simplified_html_t`；
- 当前 `url_t`（必要时做 URL normalization，但保留 host/path provenance）；
- 严格裁剪的 `H_obs_<t`：过去已经发生的 action、过去时点的合法 O/history，以及不含当前 target 的 session context；
- deterministic extractor 输出的 raw interactive elements、DOM/source location 和页面文本片段。

### 3.2 明确禁止输入

构造 prompt 和 candidate artifact 时不得读取或派生：

- 当前 `action_type_t`、`click_type_t`、`semantic_id_t`；
- 当前 action 对齐的 `element_meta`（它可能直接给出被点击 target）；
- 当前 action-specific `input_text_t`；
- 当前 `rationale`、`products`、`image`；
- future HTML/URL/action；
- 从 gold row 派生的 target hint、候选补全、miss 修复规则。

当前 action 的 `element_meta` 即使看起来像页面结构，也不能作为 `simplified_html` 的替代品；它与 gold action 行对齐，因此必须进入 evaluator-only quarantine。

## 4. Terra candidate protocol（尚未执行）

Terra 的角色不是凭空列举动作，而是对 grounded raw elements 做受限语义处理：

1. 判断哪些元素在当前页面与合法 history 下是合理可考虑行为；
2. 合并明显同义的 raw elements，但不能丢失 target identity；
3. 生成稳定的 canonical verb/target description；
4. 过滤装饰、不可操作或明显无关节点；
5. 为每个候选保存 raw-element provenance、prompt/version/model/temperature 和生成 rationale。

Terra 不得创造当前 HTML/URL 或合法 history 中不存在的对象。若页面上有多个相似目标，必须分别保留 target identity；若无法判断，应保留为 ambiguous，而不是替 gold 做唯一化选择。

每个 step 应先写入不可变的 candidate artifact，再由独立 evaluator reveal `A*_t`。若发生 miss，只记录 miss；不得将 gold 补进该 row，也不得只重写失败 row。若要改 generator protocol，必须递增 protocol version，并从头重生成整个 blind fixture。

建议下一次可执行的最小 fixture 为 20–30 steps，按 session hash 和 step index 预先冻结，不按 click type、semantic_id 或预测难度抽样。该 fixture 需要记录：

```text
prompt_version
model / temperature
input-field allowlist hash
raw grounded element hash
canonical candidate list
candidate -> raw provenance
artifact hash
```

本环境没有 Terra connector/推理入口，故上述版本化 artifact 本轮未生成；不能用本模型的文字判断替代 Terra 结果。

## 5. Gold-blind / reproducibility checks

正式实现至少应自动阻断以下情况：

- prompt payload 或 serialized input 出现当前 `action_type/click_type/semantic_id/element_meta/input_text/rationale/products` 任一 prohibited key；
- candidate artifact 写入时间晚于 evaluator reveal gold 的顺序约束被破坏；
- 同一 input hash、prompt version、model、temperature 不能产生未解释的 candidate artifact 差异；
- candidate identity 不带 raw source location/provenance；
- miss evaluator 回写 generator input，或对单个失败样本做 gold-conditioned repair。

评估必须在 artifact 固化后进行：

```text
support_recall = P(A*_t ∈ Ahat^O_t)
candidate_count: mean / median / quantiles
duplicate rate
ambiguous gold-match rate
no-candidate rate
deterministic reproducibility
gold-blind invariant pass/fail
```

其中 support recall 只有在定义了 canonical candidate-to-gold matching 规则、并且 evaluator 看 gold 之前 generator 已经完全结束后才有意义。无法匹配的 exact target 必须分为 miss / ambiguous，不能默认为 hit。

## 6. Action representation compatibility

候选 support 与冻结 `S -> action` readout 是两个独立问题：

- **candidate support：未验证，当前 status = unresolved；**
- **OPeRA action semantics → canonical Replay 13D：当前不兼容/未授权。**

OPeRA 的 observed labels 主要是 `click_type`，exact target 还涉及开放的 semantic ID、URL、element metadata 等。HTML grounding 能给出 target identity，但不能因此自动得到当前 13D 所需的稳定 verb/target feature；也不能为 OPeRA 新造 `OPeRAFeatureV2`。所以即使未来 Terra support recall 良好，仍只能先作为 candidate-reconstruction feasibility 结果，不能直接宣布 OPeRA 可训练冻结的 canonical readout。

## 7. Verdict and next action

**Verdict：LIMITED-GO。**

- deterministic page grounding：GO（可复现、非空、可保留 provenance）；
- Terra semantic candidate generation：未执行，不能判 GO；
- gold-blind support recall：可定义、尚未测量；
- canonical 13D action compatibility：当前 unresolved / not authorized；
- OPeRA frozen overall protocol：**仍 LIMITED-GO**，继续作为 coarse click-type auxiliary candidate，而不是 Paper-0 canonical `A^O` 主实验。

下一步若要重新打开这一支，只做一个隔离的 Terra blind fixture：固定 20–30 steps，先落盘候选 artifact，再 reveal gold，完成上述 support/ambiguity/reproducibility 指标。该 fixture 不得修改 OPeRA protocol、Theory-S、action feature basis 或训练状态。

