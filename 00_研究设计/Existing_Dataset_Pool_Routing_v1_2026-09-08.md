# Existing Dataset Pool Routing v1

核查日期：2026-09-08  
范围：只读横向 routing；不下载、不新增 adapter、不训练、不修改 Theory-S、X/S schema 或冻结协议。

## Superseding update（2026-09-09）

The shortlist below is historical routing v1. It is superseded for the current next-action route: ClubFloyd Stage 0c found no positive low-order history increment after exact pair repeats were excluded, so its persistent-compression / Theory-S bridge is paused. LIGHT H0b now finds aligned generic action-transition signal beyond O-only and a permuted control. LIGHT may proceed to a generic/raw-history versus naive persistent-compression benchmark; this is not permission to start Theory-S training. OPeRA remains the backup if that compression benchmark fails.

## Decision summary

### Primary shortlist

1. **#1 ClubFloyd — `PRIMARY_ACTION_CANDIDATE`**：425 条单玩家 transcript、438,188 observed steps，最天然地提供 ordered state/action history → observed chosen `A*`。corrected admission 与 multi-LLM development adjudication 已冻结；它仍不是 canonical finite-`A^O` 或完整 Theory-S 训练准入，可进入 representation baseline。
2. **#2 LIGHT — `PRIMARY_ACTION_CANDIDATE`（backup / canonical-interface candidate）**：source `A*`、scene/replay/13D 工程基础最好，但 actor-local gap 与 X 缺失阻止完整六维训练。它是现有 Theory-S 工程接口的备选，不是已通过 D01 的主数据。

**如果今天必须开始第一次 real 3D Theory-S development experiment：选 LIGHT 的受限 actor-local development slice，不填缺失 X，不把 observed `available_actions` 当 `A^O`。**

**OPeRA 不进入前二**：真人 web action 和 O 最干净，但 v1 只测了 single-target identity selection（10/30），不是 bounded multi-candidate support；candidate-set route 仍 unresolved，且 canonical 13D 不兼容。

### Dynamics auxiliary

**AGAIN — 唯一 `DYNAMICS_AUXILIARY`。** 它有 session-local 连续时间、高频 telemetry、past-only 对齐的连续 `arousal_value` proxy，可检验 persistence、lag、decay、recovery 和一阶 relaxation 相对 AR(1)/无状态 baseline 的形状。它不能验证 Theory-S 三维语义、六维 X、行为 readout 或最终 `alpha/beta/b/W`。

## Unified routing table

| dataset | human / synthetic / telemetry | ordered trajectory | usable `H_obs` | independent `A*` | candidate / action surface | generated candidate feasibility | X/event constructibility | dynamic-state proxy | trajectory length / scale | leakage risk | engineering cost | Paper-0 role | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LIGHT | human gameplay/dialogue source | ✓ 7,258 trajectories; 25,001 steps; quarantine 后 7,256/24,999 | △ same-actor filtering; 62.2% adjacent pairs cross actors | ✓ source physical action，可作 held-out target | 有 observed action list，但不是 `A^O`；有限动作表面 | △ scene→affordance compiler 已有 dev slice；需 semantic/O audit | △ 2D 可保留；`effort_load`/`recovery_cue` unavailable，其余多需 annotation | △ source event/scene transition only | median 3 steps/trajectory；短轨迹 | cross-actor gap、observation leakage、source list≠`A^O` | 中（restricted）；高（完整 6D） | **PRIMARY_ACTION_CANDIDATE** | #2 backup；完整六维 training NO-GO |
| ClubFloyd | human/player transcript | ✓ 425 trajectories；438,188 steps；single-player | ✓ state-before-command、连续 transcript history 最自然 | ✓ observed next command；需 semantic admission | 开放文本 command；无原生 candidate set | △ Terra/grammar 可生成候选，但 legality 无游戏 parser 支撑 | △ state text 可 model-derived X；无结构化 W/P/X truth | △ command/state sequence，可作 persistence interface | median 704；max 8,934 | open-vocabulary ambiguity；chat/meta 混入；license/semantic audit | 中（source-command baseline）；高（finite `A^O`/Theory-S） | **PRIMARY_ACTION_CANDIDATE** | #1 pure next-action candidate；先冻结 command-like slice/eval |
| OPeRA | human browser sessions | ✓ 527 sessions；≥20 actions 仅 69 | ✓ pre-action HTML/URL + past actions | ✓ independent browser action | open UI target；13 click subtypes；无原生 per-step `A^O` | △ v0 semantic coverage；v1 single-target 10/30；bounded 5–10 candidate support 未测 | △ 需 Terra semantic layer；canonical 13D 不兼容 | — | median 7 actions/session；max 241 | target identity、user/session split、model-derived candidates | 高 | STRUCTURAL_AUXILIARY | LIMITED-GO；single-target task closed, set route unresolved |
| FarmQuest | telemetry + action proxy | △ 122 sessions；可靠 source order，无可靠连续时间 | ✗ `source_O=null`；仅结构化事件 context | △ action-proxy，不是独立 command truth | event/action-proxy surface；无 `A^O` | — | △ discrete event features；不能恢复连续 X dynamics | △ quest/location/availability persistence | 42 participants；10,844 strong action-proxy steps | timestamp semantics unusable；proxy≠A* | 低–中（离散）；高（连续 dynamics） | NOT_USEFUL_NOW | 仅 event-order 辅助，不作 dynamics 主线 |
| PowerWash | telemetry | ✓ 1,135 normal sessions；344,248 steps | ✗ `source_O=null` | ✗ no independent `A*` | event/progress telemetry；非 action candidate surface | — | △ external task/progress fields only | ✓ task/environment persistence | 100 participants；366,660 raw rows | same-timestamp bundle；progress≠psychological S | 中（external state） | STRUCTURAL_AUXILIARY | 任务/环境状态持久性对照，不是 affect relaxation |
| AGAIN | telemetry + continuous annotation proxy | ✓ session-local time；~521,100 rows；124 participants | △ telemetry history；不是 subjective O | ✗ keypress/telemetry 不是 independent `A*` | telemetry events, no finite action set | — | ✓ event/telemetry cues；arousal annotation is proxy, not X truth | **✓ continuous arousal proxy** | dev 20 sessions/9,302 steps；full ~521k | annotation alignment, participant/game confounding | 中 | **DYNAMICS_AUXILIARY** | #1 dynamics；窄 audit only |
| SOTOPIA | synthetic agents | ✓ ordered episodes/actions | ✓ private-goal boundary in prompt | △ synthetic policy action, not human truth | talk/nothing surface collapsed | — | △ synthetic goal/context cues | △ synthetic persistence only | 30-episode pilot | synthetic provenance/action collapse | 低–中 | STRUCTURAL_AUXILIARY | structural information-boundary check |
| Mem2Act / Mem2ActBench | mixed constructed dialogue/tool benchmark | ✓ ~2,029 sessions；~12.67 turns/session | ✓ user/assistant/tool turns | △ explicit tool calls, partly benchmark/model-constructed | tool schema/API pool; no per-step subjective `A^O` | △ schema-normalized tool candidates possible | △ history/fact/conflict features; not Theory-S X truth | △ memory evolution, not environment dynamics | ~83k tool calls; ~400 QA in benchmark slice | inferred/default args; mixed provenance; tool schema leakage | 中 | STRUCTURAL_AUXILIARY | new-asset #1; worth targeted action/history audit, not main human behavior |
| Memora | generated long-term dialogue benchmark | ✓ 7/30/90-day sessions；27,614 files | ✓ temporal dialogue/memory operations | ✗ no independent A* | free-text recommendation/answer; no candidate set | — | △ memory operation/event labels | **✓ add/update/delete/forgetting persistence** | 10 personas；avg ~15.65 turns | generated persona/answer leakage | 中 | STRUCTURAL_AUXILIARY | persistence/forgetting structure only |
| EverMemBench | multi-party dialogue + QA | ✓ dates/speakers/message index；67,256 messages | ✓ dialogue history | ✗ memory QA only | no action candidate set | — | △ temporal memory evidence | △ long-term retrieval/persistence | 307 dates；879 groups | QA/reference leakage | 低–中 | STRUCTURAL_AUXILIARY | memory retrieval structure only |
| R-Helm | conversations/emails/attachments + QA | ✓ timestamped chronology | ✓ chronological evidence history | ✗ no independent action | free-text QA/constraint response | — | △ conflict/negative-evidence labels | △ evolving state/constraint persistence | 629 conversations; 625 emails; 1,053 attachments | evidence/answer leakage | 中 | STRUCTURAL_AUXILIARY | state-boundary diagnostic only |
| DECADE | temporal memory QA | △ session IDs/dates; raw haystack absent | △ QA context, no replayable O | ✗ no A* | QA only | — | △ temporal update/absence cues | △ memory aggregation | 500 QA; ~1,024 sessions/question | missing raw sessions; QA leakage | 低 now / high if recovered | NOT_USEFUL_NOW | no next-action asset locally |
| PERMA | event-driven preference benchmark | △ design timeline; local payload incomplete | △ task/options only | ✗ no observed action trajectory | MCQ/free-text simulator output | — | △ preference drift labels | △ preference persistence | 9 task JSON locally | incomplete payload; simulator leakage | 高 | NOT_USEFUL_NOW | register only; no local admission |
| MobileMem | code/README; payload placeholder | ✗ no complete local trajectories | ✗ | ✗ | not locally inspectable | — | △ design claim only | △ design claim only | no usable local data | missing payload; would require download | blocked | NOT_USEFUL_NOW | do not download this round |

## What this routing does not claim

- ClubFloyd is a primary **next-action candidate**, not already admitted finite-
  candidate Theory-S data. Its first protocol must define command-like filtering,
  open-text scoring, and semantic ambiguity handling.
- LIGHT remains the closest canonical engineering interface, but D01's missing
  X fields and actor-local gap rules remain hard boundaries.
- AGAIN is an external arousal-proxy dynamics audit, not psychological proof and
  not direct identification of Theory-S parameters.
- “Memory benchmark” does not mean `H_obs → S → A*`; only Mem2Act has a directly
  inspectable tool-call surface among the new archive group, and even that is
  mixed/model-constructed.

## Next action

Do **not** start Theory-S training from this historical routing page. ClubFloyd
Stage 0c is paused for this estimand. LIGHT H0b has passed the history-signal
gate, so the next action is a generic/raw-history versus naive
persistent-compression benchmark with lossless source, source candidate lists
treated only as observed support (not `A^O`), and no new X fields. If that
compression benchmark fails, route to OPeRA; do not reopen ClubFloyd Stage 0d.
