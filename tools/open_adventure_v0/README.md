# Open Adventure native runner v0

This is a thin subprocess wrapper around the pinned upstream Open Adventure 1.22 executable. It sends a complete UTF-8 command transcript to a fresh native process, captures both runs' stdout/stderr and exit status, repeats the same execution directly with the same binary, and records whether both byte streams match. It does not parse game text into hidden state, infer action effects, or expose internal game data. A run is accepted only when both exits are zero, both stdout and stderr match, the pinned tracked source remains unchanged, and the binary hash stays constant during execution.

The wrapper supports complete episodes, not turn-by-turn interaction: upstream `-o` mode accepts a scripted stdin stream, and this runner preserves that boundary explicitly. A seed command in a transcript is an ordinary native game command, so only randomness after that command is controlled. Startup behavior before the seed may still depend on the game's initialization.

The default binary is the isolated local copy at `_local_data/external_games/open_adventure/upstream/advent`; run records go to `02_实验/OpenAdventure_Native_v0/runs/`. The runner rejects a different source revision/tag or a dirty tracked checkout. It records the binary path and before/after SHA-256, plus hashes of all tracked upstream files before and after an episode. Failures and timeouts still retain both runs' available raw outputs, inputs, errors and exit states.

The upstream project is licensed BSD-2-Clause. Keep the full source, generated executable, and bundled game data inside the ignored local directory. Public evidence should contain only short native transcripts, build/test logs, and a source/license manifest.

Get the original game from the [official repository](https://gitlab.com/esr/open-adventure), check out tag `1.22` / commit `e6160529e70a8c7a06b9a5f190d69aa35c4c62f5`, and follow the actual local [build record](../../02_实验/OpenAdventure_Native_v0/BUILD_AND_RUN.md). A fresh clone of this research repository does not include the ignored upstream checkout or executable. Hash recording is provenance evidence, not automatic proof that an arbitrary custom binary was built from the supplied source.

Example:

```sh
python3 tools/open_adventure_v0/runner.py \
  --id short-scenario \
  --commands /path/to/commands.txt
```

Transcript format is one native command per line. It must answer the initial instructions question first; comments start with `#`. If the source fixture does not already end the episode, the wrapper appends the native `quit` / `yes` exchange. It preserves the original input and also records the exact stdin sent to the process.

Focused wrapper checks:

```sh
python3 -m unittest tools.open_adventure_v0.tests.test_runner
```
