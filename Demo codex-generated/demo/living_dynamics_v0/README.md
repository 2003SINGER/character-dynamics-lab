# Living Dynamics v0 / FREE_RUN_6H

**STATUS: DEMO / APPLICATION ONLY**  
**RESEARCH EVIDENCE: NONE**

This is a development-only engineering sandbox for coupled living dynamics. It is not validated psychology, a research result, or proof of realism.

Persistent S is unchanged. Perceived hunger, perceived bathroom need, overload, sleep readiness, recovery efficiency, and task absorption are derived transient modifiers.

The first life loops are now coupled rather than fixed scripts: hunger and bathroom
urge accumulate from elapsed time, current fatigue/anxiety, and the running action;
their perceived discomfort feeds satisfaction and anxiety; meal relief, bathroom
relief, and rest recovery depend on the state at the moment of completion. The
policy sees those derived pressures when choosing whether to study, recover, eat,
or leave the room. This is an executable sandbox coupling, not a calibrated
physiology model.

The five frozen runs use scenario/policy seeds `(17,101)`, `(29,202)`, `(43,303)`, `(61,404)`, and `(89,505)`. Generate them with:

```sh
cmake --build build
python3 tools/free_run_report.py demo/living_dynamics_v0 build/character_dynamics_free_run
```

The generated report is diagnostic only. Known limitations: the free-run trace is a compact development readout, action semantics remain rule-based, and no claim of human realism is made.
