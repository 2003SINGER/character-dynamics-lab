# ClubFloyd command admission definition v1

## Frozen boundary

ClubFloyd `[ACTION]` is admitted as an observed chosen action `source_action_A_star` when it can be interpreted as a player's in-world choice or attempt. Admission does **not** test objective world legality.

\[
A_t^W = \text{objectively executable actions in real world state }W_t
\]
\[
\hat A_t^O = \text{candidate actions the character forms from its own }O_t
\]
\[
A_t^* = \text{the action actually selected/attempted by the player}
\]

The Stage-A boundary is:

`W -> O -> X -> S -> generated/estimated A^O -> policy -> A* -> W settlement -> W'`

`A*` need not belong to `A^W`. A mistaken-belief, rejected, failed, unreachable-target, or parser-rejected attempt remains an observed `A*` when the choice itself is clear. Post-action feedback may describe settlement/outcome, but cannot retroactively decide whether the choice existed.

## Final admission labels

- `IN_WORLD_CHOICE`: a player attempt to act in the game world, including success, failure, rejection, shorthand navigation, object interaction, speech/social action, custom verbs, spells, and parser-rejected inputs whose in-world intent is clear.
- `META_COMMAND`: explicit control of the game/system rather than the game world: save, restore, restart, quit, transcript, debug, credits, walkthrough, hint, and equivalent bookkeeping/system controls.
- `CHAT_OR_COMMENTARY`: commentary to people, logs, audience, parser, or game design rather than an in-world character/world action. In-world speech remains `IN_WORLD_CHOICE`.
- `UNRESOLVED`: only when raw action plus prediction-time legal context cannot stably distinguish the three classes above. World legality uncertainty alone is never `UNRESOLVED`.

## Annotation question

Ask only: **Does this `[ACTION]` represent the player choosing or attempting an in-world behavior?**

Do not ask whether the action is legal in `W`, whether it succeeded, or whether the pre-state proves the target exists. Those belong to the later `A* -> W` settlement/outcome layer. Stage A does not recover complete `A^O` or `A^W`.

## Provenance and evaluation

`command_admission_audit_semantic_v0.jsonl` and `command_admission_review_independent_v0.jsonl` are model-assisted review artifacts, not human gold. The semantic-equivalence evaluator remains separately frozen in `evaluate_command_v0.py`; classification labels must not be used as command-equivalence labels.
