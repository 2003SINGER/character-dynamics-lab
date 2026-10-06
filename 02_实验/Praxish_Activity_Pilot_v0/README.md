# Praxish Activity Pilot v0

**Status: READY_FOR_INDEPENDENT_REVIEW** — reference execution, paired scenario, provenance checks and 11 fixture tests passed; the parent independently checked the source mechanism, plain-API replay and deterministic CLI runs. [Parent acceptance evidence and limits](PARENT_REVIEW.md) records what was actually verified. User/external review remains open; this is not `CLOSED`.

中文快速查看：没有请求时，worker 开始备货后直接完成；有请求时，先回应（11 > 完成的 5），备货状态仍保留，然后完成备货。把作者设定的请求权重从 10 降到 1，则先完成备货、后回应。实际逐回合事实与解释见[父代理验收](PARENT_REVIEW.md)，不是训练效果或玩家认可。

This is a small application-side exercise using the publisher-provided AIIDE 2023 Praxish release artifact. It asks one narrow mechanism question: when a request becomes visible, can an authored activity make a worker's action set and goal score change while preserving the worker's own work state?

The paired conditions have the same characters, practices, goals, action rules, initial world facts, and seed. `no_request` has no event. `request` inserts a request-practice instance before turn 1. The event creates only a pending request; it does not choose a response. The worker's restocking activity advances `waiting → working → complete`. At turn 2, a request can compete with finishing work. If the worker answers, the work phase remains `working` and is completed at turn 4.

Praxish's original `tick` remains the decision procedure. In this release it cycles actors round-robin, enumerates practice actions that satisfy their conditions, temporarily applies each candidate, and scores the resulting state as the sum of `goal.utility × post-action match count`. It chooses among the maximum-scoring candidates with the artifact's random tie-break. Scores in these traces are absolute goal-satisfaction values, not score deltas. This is one-step action selection, not multi-step planning. Role limits come only from the authored action conditions; the harness does not claim automatic actor-local observation permissions.

## Run

From the repository root:

```sh
node "02_实验/Praxish_Activity_Pilot_v0/tools/pilot.mjs" fetch
node "02_实验/Praxish_Activity_Pilot_v0/tools/pilot.mjs" test
node "02_实验/Praxish_Activity_Pilot_v0/tools/pilot.mjs" original --run-id original-demo-fresh-id
node "02_实验/Praxish_Activity_Pilot_v0/tools/pilot.mjs" run --run-id paired-run-fresh-id
```

The runner resolves files relative to itself, so the same commands work from another current directory with the script's absolute path. Node's built-in modules are sufficient. `fetch` uses `gh` and `unzip`; it downloads the release only when no local snapshot exists. It verifies the pinned archive and source-file SHA-256 values. `original` executes the untouched `db.js`, `praxish.js`, and `tests.js` files in their documented order, without the scenario observer, and saves the fixed seed, console log, final database, and final-database hash. Choose a fresh run ID for every invocation; both run commands refuse an existing ID and never replace prior output. They save a manifest with status, seed, Node version, scenario and runner hashes, and source pin under the ignored `outputs/praxish_activity_pilot_v0/runs/<run-id>/` directory. If a run fails, partial output and an `error.json` remain for inspection.

Turns are zero-indexed. An event is applied immediately before that turn's actor is selected; `pre_facts` are sampled after the event and before the original `tick`, while `post_facts` are sampled after `tick`. Each trace records activity and action templates, role assignments, eligible candidates, per-goal match counts and score contributions, the selected action, and runtime messages. The VM observer patches only the VM's `randNth` binding to record the original selection; it does not edit upstream source. A seeded 32-bit LCG replaces `Math.random` in the VM, using `state = (state × 1664525 + 1013904223) mod 2^32`; the upstream selection calls are otherwise unchanged. Repeating a condition with the same seed produces the same typed trace. At the six-turn horizon, actors with no eligible action log the upstream `No actions to perform` warning; the worker has already completed its finite task. This is the fixture horizon, not evidence of long-term idle behavior or a broken simulation.

The run is not a browser-UI verification. The original release's noninteractive browser page was executed in Node's VM with the three script files loaded in its documented order. No visual interaction or presentation claim is made. This is not a baseline comparison, a player study, or evidence that activity-based NPCs outperform another method.

## Scope

The scenario has four candidate actions: start and finish restocking, answer the request, and wait for an answer. It deliberately allows a request to lose to the worker's other goal, and allows ties under other author settings. A separate authored sensitivity variant lowers only `serve_visitor` utility from 10 to 1; the same request is then deferred until after restocking. This demonstrates that behavior depends on author-specified preferences and is not a method-advantage comparison. The included tests check event-to-candidate changes, role conditions, max-score selection by the original tick, state retention and later completion, fixed-seed repeatability, original-demo repeatability, and upstream byte hashes. They test this fixture, not the general adequacy of Praxish or a game implementation.

A trimmed paired-turn example generated by the harness is in [examples/paired_choice_excerpt.json](examples/paired_choice_excerpt.json); the complete six-turn records are in ignored run `paired-review-20261006-04`.

See [PROVENANCE.md](PROVENANCE.md) for the release pin and licensing boundary. Do not treat this artifact pilot as a new NPC architecture or as a baseline advantage claim.
