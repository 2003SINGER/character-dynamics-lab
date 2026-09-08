# ClubFloyd multi-LLM adjudication aggregation rule v1

This rule is frozen before reviewer outputs are revealed.

- `MODEL_CONSENSUS`: all three labels agree and at least two confidences are `high` or `medium`.
- `MODEL_MAJORITY`: two labels agree and both majority confidences are not `low`.
- `HUMAN_REVIEW_REQUIRED`: three-way split, low-confidence majority, schema/protocol violation, or reasons contaminated by world-legality/post-state reasoning.

The accepted label is the consensus or majority label. Human-required rows remain blank and are excluded from the development-admitted subset until reviewed. These outputs are frozen multi-LLM adjudicated development labels, not human gold.
