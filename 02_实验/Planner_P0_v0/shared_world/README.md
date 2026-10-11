# P0 shared-world fixture

This is a small native-world control fixture, not a claim of autonomous NPC agency. One authenticated local controller explicitly orchestrates A and B; the testplayer can only inject the registered route closure at the sealed hour-2 prefix.

## Registered RPC operations

- `reset_p0_shared_world({seed?})` creates one fresh, isolated Evennia scene. The current process scene quota remains 16.
- `snapshot_p0_shared_world({scene_id})` returns authoritative positions, clock, weather, observation receipts, and routes read back from native rooms/Exits.
- `step_p0_shared_world({scene_id, request_id, action, predicted_post?})` allows only `wait`, `observe_weather`, `move`, or joint `meet`. Each attempt is recorded and consumes one hour unless the fixed deadline has already been reached.
- `inject_p0_route_block({scene_id, route, request_id})` allows only the testplayer's `main`, `side`, or `all` route closure at hour 2, after the prefix is sealed.
- `get_p0_shared_world_trace({scene_id})` returns the bounded scene ledger and final authoritative snapshot.

The room graph is Junction→Inn (main), Junction→Covered Passage→Inn (side). Weather is a world attribute that changes from clear to storm at hour 2. Only a real `look` by an actor at the Junction produces a receipt-derived weather observation; weather triggers never grant character knowledge. Physical movement checks native Exit traversal only. Meeting is physically legal whenever A and B share the Inn; an author-goal witness is latched only if the meeting occurs during storm after B observed storm. The deadline is fixed at hour 48.

## Reproduction status

`tools/planner_p0_v0/shared_world/handtrace_runner.py --case clean|mainblockedrepair|allblockednegative` runs a bounded, explicitly scripted mechanics control trace and stores a unique JSON record here under `runs/`. Its output is labelled `SCRIPTED_CONTROL_NOT_PLANNER_OUTPUT`; it is not a Sabre-generated plan. The common-instance comparison is `tools/planner_p0_v0/shared_world/planner_runner.py --case clean|mainblockedrepair|allblockednegative`: it exports a live snapshot, invokes the original Sabre v0.8 wrapper with `-Xss8m`, executes only Sabre's grounded plan through native RPC, and preserves the full native trace plus partial failure evidence in a fresh run folder. The repair/negative cases use the first two actions of Sabre's clean plan as the sealed prefix, then let the testplayer close a real Exit and replan. Neither runner starts/stops Evennia or writes world state outside authenticated RPC.

`sabre_export.py` emits a snapshot-specific Sabre problem. `known_storm(B)` is a narrow predicate projected only from the native observation ledger; it is not full belief-state fidelity. The three text files in `tools/planner_p0_v0/shared_world/fixtures/` are deterministic input-state fixtures for planner debugging, not logs of executed actions; their post-prefix state does not encode which actor consented to a wait. Only `planner_runner.py` run evidence proves the exact original Sabre actions were executed and sealed in the native ledger. The official Sabre v0.8.0 parser accepts the emitted model. Its default 1 MiB JVM stack previously failed during compilation with a `StackOverflowError` whose CLI message was `null`; an 8 MiB stack produced native plans in the original CLI. The shared-world runner pins that stack parameter and records native status, plan, budget, problem hash, and actual game readback. A failure or budget limit remains such, not an `UNREACHABLE` claim.
