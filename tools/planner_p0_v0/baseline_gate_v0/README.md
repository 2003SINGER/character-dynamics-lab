# P0 Baseline Gate v0

This isolated gate compares two bounded planning architectures over the same
P0 direct-control scene and author monitor:

- A: Sabre selects atomic GET, MOVE, and DROP actions.
- B: Sabre selects the frozen `deliver_shelter` macro, refined by the existing
  P3 `plan_next(..., "deliver_supply")` GTPyhop implementation into native
  GET/MOVE/DROP calls.

Both use the same frozen native world, route facts from the authorized global
snapshot, mode/author permissions, action effects outside delivery, weather
timer, one-look/one-meeting symbolic guards, horizon, TypedIR monitor, and
Sabre per-call limits. The new renderer adds the same `!knows_storm(actor)`
look guard and `!met_witness()` meeting guard to both models so the symbolic
plan cannot count repeated observations or meetings against the monitor's
once-only constraints. This is a shared projection correction; it does not
modify the frozen integration world or its rules.

The delivery abstraction differs intentionally. A's GET/MOVE/DROP each cost
one world minute. B reuses the structure of the integration delivery macro,
but this exporter is not a byte-for-byte frozen macro: it adds the
`!kit_held(A)` effect to match native DROP, and A also clears held state. B's
single Sabre macro is priced from the full route facts as a manually authored
primitive-count cost, then actually refined by the existing local-view HTN
and settled one primitive at a time. Both variants also receive this gate's
shared once-only look/meeting projection correction. The HTN sees actor-local
observations; Sabre receives the same authorized `snapshot.routes` projection
in both variants. Consequently this is not a claim that only the search
algorithm differs: B has a hand-modeled macro and a local-view HTN dependency.
These projection corrections are confined to the new gate exporter; the old
P0-Integration renderer, runner, monitor, and HTN source are unchanged. The run
records generated action-declaration counts and source LOC for maintenance
visibility; it does not infer human authoring hours.

Sabre `--cost t` is Sabre's temporal progression-depth measure, not the native
world's minute fluent. `--author-limit 24` is likewise a symbolic depth ceiling,
not proof of the native 24-minute deadline. Never compare A's atomic search
depth directly to B's macro depth as if those were equal units. Compare real
native outcome, receipt-only TypedIR result, world minutes, and per-layer cost
accounting. Every invocation retains its own visited/generated/native-time
budget; totals are reported separately, including wrapper (Java startup plus
search) wall time, problem-export time, HTN proposal visits, RPC wall time,
and evaluation-window drain. The difference between wrapper wall and Sabre
native search time is only an overhead proxy, not a precise Java-startup
measurement.

The route-repair perturbation is triggered when each method has A holding the
kit and has proposed the same Junction-to-Inn main-route move, before that
proposal is dispatched. Mutation must consume zero minutes; the already
proposed move is dispatched unchanged and must fail natively while consuming
one minute. The run asserts task identity, held kit, task progress, and A's
local observation of the closed route, then records the subsequent repair.
The high-causal-replan perturbation fires immediately after the first settled
cloud seed leaves a pending cloud and before its due time; it records that the
mutation costs zero minutes and clears pending weather. The two algorithms may
reach these same causal points at different minutes; no fixed action sequence
or matching plan prefix is imposed.

The monitor requires delivery-before-meeting and B-observation-before-meeting;
it does not require delivery-before-observation. Sabre utility and effects are
not accepted as evidence: only the frozen native ledger projected through the
repository TypedIR monitor can pass. Direct control is authorized joint
orchestration, not independent NPC agency.

Run each cell separately with the same seed after the parent authorizes live
execution; this package does not start or stop Evennia. Results are unique and
non-overwriting under `02_实验/Planner_P0_Baseline_Gate_v0/runs/`, with Sabre's
raw logs under the existing baseline evidence root.

The no-server preflight problems are owned here:
`02_实验/Planner_P0_Baseline_Gate_v0/preflight/baseline-gate-a-20261011.txt`
and `baseline-gate-b-20261011.txt`. The unchanged wrapper run IDs are
`p0-baseline-gate-a-preflight-20261011-01` and
`p0-baseline-gate-b-preflight-20261011-01`.

Offline tests:

```sh
python3 -B -m unittest discover -s tools/planner_p0_v0/baseline_gate_v0/tests -p 'test_*.py'
```

Live command shape (do not run until explicitly authorized):

```sh
PYTHONPATH=.:tools:tools/native_platform_v0/bridge _local_data/native_platform_v0/evennia/venv/bin/python -m tools.planner_p0_v0.baseline_gate_v0.runner --case direct-clean --variant A --seed 0
```

Repeat with variants `A` and `B` for each of `direct-clean`, `route-repair`,
and `high-causal-replan`. A budget limit, timeout, error, or native refusal is
retained as such and is never relabeled unreachable or retried with larger
limits.
