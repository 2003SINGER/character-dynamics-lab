# LayaTypedPolicyV0 — actual local typed-decisions checkpoint

This optional **Demo-only** policy uses the real
[`convaiinnovations/laya-typed-decisions`](https://huggingface.co/convaiinnovations/laya-typed-decisions)
checkpoint, not the historical Qwen action selector. The Python loopback
bridge calls `laya.load()` once and asks a typed `choice` over O-known,
hard-admissible A^O. Rule activation remains a soft preference used by
RulePolicy; it does not hide otherwise admissible choices from Laya. Hard
bodily-need and extreme-fatigue exclusions still apply. Each option includes
its known target and planned default duration. It records every raw option probability in a local cassette.
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
New runs pin the checkpoint to Hugging Face revision
`f9ab0b228f0fc0f14d873dbc99038f135c2da1b2` and record revision,
protocol/prompt v3, decoding contract, raw typed answer, request hash, and
state/input/head/option token counts and budgets in the local cassette. Before
every typed policy, soft-gate, commitment, or appraisal prediction, the bridge
uses the loaded model tokenizer and Laya's actual sequence builder to verify
that the complete instructions, every option, and all compact-state tokens
enter the model sequence untruncated. The same check rejects clipped question
heads/options and over-budget state before inference. Token audit fields contain
counts only; they add no state text to cassette rows. Scheduler time projects
both `clock.total_minutes` and formatted `clock.time` into O from the same
boundary timestamp. Request hashes include protocol and prompt versions;
ordinary replay accepts only matching v3 cassettes from the same proxy source
SHA-256; legacy v1 hash fallback requires the explicit `--allow-v1-replay`
option alongside `--replay`. The startup banner
and read-only `{"operation":"identity"}` handshake expose the checkpoint and
bridge source identity. The handshake performs no inference and adds no cassette
row. The loopback protocol is newline-framed over a reused connection; a closed
proxy session is detected before the next request and can be reconnected safely.
An ambiguous send/receive failure is reported without automatic retry, so a
possibly processed request is never silently duplicated.

The earlier v2 7-day pilot cassette is retained only as invalid-input evidence,
not as a current behavioral result: its numeric clock advanced while the
formatted `clock.time` stayed stale, and Rule-soft-filtered actions were absent
from the Laya choice surface. Do not resume it or replay it as a v3 experiment.

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

## Optional typed soft reconsideration

`--laya-soft-gate` is an opt-in Demo-only extension to `--laya-port` for
`character_dynamics_free_run` and `character_dynamics_long_horizon`. At a
boundary with a still-running action and no existing hard gate, Laya receives
only O/S/P/I plus the current RunningAction and answers a typed `noul` question.
C++ validates its probability and uses the Runtime's seeded RNG to decide
whether to **add** a decision opportunity. A false answer cannot close a
World/need/completion/rejection gate. If the subsequent policy keeps the same
action, its original start time and elapsed progress survive; only an explicit
replacement is validated and interrupts it. The returned probability,
sampled Boolean and cassette hash are traced in `model_soft_reconsideration`.

The policy-only Rule/Laya comparison above leaves this switch off, so the
paired experiment still changes only π. Soft-gate mode is a separate
intervention, not evidence about policy-only effects. The checkpoint's raw
`noul` probabilities are not calibrated psychological probabilities.

## Optional typed commitment and appraisal

The long-horizon executable also accepts `--laya-commitment` and
`--laya-appraisal` after `--laya-port`. These switches replace only selected
DemoLiving Dynamics hooks; they are **not** part of the policy-only Rule/Laya
A/B above. The model receives actor-local O, current Delta-O, observed
self-action feedback, S/P/I, and no hidden W or executable primitive.

- Commitment is a typed choice among `continue/suspend/resume/abandon`, with
  options constrained by current I. C++ samples the validated distribution
  with the Runtime RNG. Visible task completion or an observed replacement of
  the task episode clears I deterministically; hidden W completion cannot.
  Continuing or resuming retains the original commitment start time.
- Appraisal asks seven typed `score` questions (0–4): goal progress,
  obstruction, stimulation, uncertainty, positive outcome, negative outcome,
  and restored control. DemoLivingV1 still performs the deterministic S update.
  Hunger/bathroom relief, physical fatigue, screen strain, purchase inventory
  and O-derived task-pressure geometry remain outside Laya's control.
  Observed task completion keeps its exactly-once canonical signal.
- `--laya-soft-gate` is independently selectable. A full Demo intervention
  can combine all three switches; its changed behavior must not be attributed
  to policy alone.

An actual 1-day `balanced` full typed X/I run (scenario `1000`, policy seed
`5000`) exercised 48 appraisal scores, 21 commitment choices and 44 policy
choices, including continue/suspend/resume/abandon. Independent cassette
replay reproduced its JSONL trace byte-for-byte. This is an integration test,
not a long-run or human-validity finding. A model-free contract smoke also
checks visible versus hidden commitment clearing and unchanged bodily-state
updates.

## Historical v1 pilot record (2026-09-24; not behavioral evidence)

The earlier v1 one-tape run exercised the paired execution and cassette-replay
workflow for eight P profiles. Its historical Laya-minus-Rule averages were
+176.25 rest minutes/day, -101.02 sleep minutes/day, -24.75 study minutes/day,
and 0.00 task completions/day. Keep these numbers only as a record of that
workflow run: subsequent inspection found that most model inputs may have
silently truncated state, so the comparison is not interpretable as a
behavioral result and must not support behavioral claims.

The v2 multi-tape run has not yet been completed. The old v1 traces, cassette,
and interrupted partial artifacts are excluded from it and must not be mixed
into a new experiment. Each new Laya run uses a dedicated initially empty
cassette; the evaluator atomically records a per-actor `DONE` marker with trace
and replay evidence, and resumes only actors whose signature and hashes validate.
The default Rule/Laya A/B is policy-only and eligible for the existing paired
policy comparator. Full typed X/I modes alter Dynamics and are a separate
supplementary track; they cannot be interpreted as changing only π or compared
under the `only_policy_changed` claim. Soft-gate mode is likewise a separate
factor. Raw historical artifacts remain under
`/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/` and are
intentionally not committed.
