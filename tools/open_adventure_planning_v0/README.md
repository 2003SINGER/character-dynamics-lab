# Open Adventure B0 v0

This isolated package implements a finite STRIPS-like prediction model and classical forward uniform-cost search (`h=0`). It is a baseline, not a walkthrough, HTN, game authority, or general planning platform. `domain.py` keeps source references with operators; `observe.py` changes predicted state only from completed visible native text; `verify.py` independently checks the raw P1 event ledger.

The fixed protocol is `02_实验/OpenAdventure_Planning_B0_v0/PROTOCOL.md`. Initial map/object positions are common `STATIC_MODEL_ASSUMPTION`s. The safety restriction against entering non-LIT rooms without the carried, lit lamp is a conservative `MODEL_POLICY_SAFETY`, not a claim about native legality or full-domain optimality. Unmodeled events, death, unknown native questions, and budget exhaustion do not count as success; the known cave-hint question is declined and normal feedback handling continues.

Offline tests: `python3 -m unittest tools.open_adventure_planning_v0.tests.test_baseline`. They do not launch or simulate the original game.

Native runs, when separately authorized, are available through `python3 -m tools.open_adventure_planning_v0.execute --goal D --execute-native`; output is restricted to the protocol's non-overwriting run directory. This module is not to be used for E until its separate authorization.
