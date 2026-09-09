# Paired commitment / interruption / recovery v0

- source revision: `a3a4488`
- runner: `character_dynamics_reference --paired-commitment`
- setup: accepted focused study establishes an active coursework commitment
- interruption: controlled meal with unresolved fatigue suspends commitment
- ablation: same W/O/S/P snapshot with only commitment cleared

Observed run:

- active commitment setup: PASS
- interruption Active → Suspended: PASS
- unresolved need: reconsideration defers return
- resolved need: reconsideration permits return
- preserved vs ablated policy TV: `0.0283871`
- recovered fatigue: `0.55796`
- observable completion feedback closes commitment → `none`
- hidden completion feedback preserves commitment → `active`
- accepted resumed study restores Suspended → Active: PASS

This is a deterministic mechanism probe, not natural-behavior or psychological evidence.
