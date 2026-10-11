# P0 Baseline Gate v0 — protocol

> Status: **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW**. Results are owned only by [RESULTS.md](RESULTS.md); this file remains the frozen protocol. Source freeze: `ad2e017` (`webgpt-sync@ad2e017`).

## Question and comparison

In the existing fixed game and author-goal fixture, what differs between **A: single-level Sabre** and **B: Sabre + the existing GTPyhop refinement** in execution, disturbance recovery, search/runtime cost, and hand-modeling cost?

Both arms run in direct author-authorized mode from the same global world snapshot, receive the same Sabre route facts, action/observation access, author permissions, Evennia world, event ledger, TypedIR monitor, simulation horizon, and disturbance trigger. B keeps its existing local HTN unchanged. This is an architecture comparison—not a byte-for-byte replay of the earlier P0-Integration domain and not merely a drop-in solver substitution.

The common goal monitor requires exactly one delivery, one storm observation by B, and one meeting witness; delivery and observation must each precede the meeting. It does **not** require delivery to precede storm observation. Keep the same renderer/common domain facts for both arms, including one storm look and one meeting witness; do not modify the game mechanics or author goal to favor either arm.

## Fixed cases and run budget

Use only the three existing direct scenarios, once per arm (six descriptive DEVELOPMENT runs total):

- `direct-clean`: normal delivery, storm observation, meeting.
- `route-repair`: main-route closure at the same causal progress point in both arms; compare recovery while retaining the executed prefix.
- `high-causal-replan`: cancel the pending cloud at the same causal progress point in both arms; compare high-level replanning and prefix preservation.

Trigger disturbances by the same state/progress predicate, not by forcing an absolute minute. Both arms use the same per-call Sabre v0.8.0 limits (200 visited, 5,000 generated, 5,000 ms native, 12 s wrapper). B additionally retains its existing GTPyhop cap (500 visits / 0.25 s), reported separately and included in total cost; do not imply a shared total-compute ceiling or equal-total-compute comparison. The common process limits are `MAX_REPLANS=40` and native horizon 24. Record cumulative end-to-end wall time across all calls, as well as `elapsed_native_ms` and per-layer time. This is a descriptive architecture comparison under equal per-call Sabre budgets, not evidence of superiority at equal total compute. A budget timeout is not evidence of unreachability.

Sabre `--cost t` and the author limit 24 measure symbolic action temporal depth, not `now()`-advancing native simulation minutes. Since macro/atomic action granularity differs between arms, symbolic depth/cost and node counts are not like-for-like search-efficiency measures; do not claim native shortest-completion-time optimality. Keep parameters fixed and judge practical outcomes using native execution and the TypedIR monitor.

## Measures and stop rule

Record per run: planner/native status and failure type; search nodes; per-layer and total runtime; actual primitive actions and repeated/unnecessary actions; replans; goal-monitor verdict; preserved history; and hand-modeling proxy (rule/LOC/dependency counts, with Java startup, HTN, export, RPC, and monitor-window drain cost itemized). Do not make labor-hour claims from LOC or rule counts. The six runs are descriptive development evidence, not a statistical success-rate or generalization study.

Allow at most one correctness repair if it is necessary for a fair comparison; do not tune parameters, raise budgets, or repeatedly rebuild scenes. If a common action/observation contract or comparable domain cannot be achieved without a broad planner-domain rewrite, record the blocker and estimated scope, then stop. Regardless of which arm appears better, freeze this gate and stop. The result must conclude one of: single-level is sufficient here; layering has a bounded observed advantage; both share a limitation; or a fair comparison was infeasible. None establishes a novel method.

## Exclusions and next boundary

No LLM, embedding, Qwen, general author-language compiler, frozen C++ changes, P5 shared-supply repair, new scene/NPC/state, or additional benchmark. The comparison does not test player benefit or independent NPC agency. Changing author constraints or building a general compiler is a later, separately authorized question; it is not implemented in this gate.

The prior P0-Integration checkpoint and all its successes/failures remain owned by [P0-Integration RESULTS](../Planner_P0_Integration_v0/RESULTS.md). This gate gets its own result owner only when a result is authorized/produced; this protocol makes no comparison claim.
