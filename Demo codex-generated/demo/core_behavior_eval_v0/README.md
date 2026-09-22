# Demo core behavior evaluation v0

This is a development instrument for two questions: does changed personality
`P` alter behavior under the *same* world, and does the actor's accumulated
state/commitment alter subsequent decisions under the *same* `W/O/P`? It is
not a human-validity benchmark or a reason to freeze DemoLivingV1.

## Reproduce

From the repository root, configure/build `Demo codex-generated` and run:

```sh
python3 'Demo codex-generated/tools/long_horizon_eval.py' \
  build/character_dynamics_long_horizon OUTPUT_DIR --days 30 --cases 3 --axes
python3 'Demo codex-generated/tools/long_horizon_eval.py' \
  build/character_dynamics_long_horizon OUTPUT_DIR --days 180 --cases 8
```

Use a new `OUTPUT_DIR` for each experiment. The manifest records the full Git
revision, executable SHA-256, all profile vectors, scenario/policy seeds, and
per-run raw-trace hashes. Each run is independently replayed and byte-compared.
The compressed JSONL contains boundary, daily, and history-fork records.

Within a case, all eight profiles start with identical `W/O/S/I`, the same
scenario and policy RNG seeds, and a three-day coursework tape. The evaluator
compares the observed external event tape byte-for-byte across profiles. The
single-axis experiment starts from balanced `P`, changes one dimension to
0.2/0.5/0.8, and checks that every other dimension and the tape remain fixed.

At days 7/30/60/120/180 of a 180-day run, history forks copy `W/O/P`, the
scheduler (including any RunningAction), and the exact policy RNG state. They
then replace only `S/I` with a neutral reset or prior-day snapshot. Immediate
policy distributions and subsequent 6h/24h/72h trajectories are compared;
the evaluator also checks the future external event tape matches between
branches. Shorter runs fork at day 7 and the final day when available.

The life tape is opt-in to this runner; historical Reference fixtures retain
their original World behavior. A `task-assigned` event explicitly informs the
actor, supersedes the prior task, and opens a decision boundary. This is an
experimental repeated-stimulus room, not a full social life. The old 48-hour
batch remains engineering regression evidence and must not be cited as a
paired personality experiment.
