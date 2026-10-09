# LIGHT native no-model probe — 2026-10-10

## Decision

**NO_GO_WITHIN_THIS_TIMEBOX.** The unchanged upstream `play_map.py` was invoked with the approved Hydra map override, but could not pass its first import because dependency installation had not completed. The environment was created, but the runtime dependencies were not installed; this result does not prove that the engine or algorithm cannot run. No initial look, legal action, or real state transition was observed. Importing source modules or the existence of old LIGHT replay artifacts does not satisfy this gate.

## Scope and provenance

- Upstream: `facebookresearch/LIGHT`, detached at `71a06cae8573048b1af41507ac52fe33b650fab3` (`Update api.js`).
- Interpreter: Python 3.12.14; isolated venv at `_local_data/native_platform_v0/light/env/`.
- Entry: `scripts/examples/play_map.py` (SHA-256 `02ec172be1469f248df51e1e04ae45c87ae503a36f765d9e4eb9df76e72d51f3`).
- Complex map: `scripts/examples/complex_world.json` (SHA-256 `762d75a560924cf566b117b0a340f52fa1b3856709f704943ecaa09453c0ecc5`).
- Requirements: SHA-256 `7b24ac4f0566e37164d63cb56fc0d3e6763ebcb8dcb123605e4d0b3ea709dcae`.
- The source checkout is clean and detached at the requested commit. No model was downloaded or loaded. No tracked project file outside the authorized probe README and this result was changed; unrelated pre-existing NPC edits were left untouched.

## Attempt log

1. `git clone --no-checkout https://github.com/facebookresearch/LIGHT.git _local_data/native_platform_v0/light/upstream` then `git -C _local_data/native_platform_v0/light/upstream checkout --detach 71a06cae8573048b1af41507ac52fe33b650fab3` — **PASS**. Checkout reports `HEAD is now at 71a06cae Update api.js`.
2. `python3 --version && python3 -m venv .../env && .../env/bin/python -m pip --version && .../env/bin/python -m pip install .` — venv creation **PASS** (Python 3.12.14, pip 26.2.1); installation was **cancelled during prolonged resolver backtracking**. It enumerated the complete upstream requirements, including `torch>=1.5.0`, ParlAI, Mephisto, and SQLAlchemy. Resolver output showed Mephisto's legacy pins (including `markupsafe==2.0.1`) and repeated ParlAI version/dataset/transformers dependency exploration; it backtracked through many `huggingface-hub` versions and warned that this was taking longer than usual. It had not reached a successful install or a definitive compatibility resolution when cancelled. No second pip-version experiment was made. The task dispatch/start wall-clock time was not captured, so no exact elapsed time is asserted; the user-specified 15-minute bound was treated as a hard cap.
3. Actual unchanged entry invocation: `.../env/bin/python scripts/examples/play_map.py builder.load_map=scripts/examples/complex_world.json` — **FAIL**, stderr:

   ```text
   Traceback (most recent call last):
     File ".../scripts/examples/play_map.py", line 24, in <module>
       import hydra
   ModuleNotFoundError: No module named 'hydra'
   ```

   This confirms the actual native entry is currently blocked before map construction; it is not evidence of runtime behavior.

4. Replayed that entry once after moving the venv beside (rather than inside) the upstream clone, saving actual separate streams: `entry_attempt_03.stdout.log` (0 bytes; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`) and `entry_attempt_03.stderr.log` (263 bytes; SHA-256 `7aebc36dd5e9aace27d2ffef9ef3067965fcf32da211b71ccd981b54fbce3548`). Exit code 1; stderr is the traceback above. No dependency installation was repeated.
5. One intervening log-capture command used the now-stale pre-move path and exited 127 before Python launched. Its actual streams are retained as `entry_attempt_02.stdout.log` (0 bytes; same empty-file SHA-256) and `entry_attempt_02.stderr.log` (86 bytes; SHA-256 `91fca2b22ecf8f9385cbf36f6ee2aa8597ab939114b90980e3f89bf544d083d0`): `zsh:1: no such file or directory: _local_data/native_platform_v0/light/env/bin/python`. This was a path error in the log-capture replay, not a LIGHT entrypoint result; attempt 03 is the valid replay.

## Gate status

| Gate | Result |
|---|---|
| Pinned official source checkout | PASS |
| Isolated Python environment | PASS, incomplete dependencies |
| Unmodified original entry starts | FAIL (`hydra` unavailable after install cancellation) |
| Initial observation (`look`) | NOT REACHED |
| Legal action accepted | NOT REACHED |
| Real world state changes after action | NOT REACHED |
| Native admission | **NO_GO_WITHIN_THIS_TIMEBOX** |

Do not claim native LIGHT usability, or continue this probe by silently omitting declared dependencies. Remaining unverified: whether an appropriately compatible dependency set can be installed in this environment, and all in-game interaction/state-change gates. No source code was adapted and no model/runtime inference was attempted.
