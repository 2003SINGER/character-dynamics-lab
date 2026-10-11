# Sabre upstream baseline adapter

This adapter invokes Sabre's unmodified command-line planner. It contains no replacement planner or upstream Java source. The ignored local checkout and build are under `_local_data/planner_p0_v0/`.

## Pinned inputs

- Sabre: upstream `sgware/sabre`, commit `73a128123b10a57843068b69d0b0e0601f37488a` (v0.8.0), GPL-3.0.
- Benchmark collection: upstream `sgware/sabre-benchmarks`, commit `d9327b3ec2706a468c580c332d3f848ffb4c47fc`; its Sabre submodule is pinned by upstream to `f1a683c32eb23800e4f66fddde3cbf3988db2777`. Benchmark collection is GPL-3.0; individual problem provenance remains with the benchmark authors.
- v0.8 source compile/runtime: Eclipse Temurin 17.0.20.1+1, macOS aarch64; upstream package SHA-256 `196d13ba5f10414bef7f6a05a9b3f00edacb18ebacef2b99485db9e2ee18f0e8`.
- Historical v0.7 JAR runtime: Eclipse Temurin 21.0.12.1+1, macOS aarch64; upstream package SHA-256 `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998`. Java 21 is isolated alongside JDK 17 under the ignored project-local JDK directory; neither runtime is globally installed.

The separately maintained historical v0.7 JAR used by the related reproduction is not this v0.8 checkout. Do not compare their search costs or node counts as if they were the same version. The wrapper accepts an explicit Java executable, classpath, main class, and version label for such calls.

## Invocation

Run one planner invocation with a unique slug; existing run IDs are never overwritten. A shared-world domain may select a larger Java thread stack if compilation hits deep recursive collection conversion:

```sh
python3 tools/planner_p0_v0/sabre_baseline/runner.py \
  --problem /absolute/path/to/problem.txt \
  --run-id sharedworld-clear-01 \
  --method bf --cost t --heuristic 'h+' \
  --epistemic-limit 1 --max-visited 200 --time-limit-ms 5000 \
  --author-limit 48 --stack-size 8m
```

Default Java/classpath use the ignored v0.8 local source build. For a different upstream binary, pass `--java`, `--classpath`, `--main-class`, and `--planner-version`. All output must remain beneath this directory's `evidence/` tree. The default process watchdog is 30 seconds; override it with `--process-timeout-s` when the problem/configuration needs a longer grounding phase. A watchdog expiry is returned as `PROCESS_TIMEOUT`, distinct from Sabre's native search, space, or time limit.

The wrapper returns one JSON line and stores `config.json`, full `stdout.log`, full `stderr.log`, and `result.json` in `02_实验/Planner_P0_v0/sabre_baseline/evidence/<run-id>/`. JSON fields include `status`, `native_result`, `utility_achieved`, `nodes_visited`, `nodes_generated`, `elapsed_native_text`, `elapsed_native_ms`, `java_stack_size`, `plan_actions`, `exit_code`, and paths to the raw logs. `plan_actions` contains only unindented grounded actions; verbose explanation steps remain unparsed in raw stdout. If Sabre reports a search limit, it is `BUDGET_LIMIT`; a native “No solution exists” string is retained as `NATIVE_NO_SOLUTION` and is not upgraded into a broader reachability claim. Composite/unrecognized duration formats are preserved as text and leave the numeric duration empty.

Sabre v0.8's CLI catches `Throwable` and prints only `Error: <message>`. `DebugSabre.java` calls the same `Session` API and emits exception type plus stack frames; compile its adapter class into an ignored side directory rather than the upstream build output. The shared-world initial problem parsed successfully but default-stack compilation raised `StackOverflowError` in recursive `Utilities.toArray`; `-Xss8m` allowed native compilation and search. This is a runtime-stack accommodation, not an algorithm/source change. Preserve the default-stack failure as diagnostic evidence and use the same explicit stack setting across compared shared-world conditions.

Sabre's native cost is a selected measure (`t`, `n`, or `x`), not a universal numeric objective. The full CLI output is the authority for its heuristic, limits, actual plan, utility, and counts.

## Scope

The official MacGuffin example is a small upstream smoke reproduction for compiler, parser, grounded-plan, and explanation behavior. It is not a reproduction of the full Sabre paper or benchmark suite. Shared-world experiments should supply their own native Sabre problem file, generated from the authoritative world snapshot, and record the exact problem hash and planner configuration for every call.
