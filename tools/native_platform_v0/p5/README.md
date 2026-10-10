# P5 author bundle core

P5 adds a small, opt-in author layer over the existing native Evennia/HTN and Ensemble runtime. The Python core is in `bundle.py`, `monitor.py`, and `planning.py`; focused tests run with:

```sh
PYTHONPATH=.:tools:tools/native_platform_v0/bridge PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/native_platform_v0/p5/tests -v
```

## Bundle surface

`load_bundle(raw_or_path, registry=None, entities=None, physical_budget=2)` accepts a JSON object (`native-author-bundle-v1`) and returns an immutable `AuthorBundle`. It compiles only registered event counts, event ordering, and the `holding` / `route_open` state predicates into the existing trajectory TypedIR. Stable role aliases are `A`, `B`, `note`, `courier_supply`, and `resident_parcel`; a scene may bind those aliases to its own stable entity IDs.

The only author-controlled world opportunities are `open_main_passage` and `open_side_passage`; NPC responses cannot be forced. At most one opportunity may be used, with an initial physical cost ceiling of 2. Unsupported event or state semantics fail with `SEMANTIC_GAP`, rather than being interpreted as text instructions. Story branches may be guarded only by a committed `note_response` (`accepted` or `rejected`); the attached storylet is content-only and cannot execute world effects.

`BundleStore.replace(raw, expected_version, now=...)` is an atomic compare-and-swap: the bundle ID is stable, the version increments by exactly one, permissions cannot expand, and a new requirement cannot start in the past. Completed or closed requirements cannot be rewritten; service code retains prior-version verdicts rather than retroactively replacing them.

## Evidence and planning boundary

`evaluate_bundle(bundle, trace)` consumes an existing TypedIR `Trace` built from sealed native ledger receipts and committed Evennia snapshots. Proposals, authored storylet text, and planner candidates are not monitor evidence. Missing evidence remains pending or indeterminate until the relevant prefix is sealed.

`plan(bundle, symbolic_state)` enumerates `NO_OP` and the two registered passage opportunities. It reports goal-specific dependencies, cost and deadline lower-bound checks, unsupported/conflicting goals, and conditional candidates. Opening a passage settles at the current simulated minute; `route.min_minutes` is a separate conservative path/task travel lower bound, not door activation latency or an NPC arrival prediction. A passage may be a prerequisite for an A delivery or later interaction; it does not guarantee delivery, contact, intent, or B's response. B's own delivery remains a parallel NPC obligation. A physical goal that cannot be supported by the permitted action is not silently treated as satisfied.

This is project glue, not a replacement for the mature components: GTPyhop plans each NPC's authored task, and the native Ensemble engine supplies social intent/response behavior. P5 does not fork an Evennia world for planning and does not reproduce a full DM/HTN method. Its finite passage enumeration is a small project-specific author-opportunity selector; lower-bound times are symbolic assumptions, not NPC-arrival predictions. No general method or behavioral validity claim follows from this interface.

## Native scenario integration

The service layer is exposed through the existing P3 control service as `run_p5_scenario`; it creates the bounded shared-world scene, runs native NPC callbacks, applies scheduled player/author interventions and bundle edits, and returns receipts plus trace data. This is a finite development integration, not a general scene editor or durable simulation framework. Current scenario/matrix and evidence status belong to [P5 RESULTS](../../../02_实验/Native_Platform_P5_v0/RESULTS.md).

The command below assumes the repository's locally initialized Evennia database/game, project venv, and a fresh loopback service process. The quota cap is 16; this 12-scene suite needs 12 free slots. A public checkout alone does not provide that local environment. If calls have already consumed quota, restart the same configured instance through the existing `stop_loopback.sh` / `start_loopback.sh` helpers; do not delete scenes/database or create another server. Then run the fixed development suite:

```sh
PYTHONPATH=.:tools:tools/native_platform_v0/bridge _local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p5.runner \
  --suite 02_实验/Native_Platform_P5_v0/bundles/dev-matrix-v1.json
```

The runner records each response and performs a separate persisted-database export by default. Each artifact can then be structurally checked without rewriting it:

```sh
PYTHONPATH=.:tools:tools/native_platform_v0/bridge _local_data/native_platform_v0/evennia/venv/bin/python -m tools.native_platform_v0.p5.audit \
  02_实验/Native_Platform_P5_v0/runs/<run-artifact>.json
```

The audit is an integrity/contract check, not a score for method quality or NPC realism. The bundle edit mechanism updates planned identity/version under CAS; it does not create durable goal progress, erase spent opportunity cost, or rewrite earlier verdicts.
