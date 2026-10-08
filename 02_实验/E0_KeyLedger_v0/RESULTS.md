# E0-KeyLedger-v0 results

## Formal run

- macOS formal run outcome: **14/14 fixture tests PASS**. Cross-platform CI is currently **NOT_PASS_BUDGET** (Ubuntu H02 planner hits the fixed 2-second cap while the independent Oracle exhausts); do not describe overall E0 as passed. This is finite-software evidence, not NPC/player validity or a claim about psychological mechanisms.
- Run: [`result.json`](../../runs/e0_keyledger_v0/formal/20261008T123731Z_all_formal-4caa088-20261008/result.json), created `2026-10-08T12:37:31Z`; SHA-256 `e66d29315a59917f75e700d13b7d7b7f7e22c54a39481f742306e7db113ba64c`.
- Code: `4caa0885f4b27f07e0695ddb2f530ae9656e4baa`; E0-scoped tree clean. Protocol freeze: `e411ff45f67855e58d047fd37332b6896db5b8fe`; protocol SHA-256 `0837eaa2e7b53e5aa00578534b714f38b055cc6389191ca7c5687eb5f3b1c7f9`. The run JSON records per-source hashes.
- Environment/config: Python 3.12.14; macOS 27.0.1 arm64, Apple Silicon, 8 CPUs, 16 GiB; one process/thread; fixed 10,000-expansion / 2.0-second budgets.

Each search cell gives `status / expansions / wall-seconds / exhausted`; witness cells also give simulated cost and absolute completion time (`cost@t`). Planner's `exhausted=false` for successful cases is expected: it proves the shortest witness, while the independent Oracle exhausts. Actual replay Monitor evidence is listed separately from search outputs.

| Fixture | Planner | Independent Oracle | Actual Monitor / fixture evidence |
|---|---|---|---|
| P01 | witness / 84 / 0.125s / no; 5@7 | POSSIBLE / 2,187 / 0.657s / yes | SATISFIED, `event-000004` at t7 |
| N01 (DECLINE pin) | unreachable / 711 / 0.604s / yes | PROVEN_UNREACHABLE / 711 / 0.175s / yes | VIOLATED after real offer→DECLINE; item not transferred, monitor PENDING at decline, then sealed |
| B01 | witness / 84 / 0.122s / no; 5@7 | POSSIBLE / 192 / 0.040s / yes | SATISFIED, `event-000004` at t7 |
| B02 | unreachable / 80 / 0.046s / yes | PROVEN_UNREACHABLE / 80 / 0.017s / yes | VIOLATED |
| B03 | witness / 84 / 0.161s / no; 5@10 | POSSIBLE / 192 / 0.057s / yes | Positive replay SATISFIED with `event-000004`; negative replay VIOLATED |
| H01 | witness / 84 / 0.132s / no; 5@7 | POSSIBLE / 2,187 / 0.658s / yes | SATISFIED, `event-000004`; key0 unlock and unknown clear rejected, separate valid branch reaches goal |
| N02 | unreachable / 711 / 0.769s / yes | PROVEN_UNREACHABLE / 711 / 0.200s / yes | VIOLATED; tombstoned key1 does not create a legal path |
| H02 | unreachable / 1,887 / 1.879s / yes | PROVEN_UNREACHABLE / 1,887 / 0.559s / yes | VIOLATED; ledger held at t10 is not the required event witness |
| X01 | — | — | valid forecast MATCH; explicit key binding INVALID_BINDING before dispatch; premature key disclosure and false unlock-ledger prediction each PREDICTION_MISMATCH after real settlement; no ledger witness |
| X02 | — | — | failed exchange REJECTED at t4 with PRECONDITION_FAILED; real t4 checkpoint hash `896dcbbb…9292c3` differs from fixture input `14eb207d…0c052`; rejected fork has no mutation |
| P02 | witness / 432 / 0.689s / no; 7@9 | POSSIBLE / 1,488 / 0.409s / yes | event-goal SATISFIED at t9 with `event-000004`; running unlock/reservation persists at t6–7 and clears at t8 |
| U01 | — | — | untampered input retained; seal-deleted evidence copy is INDETERMINATE; fake event rejected (“no admitted producer receipt”), forged version rejected (identity/time/sequence/producer/payload invalid) |
| C01 | BUDGET / 1 / 0.001s / no; incomplete | BUDGET / 1 / 0.00045s / no; incomplete | Fixture test PASS means the cap-1 search correctly reported BUDGET/incomplete, not solved or unreachable |
| F01 | — | — | running checkpoint forked twice; complete fork hashes match (`9fa65771…b54e71`), traces match; mutation on one fork leaves the other/input unchanged |

### Separate JOINT counterfactual

N01's fixture is the pinned DECLINE case above. Its separately pinned JOINT counterfactual found a witness at t7/cost 5 (Planner 109 expansions / 0.170s / not exhausted; Oracle 2,649 / 0.781s / exhausted, POSSIBLE). The N02 JOINT counterfactual remained PROVEN_UNREACHABLE (711 / 0.657s Planner; 711 / 0.205s Oracle, exhausted). These do not replace or relabel the fixture pins.

### Audit note

The parent audit checked the run's exact input/source hashes, code revision, clean E0 scope, and unchanged per-search budget. A same-run-id CLI retry exited 2 at preflight (“refusing before running”); the original JSON SHA remained unchanged and no second formal run was created. Raw traces, branch checkpoints, errors, and provenance are in the linked run JSON. Development evidence remains separate below. Ubuntu CI run `37778341351` failed: the E0 unit job reports H02 planner `BUDGET` rather than expected `UNREACHABLE`, although its independent Oracle completed. The all-fixture step was skipped after that unit failure, so this CI run supplies no per-fixture batch result. A narrowly scoped workflow evidence fix now always runs the fixture batch and preserves unit output; new complete CI evidence is pending on the next head. The budget and acceptance gate are unchanged.

## Development diagnostics (separate from formal)

- Unit suite: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m unittest discover -s tools/e0_keyledger_v0/tests -v`, 33/33 PASS after a recorded intermediate 30/31 failure was repaired.
- Development all-fixture run: [`development result.json`](../../runs/e0_keyledger_v0/development/20261008T123337Z_all_dev-20261008-a/result.json), 14/14 fixture assertions PASS. It used an uncommitted E0-scoped tree and is not formal evidence; C01 PASS only checks correct BUDGET reporting.

## State

**E0_LOCAL_ACCEPTANCE_PASS / CI_NOT_PASS_BUDGET / READY_FOR_REVIEW.** The Mac formal run passed its 14 fixture assertions; the Ubuntu fixed-budget gate did not. Review portability/performance under the unchanged wall-time budget. This does not close the broader research task or authorize E1.
