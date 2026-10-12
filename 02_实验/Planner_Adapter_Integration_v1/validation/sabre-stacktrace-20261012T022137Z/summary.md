# Sabre negative-case stack diagnostic

- Input: `../sabre-domain-preflight-20261012T021250Z/negative-no-opportunity/problem.txt`
- Input SHA-256: `64a385b42098623ef5ace134775a7ad7573b8c922716fde76293d76efcb6cbf6`
- Diagnostic entry point: `tools/planner_adapter_integration_v1/validation/SabreStackTrace.java` (SHA-256 `5f0627847e1158b615fe5d14168ad8c5fdd8d3876f56e12a8d4bf32f8b693a30`)
- Sabre `Main.class` SHA-256: `3835ffd623059aa0806974632675fc4acdf3d46243660270e48cb16fc6d97678`
- `Comparison.class` SHA-256: `c2baff0b01e41ae79ed9bc2a0d9db662466764d1b42eb90781d96a1638959db8`
- CLI search arguments kept identical to the failed preflight: `-v -p <same problem> -m bf -c t -h h+ -el 1 -vl 200 -gl 5000 -tl 5000 -atl 24 -ctl 16`; JVM heap/stack and locale flags also unchanged. The main class was switched to the existing stack-diagnostic entry point; `-XX:MaxJavaStackTraceDepth=48` only caps repetitive trace printing.
- Result: parser reports 2 characters, 10 entities, 42 fluents, 38 actions, 0 triggers, then throws `java.lang.StackOverflowError` before compilation/search. The recurring top frames alternate `Comparison$3.combine(Comparison.java:472)` and `Comparison$NumericOperator.combine(Comparison.java:361)`. This localizes the failure to recursive numeric-comparison combination during compilation; it does not establish the deeper cause or any search-method efficacy.
- The existing preflight positive case remains separately recorded as `BUDGET_LIMIT` after 200 visited / 604 generated nodes in 29 ms. This diagnostic provides no native execution evidence.
- `stacktrace.txt` preserves the captured diagnostic output with JVM stack printing capped at 48 frames; the unbounded trace is highly repetitive. No source, Sabre binary, or previous run was modified.
