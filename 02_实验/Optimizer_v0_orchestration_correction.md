# Optimizer v0 orchestration correction

The historical artifacts under `outputs/optimizer_v0_smoke_r4/` and the
earlier holdout report are retained as `ORCHESTRATION_SMOKE_V0`. Their 16
candidate configs did not enter the C++ Engine: every candidate reused one
baseline trajectory, so `candidate_000` was not an optimization result and the
holdout report was only a firewall-program smoke.

After this correction, `tools/optimizer_v0.py` writes a distinct config and
invokes the Engine for every candidate. The current real smoke is under
`outputs/optimizer_v0_real_smoke2/`: four candidates have distinct batch
directories and engine config hashes, all fixture gates pass, and the honest
selection is `BASELINE_RETAINED / NO_SELECTION` because no optimizer-eligible
behavior objective is frozen.
