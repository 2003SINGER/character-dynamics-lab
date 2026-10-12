# Planner Adapter Integration v1

This package is a bounded adapter experiment: P5 remains the only world, clock,
and receipt authority; Sabre searches a finite causal candidate domain; and the
existing P5 actors continue to plan through their native actor-local GTPyhop /
Ensemble callbacks. A Sabre plan is not an execution receipt, NPC acceptance, or
proof that the author bundle is satisfied. Only the two registered P5 route
opportunities can be dispatched by this adapter; delivery and social effects
remain conditional predictions until P5 records them.

The fixed case matrix is in `cases/suite.json`. Its current bounded search
revision is `primitive-domain-r2`: best-first (`bf`), cost `t`, heuristic
`h+`, 10,000 visited nodes, 100,000 generated nodes, 5,000 ms native search
limit, epistemic limit 1, author limit 24, character limit 16, and a 30-second
process timeout. These are frozen experiment limits, not automatic tuning
targets. `BUDGET_LIMIT` means the search cap was reached; it does not establish
world-level infeasibility. `NATIVE_NO_SOLUTION` is the planner's result for the
rendered bounded domain, not a claim about all possible P5 behavior. Missing
runtime prerequisites or malformed evidence remain explicit errors; there is
no mock/runtime fallback in a native run.

## Checks and runs

Run the offline package contracts from the repository root:

```sh
python -B -m unittest discover -s tools/planner_adapter_integration_v1/tests -p 'test_*.py' -v
```

The tests do not start Evennia or dispatch actions. They use fixed bundle
fixtures, mocked RPC boundaries, and a small immutable extract of a real
minute-zero capture. The extract records its source run ID and original file
SHA-256 values; it is explicitly not presented as the complete run artifact.

The Sabre-only preflight can be invoked with:

```sh
python -B -m tools.planner_adapter_integration_v1.offline_preflight
```

It writes non-overwriting synthetic-domain artifacts under
`02_实验/Planner_Adapter_Integration_v1/validation/runs/`. Those artifacts are
parser/search diagnostics only, never native-world evidence.

The fixed native suite command is:

```sh
python -B -m tools.planner_adapter_integration_v1.run_suite
```

Only run it against the repository's owned, isolated Evennia/P5 development
world, using the repository's configured Evennia virtual environment, the
authenticated loopback P3 service at `127.0.0.1:14011`, and the pinned local
Java/Sabre installation expected by `sabre.py`. The suite creates bounded
scenes, advances the native clock, may issue the scheduled player/author
interventions and bundle edit, and preserves per-run outputs under
`02_实验/Planner_Adapter_Integration_v1/runs/`. It is not safe to point at a
shared or production world. A missing service, token, Java/Sabre installation,
or valid evidence stops the run; the suite does not substitute a fake world.
The current P3 process quota is 16 created scenes, while this suite expands to
17 (eight matched pairs plus one stale-version negative). Thus the one-command
invocation cannot finish under the current quota in a single service process.
For a complete run, invoke the existing `load_suite` and `run_case` APIs in
two batches, keeping each Sabre/Director pair together. From the repository
root, use the configured Evennia Python executable:

```sh
_local_data/native_platform_v0/evennia/venv/bin/python -c 'from tools.planner_adapter_integration_v1.run_suite import load_suite; from tools.planner_adapter_integration_v1.runner import run_case; _, cases = load_suite(); [run_case(case) for case in cases[:14]]'
```

Then use the repository's existing controlled stop/start helpers against the
same configured Evennia instance and database (do not delete scenes or
recreate the database). In the fresh process epoch, run the remaining matched
pair and stale-control case:

```sh
_local_data/native_platform_v0/evennia/venv/bin/python -c 'from tools.planner_adapter_integration_v1.run_suite import load_suite, DEFAULT_SUITE; from tools.planner_adapter_integration_v1.runner import run_case, run_stale_edit_negative; from pathlib import Path; suite, cases = load_suite(); [run_case(case) for case in cases[14:]]; stale = suite["stale_negative"]; run_stale_edit_negative(bundle_path=DEFAULT_SUITE.parent / stale["bundle"], edited_bundle_path=DEFAULT_SUITE.parent / stale["edited_bundle"])'
```

Start with a fresh process epoch and enough scene-quota headroom; original
scenes remain intact. Preserve every partial result. If no exact stale candidate
is available, the stale result is `STALE_CONTROL_NOT_EXERCISED`, not a passing
negative control. Report interrupted batches as incomplete; do not retry the
full suite to conceal quota exhaustion.

For current evidence, limitations, and the experiment's status, see the single
report at [`02_实验/Planner_Adapter_Integration_v1/RESULTS.md`](../../02_实验/Planner_Adapter_Integration_v1/RESULTS.md).
