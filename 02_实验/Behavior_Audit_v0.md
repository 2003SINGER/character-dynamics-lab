# Behavior audit v0｜optimizer_train failure mining

状态：**development exploration / casebook generated / Objective not frozen**。

## Purpose and boundary

This audit inspects existing synthetic `optimizer_train` trajectories to learn
what actually looks broken before inventing a pathology objective. It is not a
pre-registered experiment, not a quality score, and never reads
`internal_holdout`.

The reproducible exporter is
`tools/behavior_audit_casebook_v0.py`. Its local output is ignored at
`outputs/behavior_audit_casebook_v0/`: `casebook.md`, `cases.json`, and one
complete 256-step CSV trace per selected case.

The exporter hard-checks that every input `scenario_seed` belongs to frozen
`optimizer_train` (1101–1128). It does not open an input containing holdout
seeds.

## v0 screeners

The following only select material for human review; none is an objective term
or a declared pathology threshold:

- same-action runs;
- consecutive zero-minute actions;
- high hunger without `get_meal` and high bathroom urge without
  `go_to_bathroom`;
- high task pressure with low study probability while the task is active;
- active-task no-effort segments;
- long suspended commitments.

The baseline trajectory schema lacks `deadline_remaining`. Therefore this v0
casebook deliberately does not screen or claim deadline non-response; task
pressure is not a substitute for an observable deadline.

## First readout

The baseline train batch yielded 52 distinct cases from 896 trajectories. Five
initial full-trace reads established useful counterexamples:

1. A run of eight `idle` decisions advanced time by ten minutes per decision,
   followed task completion, and had low needs. Repetition alone is not a
   pathology.
2. Several `shop_on_phone` runs repeated six or seven times at zero elapsed
   minutes after completion. World time and state did not advance during the
   run. This is a plausible time-stall failure mode worth further review, not
   yet a frozen penalty.
3. High hunger/bathroom screen hits can occur in a task-pressure / recovery
   trade-off and frequently later receive a meal or bathroom action. Exposure
   count alone cannot decide whether the behavior is unreasonable.
4. Long commitment suspension can resume and complete after recovery. Duration
   alone cannot diagnose a commitment lock.
5. A high-pressure active task may continue studying despite high hunger. Its
   reasonableness depends on known affordances, urgency, elapsed time, and
   subsequent recovery, so it requires contextual labels rather than a scalar
   cutoff.

## Next action

Review the selected traces, recording for each proposed failure mode at least
one true positive, true negative, false positive, and false negative. Only
then draft a candidate metric and test it against those counterexamples. Keep
Objective v0 and optimizer selection disabled until that calibration is
complete.
