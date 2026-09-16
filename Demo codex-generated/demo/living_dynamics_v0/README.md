# Living Dynamics v0 / FREE_RUN_6H

This is a development-only engineering sandbox for coupled living dynamics. It is not validated psychology, a research result, or proof of realism.

Persistent S is unchanged. Perceived hunger, perceived bathroom need, overload, sleep readiness, recovery efficiency, and task absorption are derived transient modifiers.

The five frozen runs use scenario/policy seeds `(17,101)`, `(29,202)`, `(43,303)`, `(61,404)`, and `(89,505)`. Generate them with:

```sh
cmake --build build
python3 tools/free_run_report.py demo/living_dynamics_v0 build/character_dynamics_free_run
```

The generated report is diagnostic only. Known limitations: the free-run trace is a compact development readout, action semantics remain rule-based, and no claim of human realism is made.
