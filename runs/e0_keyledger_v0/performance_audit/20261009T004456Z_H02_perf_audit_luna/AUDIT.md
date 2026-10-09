# E0-H02 Planner Performance Audit

Status: pre-change measurement; no algorithm or source edits were made during these two runs.

## Reproduction context

- Timestamp: `2026-10-09T00:44:56Z`.
- Checkout: `/Users/2003singer/Workspace/Research/character-dynamics-lab`, branch `webgpt-sync`, `HEAD=885dc78d1e7b1c89522b409b4607a88491cf52b7`.
- Protocol: `E0-KeyLedger-v0`, SHA-256 `0837eaa2e7b53e5aa00578534b714f38b055cc6389191ca7c5687eb5f3b1c7f9`.
- Planner SHA-256: `6afde80f85ce0e5ce300e685afcdefffc5586b5991107a35e99f8e67b44cb1d3`.
- Executor SHA-256: `65ad9079e36dce8f758ea823a74d34f5acb1411a4d7de7099ab1fff7bbc3b60b`.
- Fixture module SHA-256: `547851a8f77272be910c3c6a372b216d8e262ebf464b10e0f62e6c40a8855b6a`.
- Fixture: `E0-H02`; canonical checkpoint SHA-256 (sorted compact UTF-8 JSON) `02e5e5df85f51422479e277dc32a82a51450271e6c724cdb30b9c0859fd919d1`.
- Pins: deadline `10`, reply `ACCEPT`, unlock duration `1`.
- Budget for both calls: `max_expansions=10000`, `wall_seconds=2.0`; planner code and state key were unchanged.
- Runtime: CPython `3.12.14` (`Clang 21.0.0`), macOS `27.0.1`, Apple M3 MacBook Air, 8 CPU cores (4 performance + 4 efficiency), 16 GB RAM; single process, default interpreter optimization.
- Repo had unrelated dirty NPC paired Demo files before and after audit; they were not touched. No Runtime code or E1 was run.

## Results

| Run | Result | Expansions | Visited | Frontier | Planner elapsed |
|---|---|---:|---:|---:|---:|
| Unprofiled baseline | `UNREACHABLE / FRONTIER_EXHAUSTED`, complete and exhausted | 1,887 | 1,887 | 0 | 1.786591 s |
| cProfile diagnostic | `BUDGET / WALL_TIMEOUT`, incomplete and not exhausted | 286 | 286 | 331 | 2.002251 s |

The cProfile row is instrumentation-distorted and is not a comparable performance result or formal E0 result. The unprofiled run is the only baseline timing here.

## cProfile cumulative cost (diagnostic only)

The profiled run made 14,232,875 calls (11,477,941 primitive) over 2.002 seconds. The largest cumulative entries were:

| Function | Calls | Cumulative seconds | Approx. share of profiled wall |
|---|---:|---:|---:|
| `copy.deepcopy` | 2,326,895 / 7,354 recursive entries | 1.917 | 95.8% |
| `Executor.checkpoint` | 1,232 | 1.268 | 63.3% |
| `Executor.advance_minute` | 616 | 0.741 | 37.0% |
| `Executor.__init__` | 616 | 0.565 | 28.2% |
| `copy._deepcopy_dict` | 295,953 / 7,333 recursive entries | 1.909 | 95.4% |
| `copy._deepcopy_list` | 171,601 / 24,828 recursive entries | 1.614 | 80.6% |
| `planner._key` + JSON encoding | 286 calls | 0.025 | 1.2% |
| `Executor._evaluate_monitor` | 616 | 0.031 | 1.5% |
| `Executor._validate_ledger_and_seals` | 616 | 0.030 | 1.5% |

## Specific redundant work identified

Each generated candidate currently constructs `branch = Executor(state)`, which deep-copies the input checkpoint. The planner then calls `branch.advance_minute(...)`, whose return value is already a detached complete checkpoint because the method returns `self.checkpoint()`. The planner discards that return and immediately calls `branch.checkpoint()` again. Profile counts show 616 `advance_minute` and 1,232 `checkpoint` calls: exactly two full checkpoint snapshots per processed candidate edge. The second snapshot per edge is redundant; using the existing return value should remove only that copy while preserving full state/history, checkpoint isolation, event/seal/ID data, candidate order, tie-break, and state key.

Other cost is intentional under the frozen contract: each candidate forks a fully isolated executor, and snapshots/state keys preserve full append-only history. No history folding, state-key changes, altered transition effects, monitor semantics, or budget changes are proposed.

## Raw artifacts

- `unprofiled.stdout.json`: raw unprofiled planner result.
- `profiled.stdout.txt`: raw profiler result and cumulative report.
- `h02.cprof`: binary cProfile data for offline inspection.
- `post_optimization.stdout.json`: the one fixed-budget H02 run after the approved planner-only snapshot reuse.
- `parity_v2.stdout.json`: three-branch (idle, actor start, mid-R) full-checkpoint equality and bidirectional snapshot isolation smoke.
- `post_copier.stdout.json`: the one fixed-budget H02 run after the approved memo-aware checkpoint copier.
- `post_atomic_fastpath.stdout.json`: the one fixed-budget H02 run after the approved immutable-atom fast path.
- `final_unit_tests.stdout.txt`: final executor + monitor bridge unittest run after all approved source changes.

## Approved minimal optimization follow-up

The only source change after baseline measurement was in `planner.py` (post-change SHA-256 `d93b0b920724a4d83d0a99075eb7595bee2e2f74d9108477afb93724b4c1ec21`): each branch now assigns `next_state` from the already-detached return value of `advance_minute()` and no longer requests a second `branch.checkpoint()` snapshot. Executor behavior, complete state key, history, transition/effect logic, candidate order, heap tie-break, search budgets, and oracle/runtime code remain unchanged.

One post-change H02 run at the same budget completed as `UNREACHABLE / FRONTIER_EXHAUSTED`, `complete=true`, `exhausted=true`, with the same 1,887 expansions, 1,887 visited, and empty frontier as the unprofiled baseline. Its elapsed time was `1.318013 s` versus baseline `1.786591 s` (one run each; timing improvement is descriptive, not a repeated benchmark or CI claim).

The three-branch parity smoke compared the returned advance snapshot against the legacy `advance_minute(); checkpoint()` result as a complete dict and canonical JSON. For idle, actor-start settlement, and mid-R, all snapshots matched; deep mutation of the returned W/O/history/receipts/events/seals/monitor followed by another Executor advance remained isolated in both directions. P02 progress/reservation remained the same running action at elapsed 1 then 2 and released at elapsed 3. All three branches passed.

The earlier `parity.stdout.json` is retained as originally produced; its `P01_final_clock` label accidentally reports the subsequent P02 terminal clock. `parity_v2.stdout.json` is the corrected branch-scoped parity record.

The second approved source change added `_checkpoint_copy` in `executor.py` (intermediate SHA-256 `77e0bc4689c1c44ef2dda86bbd5706b524f97e9afefc321650a129caa9ea2feb`; `planner.py` remains `d93b0b920724a4d83d0a99075eb7595bee2e2f74d9108477afb93724b4c1ec21`). It handles only exact built-in dict/list plus immutable JSON atoms in a shared memo; all other values/subclasses fall back to `deepcopy(value, memo)`. Only `Executor.__init__` and `checkpoint()` use it. No JSON round-trip or shallow copy is used.

After this change, exactly one fixed-budget H02 run again completed `UNREACHABLE / FRONTIER_EXHAUSTED`, `complete=true`, `exhausted=true`, with the same 1,887 expansions and visited states and empty frontier. Elapsed time was `1.070706 s` (baseline 1.786591 s; planner-snapshot-only 1.318013 s). This is one local run at each stage, not a repeated benchmark; no CI was rerun. The latest already-existing remote CI result reported by the parent was H02 planner 534 expansions / 2.001705 s and independent oracle 1,887 / 1.210996 s; this local timing does not resolve that remote environment's H02 timeout.

`test_executor.py` now checks all 14 fixtures, a successful receipt/event history and mid-R checkpoint against stdlib `deepcopy`, including alias topology and isolation; explicit `delta_w.holders`↔`W.holders` and `outcome_history.event_ids`↔`receipt.event_ids` aliases; cycles and repeated containers; non-JSON and subclass fallback with a fallback object referencing a fast-copied shared list; and idle/actor-start/mid-R advance-return parity plus bidirectional isolation. The executor suite passes 8 tests; the executor + monitor bridge suites passed 21 distinct tests before the final test-only fallback assertion was added, and the 8 executor tests passed again afterward.

The third approved change hoisted `_CHECKPOINT_ATOMIC_TYPES` and directly reused only exact immutable atoms inside dict/list traversal. Final atomic-fast-path H02 ran once at the same 10,000/2.0 budget and completed `UNREACHABLE / FRONTIER_EXHAUSTED`, `complete=true`, `exhausted=true`, with 1,887 expansions/visited and empty frontier in `0.808836 s` (`post_atomic_fastpath.stdout.json`). This is about 54.8% below the single initial unprofiled timing, but is still one run per stage and not a repeated benchmark.

Final source SHA-256 values: `planner.py=d93b0b920724a4d83d0a99075eb7595bee2e2f74d9108477afb93724b4c1ec21`; `executor.py=9f8e17e3e28fb50ca0be542b35184d5903bc70b68e88509ee4510004373a4af8`; `tests/test_executor.py=acbf61db0898a1a675a7de8537b5c7f96e17ee505ab084c42d3e3f406edaec7d`. Final executor + monitor bridge unittest output is preserved in `final_unit_tests.stdout.txt`: **17 tests passed**. `git diff --check` passed. No Runtime, E1, oracle change, or CI run was performed here.

Reproduce the final planner measurement from the final sources with:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -c 'import json; from e0_keyledger_v0.fixtures import initial_checkpoint; from e0_keyledger_v0.planner import uniform_cost_search; result=uniform_cost_search(initial_checkpoint("E0-H02"),max_expansions=10000,wall_seconds=2.0); print(json.dumps(result,sort_keys=True,separators=(",",":")))'
```

The original unprofiled baseline must be reproduced against the original `885dc78d1e7b1c89522b409b4607a88491cf52b7` source revision; do not compare current sources to a run whose code hash differs.
