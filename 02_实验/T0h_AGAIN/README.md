# AGAIN adapter

`again_adapter.py` uses the real AGAIN schema. It groups telemetry by the dataset's `(player_id, session_id, game)` key and aligns each telemetry row to the latest valid arousal annotation at or before the same session-relative `time_stamp`. Future annotation values are never interpolated backward.

The arousal value is exposed only as `source_arousal_proxy`; `source_O`, `source_action_A_star`, and `state_label` remain null. The 20-session development slice is in `again_dev_20_v2/` with 300 review fixtures and executable QA.
