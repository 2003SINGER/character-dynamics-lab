# System Baseline v0 — M3 result report

**Overall: `PARTIAL` / `READY_FOR_INDEPENDENT_REVIEW`.** M1's four bounded native scenarios and one stale-candidate rejection control are complete. M2's three local model calls all ended `INVALID_RESPONSE`; no candidate was dispatched to P5. This report does not claim complete natural-language binding, correct residual handling for the negative request, general planner competence, or NPC-behavior efficacy.

## M1 — bounded native integration

The existing P5 Evennia instance was restarted once by the parent to load the native candidate guard and trace envelope. The four fixed cases below and one adversarial negative used fresh scenes in that same existing database. The Sabre process only selected `open_main_passage` or `open_side_passage`; native P5 checked bundle version, scene, action identity, next-minute boundary and sealed frontiers, then enforced its existing permission/budget rules and produced the actual world receipt. P5's own A/B callbacks and social fixture remained the only source of delivery and response outcomes.

| Case | Native result | Evidence |
|---|---|---|
| Main-route target, default reject preset | `hard_status=SATISFIED`; main route open; both deliveries settled at minute 6; rejected-note branch eligible | `runs/C1-C2-main-C3-reject-20261011T164634Z-b48bff/` |
| Matched side-route target, same reject preset | `hard_status=SATISFIED`; side route open; both deliveries settled at minute 16; rejected-note branch eligible | `runs/C1-C2-side-C3-reject-20261011T164643Z-5b5c12/` |
| Same side bundle/state, accept preset | `hard_status=SATISFIED`; side route open; both deliveries settled; accepted-note branch eligible | `runs/C3-side-accept-20261011T164653Z-16ca2c/` |
| Future edit plus player perturbation | Version 1→2 edit accepted at minute 2 after a sealed prefix; native player `get` at minute 2 and `drop` at minute 3 both settled; newly added side-route goal satisfied; both deliveries settled at minute 19 | `runs/C4-C5-edit-player-perturbation-20261011T164702Z-5b228a/` |
| Same-minute stale-candidate negative | Edit to v2 accepted; v1 candidate received native `STALE_CANDIDATE`; neither route opened | `runs/stale-edit-negative-20261011T164712Z-54d4ac/` |

All five final cases have a separate P3 DB export with explicit scene selection and a recorded exporter artifact SHA-256. `run_status=COMPLETE` means the P5 horizon and event/snapshot prefix completed; only the per-constraint verdicts above are used for hard-goal outcomes. Branch eligibility comes from the sealed social response receipt; the branch effect is content-only, not a world effect.

The first implementation attempt is also preserved rather than overwritten. It completed four 24-minute runs but dispatched no Sabre choice: the runner incorrectly compared the native result text (`Success!`) to the nonexistent literal `PLAN_FOUND`. The normalized status was already correct (`PLAN_FOUND_NOT_EXECUTION_EVIDENCE`); the bug was in the separate dispatch condition. Those traces show the resulting violations. Its stale-control artifact is an explicit `INCOMPLETE_ERROR`. The corrected second batch is the result set above. This failure history is included in the evidence pack and its earlier runner hash differs from the successful source hash.

## M0 flow and seam

| Stage | Authority / data | Boundary |
|---|---|---|
| World and author state | Existing P5 Evennia scene, registered opportunity/actor catalog, versioned author bundle, native permissions and budgets | P5 remains the only world and the authority for accepting actions and producing receipts. |
| Observation | P3 reads the live trace envelope and sealed event/value/snapshot prefix from P5; it also exports scene-selected DB evidence after each run | A prefix is usable only when its sealed frontiers match the current minute. The independent DB export is a separate readback, not planner output. |
| Planning | The System Baseline adapter projects the current P5 bundle/world snapshot into a small Sabre problem with the registered `open_main_passage` / `open_side_passage` choices | Sabre selects among those route opportunities only. It is not a wrapper around the P5 finite planner and does not plan deliveries, social response, player actions, or edits. |
| Dispatch and outcome | Candidate carries scene/version/minute/frontier/action/opportunity identity; P5 rechecks it and then applies native permission/budget validation | Only P5 can accept/reject and mutate the world. Receipts and monitor verdicts—not the predicted plan—establish observed outcomes. |

Non-route hard obligations stay visible to the native monitor and NPC/callback chain; the route-only Sabre projection cannot establish that the complete authored scenario is satisfied. `hard_status=SATISFIED` in the fixed cases refers to the bundle's observed typed monitor verdicts, not completeness of Sabre's planning model.

## Reproduction and provenance

From the repository root:

```sh
_local_data/native_platform_v0/evennia/venv/bin/python -B -m unittest discover -s tools/system_baseline_v0/tests -v
_local_data/native_platform_v0/evennia/venv/bin/python -B -m tools.system_baseline_v0.run_suite
```

The suite input is [cases/suite.json](../../tools/system_baseline_v0/cases/suite.json), SHA-256 `823c980489d9a4be45f77a7f618e21d1821d25c793217b571066c0b6bf27c58d`. Each run's `case.json`/`result.json` records baseline Git `50eb855` and hashes for the source files used; the successful runner hash is `dcf544af526cc0baad73cc536122ed0130ae0b8f837ea58cfdd5ba6fbee91a47`. Do not interpret the baseline commit as the executed implementation revision: this run used the listed, uncommitted working-tree sources.

The full run tree, including both failed and successful attempts, remains uncompressed under `runs/`. A review copy of all 293 files (190,826,542 uncompressed bytes) is in `public_evidence/system-baseline-runs-20261011T165402Z-9ee51f.tar.gz` (SHA-256 `46bd9f55fc43a85b0d131e61daa60fb93384f122ca71d9fa512fd1bff5c646b6`). Its adjacent manifest records per-file SHA-256 values, per-run source hashes and a successful member-by-member archive round trip. The compact machine-readable result is [public_summary.json](public_evidence/public_summary.json).

## Scope limits

- Sabre's exported domain covers only the two registered route-opening opportunities. Delivery, note response, edits, and player commands are not Sabre actions; delivery and social requirements remain native-monitor obligations and were observed through P5 receipts.
- The route projection supports hard `EVENTUALLY true` goals only when the next dispatch minute lies inside the absolute window. Other temporal operators, route closing, expired/unreachable goals and unregistered requirements stay explicit residuals; a residual prevents a whole-bundle success claim.
- The stale guard is a narrow freshness and identity check, not cryptographic authentication. Only the authenticated local P3 RPC path and the fixed local case set were exercised.
- C2 changes only the route target in the matched bundles; C3 changes only the registered native social preset. This is a small deterministic development matrix, not statistical evidence or a causal claim about NPC behavior.
- M2 natural-language binding was attempted but not accepted. Any future schema-valid candidate would still require a separate requirement-by-requirement semantic audit.
- M2 produced no accepted author binding and provides no evidence of complete NL coverage; its outcomes must remain separate from the M1 native observations.

## M2 — local binding attempts (not accepted)

Three calls were made against the local OpenAI-compatible endpoint using `qwen3-4b-q4_k_m`, temperature 0, 2,048 max tokens, and `enable_thinking=false`: an initial positive request, one permitted positive retry, and a negative request. All three returned raw model content, so this was not a connection failure; all three were rejected before any native run. The saved `outcome.json` files are the original adapter outcomes. The separate `offline_revalidation.json` files were added later by stricter, byte-preserving review logic (except for stripping a closed empty `<think>...</think>` prefix); they do not overwrite or replace those original outcomes.

| Call | Original adapter outcome | Later strict offline revalidation | Usage / elapsed |
|---|---|---|---|
| Positive, initial | `INVALID_RESPONSE: JSONDecodeError` | After empty-think-prefix normalization, duplicate JSON key `id`; still invalid | 1,725 prompt + 584 completion = 2,309 tokens; 29.547 s |
| Positive, sole retry | `INVALID_RESPONSE`; candidate bundle null because all four requirement refs pointed to nonexistent candidate refs; typed validation failed | Duplicate JSON key `constraints`; still invalid | 2,223 prompt + 522 completion = 2,745 tokens; 27.173 s |
| Negative request | `INVALID_RESPONSE: JSONDecodeError` | JSON syntax error at character 1771; still invalid | 1,780 prompt + 1,380 completion = 3,160 tokens; 56.688 s |

Total: 5,728 prompt tokens, 2,486 completion tokens, 8,214 tokens, and 113.408 seconds (about 1m53.4s). All three costs are `LOCAL_UNPRICED`; no monetary cost is inferred. The negative call did not yield a valid hard residual, so it is not evidence that the model correctly represented or rejected the worsened hard relation. These failures establish a local output/structure-generation and compatibility problem for this narrow prompt/API/configuration, not a failure of Sabre planning or P5 execution.

Raw requests, responses, original outcomes, configs, usage metadata, and later offline revalidation remain in the repository-local, ignored path `02_实验/System_Baseline_v0/runs/m2-llm-20261012-positive-negative/`; that raw directory is not a GitHub link. The scrubbed review archive is [llm-binding-20261012.tar.gz](public_evidence/llm-binding-20261012.tar.gz) with its [manifest](public_evidence/llm-binding-20261012.manifest.json). Parent evidence review is recorded in [parent-evidence-review.json](validation/parent-evidence-review.json), including archive member/hash checks, three original invalid outcomes, zero native dispatches, and the explicit finding that the negative is not correct-residual evidence.

The final bounded regression report is [validation/20261012T-final-bounded-regression-03/summary.json](validation/20261012T-final-bounded-regression-03/summary.json), with its [raw test log](validation/20261012T-final-bounded-regression-03/raw-regression.log), [source hashes](validation/20261012T-final-bounded-regression-03/source-sha256.txt), and [LLM raw-call audit](validation/20261012T-final-bounded-regression-03/llm-raw-call-audit.json). It reports 133/133 passing across System Baseline 25, P5 43, P0 integration 7, P0 baseline gate 6, author binding 22, and TypedIR trajectory constraints 30; zero failures/errors. This is bounded regression and raw-evidence verification, not evidence that M2 works or that another native simulation was run.

## CI for implementation commit `0e973ea`

- [planner-p0-contracts](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38158475962) — success.
- [native-platform-p3](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38158475869) — success.
- [runtime-regression](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38158476174) — partial failure: the sole failing legacy `e0-keyledger-contract` case was H02, where planner outcome `BUDGET` differed from expected `UNREACHABLE` (37/38 unit checks; 13/14 fixtures). The other five jobs passed, including C++ configure/build/CTest/reference and repository-health checks.

This keeps the overall report `PARTIAL`. The legacy budget expectation was not changed or renamed, no old budget was tuned, and no retry was used to turn the failure green. The independently checked local audit summary is [validation/ci-0e973ea/summary.json](validation/ci-0e973ea/summary.json); the captured H02 failure output is [actual-failure-log.txt](validation/ci-0e973ea/actual-failure-log.txt).

## Closeout

M1 shows this specific route-selection seam can choose between two matched native opportunities, pass a same-minute stale candidate to native rejection, and observe downstream receipts/readback in the fixed scene matrix. It does not show Sabre planning the complete authored story. Non-route hard obligations remain native monitor/NPC-callback responsibilities, and the route-only planner cannot certify them prospectively. M2 remains unresolved after three invalid outputs. The next step is to discuss the observed format/reference-generation bottleneck before deciding whether to modify the binding contract or make any further model calls; no additional call or P6 scope is authorized by this report.
