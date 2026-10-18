# Loaded Msg repair — attempts before the single native pair

No native server was launched by any attempt below. All are build, offline-test or input-preflight outcomes; they do not count as an OFF/ON rerun.

| Attempt | Actual result | Bounded correction |
|---|---|---|
| Rust build 001 | FAIL: `Actor` used where `NpcId` was required; an `FnMut` parameter lacked `mut` | Unwrap `Actor::Npc` for diagnostic identity checks; make the callback binding mutable. Preserve the native RequestHire branch. Failed patch and compiler log retained. |
| Rust build 002 | PASS | No dependency, feature, RNG or rule change. |
| RTSim test build 001 | FAIL: test used `CharacterId::default()`, which does not exist | Explicit `CharacterId(0)` in the invalid-recipient test only. Failed patch and log retained. |
| RTSim test 002 | PASS, 8 tests | Production routing helper, original-index handoff, source mismatch, Simulated and invalid-recipient cases. |
| Server native tests 001 | PASS, 7 tests | Includes old Talk guards and the real-Job/correlated-effect predicate. |
| Final build 003 | PASS | Rebuild the final source, including the corrected test fixture, before freezing the binary. |
| New Python suite in read-only sandbox | 15 PASS, 4 environmental ERROR | Temporary-directory access unavailable; rerun under the already authorized isolated test permission: 19/19 PASS. |
| Parent Python decision regression | PASS, 54 tests | Old 35 plus new 19, independently rerun; raw output retained. |
| Old runner test discovery using wrong filename | 0 tests, exit 5 | Correct filename `test_runner_contract.py`: 9/9 PASS; no false claim that the empty discovery passed. |
| Freeze command quoting | SyntaxError before execution | Correct shell argument quoting; no file or server action occurred. |
| Complete-assets preflight | Refused: original manifest used Path-component order, not POSIX-path-string order | Keep the original manifest; create a separate sorted manifest with the same 10,419 files, sizes and individual hashes. Recompute only its canonical tree digest. |
| Final freeze preflight | PASS | Validate complete assets, independent world/config manifests, final source patch, binary and lock. No server until this gate passed. |

The final freeze and the raw pair are immutable. A later result must be read from their recorded manifests, not inferred from this preflight table. Any provenance violation, including a duplicate after an initially trusted Job, makes the final causal-chain verdict FAIL; an earlier Job observation is not silently erased from raw evidence.
