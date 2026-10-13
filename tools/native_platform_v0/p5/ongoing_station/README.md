# Ongoing station runner

This package contains the fixed case inputs, one-scene runner, evidence audit,
and readable replay for the opt-in P5 ongoing-station profile. The runner uses
the existing authenticated P3 control service, one-minute `step_world` calls,
`get_trace`, and the separate read-only P5 DB exporter. It does not issue NPC
commands or call `observe_actor`; actor choices and physical actions must come
from the native callbacks and world receipts.

## T1: author-free autonomy

`cases/suite.json` fixes seed, initial preset, world settings, and horizon. The
profile has `author: null`; the empty legacy bundle contributes no authored
constraint. T1 records both role IDs, each role's self-goal decisions and
commitment history, native settled receipts, and a subsequent distinct
self-goal that is either physically receipted or still has its matching native
pending execution. The audit returns `NOT_CERTIFIED` when any source is absent
or malformed; a planner proposal alone is insufficient.

The JSON exporter is scoped to the explicit scene ID and returns the persisted
objects under `scenes[].objects[]`. The raw export is copied byte-for-byte into
the run directory and hashed before auditing. Minute files retain only each
round's incremental delta; the full cumulative trace is saved once at the end.
Run directories are unique and failures are preserved.

Preflight is read-only:

```sh
python -m tools.native_platform_v0.p5.ongoing_station.runner \
  --case-id t1-no-author-autonomy
```

Creating a native scene requires the explicit `--execute` flag and a separate
operator gate. Offline case/audit tests do not authorize a run. The fixed suite
contains five final conditions: the author-null T1 control; a matched
mixed-author GTPyhop/event-driven pair; a separate result-only live-deferral
and future-edit case; and a resource-held negative. Each failure remains in its
own run directory. The earlier T1 smoke remains an early probe, not one of the
five final conditions.

## Fixed author and intervention cases

The matched pair activates at minute 5 and performs its future-only CAS at
minute 6. Version 1 combines an archive result constraint restricted to B with
a separate locked B-handover/A-archive sequence. The result planner's
`file_by_B` search and the lock's `return_then_file_by_A` requirement must be
recorded as incompatible; that conflict is not an actor offer. Version 2
changes only the archive binding's filer from B to A. The bundle constraints,
deadline, permissions, and locked-sequence hash remain fixed. The audit checks
the v1 conflict, v2 method compatibility, obsolete projection identity, and
exact lock-source/sequence/grant provenance on physical receipts. It does not
claim cancellation of an NPC task that was never offered in v1.

T4 is a separate result-only GTPyhop episode so an actual offer can reach an
actor with a live routine commitment. Version 1 binds the archive goal to A;
the actor's `AUTHOR_OFFER_DEFERRED` history must name its active route
commitment. After the preserved minute-7 move, a minute-8 future edit changes
the filer from A to B. The audit requires a real `CANCELLED_STALE` transition
for the old undispatched suffix and evidence that the movement receipt was
retained. This is task-lifecycle evidence, not a scripted rejection or an
interruption of a running world action.

T6 issues the existing generated-player `get courier_supply` command at minute
1, before NPC callbacks, and leaves the item with the player through minute 24.
It is an initial resource-held negative, not a midstream disturbance. The
audit verifies the actual command receipt and final persisted item holder, A's
still-configured but unfulfilled target, and B's independent native route
receipts. No object location or inventory is edited in the database.

## Runtime ownership and role goals

The nested, validated `AuthorBundle` remains the only source of story goals. The
`ongoing-station-author-v1` wrapper binds those existing constraints to registered
control modes and immutable task grants; the station projection is derived from
that source and is not separately edited. A sealed-ledger controller uses the
existing story-process GTPyhop planner to turn a currently applicable constraint
into future actor task offers. The NPC callback receives only its eligible offers
and the projection identity; it builds its own local view through P3
`observe_actor`, never from the controller's global world snapshot.

Each actor keeps its own goal/commitment history and current commitments
(`ACCEPTED`, `IN_PROGRESS`, `SUSPENDED`, `SETTLED`, or terminal expiry evidence).
An existing commitment is retained while feasible; lost local item evidence
suspends it without erasing it, and later local re-observation may resume it. A
competing offer records a concrete defer reason when work is active or the exact
item is not locally available. There is no first-invitation refusal rule or
synthetic refusal event. Commitments settle only from a new matching native
receipt, after the receipt frontier captured when that commitment was accepted.

Own tasks and author tasks enter the same opt-in P3 actor task planner. P3's
pinned GTPyhop runtime, actor-local known-exit graph, and route helper are reused;
the station task methods decompose delivery/archive, handover, and real route
activity into one proposed native primitive. P3's existing pending-action
dispatcher remains the only place that executes move/get/drop, with an opt-in
give operator for a registered visible recipient. Completion comes from the
resulting Evennia state and receipt, not from the HTN prediction. A routine route
is a real two-leg out-and-back movement commitment: its first waypoint does not
settle the goal, and only its own ordered, commitment-tagged receipts for both
waypoints complete it. An author offer arriving between legs is logged as
deferred against that still-active commitment; no refusal is scripted.

The method reuse boundary is deliberate and narrow. The existing pinned
GTPyhop 2.0.2 runtime/DFS, P3 actor-local observation, known-exit route helper,
pending-action dispatcher, Evennia world validation, and native receipt
structure are reused. The station does **not** reuse an existing P3
delivery/handover task-method domain: `deliver_supply`, the two-leg
`routine_route`, `archive_note`, and `handover_note` decompositions and the
`file_by_B` / `return_then_file_by_A` story methods are newly written for this
profile. Existing `get`/`move`/`drop` operators and the registered `give`
operation remain the low-level execution boundary. Event-driven planning is a
separate candidate-selection policy over the same sealed state and guards; it
does not use the high-level GTPyhop search. Nothing here ports Praxish, adds a
second pathfinder, infers psychological utility weights, or claims a general
BDI architecture. Other new work is the strict author binding/projection,
future-version CAS, actor-local commitment arbitration/history, typed native
readback, and their integration and tests.

Current source footprint (not net-new LOC, effort, or a performance measure):
the five core station modules `actor/controller/goals/model/native` total 1,960
lines; runner/audit/replay total 1,144; the four focused station test modules
total 1,489. These counts exclude the P3/P5 service and dispatcher integration,
shared story-process planner, case data, and documentation. They include schema
validation, provenance, and evidence-boundary checks as well as behavior.

## 2026-10-13 execution and source provenance

The saved T4 prefix is important to interpreting the result. At minute 6, B's
result-only `PLANNER` handover offer was deferred against a live SELF
`routine_route`, with native route receipt `p3:7525:0:13` in the blocker
evidence. At minute 7, the offered handover give was actually attempted but
Evennia rejected it because A was not visible;
the execution-settlement record `p3:7525:0:19` is `WORLD_VALIDATION_REJECTED`,
`dispatch_succeeded=false`, and is **not** a successful/settled give receipt.
At minute 8, the legal CAS edit changed only the filer from A to B, listed the
old v1 request in `invalidated_offer_ids`, and marked its undispatched
handover suffix `CANCELLED_STALE`. The pre-edit SELF route receipts remained in
the commitment frontier/history. B later filed the same note at minute 10 with
receipt `p3:7525:0:28`. This is cancellation of an unexecuted suffix, not a
claim that an in-flight physical action was interrupted. The saved v3 offline
audit binds this conclusion to the full scene trace and DB readback.

Native run source manifests are per-run working-tree byte sets, not one shared
commit identifier. The final T1 and T6 runs and the two pre-fix author runs use
file-set SHA-256 `43941d01c13d43c70c4aeaddbb1504235dc3a3895eb165613555d99dc6561b23`.
The repaired GTPyhop author run uses
`6275afc73cd642bd834c8efb7dc0abd7378e34f21aa89d8d6323e6053028d3da`; relative
to the preceding source set, only `ongoing_station/controller.py` and
`test_ongoing_station_native.py` changed. The matched event-driven run and T4
use `85fb9d752350a62c774900521614c19aaf1bd7d31602afd9d26cd421e07aee84`;
relative to the repaired GTPyhop run, only `ongoing_station/audit.py` and
`test_ongoing_station_runner.py` changed. Thus the two matched native runtime
paths have the same controller/actor code; the full source manifests still
differ, and no cross-version runtime or performance claim is made. The
final offline audit bytes are SHA-256
`9fe219389efa210929312ee5d8ccd926eb7b1812274eb6c40a361b05ce04b480`; the
package contains an exact `audit-source-v3.py` carrier and five hash-bound
offline audit rechecks.

## Reserved LLM insertion points

No LLM call is part of the current native runtime. Future experiments may place
one model boundary between author prose and the registered `AuthorBundle`
constraints, and another between an actor's local observation/commitment history
and a candidate goal explanation. In both cases the current strict schemas,
actor-local visibility, native action validation, and receipt-based settlement
remain authoritative. No model download, embedding index, fine-tuning, or model
generated world effect is included here.
