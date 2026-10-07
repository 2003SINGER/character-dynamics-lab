# Laya v4 controlled history probe

This is a local, controlled input-sensitivity fixture, not a natural trajectory
or evidence of psychological validity.

Artifact root: `/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v4_probe_20260925/`.

- Source HEAD: `81694a923fbcddf73f40fe9f090ced9163d5571c` plus the uncommitted v4
  ActorHistory worktree changes.
- Checkpoint: `convaiinnovations/laya-typed-decisions`, revision
  `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`; local MPS inference.
- Protocol / prompt: `laya-typed-v4` / `character-dynamics-laya-typed-v4`.
- C++ fixture: identical current O/S/P/AO, running action and scheduler time
  (Day 2 00:00); hidden wallet differs 1 vs 999 but is not observable. Arm A
  contains several Rest episodes in the prior ~20 hours and no Sleep. Arm B
  contains a 480-minute Sleep ending 60 minutes ago, plus older Rest episodes.
- Candidate set in both arms: hard-admissible SleepAtBed and RestAtBed. Soft
  gate, typed appraisal, and typed commitment are disabled.

Live probabilities:

| History fixture | Sleep π | Rest π | request hash |
|---|---:|---:|---|
| A: repeated Rest, no recent Sleep | 0.4673 | 0.5327 | `0c8053162d908c528e04674aae55595f2c52c3d57e0ba7c817267942af881ad6` |
| B: 8h Sleep, awake 1h | 0.5163 | 0.4837 | `6d6b0f494314934fb4bd10cd8ee959f0fe91235abcd4f0a12696b56bfcadc198` |

The controlled fixture changed Sleep π by +0.0490 and Rest π by -0.0490.
This establishes sensitivity to the serialized H difference only. The direction
is not interpreted as behaviorally valid.

Exact checkpoint-tokenizer audit stored per cassette row:

| Arm | State tokens / budget | State margin | Full input / max_len | Question head / max |
|---|---:|---:|---:|---:|
| A | 542 / 902 | 360 | 664 / 1024 | 98 / 256 |
| B | 557 / 902 | 345 | 679 / 1024 | 98 / 256 |

The auxiliary H60/H30 serializer test is retained separately. Its exact live
cassette hash is recorded in the shell transcript; the main evidence is the
controlled Sleep/Rest pair above.

Cassette SHA-256:

- `controlled-sleep-rest-live-cassette.jsonl`: `deb52a9671a05725cf1a245fe5c0620b3279df3bf997eab06139bef78d8c8b30`
- `auxiliary-sleep-duration-contract-cassette.jsonl`: `3a1a6645524ee999371ba22ff8ac0a22f40d50da8fa4f9888a7fa37736db1dcd`

After adding the explicit `window_h:48` field and matching prompt, the
worst-policy request was re-audited from the actual checkpoint tokenizer:
848/861 state tokens, 13-token state margin, and 1011/1024 complete input
tokens. The exact request is preserved as
`worst-policy-request-pre-freeze.json` (SHA-256
`49c567a44788d49678527697b60db04d80ab3007b1875008bb8242474834866a`). This
request snapshot is newer than the controlled-pair cassettes above; both are
pre-commit exploratory artifacts and should be regenerated on the frozen exact
source revision before final behavioral conclusions.
