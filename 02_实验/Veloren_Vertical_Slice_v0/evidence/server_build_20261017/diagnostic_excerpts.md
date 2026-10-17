# Diagnostic excerpts and versioned outcomes

Large raw Cargo stderr files contain verbose HTTP traces and/or local paths, so only minimal diagnostics and their raw byte counts/SHA-256 are published in `manifest.json`. Raw originals remain unchanged in the ignored local evidence directory.

| Run | Safe diagnostic / result | Status and patch boundary |
|---|---|---|
| `server-only-rsproxy-check` | `--locked` refused because pruning the workspace would require updating `Cargo.lock`. | Exit 101; setup limitation, not a source compilation result; patch `37f5932f…`. Lock remained unchanged. |
| `full-workspace-rsproxy-check-run01-tool-path-error` | `error: could not execute process rustc -vV (never executed)` | Exit 101; toolchain PATH issue, no compilation. |
| `full-workspace-rsproxy-check-run02` | `error[E0277]: the trait bound … is not satisfied` | Exit 101; compile failure in `veloren-rtsim`; patch `37f5932fdf3abf2564314f897032b14f2a8b187697d529d1b65b4ef282c695ca`. |
| `full-workspace-rsproxy-check-run03-finalpatch` | `error[E0308]: mismatched types; expected &NpcId, found NpcId` | Exit 101; compile failure in `veloren-server`; patch `f866e8362fc10342d0331b00f9fcb0171ab13b5b1cc8feaa8c903520f0c6fb59`. |
| `full-workspace-rsproxy-check-run04-frozen` | `error[E0716]: temporary value dropped while borrowed` | Exit 101; compile failure in `veloren-server`; patch `fcf91c8eb584827d5e867645c0feb279eb7ccb77c48e09380fa52f2f3d37b70f`. |
| `full-workspace-rsproxy-check-run05` | Cargo `Finished dev profile` in 12.53s. | Exit 0 per index; `cargo check` for patch `f3545b19fab29e977c459c002d8231f649d0dec8d43cff0e78d71d0ec0013bd0`, not the final patch. |
| `targeted-rust-tests` | `error[E0433]: failed to resolve: use of undeclared type HashSet` | Exit 101; test compilation failed, tests did not execute; patch `f3545b19…`. |
| `targeted-rust-tests-run02-no-assets` | Common tests failed to locate assets; subsequent failures included poisoned lazy statics. | Exit 101; 52 passed / 48 failed in the common crate; no rtsim/server tests ran; patch `e480a5e6…`. This is a test-environment failure, not a negative target outcome. |
| `targeted-rust-tests-run03-with-assets` | Selected crate suites completed. | Exit 0; 136 passed / 18 ignored, but on earlier patch `e480a5e6…`; not represented as a final-patch suite. |
| `full-workspace-rsproxy-build-with-plugins` | Cargo `Finished dev profile` in 8m 01s. | Exit 0; final patch `1ccf5c1…`; selected server CLI dependency graph only; `plugins` feature includes the `RequestPluginsEvent` consumer. Original lock unchanged. Binary SHA-256 `2760baacf42ad8b403f9ee94c721503ff0e7521f40f20d865e9a8b331ea7ab28`. |
| Final focused Rust tests | Common 1 + rtsim 6 + server 5 passed. | Exit 0, 12/12 focused tests on final patch `1ccf5c1…`. Two earlier cwd/redirect invocation failures occurred before Rust ran and are not test failures. |
| `server-build-final` | Cargo `Finished dev profile` after 4m54s is present in its raw stderr. | No matching raw-index record in the frozen index; retained as `RUN_COMPLETE_INDEX_PENDING`, with no inferred exit code or patch attribution. |

The initial no-plugins server startup panic, stable native baseline, zero-input C run, and D partial request run have separate verbatim raw artifacts and bounded interpretation notes in this directory. The plugin-assets missing-file error is retained in raw native stdout; it is not hidden by later successful startup.
