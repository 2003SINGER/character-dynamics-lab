# Planner P0 Integration v0

This is a bounded integration experiment, not a complete traditional planning
system or a claim of autonomous NPC agency. Sabre v0.8.0 selects among a
hand-authored, fixture-specific set of actions. In `conditional`, `offer_task`
is available only when the fixed fixture A own-goal matches; the native server
decides the real offer result. In primary `direct`, `dispatch_task` is an
explicit author-forced joint-control action, not consent. `deliver_shelter` is
the sole compound action and is expanded by
the existing P3 `plan_next(local_view, "deliver_supply")` implementation.
Each returned GET/MOVE/DROP is dispatched and checked against native readback;
the macro effect itself is never treated as a receipt.

The Sabre export contains the current clock, weather, registered route facts,
actor locations, receipt-backed knowledge, mode permissions, and the physical
cost of delivering from each reachable A start room. That cost is calculated
from route distance plus the required GET/DROP primitives. It is a manually
authored domain cost abstraction, not a Sabre-learned cost model and not an
independent HTN implementation. If native execution differs from that forecast,
the runner records `TEMPORAL_REBASE` and replans from a fresh native snapshot.
Pending clouds cannot be forgotten by planning: native ticks create storm at
the due time, and Sabre's numeric-time trigger fires when a macro crosses it.
Only `look` gives B storm knowledge. Physical move legality is route-only;
character intent and the author's goal are modeled separately.

Control modes are distinct. `direct` is authorized joint control and is the
primary vertical integration condition; it does not demonstrate independent
character consent. `conditional` adds a fixed own-goal offer gate and a trusted
controller, not an autonomous NPC decision loop. `free` is an ACL negative
control; its lack of a solution is only “no plan in this exported domain,” not a
proof that the game state is unreachable.

The runner never starts or stops Evennia. An already running authorized local
control service is required for live cases. It preserves one non-overwriting
run under `02_实验/Planner_P0_Integration_v0/runs/` and nests full Sabre
configuration/stdout/stderr under the existing Sabre evidence root. Native
ledger receipts are projected through the repository's TypedIR
`EventCount`/`EventOrder` monitor; offers, candidates, symbolic effects, and
unsealed prefixes cannot witness the author goal.

Native timestamps are explicit: a successful primitive settlement event is
stamped at its pre-action minute `t`; then the server clock advances and the
response's post snapshot is at `t+1`. Weather/time transition events are
stamped at the advanced minute. Goal ordering is evaluated on settlement-event
timestamps, not inferred from post-state snapshots.

Bounded cases, one invocation each:

- `direct-clean`: complete direct-control vertical path.
- `route-repair`: after GTPyhop proposes the current main-route move and before
  dispatch, block main; retain task/item/progress, record the failed native
  dispatch, and locally replan the remaining HTN primitives over side.
- `high-causal-replan`: after a Sabre-planned cloud seed but before its due
  minute, dissipate the pending cloud; preserve the prefix and replan the Sabre
  problem from the live snapshot.
- `conditional-consent-smoke`: fixed offer gate plus trusted-controller path;
  not an independent agency result.
- `free-acl-negative`: no-plan result plus a separate native author ACL denial.

Search settings are fixed in `runner.py`: Sabre 200 visited nodes, 5000
generated nodes, 5000 ms native search, 24 author limit, and a 12-second outer
watchdog for preprocessing/grounding. A wrapper timeout is not `UNSAT`.

Offline checks (do not require Evennia, Java, Sabre, or a server):

```sh
python3 -B -m unittest discover -s tools/planner_p0_v0/integration_v0/tests -p 'test_*.py'
```

Live use requires the server to be started separately by the authorized owner:

```sh
PYTHONPATH=.:tools:tools/native_platform_v0/bridge _local_data/native_platform_v0/evennia/venv/bin/python -m tools.planner_p0_v0.integration_v0.runner --case direct-clean
```

After a real meeting-witness receipt is present, the runner stops story actions
and advances with explicit native `wait` steps to minute 24 solely to close the
fixed evaluation window. This evaluation-clock drain is not autonomy evidence.
