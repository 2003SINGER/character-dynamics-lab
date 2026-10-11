# Offline replay shim for the P0 LLM-Sabre route

`replay_src/r7/llmsearch/OpenAIComponent.java` is a no-network transport replacement for the upstream `r7.llmsearch.OpenAIComponent`. Put its compiled output before upstream classes on the classpath. It only replays a transcript when every request prompt matches exactly; embeddings are never synthesized or requested. Use only with the private ignored upstream checkout and the matching historical cache.

## Build and run

The upstream checkout is intentionally ignored because no license file was found. The original bundled JAR has class-file major 64 but omits `ProgressionPlanner$Method$4`; use a local Java 21 compatibility build instead of modifying the source checkout. In this task, whole-source JDK 21 compilation required this one explicit-generic compatibility edit in an ignored source copy:

```diff
- return new Disjunction<>(new Clause<>(this));
+ return new Disjunction<Clause<Precondition>>(new Clause<Precondition>(this));
```

From `_local_data/planner_p0_v0/source_compat_0_7/` (after creating that ignored copy and compiling its complete `src` tree to `classes`):

```sh
JDK=/Users/2003singer/Workspace/Research/character-dynamics-lab/_local_data/planner_p0_v0/jdk/jdk-21.0.12.1+1/Contents/Home/bin
ROOT=/Users/2003singer/Workspace/Research/character-dynamics-lab
mkdir -p replay_classes
"$JDK/javac" -proc:none -cp 'lib/*' -d replay_classes \
  "$ROOT/tools/planner_p0_v0/llm_search_guide/replay_src/r7/llmsearch/OpenAIComponent.java"
"$JDK/java" -Dp0.replay.transcript=run_1/transcript.txt \
  -cp 'replay_classes:classes:lib/*' edu.uky.cs.nil.sabre.Main \
  -p problems/gramma.txt -atl 5 -ctl 4 -el 1 -g 1 -m llm
```

The run must emit five `P0_REPLAY` markers. It then reaches the upstream hardcoded `SEARCH_NODE_LIMIT=5` and reports that cap; `-atl 5` is a temporal-depth setting, not that node cap. Compare the generated files to the historical run with SHA-256; do not treat the CLI exit code or a `Solution found` message as standalone acceptance. The shim fails on prompt mismatch or any embedding miss, and the upstream caller catches exceptions before later failing on missing costs, so inspect stderr and require the exact output comparison.

Do not run this shim against a new model response. New response keys need the original embedding provider or exact cached vectors; a miss is a stop condition. Experiment metadata and the verified replay hashes are in `02_实验/Planner_P0_v0/llm_search_guide/REPLAY_AND_PREFLIGHT.md`.
