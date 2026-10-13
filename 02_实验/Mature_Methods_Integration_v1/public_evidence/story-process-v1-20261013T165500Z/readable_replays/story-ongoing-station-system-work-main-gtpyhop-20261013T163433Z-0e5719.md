# Ongoing Station — Native Run Replay

Scene: `20261013163433-17a730` · status: `COMPLETE` · sealed through: `{'events': 24, 'values': 24}`

This is a derived replay. Sealed ledger rows are ordered by their recorded minute and sequence (with source-array order as a tie-breaker). Decisions and receipts retain their order within each actor-local source stream. The evidence does not provide a precise cross-stream sequence, so the sections below are not a claim of total ordering.

## Minute 1

### Sealed ledger (recorded sequence)

- `P5_STATION_WORK_STARTED` — event `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8806:1:1:self:8806:inspect_supply:8808:start`, sequence `3`; actor=`A`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:inspect_supply` / `ACCEPTED`; source=`actor_evidence[0].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:inspect_supply:8808`; task_kind=`inspect_supply`; intent=`use_tool`; callback_event=`p5:20261013:A:1:callback`
- NPC `B`: SELF goal `self-goal:8807:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8807:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:1:callback`

### Settled native receipts (actor receipt-array order)

- NPC `B`: `move` receipt `p3:8807:0:2`; commitment `self:8807:routine_route:0:8803`

## Minute 2

### Sealed ledger (recorded sequence)

- `P5_ONGOING_STATION_ACTIVATION` — event `station:20261013163433-17a730:2:activate:1`, sequence `8`
- `P5_INTERVENTION` — event `p5:20261013:2:intervention:ongoing_station_author_activation`, sequence `9`; operation=`ongoing_station_author_activation`

### Actor-local decisions (source-log order)

- NPC `B`: SELF goal `self-goal:8807:routine_route:0` / `DEFERRED`; source=`actor_evidence[1].log[4]`; no locally known route or required item is available; commitment_id=`self:8807:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8807:0:2', None]`; callback_event=`p5:20261013:B:2:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[0]`; constraint `supply-stored-by-horizon`, author version `1`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

## Minute 3

### Sealed ledger (recorded sequence)

- `P5_ONGOING_STATION_AUTHOR_EDIT` — event `station:20261013163433-17a730:3:edit:1`, sequence `15`
- `P5_INTERVENTION` — event `p5:20261013:3:intervention:ongoing_station_author_edit`, sequence `16`; operation=`ongoing_station_author_edit`
- `P5_STATION_SUPPLY_INSPECTED` — event `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8806:1:1:self:8806:inspect_supply:8808:finish`, sequence `18`; actor=`A`, receipt=`station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8806:1:1:self:8806:inspect_supply:8808:finish`

### Actor-local decisions (source-log order)

- NPC `B`: SELF goal `self-goal:8807:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[6]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8807:routine_route:0:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:3:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[1]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[2]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `B`: `move` receipt `p3:8807:0:7`; commitment `self:8807:routine_route:0:8802`

## Minute 4

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[4]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:4:callback`
- NPC `B`: SELF goal `self-goal:8807:routine_route:0` / `CONTINUE`; source=`actor_evidence[1].log[9]`; retain existing actor commitment; commitment_id=`self:8807:routine_route:0:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`['p3:8807:0:7', None]`; intent=`move`; callback_event=`p5:20261013:B:4:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[3]`; constraint `supply-stored-by-horizon`, author version `2`, status `CONDITIONAL_PLAN`, selected method `inspect_then_repair`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`True`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[4]`; constraint `repair-before-storage`, author version `2`, status `CONDITIONAL_PLAN`, selected method `inspect_then_repair`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`True`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:5`; commitment `self:8806:routine_route:0:8803`
- NPC `B`: `move` receipt `p3:8807:0:10`; commitment `self:8807:routine_route:0:8802`

## Minute 5

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:0` / `DEFERRED`; source=`actor_evidence[0].log[7]`; no locally known route or required item is available; commitment_id=`self:8806:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8806:0:5', None]`; callback_event=`p5:20261013:A:5:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `ACCEPTED`; source=`actor_evidence[1].log[12]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; intent=`move`; callback_event=`p5:20261013:B:5:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[5]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[6]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `B`: `move` receipt `p3:8807:0:13`; commitment `system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`

## Minute 6

### Sealed ledger (recorded sequence)

- `P5_INTERVENTION` — event `p5:20261013:6:intervention:player_native_command`, sequence `33`; operation=`player_native_command`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[9]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:0:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:6:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[15]`; exact tool is not locally visible or held; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:6:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[7]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[8]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:10`; commitment `self:8806:routine_route:0:8802`

## Minute 7

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:0` / `CONTINUE`; source=`actor_evidence[0].log[12]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:0:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`['p3:8806:0:10', None]`; intent=`move`; callback_event=`p5:20261013:A:7:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[17]`; exact tool is not locally visible or held; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:7:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[9]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[10]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:13`; commitment `self:8806:routine_route:0:8802`

## Minute 8

### Sealed ledger (recorded sequence)

- `P5_INTERVENTION` — event `p5:20261013:8:intervention:player_native_command`, sequence `44`; operation=`player_native_command`
- `P5_STATION_WORK_STARTED` — event `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8807:8:1:self:8807:repair_passage:8812:start`, sequence `46`; actor=`B`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[15]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8806:0:5', None]`; intent=`move`; callback_event=`p5:20261013:A:8:callback`
- NPC `B`: SELF goal `self-goal:8807:repair_passage` / `ACCEPTED`; source=`actor_evidence[1].log[19]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8807:repair_passage:8812`; task_kind=`repair_passage`; intent=`use_tool`; callback_event=`p5:20261013:B:8:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[11]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[12]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:16`; commitment `self:8806:routine_route:0:8803`

## Minute 9

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:2` / `ACCEPTED`; source=`actor_evidence[0].log[18]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:2:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:9:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[13]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[14]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:19`; commitment `self:8806:routine_route:2:8803`

## Minute 10

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:2` / `CONTINUE`; source=`actor_evidence[0].log[21]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:2:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8806:0:19', None]`; intent=`move`; callback_event=`p5:20261013:A:10:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[15]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[16]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:22`; commitment `self:8806:routine_route:2:8803`

## Minute 11

### Sealed ledger (recorded sequence)

- `P5_STATION_PASSAGE_REPAIRED` — event `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8807:8:1:self:8807:repair_passage:8812:finish`, sequence `62`; actor=`B`, receipt=`station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8807:8:1:self:8807:repair_passage:8812:finish`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:3` / `ACCEPTED`; source=`actor_evidence[0].log[24]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:3:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:11:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[17]`; constraint `supply-stored-by-horizon`, author version `2`, status `CONDITIONAL_PLAN`, selected method `inspect_then_repair`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[18]`; constraint `repair-before-storage`, author version `2`, status `CONDITIONAL_PLAN`, selected method `inspect_then_repair`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:25`; commitment `self:8806:routine_route:3:8803`

## Minute 12

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:3` / `CONTINUE`; source=`actor_evidence[0].log[27]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:3:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8806:0:25', None]`; intent=`move`; callback_event=`p5:20261013:A:12:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[22]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:12:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[19]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[20]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:28`; commitment `self:8806:routine_route:3:8803`

## Minute 13

### Actor-local decisions (source-log order)

- NPC `A`: AUTHOR goal `repair-before-storage` / `ACCEPTED`; source=`actor_evidence[0].log[30]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:locked_fragment:A:store_item`; task_kind=`store_item`; intent=`get`; callback_event=`p5:20261013:A:13:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[24]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:13:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[21]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[22]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `get` receipt `p3:8806:0:31`; commitment `system-work-v1:2:47b66b7b5ce3:repair-before-storage:locked_fragment:A:store_item`

## Minute 14

### Actor-local decisions (source-log order)

- NPC `A`: AUTHOR goal `repair-before-storage` / `CONTINUE`; source=`actor_evidence[0].log[33]`; retain existing actor commitment; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:locked_fragment:A:store_item`; task_kind=`store_item`; intent=`move`; callback_event=`p5:20261013:A:14:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[26]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:14:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[23]`; constraint `supply-stored-by-horizon`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[24]`; constraint `repair-before-storage`, author version `2`, status `WAIT_OR_UNSATISFIED`, selected method `None`.
  - method `inspect_then_repair` feasible=`False`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:34`; commitment `system-work-v1:2:47b66b7b5ce3:repair-before-storage:locked_fragment:A:store_item`

## Minute 15

### Sealed ledger (recorded sequence)

- `P5_STATION_SUPPLY_STORED` — event `station-store:20261013163433-17a730:8806:8808:15:1`, sequence `83`; actor=`A`, operation=`store_item`, receipt=`station-store:20261013163433-17a730:8806:8808:15:1`

### Actor-local decisions (source-log order)

- NPC `A`: AUTHOR goal `repair-before-storage` / `CONTINUE`; source=`actor_evidence[0].log[36]`; retain existing actor commitment; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:locked_fragment:A:store_item`; task_kind=`store_item`; intent=`store_item`; callback_event=`p5:20261013:A:15:callback`
- NPC `B`: SELF goal `self-goal:8807:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[27]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8807:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8807:0:2', None]`; callback_event=`p5:20261013:B:15:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[25]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[26]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `store_item` receipt `p3:8806:0:37`; commitment `system-work-v1:2:47b66b7b5ce3:repair-before-storage:locked_fragment:A:store_item`

## Minute 16

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:store_item` / `DEFERRED`; source=`actor_evidence[0].log[39]`; exact supply lacks a locally visible completed inspection; commitment_id=`self:8806:store_item:8808`; task_kind=`store_item`; callback_event=`p5:20261013:A:16:callback`
- NPC `B`: SELF goal `self-goal:8807:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[28]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8807:routine_route:0:8803`; task_kind=`routine_route`; route_waypoints=`[8803, 8802]`; waypoint_receipts=`['p3:8807:0:2', None]`; callback_event=`p5:20261013:B:16:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[27]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[28]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

## Minute 17

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:4` / `ACCEPTED`; source=`actor_evidence[0].log[40]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:4:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:17:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[30]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:17:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[29]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[30]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:41`; commitment `self:8806:routine_route:4:8802`

## Minute 18

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:4` / `CONTINUE`; source=`actor_evidence[0].log[43]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:4:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`['p3:8806:0:41', None]`; intent=`move`; callback_event=`p5:20261013:A:18:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[32]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:18:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[31]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[32]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:44`; commitment `self:8806:routine_route:4:8802`

## Minute 19

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:5` / `ACCEPTED`; source=`actor_evidence[0].log[46]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:5:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:19:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[34]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:19:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[33]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[34]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:47`; commitment `self:8806:routine_route:5:8802`

## Minute 20

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:5` / `CONTINUE`; source=`actor_evidence[0].log[49]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:5:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`['p3:8806:0:47', None]`; intent=`move`; callback_event=`p5:20261013:A:20:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[36]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:20:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[35]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[36]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:50`; commitment `self:8806:routine_route:5:8802`

## Minute 21

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:6` / `ACCEPTED`; source=`actor_evidence[0].log[52]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:6:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:21:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[38]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:21:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[37]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[38]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:53`; commitment `self:8806:routine_route:6:8802`

## Minute 22

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:6` / `CONTINUE`; source=`actor_evidence[0].log[55]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:6:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`['p3:8806:0:53', None]`; intent=`move`; callback_event=`p5:20261013:A:22:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[40]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:22:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[39]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[40]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:56`; commitment `self:8806:routine_route:6:8802`

## Minute 23

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:7` / `ACCEPTED`; source=`actor_evidence[0].log[58]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:8806:routine_route:7:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:23:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[42]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:23:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[41]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[42]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:59`; commitment `self:8806:routine_route:7:8802`

## Minute 24

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:8806:routine_route:7` / `CONTINUE`; source=`actor_evidence[0].log[61]`; retain existing actor commitment; commitment_id=`self:8806:routine_route:7:8802`; task_kind=`routine_route`; route_waypoints=`[8802, 8803]`; waypoint_receipts=`['p3:8806:0:59', None]`; intent=`move`; callback_event=`p5:20261013:A:24:callback`
- NPC `B`: AUTHOR goal `repair-before-storage` / `DEFERRED`; source=`actor_evidence[1].log[44]`; exact closed repair exit is not locally observed at the workbench; commitment_id=`system-work-v1:2:47b66b7b5ce3:repair-before-storage:inspect_then_repair:B:repair_passage`; task_kind=`repair_passage`; callback_event=`p5:20261013:B:24:callback`

### Author/controller evaluation

- source `ongoing_station.controller_decisions[43]`; constraint `supply-stored-by-horizon`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.
- source `ongoing_station.controller_decisions[44]`; constraint `repair-before-storage`, author version `2`, status `SATISFIED_PREFIX`, selected method `None`.
  - method `inspect_then_repair` feasible=`True`; causal support=`[]`; missing=`[]`.
  - method `repair_then_inspect` feasible=`False`; causal support=`[]`; missing=`[]`.

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:8806:0:62`; commitment `self:8806:routine_route:7:8802`

## Complete sealed-ledger index

The following appendix preserves every ledger source ID in its recorded sequence; routine ticks/callbacks are omitted from the story body only.

- minute `1`, sequence `1`: `TIME_ADVANCED` — `p4:20261013:1:time`
- minute `1`, sequence `2`: `P5_DIRECTOR_DECISION` — `p5:20261013:1:director:v1`
- minute `1`, sequence `3`: `P5_STATION_WORK_STARTED` — `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8806:1:1:self:8806:inspect_supply:8808:start`
- minute `1`, sequence `4`: `P5_NPC_CALLBACK` — `p5:20261013:A:1:callback`
- minute `1`, sequence `5`: `P5_NPC_CALLBACK` — `p5:20261013:B:1:callback`
- minute `1`, sequence `6`: `P5_WORLD_SNAPSHOT` — `p5:20261013:1:snapshot`
- minute `2`, sequence `7`: `TIME_ADVANCED` — `p4:20261013:2:time`
- minute `2`, sequence `8`: `P5_ONGOING_STATION_ACTIVATION` — `station:20261013163433-17a730:2:activate:1`
- minute `2`, sequence `9`: `P5_INTERVENTION` — `p5:20261013:2:intervention:ongoing_station_author_activation`
- minute `2`, sequence `10`: `P5_DIRECTOR_DECISION` — `p5:20261013:2:director:v1`
- minute `2`, sequence `11`: `P5_NPC_CALLBACK` — `p5:20261013:A:2:callback`
- minute `2`, sequence `12`: `P5_NPC_CALLBACK` — `p5:20261013:B:2:callback`
- minute `2`, sequence `13`: `P5_WORLD_SNAPSHOT` — `p5:20261013:2:snapshot`
- minute `3`, sequence `14`: `TIME_ADVANCED` — `p4:20261013:3:time`
- minute `3`, sequence `15`: `P5_ONGOING_STATION_AUTHOR_EDIT` — `station:20261013163433-17a730:3:edit:1`
- minute `3`, sequence `16`: `P5_INTERVENTION` — `p5:20261013:3:intervention:ongoing_station_author_edit`
- minute `3`, sequence `17`: `P5_DIRECTOR_DECISION` — `p5:20261013:3:director:v1`
- minute `3`, sequence `18`: `P5_STATION_SUPPLY_INSPECTED` — `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8806:1:1:self:8806:inspect_supply:8808:finish`
- minute `3`, sequence `19`: `P5_NPC_CALLBACK` — `p5:20261013:A:3:callback`
- minute `3`, sequence `20`: `P5_NPC_CALLBACK` — `p5:20261013:B:3:callback`
- minute `3`, sequence `21`: `P5_WORLD_SNAPSHOT` — `p5:20261013:3:snapshot`
- minute `4`, sequence `22`: `TIME_ADVANCED` — `p4:20261013:4:time`
- minute `4`, sequence `23`: `P5_DIRECTOR_DECISION` — `p5:20261013:4:director:v1`
- minute `4`, sequence `24`: `P5_NPC_CALLBACK` — `p5:20261013:A:4:callback`
- minute `4`, sequence `25`: `P5_NPC_CALLBACK` — `p5:20261013:B:4:callback`
- minute `4`, sequence `26`: `P5_WORLD_SNAPSHOT` — `p5:20261013:4:snapshot`
- minute `5`, sequence `27`: `TIME_ADVANCED` — `p4:20261013:5:time`
- minute `5`, sequence `28`: `P5_DIRECTOR_DECISION` — `p5:20261013:5:director:v1`
- minute `5`, sequence `29`: `P5_NPC_CALLBACK` — `p5:20261013:A:5:callback`
- minute `5`, sequence `30`: `P5_NPC_CALLBACK` — `p5:20261013:B:5:callback`
- minute `5`, sequence `31`: `P5_WORLD_SNAPSHOT` — `p5:20261013:5:snapshot`
- minute `6`, sequence `32`: `TIME_ADVANCED` — `p4:20261013:6:time`
- minute `6`, sequence `33`: `P5_INTERVENTION` — `p5:20261013:6:intervention:player_native_command`
- minute `6`, sequence `34`: `P5_DIRECTOR_DECISION` — `p5:20261013:6:director:v1`
- minute `6`, sequence `35`: `P5_NPC_CALLBACK` — `p5:20261013:A:6:callback`
- minute `6`, sequence `36`: `P5_NPC_CALLBACK` — `p5:20261013:B:6:callback`
- minute `6`, sequence `37`: `P5_WORLD_SNAPSHOT` — `p5:20261013:6:snapshot`
- minute `7`, sequence `38`: `TIME_ADVANCED` — `p4:20261013:7:time`
- minute `7`, sequence `39`: `P5_DIRECTOR_DECISION` — `p5:20261013:7:director:v1`
- minute `7`, sequence `40`: `P5_NPC_CALLBACK` — `p5:20261013:A:7:callback`
- minute `7`, sequence `41`: `P5_NPC_CALLBACK` — `p5:20261013:B:7:callback`
- minute `7`, sequence `42`: `P5_WORLD_SNAPSHOT` — `p5:20261013:7:snapshot`
- minute `8`, sequence `43`: `TIME_ADVANCED` — `p4:20261013:8:time`
- minute `8`, sequence `44`: `P5_INTERVENTION` — `p5:20261013:8:intervention:player_native_command`
- minute `8`, sequence `45`: `P5_DIRECTOR_DECISION` — `p5:20261013:8:director:v1`
- minute `8`, sequence `46`: `P5_STATION_WORK_STARTED` — `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8807:8:1:self:8807:repair_passage:8812:start`
- minute `8`, sequence `47`: `P5_NPC_CALLBACK` — `p5:20261013:A:8:callback`
- minute `8`, sequence `48`: `P5_NPC_CALLBACK` — `p5:20261013:B:8:callback`
- minute `8`, sequence `49`: `P5_WORLD_SNAPSHOT` — `p5:20261013:8:snapshot`
- minute `9`, sequence `50`: `TIME_ADVANCED` — `p4:20261013:9:time`
- minute `9`, sequence `51`: `P5_DIRECTOR_DECISION` — `p5:20261013:9:director:v1`
- minute `9`, sequence `52`: `P5_NPC_CALLBACK` — `p5:20261013:A:9:callback`
- minute `9`, sequence `53`: `P5_NPC_CALLBACK` — `p5:20261013:B:9:callback`
- minute `9`, sequence `54`: `P5_WORLD_SNAPSHOT` — `p5:20261013:9:snapshot`
- minute `10`, sequence `55`: `TIME_ADVANCED` — `p4:20261013:10:time`
- minute `10`, sequence `56`: `P5_DIRECTOR_DECISION` — `p5:20261013:10:director:v1`
- minute `10`, sequence `57`: `P5_NPC_CALLBACK` — `p5:20261013:A:10:callback`
- minute `10`, sequence `58`: `P5_NPC_CALLBACK` — `p5:20261013:B:10:callback`
- minute `10`, sequence `59`: `P5_WORLD_SNAPSHOT` — `p5:20261013:10:snapshot`
- minute `11`, sequence `60`: `TIME_ADVANCED` — `p4:20261013:11:time`
- minute `11`, sequence `61`: `P5_DIRECTOR_DECISION` — `p5:20261013:11:director:v1`
- minute `11`, sequence `62`: `P5_STATION_PASSAGE_REPAIRED` — `station-work:20261013163433-17a730:station-attempt:20261013163433-17a730:8807:8:1:self:8807:repair_passage:8812:finish`
- minute `11`, sequence `63`: `P5_NPC_CALLBACK` — `p5:20261013:A:11:callback`
- minute `11`, sequence `64`: `P5_NPC_CALLBACK` — `p5:20261013:B:11:callback`
- minute `11`, sequence `65`: `P5_WORLD_SNAPSHOT` — `p5:20261013:11:snapshot`
- minute `12`, sequence `66`: `TIME_ADVANCED` — `p4:20261013:12:time`
- minute `12`, sequence `67`: `P5_DIRECTOR_DECISION` — `p5:20261013:12:director:v1`
- minute `12`, sequence `68`: `P5_NPC_CALLBACK` — `p5:20261013:A:12:callback`
- minute `12`, sequence `69`: `P5_NPC_CALLBACK` — `p5:20261013:B:12:callback`
- minute `12`, sequence `70`: `P5_WORLD_SNAPSHOT` — `p5:20261013:12:snapshot`
- minute `13`, sequence `71`: `TIME_ADVANCED` — `p4:20261013:13:time`
- minute `13`, sequence `72`: `P5_DIRECTOR_DECISION` — `p5:20261013:13:director:v1`
- minute `13`, sequence `73`: `P5_NPC_CALLBACK` — `p5:20261013:A:13:callback`
- minute `13`, sequence `74`: `P5_NPC_CALLBACK` — `p5:20261013:B:13:callback`
- minute `13`, sequence `75`: `P5_WORLD_SNAPSHOT` — `p5:20261013:13:snapshot`
- minute `14`, sequence `76`: `TIME_ADVANCED` — `p4:20261013:14:time`
- minute `14`, sequence `77`: `P5_DIRECTOR_DECISION` — `p5:20261013:14:director:v1`
- minute `14`, sequence `78`: `P5_NPC_CALLBACK` — `p5:20261013:A:14:callback`
- minute `14`, sequence `79`: `P5_NPC_CALLBACK` — `p5:20261013:B:14:callback`
- minute `14`, sequence `80`: `P5_WORLD_SNAPSHOT` — `p5:20261013:14:snapshot`
- minute `15`, sequence `81`: `TIME_ADVANCED` — `p4:20261013:15:time`
- minute `15`, sequence `82`: `P5_DIRECTOR_DECISION` — `p5:20261013:15:director:v1`
- minute `15`, sequence `83`: `P5_STATION_SUPPLY_STORED` — `station-store:20261013163433-17a730:8806:8808:15:1`
- minute `15`, sequence `84`: `P5_NPC_CALLBACK` — `p5:20261013:A:15:callback`
- minute `15`, sequence `85`: `P5_NPC_CALLBACK` — `p5:20261013:B:15:callback`
- minute `15`, sequence `86`: `P5_WORLD_SNAPSHOT` — `p5:20261013:15:snapshot`
- minute `16`, sequence `87`: `TIME_ADVANCED` — `p4:20261013:16:time`
- minute `16`, sequence `88`: `P5_DIRECTOR_DECISION` — `p5:20261013:16:director:v1`
- minute `16`, sequence `89`: `P5_NPC_CALLBACK` — `p5:20261013:A:16:callback`
- minute `16`, sequence `90`: `P5_NPC_CALLBACK` — `p5:20261013:B:16:callback`
- minute `16`, sequence `91`: `P5_WORLD_SNAPSHOT` — `p5:20261013:16:snapshot`
- minute `17`, sequence `92`: `TIME_ADVANCED` — `p4:20261013:17:time`
- minute `17`, sequence `93`: `P5_DIRECTOR_DECISION` — `p5:20261013:17:director:v1`
- minute `17`, sequence `94`: `P5_NPC_CALLBACK` — `p5:20261013:A:17:callback`
- minute `17`, sequence `95`: `P5_NPC_CALLBACK` — `p5:20261013:B:17:callback`
- minute `17`, sequence `96`: `P5_WORLD_SNAPSHOT` — `p5:20261013:17:snapshot`
- minute `18`, sequence `97`: `TIME_ADVANCED` — `p4:20261013:18:time`
- minute `18`, sequence `98`: `P5_DIRECTOR_DECISION` — `p5:20261013:18:director:v1`
- minute `18`, sequence `99`: `P5_NPC_CALLBACK` — `p5:20261013:A:18:callback`
- minute `18`, sequence `100`: `P5_NPC_CALLBACK` — `p5:20261013:B:18:callback`
- minute `18`, sequence `101`: `P5_WORLD_SNAPSHOT` — `p5:20261013:18:snapshot`
- minute `19`, sequence `102`: `TIME_ADVANCED` — `p4:20261013:19:time`
- minute `19`, sequence `103`: `P5_DIRECTOR_DECISION` — `p5:20261013:19:director:v1`
- minute `19`, sequence `104`: `P5_NPC_CALLBACK` — `p5:20261013:A:19:callback`
- minute `19`, sequence `105`: `P5_NPC_CALLBACK` — `p5:20261013:B:19:callback`
- minute `19`, sequence `106`: `P5_WORLD_SNAPSHOT` — `p5:20261013:19:snapshot`
- minute `20`, sequence `107`: `TIME_ADVANCED` — `p4:20261013:20:time`
- minute `20`, sequence `108`: `P5_DIRECTOR_DECISION` — `p5:20261013:20:director:v1`
- minute `20`, sequence `109`: `P5_NPC_CALLBACK` — `p5:20261013:A:20:callback`
- minute `20`, sequence `110`: `P5_NPC_CALLBACK` — `p5:20261013:B:20:callback`
- minute `20`, sequence `111`: `P5_WORLD_SNAPSHOT` — `p5:20261013:20:snapshot`
- minute `21`, sequence `112`: `TIME_ADVANCED` — `p4:20261013:21:time`
- minute `21`, sequence `113`: `P5_DIRECTOR_DECISION` — `p5:20261013:21:director:v1`
- minute `21`, sequence `114`: `P5_NPC_CALLBACK` — `p5:20261013:A:21:callback`
- minute `21`, sequence `115`: `P5_NPC_CALLBACK` — `p5:20261013:B:21:callback`
- minute `21`, sequence `116`: `P5_WORLD_SNAPSHOT` — `p5:20261013:21:snapshot`
- minute `22`, sequence `117`: `TIME_ADVANCED` — `p4:20261013:22:time`
- minute `22`, sequence `118`: `P5_DIRECTOR_DECISION` — `p5:20261013:22:director:v1`
- minute `22`, sequence `119`: `P5_NPC_CALLBACK` — `p5:20261013:A:22:callback`
- minute `22`, sequence `120`: `P5_NPC_CALLBACK` — `p5:20261013:B:22:callback`
- minute `22`, sequence `121`: `P5_WORLD_SNAPSHOT` — `p5:20261013:22:snapshot`
- minute `23`, sequence `122`: `TIME_ADVANCED` — `p4:20261013:23:time`
- minute `23`, sequence `123`: `P5_DIRECTOR_DECISION` — `p5:20261013:23:director:v1`
- minute `23`, sequence `124`: `P5_NPC_CALLBACK` — `p5:20261013:A:23:callback`
- minute `23`, sequence `125`: `P5_NPC_CALLBACK` — `p5:20261013:B:23:callback`
- minute `23`, sequence `126`: `P5_WORLD_SNAPSHOT` — `p5:20261013:23:snapshot`
- minute `24`, sequence `127`: `TIME_ADVANCED` — `p4:20261013:24:time`
- minute `24`, sequence `128`: `P5_DIRECTOR_DECISION` — `p5:20261013:24:director:v1`
- minute `24`, sequence `129`: `P5_NPC_CALLBACK` — `p5:20261013:A:24:callback`
- minute `24`, sequence `130`: `P5_NPC_CALLBACK` — `p5:20261013:B:24:callback`
- minute `24`, sequence `131`: `P5_WORLD_SNAPSHOT` — `p5:20261013:24:snapshot`

## Outcome boundary

A proposal is not an accepted commitment; an accepted commitment is not a settled action. Only the native ledger, receipt, and independent database readback establish physical effects.
