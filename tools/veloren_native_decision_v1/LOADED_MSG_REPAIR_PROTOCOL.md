# Loaded RequestHire message-repair pair (new revision)

This protocol is separate from the frozen decision-v1 run. It is a bounded
interface-causality check for the minimal Loaded Msg routing repair; it does
not change recruitment rules, population/site guards, Job semantics, RNG, or
native receiver behavior.

## Frozen boundaries

- Exactly one OFF and one ON server launch, each at most 360 wall seconds;
  independent prebuilt userdata copies share the same source-world payload,
  world seed 130626853, and normalized settings contract.
- Use one pinned repaired server binary, source patch, original Cargo lock,
  and complete official assets-tree manifest. Verify all file hashes before
  launch. Never modify old runs or source-world inputs.
- Leader UID is fixed at 476. OFF and ON use the same native observer and
  persister list: [476,433,450,451,452,459,469,472,475,442].
- ON sends at most six requests, each with the pinned native TTL. The first
  qualified planner result INSUFFICIENT_CHOICES ends ON immediately. It is
  not a reason to wait for more candidates or restart.
- Before the first proposal, require the already-defined alive/Loaded/finitely
  positioned leader and two Loaded candidates across three distinct game-time
  samples spanning at least two wall-clock seconds. The cached ActorView must
  also be no older than 1.5 wall-clock seconds. No SPEAK requirement.
- First fully attributed native Hired Job freezes further submissions. Observe
  only that recipient's native hired/follow behavior for at most 30 additional
  seconds, then stop. If no trusted Job occurs, the fixed 360-second cap is
  right-censored; do not retry with a new world or seed.
- Maintain loopback-only networking, query disabled, 6 GiB disk floor, and
  telemetry caps of 10,000 records, 16 MiB, and 1,800 seconds. Do not launch a
  GUI, compile, or alter system security as part of this runner.
- The 360-second cap is the time to request stop; SIGUSR1 shutdown grace and
  total supervisor elapsed time are recorded separately.

## Attribution contract

native_recruit_message_sent means only that the sender generated/enqueued
RequestHire. It is never success by itself. A request is considered a trusted
hire only with this exact ordered chain, all on one request ID and matching
leader/recipient identity:

1. accepted + started + native_recruit_message_sent;
2. native_recruit_msg_retained_rtsim;
3. native_recruit_msg_delivered_to_inbox;
4. native_recruit_hire_input_consumed;
5. native_recruit_hire_effect_applied after the original setter call;
6. native_recruit_job_observed confirming the actual recipient Job.

The three message receipts carry request_id, source_uid, target_uid,
leader_uid, recipient_uid, time, decision_source, and msg_kind="RequestHire".
The effect and Job receipts must agree on request, source, target, leader,
recipient, decision source, and hire_until="infinity"; the Job receipt
additionally identifies the actual Job actor and opaque leader/recipient
NpcIds. Native messages without the sidecar remain unattributed. Never infer
linkage from timestamps or matching source/target alone.

Post-hire continuation is judged from the recipient's own baseline only, at
game times no earlier than the trusted Job observation. Require its native
brain backtrace to state it was hired by and is following the exact mapped
leader NpcId, its controller activity to show native task execution, and
nontrivial horizontal ECS movement. Leader-side Following, Agent behavior
labels, vertical-only displacement, and message_sent do not qualify.

## Outcome language

Report each phase separately: OFF, ON prefix/choice result, number of actual
input rows, complete provenance chain, actual Job, and recipient-side native
follow evidence. A normal hire without attributable message receipts is
unattributed; a trusted Job without recipient follow evidence is PARTIAL.
No qualifying choice or no trusted Job by the cap is not evidence that the
native rule rejected the candidate. OFF/ON share a world source and seed, but
native RNG remains uncontrolled; this pair does not establish statistical
advantage or deterministic trajectory equivalence.
