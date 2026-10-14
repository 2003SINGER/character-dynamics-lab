# Open Adventure online P1 v0

The pinned Open Adventure 1.22 executable can be controlled one native input at a time through a PTY. `main.c:49-58` uses libedit `readline(prompt)` when no script arguments are supplied. `advent.h:85` defines the prompt as `> `, and `misc.c:233-258` prints a newline before every native read. In contrast, `-o` disables the prompt in `main.c:1494-1495`, so the adapter launches the ordinary mode without `-o`.

The adapter reads until the output ends with the PTY form `\r\n> `. That means only “the game requested input.” It does not mean that one world tick occurred or that an action succeeded. Startup questions, parser retries, and yes/no questions use the same native input path. No sleep or inferred game-state parser determines the boundary. The adapter uses `TERM=dumb`; command text is limited to one newline-free line of at most 1024 bytes. Raw output and both intended and actually written input bytes are recorded in each unique `runs/<episode-id>/events.jsonl` file. The controller receives only the latest completed visible text; it has no API for `game_t`, NPC state, map state, or random cursors. Observation reads the cached text and does not communicate with the process.

Minimal use:

```python
from tools.open_adventure_v0.session import OpenAdventureSession

session = OpenAdventureSession()
visible_text = session.reset({"experiment_config_version": "my-config-v0"})
result = session.step("n", controller="human", decision_source="startup answer")
visible_text = session.observe()  # cached; no game input or world update
session.close()
```

For replay, pass the recorded ordered command entries to `replay(...)`. Its result contains the initial observation and each raw step output as base64; compare those bytes against the original episode. A final clean exit after the last recorded native confirmation is reported separately from an input boundary.

`tools/open_adventure_v0/smoke_policy.py` is labeled an interface smoke policy. It enters the nearby building, records a native parser rejection, takes the lamp, and repeats `take lamp`. Only after the game returns “You are already carrying it!” does the policy choose `drop lamp`; a different visible response selects `inventory`. It checks the inventory after dropping and taking the lamp again, then leaves. It also answers `no` to the native quit question, continues with `look`, and later quits with `yes`. This is a bounded adapter smoke, not a planning result or walkthrough.

The early worker's 17-input episode and replay are historical; see the [single P1 RESULTS owner](RESULTS.md) for the final evidence and earlier-version boundary. Final implementation evidence is the parent-verified 18-input program smoke (12 game inputs), exact initial/step-byte replay, and 16/16 offline tests. The final raw run directories are `runs/626c93eb9a9046b0b16c4dc0a5aafaa1-20261014T042735Z-e18d43/` and `runs/2fe7b0a1b68f4e1dbc8b08da9334b100-20261014T042735Z-c0eddf/`; the independent clarification/recovery slice is also indexed in RESULTS. This implementation page explains the adapter; RESULTS owns run facts, failures, and acceptance status.

The preliminary prompt feasibility probes are summarized in `runs/pty-feasibility-probe-initial/record.json`. The first probe's exit code was not captured; a later process check found no live `advent`, but that does not recover the missing exit status. A second probe explicitly sent `yes` and captured exit code 0. Full byte-level replay evidence is available in the two adapter run directories above.

Focused offline contracts, using fake subprocesses and mocked source preflight/hash calls:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.open_adventure_v0.tests.test_session -v
```

These cover exact prompt boundaries, passive observation, one-line and size limits, visible-text branch selection, intended versus actual short writes, timeout partial output, clean termination, and nonzero exit evidence. No upstream source or game data was changed. A PTY boundary is specific to this pinned executable and its prompt; it is not a general terminal protocol or a game-tick abstraction.
