# Ongoing Station — Native Run Replay

Scene: `20261013092810-ba8c71` · status: `COMPLETE` · sealed through: `{'events': 24, 'values': 24}`

This is a derived replay. Sealed ledger rows are ordered by their recorded minute and sequence (with source-array order as a tie-breaker). Decisions and receipts retain their order within each actor-local source stream. The evidence does not provide a precise cross-stream sequence, so the sections below are not a claim of total ordering.

## Minute 1

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:0:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:1:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:0:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:1:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:2`; commitment `self:7972:routine_route:0:7969`
- NPC `B`: `move` receipt `p3:7973:0:2`; commitment `self:7973:routine_route:0:7969`

## Minute 2

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:0` / `DEFERRED`; source=`actor_evidence[0].log[4]`; no locally known route or required item is available; commitment_id=`self:7972:routine_route:0:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:2', None]`; callback_event=`p5:20261013:A:2:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:0` / `DEFERRED`; source=`actor_evidence[1].log[4]`; no locally known route or required item is available; commitment_id=`self:7973:routine_route:0:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7973:0:2', None]`; callback_event=`p5:20261013:B:2:callback`

## Minute 3

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:deliver_supply` / `ACCEPTED`; source=`actor_evidence[0].log[6]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:deliver_supply:7974:7969`; task_kind=`deliver_supply`; intent=`get`; callback_event=`p5:20261013:A:3:callback`
- NPC `B`: SELF goal `self-goal:7973:deliver_supply` / `ACCEPTED`; source=`actor_evidence[1].log[6]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:deliver_supply:7975:7969`; task_kind=`deliver_supply`; intent=`get`; callback_event=`p5:20261013:B:3:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `get` receipt `p3:7972:0:7`; commitment `self:7972:deliver_supply:7974:7969`
- NPC `B`: `get` receipt `p3:7973:0:7`; commitment `self:7973:deliver_supply:7975:7969`

## Minute 4

### Sealed ledger (recorded sequence)

- `p5_delivery_settled` — event `p5:delivery:20261013092810-ba8c71:A:p3:7972:0:10`, sequence `18`
- `p5_delivery_settled` — event `p5:delivery:20261013092810-ba8c71:B:p3:7973:0:10`, sequence `19`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:deliver_supply` / `CONTINUE`; source=`actor_evidence[0].log[9]`; retain existing actor commitment; commitment_id=`self:7972:deliver_supply:7974:7969`; task_kind=`deliver_supply`; intent=`drop`; callback_event=`p5:20261013:A:4:callback`
- NPC `B`: SELF goal `self-goal:7973:deliver_supply` / `CONTINUE`; source=`actor_evidence[1].log[9]`; retain existing actor commitment; commitment_id=`self:7973:deliver_supply:7975:7969`; task_kind=`deliver_supply`; intent=`drop`; callback_event=`p5:20261013:B:4:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `drop` receipt `p3:7972:0:10`; commitment `self:7972:deliver_supply:7974:7969`
- NPC `B`: `drop` receipt `p3:7973:0:10`; commitment `self:7973:deliver_supply:7975:7969`

## Minute 5

### Sealed ledger (recorded sequence)

- `SOCIAL_REQUEST` — event `p4:20261013:hero:note-source:episode1`, sequence `25`
- `SOCIAL_RESPONSE` — event `p4:20261013:love:note-response:episode1`, sequence `26`
- `SOCIAL_COMMIT` — event `p4:20261013:love:note-response:episode1:commit`, sequence `27`

## Minute 6

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[14]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:0:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:6:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[14]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:0:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:6:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:15`; commitment `self:7972:routine_route:0:7968`
- NPC `B`: `move` receipt `p3:7973:0:15`; commitment `self:7973:routine_route:0:7968`

## Minute 7

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:0` / `CONTINUE`; source=`actor_evidence[0].log[17]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:0:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7972:0:15', None]`; intent=`move`; callback_event=`p5:20261013:A:7:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:0` / `CONTINUE`; source=`actor_evidence[1].log[17]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:0:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:15', None]`; intent=`move`; callback_event=`p5:20261013:B:7:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:18`; commitment `self:7972:routine_route:0:7968`
- NPC `B`: `move` receipt `p3:7973:0:18`; commitment `self:7973:routine_route:0:7968`

## Minute 8

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[20]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:0:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:2', None]`; intent=`move`; callback_event=`p5:20261013:A:8:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[20]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:0:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7973:0:2', None]`; intent=`move`; callback_event=`p5:20261013:B:8:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:21`; commitment `self:7972:routine_route:0:7969`
- NPC `B`: `move` receipt `p3:7973:0:21`; commitment `self:7973:routine_route:0:7969`

## Minute 9

### Sealed ledger (recorded sequence)

- `P5_ONGOING_STATION_ACTIVATION` — event `station:20261013092810-ba8c71:9:activate:1`, sequence `47`
- `P5_INTERVENTION` — event `p5:20261013:9:intervention:ongoing_station_author_activation`, sequence `48`; operation=`ongoing_station_author_activation`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:2` / `ACCEPTED`; source=`actor_evidence[0].log[23]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:2:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:9:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:2` / `ACCEPTED`; source=`actor_evidence[1].log[23]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:2:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:9:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[0]`; constraint `archive-note-by-horizon`, author version `1`, status `TASKS_PROPOSED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`True`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`True`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:24`; commitment `self:7972:routine_route:2:7969`
- NPC `B`: `move` receipt `p3:7973:0:24`; commitment `self:7973:routine_route:2:7969`

## Minute 10

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:2` / `CONTINUE`; source=`actor_evidence[0].log[26]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:2:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:24', None]`; intent=`move`; callback_event=`p5:20261013:A:10:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:2` / `CONTINUE`; source=`actor_evidence[1].log[26]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:2:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7973:0:24', None]`; intent=`move`; callback_event=`p5:20261013:B:10:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[1]`; constraint `archive-note-by-horizon`, author version `1`, status `TASKS_PROPOSED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`True`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`True`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:27`; commitment `self:7972:routine_route:2:7969`
- NPC `B`: `move` receipt `p3:7973:0:27`; commitment `self:7973:routine_route:2:7969`

## Minute 11

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:3` / `ACCEPTED`; source=`actor_evidence[0].log[29]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:3:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:11:callback`
- NPC `B`: AUTHOR goal `archive-note-by-horizon` / `ACCEPTED`; source=`actor_evidence[1].log[29]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`ongoing-station-m5-v1:archive-note-by-horizon:v1:file_by_B:B:archive_note`; task_kind=`archive_note`; intent=`move`; callback_event=`p5:20261013:B:11:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[2]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:30`; commitment `self:7972:routine_route:3:7969`
- NPC `B`: `move` receipt `p3:7973:0:30`; commitment `ongoing-station-m5-v1:archive-note-by-horizon:v1:file_by_B:B:archive_note`

## Minute 12

### Sealed ledger (recorded sequence)

- `P5_ONGOING_STATION_NOTE_ARCHIVED` — event `station-receipt:p3:7973:0:33`, sequence `65`; actor=`B`, receipt=`p3:7973:0:33`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:3` / `CONTINUE`; source=`actor_evidence[0].log[32]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:3:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:30', None]`; intent=`move`; callback_event=`p5:20261013:A:12:callback`
- NPC `B`: AUTHOR goal `archive-note-by-horizon` / `CONTINUE`; source=`actor_evidence[1].log[32]`; retain existing actor commitment; commitment_id=`ongoing-station-m5-v1:archive-note-by-horizon:v1:file_by_B:B:archive_note`; task_kind=`archive_note`; intent=`drop`; callback_event=`p5:20261013:B:12:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[3]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:33`; commitment `self:7972:routine_route:3:7969`
- NPC `B`: `drop` receipt `p3:7973:0:33`; commitment `ongoing-station-m5-v1:archive-note-by-horizon:v1:file_by_B:B:archive_note`

## Minute 13

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:4` / `ACCEPTED`; source=`actor_evidence[0].log[35]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:4:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:13:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:3` / `ACCEPTED`; source=`actor_evidence[1].log[35]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:3:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:13:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[4]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:36`; commitment `self:7972:routine_route:4:7969`
- NPC `B`: `move` receipt `p3:7973:0:36`; commitment `self:7973:routine_route:3:7968`

## Minute 14

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:4` / `CONTINUE`; source=`actor_evidence[0].log[38]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:4:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:36', None]`; intent=`move`; callback_event=`p5:20261013:A:14:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:3` / `CONTINUE`; source=`actor_evidence[1].log[38]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:3:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:36', None]`; intent=`move`; callback_event=`p5:20261013:B:14:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[5]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:39`; commitment `self:7972:routine_route:4:7969`
- NPC `B`: `move` receipt `p3:7973:0:39`; commitment `self:7973:routine_route:3:7968`

## Minute 15

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:5` / `ACCEPTED`; source=`actor_evidence[0].log[41]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:5:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:15:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:4` / `ACCEPTED`; source=`actor_evidence[1].log[41]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:4:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:15:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[6]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:42`; commitment `self:7972:routine_route:5:7969`
- NPC `B`: `move` receipt `p3:7973:0:42`; commitment `self:7973:routine_route:4:7968`

## Minute 16

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:5` / `CONTINUE`; source=`actor_evidence[0].log[44]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:5:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:42', None]`; intent=`move`; callback_event=`p5:20261013:A:16:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:4` / `CONTINUE`; source=`actor_evidence[1].log[44]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:4:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:42', None]`; intent=`move`; callback_event=`p5:20261013:B:16:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[7]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:45`; commitment `self:7972:routine_route:5:7969`
- NPC `B`: `move` receipt `p3:7973:0:45`; commitment `self:7973:routine_route:4:7968`

## Minute 17

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:6` / `ACCEPTED`; source=`actor_evidence[0].log[47]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:6:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:17:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:5` / `ACCEPTED`; source=`actor_evidence[1].log[47]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:5:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:17:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[8]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:48`; commitment `self:7972:routine_route:6:7969`
- NPC `B`: `move` receipt `p3:7973:0:48`; commitment `self:7973:routine_route:5:7968`

## Minute 18

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:6` / `CONTINUE`; source=`actor_evidence[0].log[50]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:6:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:48', None]`; intent=`move`; callback_event=`p5:20261013:A:18:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:5` / `CONTINUE`; source=`actor_evidence[1].log[50]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:5:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:48', None]`; intent=`move`; callback_event=`p5:20261013:B:18:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[9]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:51`; commitment `self:7972:routine_route:6:7969`
- NPC `B`: `move` receipt `p3:7973:0:51`; commitment `self:7973:routine_route:5:7968`

## Minute 19

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:7` / `ACCEPTED`; source=`actor_evidence[0].log[53]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:7:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:19:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:6` / `ACCEPTED`; source=`actor_evidence[1].log[53]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:6:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:19:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[10]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:54`; commitment `self:7972:routine_route:7:7969`
- NPC `B`: `move` receipt `p3:7973:0:54`; commitment `self:7973:routine_route:6:7968`

## Minute 20

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:7` / `CONTINUE`; source=`actor_evidence[0].log[56]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:7:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:54', None]`; intent=`move`; callback_event=`p5:20261013:A:20:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:6` / `CONTINUE`; source=`actor_evidence[1].log[56]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:6:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:54', None]`; intent=`move`; callback_event=`p5:20261013:B:20:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[11]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:57`; commitment `self:7972:routine_route:7:7969`
- NPC `B`: `move` receipt `p3:7973:0:57`; commitment `self:7973:routine_route:6:7968`

## Minute 21

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:8` / `ACCEPTED`; source=`actor_evidence[0].log[59]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:8:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:21:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:7` / `ACCEPTED`; source=`actor_evidence[1].log[59]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:7:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:21:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[12]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:60`; commitment `self:7972:routine_route:8:7969`
- NPC `B`: `move` receipt `p3:7973:0:60`; commitment `self:7973:routine_route:7:7968`

## Minute 22

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:8` / `CONTINUE`; source=`actor_evidence[0].log[62]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:8:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:60', None]`; intent=`move`; callback_event=`p5:20261013:A:22:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:7` / `CONTINUE`; source=`actor_evidence[1].log[62]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:7:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:60', None]`; intent=`move`; callback_event=`p5:20261013:B:22:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[13]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:63`; commitment `self:7972:routine_route:8:7969`
- NPC `B`: `move` receipt `p3:7973:0:63`; commitment `self:7973:routine_route:7:7968`

## Minute 23

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:9` / `ACCEPTED`; source=`actor_evidence[0].log[65]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7972:routine_route:9:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:23:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:8` / `ACCEPTED`; source=`actor_evidence[1].log[65]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7973:routine_route:8:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:23:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[14]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:66`; commitment `self:7972:routine_route:9:7969`
- NPC `B`: `move` receipt `p3:7973:0:66`; commitment `self:7973:routine_route:8:7968`

## Minute 24

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7972:routine_route:9` / `CONTINUE`; source=`actor_evidence[0].log[68]`; retain existing actor commitment; commitment_id=`self:7972:routine_route:9:7969`; task_kind=`routine_route`; route_waypoints=`[7969, 7968]`; waypoint_receipts=`['p3:7972:0:66', None]`; intent=`move`; callback_event=`p5:20261013:A:24:callback`
- NPC `B`: SELF goal `self-goal:7973:routine_route:8` / `CONTINUE`; source=`actor_evidence[1].log[68]`; retain existing actor commitment; commitment_id=`self:7973:routine_route:8:7968`; task_kind=`routine_route`; route_waypoints=`[7968, 7969]`; waypoint_receipts=`['p3:7973:0:66', None]`; intent=`move`; callback_event=`p5:20261013:B:24:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[15]`; constraint `archive-note-by-horizon`, author version `1`, status `WAITING_OR_BLOCKED`, selected method `file_by_B`.
  - Projected source bundle/version: `ongoing-station-m5-e1-e4-v1` / `1`; required handover: `none`; deadline `24`.
  - method `file_by_B` feasible=`False`; causal support=`['p5_note_archived']`; missing=`[]`.
  - method `return_then_file_by_A` feasible=`False`; causal support=`['p5_note_archived', 'p5_note_handed_over']`; missing=`[]`.
  - method `wait_for_response` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7972:0:69`; commitment `self:7972:routine_route:9:7969`
- NPC `B`: `move` receipt `p3:7973:0:69`; commitment `self:7973:routine_route:8:7968`

## Complete sealed-ledger index

The following appendix preserves every ledger source ID in its recorded sequence; routine ticks/callbacks are omitted from the story body only.

- minute `1`, sequence `1`: `TIME_ADVANCED` — `p4:20261013:1:time`
- minute `1`, sequence `2`: `P5_DIRECTOR_DECISION` — `p5:20261013:1:director:v1`
- minute `1`, sequence `3`: `P5_NPC_CALLBACK` — `p5:20261013:A:1:callback`
- minute `1`, sequence `4`: `P5_NPC_CALLBACK` — `p5:20261013:B:1:callback`
- minute `1`, sequence `5`: `P5_WORLD_SNAPSHOT` — `p5:20261013:1:snapshot`
- minute `2`, sequence `6`: `TIME_ADVANCED` — `p4:20261013:2:time`
- minute `2`, sequence `7`: `P5_DIRECTOR_DECISION` — `p5:20261013:2:director:v1`
- minute `2`, sequence `8`: `P5_NPC_CALLBACK` — `p5:20261013:A:2:callback`
- minute `2`, sequence `9`: `P5_NPC_CALLBACK` — `p5:20261013:B:2:callback`
- minute `2`, sequence `10`: `P5_WORLD_SNAPSHOT` — `p5:20261013:2:snapshot`
- minute `3`, sequence `11`: `TIME_ADVANCED` — `p4:20261013:3:time`
- minute `3`, sequence `12`: `P5_DIRECTOR_DECISION` — `p5:20261013:3:director:v1`
- minute `3`, sequence `13`: `P5_NPC_CALLBACK` — `p5:20261013:A:3:callback`
- minute `3`, sequence `14`: `P5_NPC_CALLBACK` — `p5:20261013:B:3:callback`
- minute `3`, sequence `15`: `P5_WORLD_SNAPSHOT` — `p5:20261013:3:snapshot`
- minute `4`, sequence `16`: `TIME_ADVANCED` — `p4:20261013:4:time`
- minute `4`, sequence `17`: `P5_DIRECTOR_DECISION` — `p5:20261013:4:director:v1`
- minute `4`, sequence `18`: `p5_delivery_settled` — `p5:delivery:20261013092810-ba8c71:A:p3:7972:0:10`
- minute `4`, sequence `19`: `p5_delivery_settled` — `p5:delivery:20261013092810-ba8c71:B:p3:7973:0:10`
- minute `4`, sequence `20`: `P5_NPC_CALLBACK` — `p5:20261013:A:4:callback`
- minute `4`, sequence `21`: `P5_NPC_CALLBACK` — `p5:20261013:B:4:callback`
- minute `4`, sequence `22`: `P5_WORLD_SNAPSHOT` — `p5:20261013:4:snapshot`
- minute `5`, sequence `23`: `TIME_ADVANCED` — `p4:20261013:5:time`
- minute `5`, sequence `24`: `P5_DIRECTOR_DECISION` — `p5:20261013:5:director:v1`
- minute `5`, sequence `25`: `SOCIAL_REQUEST` — `p4:20261013:hero:note-source:episode1`
- minute `5`, sequence `26`: `SOCIAL_RESPONSE` — `p4:20261013:love:note-response:episode1`
- minute `5`, sequence `27`: `SOCIAL_COMMIT` — `p4:20261013:love:note-response:episode1:commit`
- minute `5`, sequence `28`: `P5_NPC_CALLBACK` — `p5:20261013:A:5:callback`
- minute `5`, sequence `29`: `P5_NPC_CALLBACK` — `p5:20261013:B:5:callback`
- minute `5`, sequence `30`: `P5_WORLD_SNAPSHOT` — `p5:20261013:5:snapshot`
- minute `6`, sequence `31`: `TIME_ADVANCED` — `p4:20261013:6:time`
- minute `6`, sequence `32`: `P5_DIRECTOR_DECISION` — `p5:20261013:6:director:v1`
- minute `6`, sequence `33`: `P5_NPC_CALLBACK` — `p5:20261013:A:6:callback`
- minute `6`, sequence `34`: `P5_NPC_CALLBACK` — `p5:20261013:B:6:callback`
- minute `6`, sequence `35`: `P5_WORLD_SNAPSHOT` — `p5:20261013:6:snapshot`
- minute `7`, sequence `36`: `TIME_ADVANCED` — `p4:20261013:7:time`
- minute `7`, sequence `37`: `P5_DIRECTOR_DECISION` — `p5:20261013:7:director:v1`
- minute `7`, sequence `38`: `P5_NPC_CALLBACK` — `p5:20261013:A:7:callback`
- minute `7`, sequence `39`: `P5_NPC_CALLBACK` — `p5:20261013:B:7:callback`
- minute `7`, sequence `40`: `P5_WORLD_SNAPSHOT` — `p5:20261013:7:snapshot`
- minute `8`, sequence `41`: `TIME_ADVANCED` — `p4:20261013:8:time`
- minute `8`, sequence `42`: `P5_DIRECTOR_DECISION` — `p5:20261013:8:director:v1`
- minute `8`, sequence `43`: `P5_NPC_CALLBACK` — `p5:20261013:A:8:callback`
- minute `8`, sequence `44`: `P5_NPC_CALLBACK` — `p5:20261013:B:8:callback`
- minute `8`, sequence `45`: `P5_WORLD_SNAPSHOT` — `p5:20261013:8:snapshot`
- minute `9`, sequence `46`: `TIME_ADVANCED` — `p4:20261013:9:time`
- minute `9`, sequence `47`: `P5_ONGOING_STATION_ACTIVATION` — `station:20261013092810-ba8c71:9:activate:1`
- minute `9`, sequence `48`: `P5_INTERVENTION` — `p5:20261013:9:intervention:ongoing_station_author_activation`
- minute `9`, sequence `49`: `P5_DIRECTOR_DECISION` — `p5:20261013:9:director:v1`
- minute `9`, sequence `50`: `P5_NPC_CALLBACK` — `p5:20261013:A:9:callback`
- minute `9`, sequence `51`: `P5_NPC_CALLBACK` — `p5:20261013:B:9:callback`
- minute `9`, sequence `52`: `P5_WORLD_SNAPSHOT` — `p5:20261013:9:snapshot`
- minute `10`, sequence `53`: `TIME_ADVANCED` — `p4:20261013:10:time`
- minute `10`, sequence `54`: `P5_DIRECTOR_DECISION` — `p5:20261013:10:director:v1`
- minute `10`, sequence `55`: `P5_NPC_CALLBACK` — `p5:20261013:A:10:callback`
- minute `10`, sequence `56`: `P5_NPC_CALLBACK` — `p5:20261013:B:10:callback`
- minute `10`, sequence `57`: `P5_WORLD_SNAPSHOT` — `p5:20261013:10:snapshot`
- minute `11`, sequence `58`: `TIME_ADVANCED` — `p4:20261013:11:time`
- minute `11`, sequence `59`: `P5_DIRECTOR_DECISION` — `p5:20261013:11:director:v1`
- minute `11`, sequence `60`: `P5_NPC_CALLBACK` — `p5:20261013:A:11:callback`
- minute `11`, sequence `61`: `P5_NPC_CALLBACK` — `p5:20261013:B:11:callback`
- minute `11`, sequence `62`: `P5_WORLD_SNAPSHOT` — `p5:20261013:11:snapshot`
- minute `12`, sequence `63`: `TIME_ADVANCED` — `p4:20261013:12:time`
- minute `12`, sequence `64`: `P5_DIRECTOR_DECISION` — `p5:20261013:12:director:v1`
- minute `12`, sequence `65`: `P5_ONGOING_STATION_NOTE_ARCHIVED` — `station-receipt:p3:7973:0:33`
- minute `12`, sequence `66`: `P5_NPC_CALLBACK` — `p5:20261013:A:12:callback`
- minute `12`, sequence `67`: `P5_NPC_CALLBACK` — `p5:20261013:B:12:callback`
- minute `12`, sequence `68`: `P5_WORLD_SNAPSHOT` — `p5:20261013:12:snapshot`
- minute `13`, sequence `69`: `TIME_ADVANCED` — `p4:20261013:13:time`
- minute `13`, sequence `70`: `P5_DIRECTOR_DECISION` — `p5:20261013:13:director:v1`
- minute `13`, sequence `71`: `P5_NPC_CALLBACK` — `p5:20261013:A:13:callback`
- minute `13`, sequence `72`: `P5_NPC_CALLBACK` — `p5:20261013:B:13:callback`
- minute `13`, sequence `73`: `P5_WORLD_SNAPSHOT` — `p5:20261013:13:snapshot`
- minute `14`, sequence `74`: `TIME_ADVANCED` — `p4:20261013:14:time`
- minute `14`, sequence `75`: `P5_DIRECTOR_DECISION` — `p5:20261013:14:director:v1`
- minute `14`, sequence `76`: `P5_NPC_CALLBACK` — `p5:20261013:A:14:callback`
- minute `14`, sequence `77`: `P5_NPC_CALLBACK` — `p5:20261013:B:14:callback`
- minute `14`, sequence `78`: `P5_WORLD_SNAPSHOT` — `p5:20261013:14:snapshot`
- minute `15`, sequence `79`: `TIME_ADVANCED` — `p4:20261013:15:time`
- minute `15`, sequence `80`: `P5_DIRECTOR_DECISION` — `p5:20261013:15:director:v1`
- minute `15`, sequence `81`: `P5_NPC_CALLBACK` — `p5:20261013:A:15:callback`
- minute `15`, sequence `82`: `P5_NPC_CALLBACK` — `p5:20261013:B:15:callback`
- minute `15`, sequence `83`: `P5_WORLD_SNAPSHOT` — `p5:20261013:15:snapshot`
- minute `16`, sequence `84`: `TIME_ADVANCED` — `p4:20261013:16:time`
- minute `16`, sequence `85`: `P5_DIRECTOR_DECISION` — `p5:20261013:16:director:v1`
- minute `16`, sequence `86`: `P5_NPC_CALLBACK` — `p5:20261013:A:16:callback`
- minute `16`, sequence `87`: `P5_NPC_CALLBACK` — `p5:20261013:B:16:callback`
- minute `16`, sequence `88`: `P5_WORLD_SNAPSHOT` — `p5:20261013:16:snapshot`
- minute `17`, sequence `89`: `TIME_ADVANCED` — `p4:20261013:17:time`
- minute `17`, sequence `90`: `P5_DIRECTOR_DECISION` — `p5:20261013:17:director:v1`
- minute `17`, sequence `91`: `P5_NPC_CALLBACK` — `p5:20261013:A:17:callback`
- minute `17`, sequence `92`: `P5_NPC_CALLBACK` — `p5:20261013:B:17:callback`
- minute `17`, sequence `93`: `P5_WORLD_SNAPSHOT` — `p5:20261013:17:snapshot`
- minute `18`, sequence `94`: `TIME_ADVANCED` — `p4:20261013:18:time`
- minute `18`, sequence `95`: `P5_DIRECTOR_DECISION` — `p5:20261013:18:director:v1`
- minute `18`, sequence `96`: `P5_NPC_CALLBACK` — `p5:20261013:A:18:callback`
- minute `18`, sequence `97`: `P5_NPC_CALLBACK` — `p5:20261013:B:18:callback`
- minute `18`, sequence `98`: `P5_WORLD_SNAPSHOT` — `p5:20261013:18:snapshot`
- minute `19`, sequence `99`: `TIME_ADVANCED` — `p4:20261013:19:time`
- minute `19`, sequence `100`: `P5_DIRECTOR_DECISION` — `p5:20261013:19:director:v1`
- minute `19`, sequence `101`: `P5_NPC_CALLBACK` — `p5:20261013:A:19:callback`
- minute `19`, sequence `102`: `P5_NPC_CALLBACK` — `p5:20261013:B:19:callback`
- minute `19`, sequence `103`: `P5_WORLD_SNAPSHOT` — `p5:20261013:19:snapshot`
- minute `20`, sequence `104`: `TIME_ADVANCED` — `p4:20261013:20:time`
- minute `20`, sequence `105`: `P5_DIRECTOR_DECISION` — `p5:20261013:20:director:v1`
- minute `20`, sequence `106`: `P5_NPC_CALLBACK` — `p5:20261013:A:20:callback`
- minute `20`, sequence `107`: `P5_NPC_CALLBACK` — `p5:20261013:B:20:callback`
- minute `20`, sequence `108`: `P5_WORLD_SNAPSHOT` — `p5:20261013:20:snapshot`
- minute `21`, sequence `109`: `TIME_ADVANCED` — `p4:20261013:21:time`
- minute `21`, sequence `110`: `P5_DIRECTOR_DECISION` — `p5:20261013:21:director:v1`
- minute `21`, sequence `111`: `P5_NPC_CALLBACK` — `p5:20261013:A:21:callback`
- minute `21`, sequence `112`: `P5_NPC_CALLBACK` — `p5:20261013:B:21:callback`
- minute `21`, sequence `113`: `P5_WORLD_SNAPSHOT` — `p5:20261013:21:snapshot`
- minute `22`, sequence `114`: `TIME_ADVANCED` — `p4:20261013:22:time`
- minute `22`, sequence `115`: `P5_DIRECTOR_DECISION` — `p5:20261013:22:director:v1`
- minute `22`, sequence `116`: `P5_NPC_CALLBACK` — `p5:20261013:A:22:callback`
- minute `22`, sequence `117`: `P5_NPC_CALLBACK` — `p5:20261013:B:22:callback`
- minute `22`, sequence `118`: `P5_WORLD_SNAPSHOT` — `p5:20261013:22:snapshot`
- minute `23`, sequence `119`: `TIME_ADVANCED` — `p4:20261013:23:time`
- minute `23`, sequence `120`: `P5_DIRECTOR_DECISION` — `p5:20261013:23:director:v1`
- minute `23`, sequence `121`: `P5_NPC_CALLBACK` — `p5:20261013:A:23:callback`
- minute `23`, sequence `122`: `P5_NPC_CALLBACK` — `p5:20261013:B:23:callback`
- minute `23`, sequence `123`: `P5_WORLD_SNAPSHOT` — `p5:20261013:23:snapshot`
- minute `24`, sequence `124`: `TIME_ADVANCED` — `p4:20261013:24:time`
- minute `24`, sequence `125`: `P5_DIRECTOR_DECISION` — `p5:20261013:24:director:v1`
- minute `24`, sequence `126`: `P5_NPC_CALLBACK` — `p5:20261013:A:24:callback`
- minute `24`, sequence `127`: `P5_NPC_CALLBACK` — `p5:20261013:B:24:callback`
- minute `24`, sequence `128`: `P5_WORLD_SNAPSHOT` — `p5:20261013:24:snapshot`

## Outcome boundary

A proposal is not an accepted commitment; an accepted commitment is not a settled action. Only the native ledger, receipt, and independent database readback establish physical effects.
