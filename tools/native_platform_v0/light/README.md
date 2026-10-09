# LIGHT native no-model probe

This directory contains the bounded native-entrypoint admission probe for the pinned upstream LIGHT commit `71a06cae8573048b1af41507ac52fe33b650fab3`. Probe outputs and run logs belong in `outputs/native_platform_p1p2_v0/light_probe_20261010/`; the upstream clone and isolated Python environment belong under ignored `_local_data/native_platform_v0/light/`.

Acceptance requires running the unchanged upstream `scripts/examples/play_map.py`, observing a legal action, then observing a real world state change caused by that action. Import success alone is insufficient. No model is downloaded or loaded.
