# LIGHT v2 calibration smoke result

This is the valid v2 calibration smoke, not the invalid v1 prefix and not the
later persistent-session diagnostic. It contains 60 source-only annotations in
three 20-row tasks. The 60 rows are globally trajectory-distinct; reviewer
payloads use opaque IDs and expose only `actor`, `source_O`, `source_action_A_star`,
and `candidate_set_factual`.

## Result

- ADMIT: 13
- AMBIGUOUS: 47
- REJECT: 0
- `a_star_alignment`: YES 35, UNCLEAR 25
- `candidate_usability`: USABLE 13, UNCLEAR 47
- schema/ID/order validation: passed
- controlled reason codes: passed

The high ambiguity rate is intentional evidence from the calibration: the
revised rubric does not turn unestablished entity ownership, possession, or
relations into `REJECT`. The model uses `AMBIGUOUS` for those cases and reserves
`REJECT` for explicit malformed or contradictory evidence.

The annotation JSONL is keyed only by opaque reviewer IDs; the private mapping
and source shards remain outside Git. This is model-assisted source semantic
diagnostic evidence, not a human audit or an admission mask.
