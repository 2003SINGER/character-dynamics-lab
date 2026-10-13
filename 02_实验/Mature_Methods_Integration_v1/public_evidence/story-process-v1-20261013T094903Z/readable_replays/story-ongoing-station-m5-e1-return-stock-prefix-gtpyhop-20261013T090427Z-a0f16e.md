> Failure evidence only: the scene sealed through minute 9, then post-seal publication raised TypeError; no later minutes were run. The replay is truncated at this preserved failure frontier.
> This is a derived rendering; the original trace and replay are unchanged.

# Ongoing Station — Native Run Replay

Scene: `20261013090427-19e3d7` · status: `INCOMPLETE` · sealed through: `{'events': 9, 'values': 9}`

This is a derived replay. Sealed ledger rows are ordered by their recorded minute and sequence (with source-array order as a tie-breaker). Decisions and receipts retain their order within each actor-local source stream. The evidence does not provide a precise cross-stream sequence, so the sections below are not a claim of total ordering.

## Minute 1

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:deliver_supply` / `ACCEPTED`; source=`actor_evidence[0].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7907:deliver_supply:7909:7904`; task_kind=`deliver_supply`; intent=`get`; callback_event=`p5:20261013:A:1:callback`
- NPC `B`: SELF goal `self-goal:7908:deliver_supply` / `ACCEPTED`; source=`actor_evidence[1].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7908:deliver_supply:7910:7904`; task_kind=`deliver_supply`; intent=`get`; callback_event=`p5:20261013:B:1:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `get` receipt `p3:7907:0:2`; commitment `self:7907:deliver_supply:7909:7904`
- NPC `B`: `get` receipt `p3:7908:0:2`; commitment `self:7908:deliver_supply:7910:7904`

## Minute 2

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:deliver_supply` / `CONTINUE`; source=`actor_evidence[0].log[4]`; retain existing actor commitment; commitment_id=`self:7907:deliver_supply:7909:7904`; task_kind=`deliver_supply`; intent=`move`; callback_event=`p5:20261013:A:2:callback`
- NPC `B`: SELF goal `self-goal:7908:deliver_supply` / `CONTINUE`; source=`actor_evidence[1].log[4]`; retain existing actor commitment; commitment_id=`self:7908:deliver_supply:7910:7904`; task_kind=`deliver_supply`; intent=`move`; callback_event=`p5:20261013:B:2:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7907:0:5`; commitment `self:7907:deliver_supply:7909:7904`
- NPC `B`: `move` receipt `p3:7908:0:5`; commitment `self:7908:deliver_supply:7910:7904`

## Minute 3

### Sealed ledger (recorded sequence)

- `p5_delivery_settled` — event `p5:delivery:20261013090427-19e3d7:A:p3:7907:0:8`, sequence `13`
- `p5_delivery_settled` — event `p5:delivery:20261013090427-19e3d7:B:p3:7908:0:8`, sequence `14`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:deliver_supply` / `CONTINUE`; source=`actor_evidence[0].log[7]`; retain existing actor commitment; commitment_id=`self:7907:deliver_supply:7909:7904`; task_kind=`deliver_supply`; intent=`drop`; callback_event=`p5:20261013:A:3:callback`
- NPC `B`: SELF goal `self-goal:7908:deliver_supply` / `CONTINUE`; source=`actor_evidence[1].log[7]`; retain existing actor commitment; commitment_id=`self:7908:deliver_supply:7910:7904`; task_kind=`deliver_supply`; intent=`drop`; callback_event=`p5:20261013:B:3:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `drop` receipt `p3:7907:0:8`; commitment `self:7907:deliver_supply:7909:7904`
- NPC `B`: `drop` receipt `p3:7908:0:8`; commitment `self:7908:deliver_supply:7910:7904`

## Minute 4

### Sealed ledger (recorded sequence)

- `SOCIAL_REQUEST` — event `p4:20261013:hero:note-source:episode1`, sequence `20`
- `SOCIAL_RESPONSE` — event `p4:20261013:love:note-response:episode1`, sequence `21`
- `SOCIAL_COMMIT` — event `p4:20261013:love:note-response:episode1:commit`, sequence `22`

## Minute 5

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:return_stock:p3:7907:0:8` / `ACCEPTED`; source=`actor_evidence[0].log[12]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7907:return_stock:7909:p3:7907:0:8`; task_kind=`return_stock`; intent=`get`; callback_event=`p5:20261013:A:5:callback`
- NPC `B`: SELF goal `self-goal:7908:return_stock:p3:7908:0:8` / `ACCEPTED`; source=`actor_evidence[1].log[12]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7908:return_stock:7910:p3:7908:0:8`; task_kind=`return_stock`; intent=`get`; callback_event=`p5:20261013:B:5:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `get` receipt `p3:7907:0:13`; commitment `self:7907:return_stock:7909:p3:7907:0:8`
- NPC `B`: `get` receipt `p3:7908:0:13`; commitment `self:7908:return_stock:7910:p3:7908:0:8`

## Minute 6

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:return_stock:p3:7907:0:8` / `CONTINUE`; source=`actor_evidence[0].log[15]`; retain existing actor commitment; commitment_id=`self:7907:return_stock:7909:p3:7907:0:8`; task_kind=`return_stock`; intent=`move`; callback_event=`p5:20261013:A:6:callback`
- NPC `B`: SELF goal `self-goal:7908:return_stock:p3:7908:0:8` / `CONTINUE`; source=`actor_evidence[1].log[15]`; retain existing actor commitment; commitment_id=`self:7908:return_stock:7910:p3:7908:0:8`; task_kind=`return_stock`; intent=`move`; callback_event=`p5:20261013:B:6:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7907:0:16`; commitment `self:7907:return_stock:7909:p3:7907:0:8`
- NPC `B`: `move` receipt `p3:7908:0:16`; commitment `self:7908:return_stock:7910:p3:7908:0:8`

## Minute 7

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:return_stock:p3:7907:0:8` / `CONTINUE`; source=`actor_evidence[0].log[18]`; retain existing actor commitment; commitment_id=`self:7907:return_stock:7909:p3:7907:0:8`; task_kind=`return_stock`; intent=`drop`; callback_event=`p5:20261013:A:7:callback`
- NPC `B`: SELF goal `self-goal:7908:return_stock:p3:7908:0:8` / `CONTINUE`; source=`actor_evidence[1].log[18]`; retain existing actor commitment; commitment_id=`self:7908:return_stock:7910:p3:7908:0:8`; task_kind=`return_stock`; intent=`drop`; callback_event=`p5:20261013:B:7:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `drop` receipt `p3:7907:0:19`; commitment `self:7907:return_stock:7909:p3:7907:0:8`
- NPC `B`: `drop` receipt `p3:7908:0:19`; commitment `self:7908:return_stock:7910:p3:7908:0:8`

## Minute 8

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[21]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7907:routine_route:0:7904`; task_kind=`routine_route`; route_waypoints=`[7904, 7903]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:8:callback`
- NPC `B`: SELF goal `self-goal:7908:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[21]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7908:routine_route:0:7904`; task_kind=`routine_route`; route_waypoints=`[7904, 7903]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:8:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7907:0:22`; commitment `self:7907:routine_route:0:7904`
- NPC `B`: `move` receipt `p3:7908:0:22`; commitment `self:7908:routine_route:0:7904`

## Minute 9

### Sealed ledger (recorded sequence)

- `P5_ONGOING_STATION_ACTIVATION` — event `station:20261013090427-19e3d7:9:activate:1`, sequence `47`
- `P5_INTERVENTION` — event `p5:20261013:9:intervention:ongoing_station_author_activation`, sequence `48`; operation=`ongoing_station_author_activation`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7907:routine_route:0` / `CONTINUE`; source=`actor_evidence[0].log[24]`; retain existing actor commitment; commitment_id=`self:7907:routine_route:0:7904`; task_kind=`routine_route`; route_waypoints=`[7904, 7903]`; waypoint_receipts=`['p3:7907:0:22', None]`; intent=`move`; callback_event=`p5:20261013:A:9:callback`
- NPC `B`: SELF goal `self-goal:7908:routine_route:0` / `CONTINUE`; source=`actor_evidence[1].log[24]`; retain existing actor commitment; commitment_id=`self:7908:routine_route:0:7904`; task_kind=`routine_route`; route_waypoints=`[7904, 7903]`; waypoint_receipts=`['p3:7908:0:22', None]`; intent=`move`; callback_event=`p5:20261013:B:9:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7907:0:25`; commitment `self:7907:routine_route:0:7904`
- NPC `B`: `move` receipt `p3:7908:0:25`; commitment `self:7908:routine_route:0:7904`

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
- minute `3`, sequence `13`: `p5_delivery_settled` — `p5:delivery:20261013090427-19e3d7:A:p3:7907:0:8`
- minute `3`, sequence `14`: `p5_delivery_settled` — `p5:delivery:20261013090427-19e3d7:B:p3:7908:0:8`
- minute `3`, sequence `15`: `P5_NPC_CALLBACK` — `p5:20261013:A:3:callback`
- minute `3`, sequence `16`: `P5_NPC_CALLBACK` — `p5:20261013:B:3:callback`
- minute `3`, sequence `17`: `P5_WORLD_SNAPSHOT` — `p5:20261013:3:snapshot`
- minute `4`, sequence `18`: `TIME_ADVANCED` — `p4:20261013:4:time`
- minute `4`, sequence `19`: `P5_DIRECTOR_DECISION` — `p5:20261013:4:director:v1`
- minute `4`, sequence `20`: `SOCIAL_REQUEST` — `p4:20261013:hero:note-source:episode1`
- minute `4`, sequence `21`: `SOCIAL_RESPONSE` — `p4:20261013:love:note-response:episode1`
- minute `4`, sequence `22`: `SOCIAL_COMMIT` — `p4:20261013:love:note-response:episode1:commit`
- minute `4`, sequence `23`: `P5_NPC_CALLBACK` — `p5:20261013:A:4:callback`
- minute `4`, sequence `24`: `P5_NPC_CALLBACK` — `p5:20261013:B:4:callback`
- minute `4`, sequence `25`: `P5_WORLD_SNAPSHOT` — `p5:20261013:4:snapshot`
- minute `5`, sequence `26`: `TIME_ADVANCED` — `p4:20261013:5:time`
- minute `5`, sequence `27`: `P5_DIRECTOR_DECISION` — `p5:20261013:5:director:v1`
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
- minute `9`, sequence `47`: `P5_ONGOING_STATION_ACTIVATION` — `station:20261013090427-19e3d7:9:activate:1`
- minute `9`, sequence `48`: `P5_INTERVENTION` — `p5:20261013:9:intervention:ongoing_station_author_activation`
- minute `9`, sequence `49`: `P5_DIRECTOR_DECISION` — `p5:20261013:9:director:v1`
- minute `9`, sequence `50`: `P5_NPC_CALLBACK` — `p5:20261013:A:9:callback`
- minute `9`, sequence `51`: `P5_NPC_CALLBACK` — `p5:20261013:B:9:callback`
- minute `9`, sequence `52`: `P5_WORLD_SNAPSHOT` — `p5:20261013:9:snapshot`

## Outcome boundary

A proposal is not an accepted commitment; an accepted commitment is not a settled action. Only the native ledger, receipt, and independent database readback establish physical effects.
