# Native Evennia ↔ Ensemble bridge probe

This is a bounded test adapter, not a game integration. It uses separate plain `Room`/`Character` fixtures and temporary commands; it does not modify the official EvAdventure FSM. Evennia owns locations and the actual delivered note. Ensemble proposes the narrative action; `writeLoveNoteReject` is a social/narrative rejection after a valid note delivery, while stale location/absent target is rejected by World validation before any receipt exists.

## Reproduce

The pinned upstream checkout lives at ignored `_local_data/native_platform_v0/ensemble/`:

```sh
git clone https://github.com/ensemble-engine/ensemble.git _local_data/native_platform_v0/ensemble
git -C _local_data/native_platform_v0/ensemble checkout --detach 8b74bdec4ba2ef4e14795b7591df3b5d73f283e3
git -C _local_data/native_platform_v0/ensemble rev-parse HEAD
```

The checkout is version 1.1.1 under BSD-4-Clause (see upstream `LICENSE.md`). Use Node v26.8.2. Run the native source probe and tests with the commands in `tools/native_platform_v0/ensemble/README.md`.

For the live adapter, with the nativep1 Evennia service running, use the in-game `py` command:

```text
py import sys; sys.path.insert(0,"/Users/2003singer/Workspace/Research/character-dynamics-lab/tools/native_platform_v0/bridge"); import run_live_probe; me.msg(run_live_probe.run_json(me))
```

Adjust only the absolute checkout path if reproducing elsewhere. Each invocation creates fresh,
separate test fixtures, not another official map. The returned JSON is also stored in the
administrator's `ensemble_bridge_rawlog` Attribute; export it before another run overwrites that
latest-result Attribute. Files already exported must not be overwritten. To load just the probe
commands manually in a server-side Python context:

```python
import sys
sys.path.insert(0, "/Users/2003singer/Workspace/Research/character-dynamics-lab/tools/native_platform_v0/bridge")
from evennia_bridge import install_test_commands
install_test_commands(me)
```

The probe covers stale-location rejection, one real note delivery followed by Ensemble commit, duplicate feedback, and one bounded simulated bridge-cache gap. In the cache-gap case, only the in-process result cache is evicted; the same pending proposal and existing note receipt are restored and retried. Assertions require the same receipt and `doActionCalled: false` for the repeated Node commit. The initial live snapshot is [first-live-success.json](/Users/2003singer/Workspace/Research/character-dynamics-lab/outputs/native_platform_p1p2_v0/bridge_20261010/first-live-success.json); it predates the added fourth cache-gap case. Parent-run final live output should be saved as a new file, not overwrite that initial evidence.

Live execution is not represented by the Node wrapper tests or official upstream tests. Raw logs and source hashes belong under `outputs/native_platform_p1p2_v0/bridge_20261010/`.

The parent subsequently ran all four cases in the real browser and exported fresh output under
`final-live-20261010T1735Z/`; [the public evidence index](../../../02_实验/Native_Platform_P1P2_v0/evidence/README.md)
links both generations. Current acceptance and limits are maintained only in
[the milestone result](../../../02_实验/Native_Platform_P1P2_v0/RESULTS.md).
