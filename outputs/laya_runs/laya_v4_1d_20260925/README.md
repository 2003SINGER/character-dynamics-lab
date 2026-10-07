# Laya v4 1-day gate — PRE-FINAL exploratory arms only

Artifact root: `/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v4_1d_20260925/`.

This directory currently contains only the Rule and v4 empty-history arms. They
were run before the final `window_h:48` serialization/prompt change and before
the source tree was frozen. They are preserved for audit, but are not final
three-arm evidence and must not be compared as the final gate. The v4-with-history
arm was intentionally not launched. Per parent review, rerun all arms only after
an exact source revision/build is frozen.

- Scenario seed: 17; policy seed: 101; profile: balanced; horizon: 1 day.
- Engine: direct `character_dynamics_long_horizon`, boundaries enabled.
- Rule trace SHA-256: `43c405356ae3c27d12984f5c266729b2829f748b245b1b090fec2aa1a3fe4455`.
- Empty-H trace SHA-256: `94a052bc8d52e7816241c9f1c855d9945deedb96477d79f0adfc7f16e6ffe12c`.
- Empty-H live cassette SHA-256: `e18080705d5ea80575c6aac328238f79a68515c209b23f67c7e352c602d1c85b`.
- The live cassette records protocol/prompt and per-request tokenizer audit.

No soft gate, typed appraisal, or typed commitment was enabled. These outputs
are exploratory and should not be treated as the frozen one-day acceptance gate.
