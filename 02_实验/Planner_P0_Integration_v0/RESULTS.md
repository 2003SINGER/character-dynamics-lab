# Planner P0 Integration v0 — Results

> Status: **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW** (bounded checkpoint; not CLOSED). This file is the sole result owner for this route. Thin live-mode, idempotency, append-only ledger, and temporal-history probes are recorded below. The complete traditional system remains unfinished.

## Scope

This is a bounded vertical development checkpoint: high-level Sabre planning, necessary GTPyhop primitive refinement, one Evennia clock and ledger, TypedIR monitoring, and local/high-level repair. The fixture uses a fixed author goal, hand-authored Sabre domain/utility, and corresponding TypedIR monitoring. It does not implement a general P5 AuthorBundle-to-Sabre constraint compiler. It reuses the P3 GTPyhop/TypedIR components, but does not splice in the old P5 clock/ledger semantics.

The primary direct-control path is joint orchestration. The conditional case is a fixed own-goal task-offer gate followed by a trusted-driver seam; it is not an independent NPC decision loop. The free case is an ACL negative control, not an autonomous-NPC condition. The prior P5 shared-supply failure remains unresolved and is not hidden or reinterpreted by this route. Three completed direct-mode cases demonstrate only this bounded vertical integration, not the full intended traditional system or autonomous agency.

## Implementation and fixed limits

- Sabre v0.8.0; method `bf`, cost `t`, heuristic `h+`; seed `20261011`.
- Sabre bounds: 200 visited nodes, 5,000 generated nodes, 5,000 ms native time limit, 12 s wrapper timeout. P3 primitive refinement: 500 visits / 0.25 s. `elapsed_native_ms` is Sabre-reported native search time, not full integration wall time.
- The same per-file `source_sha256` manifest is recorded in all five final `run.json` files below; each manifest is the source-hash authority for that run.
- CI: offline contract and projection checks are wired in `.github/workflows/planner-p0-contracts.yml`. They do not install or run Evennia, Sabre, a JDK, or a server, and are not native end-to-end evidence. The native run evidence is recorded below; exact-head workflow status is to be checked in GitHub Actions.

## Run inventory

| Case / run ID | Goal time / status (simulation minutes) | Interpretation / evidence |
|---|---|---|
| `direct-clean` — [`p0i-direct-clean-20261011T070448Z-08f0b6`](runs/p0i-direct-clean-20261011T070448Z-08f0b6/) | `COMPLETED`; delivery 3, B observes storm 7, meeting 8 | Direct joint-control vertical path; TypedIR `SATISFIED`; read-only DB/native-ledger readback passes. |
| `route-repair` — [`p0i-route-repair-20261011T070455Z-4c68c6`](runs/p0i-route-repair-20261011T070455Z-4c68c6/) | `COMPLETED`; delivery 5, look 10, meeting 11 | One genuine blocked-route execution failure; held item, task ID, and progress retained. Macro forecast: 3 minutes; actual: 5, including the failed attempt and one additional side-route minute. A and B use the side route. TypedIR and readback pass. |
| `high-causal-replan` — [`p0i-high-causal-replan-20261011T070503Z-ad8f06`](runs/p0i-high-causal-replan-20261011T070503Z-ad8f06/) | `COMPLETED`; delivery 3, B observes storm 8, meeting 9 | Two cloud seeds; the first pending cloud is dissipated before becoming storm, then high-level replanning preserves the executed prefix. TypedIR and readback pass. |
| `conditional-consent-smoke` — [`p0i-conditional-consent-smoke-20261011T070510Z-9f5568`](runs/p0i-conditional-consent-smoke-20261011T070510Z-9f5568/) | `SEARCH_BUDGET`; 200 visited / 366 generated; clock 0, no execution | Fixed own-goal offer gate plus trusted-driver seam only. Budget exhaustion is not unreachability and does not demonstrate NPC agency. Structural readback passes; no task-success claim. |
| `free-acl-negative` — [`p0i-free-acl-negative-20261011T070511Z-fcca15`](runs/p0i-free-acl-negative-20261011T070511Z-fcca15/) | `NO_PLAN_EXPORTED_DOMAIN` plus native `ACL_DENIED`; clock 0 | ACL negative control; no autonomous NPC loop. No-plan means no plan in this exported domain, not world unreachability. Structural readback passes; no task-success claim. |

For the three completed cases, the authored goal event occurs at the time listed above; the evaluation then drains/seals the trace through minute 24 to close the monitoring window. That evaluator drain is not evidence of NPC natural-life behavior, and its wait actions must not be interpreted as a character policy.

## Independent database and ledger audit

Each of the five final runs has a `parent-readback.json` with `pass: true`, `database_mode: read-only/query-only`, and all applicable recorded checks true. The audit uses parent read-only SQLite and native-ledger readback; checked sequence/frontier/seal integrity, unique events, actor/item database readback, scene identity, and (where applicable) native goal positions and one real delivery/meeting. This is a database/ledger evidence-integrity audit, not a claim that each planner case achieved the author goal: the conditional and free cases execute no task. The three completed direct cases also have complete sealed ledgers and TypedIR `SATISFIED`; budget/no-plan controls remain `PENDING` on the author-goal monitor as expected. The readback's action counts filter for `accepted && settled`; they are not counts of every world event. Thus the high-causal raw ledger contains one `CLOUD_DISSIPATED` player-command event (whose accepted/settled fields are absent) and the run contains a settled `MUTATION_RESULT`, while `parent-readback.json` reports zero `CLOUD_DISSIPATED` in its accepted/settled action counts. Use the raw event ledger for this world-event count.

## Thin live contract probes

[`contract-20261011T070908Z-91a83cb6`](live-contract-probes/contract-20261011T070908Z-91a83cb6/) records **23/23 checks PASS** across 12 checkpoints (9 direct-mode, 3 conditional-mode). It verifies: conditional `accept_task=false` is refused without binding a task; conditional forced dispatch is ACL-denied without a clock tick; direct forced dispatch is explicitly `author_forced` rather than consent and a native GET settles with a receipt; same-request/same-payload replay is a no-op; same request ID with altered payload is rejected without mutation; a seed creates a pending process, the server clock later causes storm, and dissipation after storm cannot reverse the settled weather. The probe does not start a server. Its config, complete checkpoints/traces, and separate source hash manifest are in the linked directory.

## Failures, retries, and preserved evidence

The earlier route-repair attempt [`p0i-route-repair-20261011T070211Z-e16fb3`](runs/p0i-route-repair-20261011T070211Z-e16fb3/) failed with a `NameError` after the contract split; it is an adapter/code failure, not a planner or native-world result, and its directory is retained. The earlier direct-clean run [`p0i-direct-clean-20261011T070142Z-af1d62`](runs/p0i-direct-clean-20261011T070142Z-af1d62/) is also retained as a prior run. Original Sabre preflights remain under `02_实验/Planner_P0_v0/sabre_baseline/evidence/integration-v0/`: they include a missing-fluent parse error (`met_witness`), a malformed Fluent expression (`Unexpected "("`), and conditional author/character-enumeration preprocessing wrapper timeouts at 5 s and 12 s. These failures are retained; the five final cases keep the declared 5 s native and 12 s outer wrapper limits rather than expanding budgets. None of these earlier attempts is substituted for or merged into the five final source-frozen run IDs above.

## Interpretation and limits

The five final run cases plus the offline suites and thin live contract probes support **DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW**, not CLOSED. Reported offline test totals: integration native contracts 9/9, integration projection/monitor 7/7, P3 53, P5 43, and original P0 7+5 all pass. These are offline tests, not a replacement for live evidence; exact-head workflow status is to be checked in GitHub Actions. The five run manifests contain the same source-hash map; canonical JSON SHA-256 of that map is `238db6e3df436cac09549de31f0d86f400085f1a335a602e64f2d5a56ed35038`. Do not infer general planner completeness, a completed P5-style author-constraint compiler, independent NPC agency, a solution to the P5 shared-supply failure, research effectiveness, or player validity from this bounded development route.
