# Sabre upstream baseline runs

This evidence package calls the official Sabre planner without modifying its algorithm. The upstream source and benchmark checkouts are kept in the ignored project-local `_local_data/planner_p0_v0/` directory; local runtime outputs are stored under `evidence/` so each bounded run can be reviewed and reproduced.

## Official small-instance reproduction

The official `macguffin.txt` benchmark instance was run twice with Sabre v0.8.0, using best-first search, temporal cost, sum-graph heuristic, epistemic limit 1, a 200 visited-node cap, and a 5,000 ms native time limit. Both runs returned the same grounded plan:

1. `walk(Tom, Home, Market)`
2. `buy(Tom, MacGuffin, Merchant)`

Both runs achieved author utility 1, visited 10 nodes, generated 57 nodes, and reported 4 ms native time. The verbose output contains the native explanations: Tom's walk is explained by the subsequent purchase; the purchase is explained by Tom's MacGuffin utility and Merchant's money utility. The official README's example plan is reproduced. This verifies the small official example only; it does not reproduce the paper's evaluation or all benchmark configurations.

The immutable run folders are indexed below. Each folder contains its exact configuration, full stdout/stderr, and parsed result record.

- [run 1](evidence/20261011T0535Z-macguffin-01/)
- [run 2](evidence/20261011T0535Z-macguffin-02/)

The official benchmark problem SHA-256 is `0b8f2311b4bca9083e51b9d724767d22b15f83feb414e346a12f79af02316957`. Upstream provenance: [Sabre source](https://github.com/sgware/sabre), [Sabre benchmark collection](https://github.com/sgware/sabre-benchmarks).

## Shared-world adapter

The wrapper contract, invocation flags, returned fields, and conservative status meanings are documented in [the adapter README](../../../tools/planner_p0_v0/sabre_baseline/README.md). In a world run, ground the native problem from a versioned snapshot and pass the same pinned planner version, utility target, search method, cost measure, heuristic, epistemic depth, and budget to every compared condition. Save the real snapshot-derived problem hash. A wrapper timeout or native search budget limit remains incomplete; it is not an unreachable proof.

### Initial shared-world fixture checks

The shared-world module supplied three deterministic synthetic-state Sabre problem fixtures (not live Evennia snapshots). All runs used the same Sabre v0.8.0 build and configuration (`bf`, temporal cost `t`, `h+`, epistemic limit 1, 200 visited nodes, 5,000 ms native search limit, author temporal limit 48, JVM stack `8m`). The explicit stack setting is needed because the normal-stack compilation raises a `StackOverflowError` in Sabre's recursive `Utilities.toArray`; see the adapter README. It changes the Java thread-stack budget, not the planner algorithm.

The [default-stack failure record](evidence/shared-clean-default-stack-failure-01/) preserves the CLI's `Error: null`. The attached [`diagnostic.log`](evidence/shared-clean-default-stack-failure-01/diagnostic.log), captured through the external `Session` API wrapper, identifies `StackOverflowError` during `Session.getCompiledProblem()` in `Utilities.toArray`; the planner search never starts. Therefore the failure is neither `NATIVE_NO_SOLUTION` nor a search-budget result.

| Fixture | SHA-256 | Native result | Grounded plan / interpretation |
|---|---|---|---|
| [clean initial](evidence/shared-clean-xss8m-01/) | `9c1c6e250a7f0aab1fa08ca56e5c9fa39bf482287e90ae057734590313398f50` | Success, utility 1; 18 visited / 264 generated | A reaches Inn; B observes rain at H2, travels via the open route, and meets by H5. |
| [main route blocked](evidence/shared-mainblocked-xss8m-01/) | `505c70b00805f573cdb7e414729810a8bcedbaa85b38c49f01e691376694fda4` | Success, utility 1; 10 / 71 | In the synthetic H3 route-closure state, B observes, takes SidePassage to Inn, then meets by H7. |
| [all routes blocked](evidence/shared-allblocked-xss8m-01/) | `7ea8d0f882cbec54db2dbdeaa4db9e9c2d3a192494a42c61922e7795c812bd31` | Sabre native `No solution exists`; 0 / 0 | With all routes closed in the synthetic state, no plan is returned. This is the native result for this finite fixture, not a general theorem about other states. |

These are deterministic synthetic replanning-state fixtures, not evidence of actual execution against Evennia or a full game integration. Each run folder retains the exact runner configuration, problem hash, stdout, stderr, and parsed result. The blocked fixtures encode the projected state that would result from a hypothetical sealed prefix with A at Inn and B waiting through H2, followed by one world tick to H3 before route closure. This is physically/time/knowledge-equivalent to the clean Sabre plan after A moves and waits through H2, but the action history differs: Sabre's clean plan chooses `wait(A, H1, H2)`, not `wait(B, H1, H2)`. Do not describe the blocked fixtures as a replay of an executed clean-plan prefix; native snapshot/export integration remains separate work.

### Historical Sabre v0.7 JAR startup failure

The historical JAR bundled with `planning-stories-neurally` was retained as-is and attempted on the approved project-local Java 21 runtime. It exits at startup with `NoClassDefFoundError: edu/uky/cs/nil/sabre/prog/ProgressionPlanner$Method$4`; the bundled JAR SHA-256 is `b74d1f73cad5a68a077794a99d97a7b0348739dcf0958b5b3d42c88e8ac2d526` (class-file major 64). The full evidence is [here](evidence/historical-v07-gramma-jar-startup/). This is an incomplete upstream artifact, not a planner search failure, so the original v0.7 route is not admitted from this JAR run. Do not substitute v0.8 results as same-version comparisons.
