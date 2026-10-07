# NPC continuity watchable playback

This is an offline, static replay for paired `npc-continuity-paired-trace-v1` JSONL runs. It is not an interactive game or player validation. The browser opens only the generated player-safe file; it never fetches or reads a raw debug trace.

## Export and open

From the repository root, assign neutral clip IDs to the six utility/history-LLM × case traces, keeping the ID-to-condition mapping only in the owning research report. The browser selector shows only these neutral IDs.

```sh
python3 "Demo codex-generated/applications/npc_continuity_v0/presentation/export_player_timeline.py" \
  --clip clip-a1=outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/alarm_active.utility.jsonl \
  --clip clip-b2=outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/near_completion_alarm.history-llm.jsonl \
  --clip clip-c3=outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/quiet_active.utility.jsonl \
  --clip clip-d4=outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/alarm_active.history-llm.jsonl \
  --clip clip-e5=outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/near_completion_alarm.utility.jsonl \
  --clip clip-f6=outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/quiet_active.history-llm.jsonl \
  --output outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/player/player.json \
  --html-output outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/player/index.html
open outputs/npc_continuity_v0/stage23_paired_20261006_WakUj8/player/index.html
```

Both output paths must be new; the exporter refuses to overwrite either file. The standalone HTML contains only the transformed allowlisted payload and inline viewer assets, so it can be opened directly without starting a server or installing packages. `player/player.json` is a separate audit copy of the same safe payload.

## Player-visible contract

The payload contains only neutral clip IDs, simulated times, known public task/alarm/message facts, actual running-action snapshots and intervals, room-object targets, and cues derived from known observation deltas. Each interval is attributed to `running_before`; `running_after` becomes current only at the boundary. `selected_action`, World events, case/policy/model identifiers, runtime gates, candidate sets, scores, history, reasons, and debug outcomes are not copied. Unknown or stale facts do not create visible state or cues.

Autoplay advances simulated time proportionally at 1, 5, or 15 simulated minutes per real second. Previous/next and the range control jump between recorded boundaries. The CSS room figure is a placeholder animation, not licensed or production character art.

Run the contract checks from this directory:

```sh
python3 -m unittest -v test_export_player_timeline.py
```
