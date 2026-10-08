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
weights stay out of Git. Selected synthetic run traces/cassettes and reports
are published under the [public review allowlist](../../../02_实验/PUBLIC_REVIEW_INDEX_2026-10-07.md);
private inputs and unlisted run artifacts remain local.

## Local run

Install `laya` in the Mac user Python environment and download the checkpoint
through Hugging Face. Start a bridge on loopback, retaining the cassette in a
new, non-overwriting directory under this project's `outputs/laya_runs/`.
Only explicitly allowlisted evidence is published:

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

## Archived v2 integration evidence (2026-09-23; not behavioral evidence)

An earlier 48-hour balanced run on this Mac (scenario seed `1000`, policy seed
`5000`) exercised the local MPS bridge and byte-identical cassette replay
(trace SHA-256 `ddae59cd972a325b0d67165ac845bfcadf24438c9097a04dc86645`).
It is retained as transport/integration evidence only: later audit found its
numeric scheduler clock advanced while formatted `clock.time` remained stale,
so its behavioral trajectory is not interpretable. The checkpoint also emitted
a warning that some bundled temperatures are invalid; probability calibration
remains unproven.
Historical v3 runs pinned the checkpoint to Hugging Face revision
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
ordinary v3 replay accepted only matching v3 cassettes from the same proxy source
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

## v4 actor-local history contract

New requests use protocol/prompt v4. `ContinuousRuntime` owns an `ActorHistory`
separate from O and S. It records only observed self-action feedback and
known/stale O deltas; no World event log is projected directly. Policy and
soft-gate requests include current action progress, up to 16 chronological
episodes from the last 12 hours, up to 2 observed events, and mechanical
explicit 48-hour action totals, last occurrences, and the last observed sleep interval.
Typed appraisal and commitment receive a shorter causal slice (up to five
episodes and eight observed events from two hours). Purchase urge and the
commitment start minute are included in the state projection. Rule activation,
probability and candidate reason remain outside the Laya payload.

These history limits bound request growth. The v4.3 model projection keeps the
full request untouched in the cassette. It uses ordered P/S values, an action
name table, semicolon-separated episode and H2 rows, and run-length known/stale
O statuses. Episode starts after the first are offsets from the preceding
episode start; action result, target, actual/planned duration, and optional task
remain explicit. Empty strings use `~`, while strings needing whitespace
escaping use `~` plus percent encoding. A value-level decoder and a self-contained
22-O/16-episode/13-action mixed-history fixture check this projection in the
local regression test. Prompt identity is
`character-dynamics-laya-typed-v4.3` (wire protocol remains v4). v4.2 cassettes
cannot replay under v4.3 because prompt identity and request hash differ. The
actual tokenizer/sequence-builder guard checks the complete sequence and fails
closed before inference if it does not fit; no facts, history, or question are
silently truncated. Use
`--laya-no-history` with the same seeds and executable for a v4 no-history
policy ablation. v3 cassettes cannot replay as v4 because protocol, prompt and
request hashes changed. This is a factual actor-local autobiography for the
Demo adapter, not evidence of psychological validity. No sleep-specific
preference or behavior parameter was added.

The preserved v4.2 exact-HEAD 1-day attempt stopped at request 11 because its
history-bearing state used 789 tokens against a 784-token allowance. v4.3 was
audited without inference using the captured complex v4 request, the actual
checkpoint tokenizer, and the captured v3 request with the largest 22-fact O
surface. The joint fixture has 22 O facts, a current RunningAction, 16
chronological episodes within 12 hours, two observed events, 13 H2 action
types, and 13 candidates. Sleep/rest durations, settled/interrupted/rejected
outcomes, task-tagged episodes, and clock time were preserved; rejected
episodes have zero actual duration. H2 totals and last-occurrence ages agree
with accepted H1 episodes; H1-absent actions have explicit older 48-hour
contributions, and `last_sleep` matches the latest accepted sleep. It uses
760/784 state tokens and 1000/1024 complete input tokens (24-token margins);
the question head uses 118/138 tokens (20-token margin). The repository
regression test also exercises this maximum-history shape. The offline audit
command is:

```sh
python3 tools/laya_v4_token_margin_audit.py \
  /absolute/path/to/v4.2-history-cassette.jsonl \
  /absolute/path/to/laya-checkpoint-snapshot \
  --stress /absolute/path/to/v3-1d-cassette.jsonl
```

These are input-fit checks, not policy outcomes. No v4.3 live 1-day or 64-actor
run was started; the exact-HEAD gate still awaits independent review.

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

An actual 1-day `balanced` full typed run on MPS (scenario `1000`, policy seed
`5000`; v3, checkpoint revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`)
produced 55 boundaries and 115 live cassette rows: 51 policy choices, 9 soft
gates, 6 commitment choices and 49 appraisal scores. Every request's numeric
and formatted clock agreed; the smallest recorded state-token margin was 147,
and the smallest complete question-head margin was 105 tokens. This head
margin subtracts the full question tokens and every option's tokens plus its
MASK marker from `head_max_len`; it does not count instructions alone. Strict
replay reproduced the trace byte-for-byte (SHA-256
`b004f9653272adbc1afb6ff7f38fbabf4f2a18ffaf8076d38a4738de62257292`). This
is an integration/input-contract check only, not a long-run or human-validity
finding. A model-free contract smoke also checks visible versus hidden
commitment clearing and unchanged bodily-state updates.

## Historical v1 pilot record (2026-09-24; not behavioral evidence)

The earlier v1 one-tape run exercised the paired execution and cassette-replay
workflow for eight P profiles. Its historical Laya-minus-Rule averages were
+176.25 rest minutes/day, -101.02 sleep minutes/day, -24.75 study minutes/day,
and 0.00 task completions/day. Keep these numbers only as a record of that
workflow run: subsequent inspection found that most model inputs may have
silently truncated state, so the comparison is not interpretable as a
behavioral result and must not support behavioral claims.

The earlier v2 policy-only multi-tape pilot was interrupted at 6/8 profiles
after the stale-clock and restricted-choice-surface defects were found; it is
invalid as behavioral evidence. The old v1 traces, v2 cassette and partial
artifacts must not be mixed into a new experiment. Each new Laya run uses a dedicated initially empty
cassette; the evaluator atomically records a per-actor `DONE` marker with trace
and replay evidence, and resumes only actors whose signature and hashes validate.
The default Rule/Laya A/B is policy-only and eligible for the existing paired
policy comparator. Full typed X/I modes alter Dynamics and are a separate
supplementary track; they cannot be interpreted as changing only π or compared
under the `only_policy_changed` claim. Soft-gate mode is likewise a separate
factor. Raw historical artifacts are under the project-local
`../../../outputs/laya_runs/` directory. Public-safe experiment traces and
cassettes are now explicitly tracked; dataset inputs, build products, large
files and sensitive logs are excluded according to the
[public review inventory](../../../02_实验/PUBLIC_REVIEW_INDEX_2026-10-07.md).
Publishing invalid/partial runs preserves negative evidence; it does not make
the old v1/v2 comparisons valid.
Archived `COMMANDS.md` files preserve their original execution paths; replace
their former Research-root run directory with `outputs/laya_runs/` when rerunning.
