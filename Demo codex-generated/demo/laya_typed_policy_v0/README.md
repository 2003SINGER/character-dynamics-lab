# LayaTypedPolicyV0 — actual local typed-decisions checkpoint

This optional **Demo-only** policy uses the real
[`convaiinnovations/laya-typed-decisions`](https://huggingface.co/convaiinnovations/laya-typed-decisions)
checkpoint, not the historical Qwen action selector. The Python loopback
bridge calls `laya.load()` once and asks a typed `choice` over the current
eligible A^O. It records every raw option probability in a local cassette.
The C++ adapter validates and normalizes that distribution, then samples it
with the existing seeded Runtime RNG. Its selected action still passes the
same World validation. Neither bridge nor model sees hidden W, World
primitives, or rule-policy probabilities. There is no cloud inference
endpoint or fallback to RulePolicy.

The public checkpoint is specialised to four synthetic workflows, not human
character behavior; its reported probability calibration is weak. Thus
these runs are engineering comparisons, not psychological validation. Model
weights/cassettes stay out of Git.

## Local run

Install `laya` in the Mac user Python environment and download the checkpoint
through Hugging Face. Start a bridge on loopback, retaining the cassette in a
non-repository data directory:

```sh
python3 tools/laya_typed_proxy.py \
  --cassette /absolute/path/to/laya-typed-probabilities.jsonl \
  --device mps --port 8743
build/character_dynamics_free_run 1000 5000 /tmp/laya-48h.json \
  balanced --laya-port 8743
```

To replay without loading the model, launch a second bridge with `--replay
/absolute/path/to/laya-typed-probabilities.jsonl` on another port and use
that port in the free-run command. The same input/seed should yield a
byte-identical trace. The `candidates` probabilities in the trace are the
actual normalised π sampled by C++, not the Dynamics proposal.

## Verified local evidence (2026-09-23)

On this Mac, actual Laya 0.3.7 on MPS produced a 48-hour balanced trajectory
for scenario seed `1000`, policy seed `5000`: 103 boundaries, 86 typed policy
decisions. The first decision's π assigned positive probability to six
actions; the run selected study, rest, sleep, meals, bathroom, device use,
room control and idle across its trajectory. Frozen-cassette replay matched
byte-for-byte (SHA-256
`ddae59cd972a325b0d67165ac845bfcadf24438c9097a04dc86645`).
The checkpoint emitted a runtime warning that some bundled temperatures are
invalid; treat confidence/probability calibration as unproven.

The Python bridge is an application adapter only. ReferenceRuleDynamicsV0,
DemoLivingDynamicsV1, W validation, scheduler and research evaluator are
unchanged by the policy-only mode. A/B experiments must record the exact
checkpoint, cassette and policy id; old RulePolicy runs cannot be renamed as
Laya runs.

## Same-world Rule/Laya experiment

Use separate, initially empty output directories outside the repository. The
Rule and Laya commands run the **same executable**, World seed/tape, initial
O/S/I, eight P profiles and policy RNG seed. The Laya evaluator independently
replays each live run from the growing raw-probability cassette and retains a
copy of that cassette in its output. History forks query the actual typed π,
not the RulePolicy proposal. The comparison refuses mismatched executable,
world tape, initial state, personality or seed.

```sh
python3 tools/long_horizon_eval.py build/character_dynamics_long_horizon \
  /absolute/path/to/rule-7d --days 7 --cases 8
python3 tools/long_horizon_eval.py build/character_dynamics_long_horizon \
  /absolute/path/to/laya-7d --days 7 --cases 8 --policy laya \
  --laya-port 8743 --laya-cassette /absolute/path/to/laya-typed-probabilities.jsonl
python3 tools/paired_policy_compare.py \
  /absolute/path/to/rule-7d /absolute/path/to/laya-7d \
  /absolute/path/to/rule-vs-laya-7d
```

`analysis.json` and `REPORT.md` include task/behavior time, history-fork
effects, action-bout persistence, commitment-active/suspended duration,
action entropy, switching and repeated-action patterns. These are descriptive
Demo diagnostics with no pre-imposed pathology threshold. Longer horizons
consume many local model calls and are not implied to have run by these
commands or by the model-free CI smoke.
