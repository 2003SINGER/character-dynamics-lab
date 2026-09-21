# Demo Living V1 mechanism-repair audit

Status: `IN_PROGRESS`; this replaces the premature baseline-freeze claim for
the Demo/application model only.  It is not research evidence.

## Confirmed defects

1. **Recovery had three fatigue writers.**  A running Rest/Sleep action
   changed fatigue continuously, its settlement appraisal changed fatigue
   again, and `Recovery` semantic signals could change it a third time.  The
   repair assigns fatigue recovery exclusively to the running-action
   continuous path.  Settlement retains typed O feedback and non-fatigue
   meaning, but has no fatigue mutation.
2. **Sleep utility double-counted fatigue.**  `recovery_drive` already
   contains `fatigue_recovery_drive`; `sleep_readiness` also contained a
   direct fatigue term.  Sleep readiness is now a circadian/screen/body
   context signal, while fatigue enters sleep selection only through recovery
   drive.
3. **A long running action cannot yet be reconsidered on a new subjective
   boundary.**  The current kernel only notices a first `.40` hunger/bathroom
   upward crossing.  It cannot request a decision on recovery satiation or a
   later urgent escalation.  This requires an explicitly authorized generic
   Runtime gate/interface change; it is deliberately not simulated with a
   V1 policy workaround.
4. **Task pressure is still an impulse stock.**  A correct repair needs a
   target derived from observable deadline, own progress, remaining workload,
   and commitment, and a continuous move toward that target.  The internal
   runtime clock must first be projected into O for that target to be honest.
   This has the same explicit Runtime-boundary dependency as item 3.

## Current safe repair scope

- `DemoLivingDynamicsV1` only: single fatigue and screen-exposure owners;
  remove the duplicated fatigue path from Sleep utility.
- No Runtime, scheduler, World, O schema, Reference model, Research model,
  Laya, or action schema change is made under this partial authorization.
- The batch is not relabelled as repaired/frozen until items 3 and 4 have
  executable Runtime evidence.
