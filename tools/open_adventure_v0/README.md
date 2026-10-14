# Open Adventure native runner v0

## 在线 P1（2026-10-14，新接缝）

[session.py](session.py)提供原版持续进程的逐次输入与被动 observe；[用法与原生边界](../../02_实验/OpenAdventure_Online_P1_v0/IMPLEMENTATION.md)见实现说明，[实际结果/失败/原始记录](../../02_实验/OpenAdventure_Online_P1_v0/RESULTS.md)是唯一 P1 结果 owner。它启动正常 PTY 模式，精确原生提示符只表示再次请求输入，不表示动作成功或世界 tick；与下方旧 `-o` 整局 runner 分开。

```sh
python3 -m tools.open_adventure_v0.smoke_policy
python3 -m unittest tools.open_adventure_v0.tests.test_runner tools.open_adventure_v0.tests.test_session -v
```

程序是 interface smoke policy，不是解谜 Planner；每次等待实际反馈才提交下一条。子进程在独立 OS session 中运行，close 只回收其自身；强制关闭退出码不是游戏胜利。只有完整输入被消费且没有超时/错误时，replay 才可标记完成。没有快照/分叉、结构化动作回执、隐藏状态观察或模型调用。

## 原整局 runner（保留）

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
