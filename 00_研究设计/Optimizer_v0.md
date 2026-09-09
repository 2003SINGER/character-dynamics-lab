# Optimizer v0

This document freezes the development-only plumbing objective. Candidate
selection is lexicographic: (1) all regression and world-integrity hard gates
pass; (2) fewer world violations; (3) avoid extreme action collapse; (4) avoid
pathological repetition; (5) retain task progression; (6) do not materially
regress efficiency. There is no naturalness score and no objective that
maximizes diversity, personality JS, or fixture policy TV.

The smoke runner may return `BASELINE_RETAINED / NO_SELECTION` when candidates
are not distinguishable. It never reads `internal_holdout` during search.

Current status: `OPTIMIZER_V0_SMOKE = NOT_RUN`.
