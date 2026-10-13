# Ongoing Station — Native Run Replay

Scene: `20261013033010-0b39f5` · status: `COMPLETE` · sealed through: `{'events': 24, 'values': 24}`

This is a derived replay. Sealed ledger rows are ordered by their recorded minute and sequence (with source-array order as a tie-breaker). Decisions and receipts retain their order within each actor-local source stream. The evidence does not provide a precise cross-stream sequence, so the sections below are not a claim of total ordering.

## Minute 1

### Sealed ledger (recorded sequence)

- `P5_INTERVENTION` — event `p5:20261013:1:intervention:player_native_command`, sequence `2`; operation=`player_native_command`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:0:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:1:callback`
- NPC `B`: SELF goal `self-goal:7470:deliver_supply` / `ACCEPTED`; source=`actor_evidence[1].log[1]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:deliver_supply:7472:7466`; task_kind=`deliver_supply`; intent=`get`; callback_event=`p5:20261013:B:1:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:2`; commitment `self:7469:routine_route:0:7466`
- NPC `B`: `get` receipt `p3:7470:0:2`; commitment `self:7470:deliver_supply:7472:7466`

## Minute 2

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:0` / `DEFERRED`; source=`actor_evidence[0].log[4]`; no locally known route or required item is available; commitment_id=`self:7469:routine_route:0:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:2', None]`; callback_event=`p5:20261013:A:2:callback`
- NPC `B`: SELF goal `self-goal:7470:deliver_supply` / `CONTINUE`; source=`actor_evidence[1].log[4]`; retain existing actor commitment; commitment_id=`self:7470:deliver_supply:7472:7466`; task_kind=`deliver_supply`; intent=`move`; callback_event=`p5:20261013:B:2:callback`

### Settled native receipts (actor receipt-array order)

- NPC `B`: `move` receipt `p3:7470:0:5`; commitment `self:7470:deliver_supply:7472:7466`

## Minute 3

### Sealed ledger (recorded sequence)

- `p5_delivery_settled` — event `p5:delivery:20261013033010-0b39f5:B:p3:7470:0:8`, sequence `14`

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[6]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:0:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:3:callback`
- NPC `B`: SELF goal `self-goal:7470:deliver_supply` / `CONTINUE`; source=`actor_evidence[1].log[7]`; retain existing actor commitment; commitment_id=`self:7470:deliver_supply:7472:7466`; task_kind=`deliver_supply`; intent=`drop`; callback_event=`p5:20261013:B:3:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:7`; commitment `self:7469:routine_route:0:7465`
- NPC `B`: `drop` receipt `p3:7470:0:8`; commitment `self:7470:deliver_supply:7472:7466`

## Minute 4

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:0` / `CONTINUE`; source=`actor_evidence[0].log[9]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:0:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7469:0:7', None]`; intent=`move`; callback_event=`p5:20261013:A:4:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:0` / `ACCEPTED`; source=`actor_evidence[1].log[10]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:0:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:4:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:10`; commitment `self:7469:routine_route:0:7465`
- NPC `B`: `move` receipt `p3:7470:0:11`; commitment `self:7470:routine_route:0:7465`

## Minute 5

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:0` / `ACCEPTED`; source=`actor_evidence[0].log[12]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:0:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:2', None]`; intent=`move`; callback_event=`p5:20261013:A:5:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:0` / `CONTINUE`; source=`actor_evidence[1].log[13]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:0:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:11', None]`; intent=`move`; callback_event=`p5:20261013:B:5:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:13`; commitment `self:7469:routine_route:0:7466`
- NPC `B`: `move` receipt `p3:7470:0:14`; commitment `self:7470:routine_route:0:7465`

## Minute 6

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:2` / `ACCEPTED`; source=`actor_evidence[0].log[15]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:2:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:6:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:1` / `ACCEPTED`; source=`actor_evidence[1].log[16]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:1:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:6:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:16`; commitment `self:7469:routine_route:2:7466`
- NPC `B`: `move` receipt `p3:7470:0:17`; commitment `self:7470:routine_route:1:7465`

## Minute 7

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:2` / `CONTINUE`; source=`actor_evidence[0].log[18]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:2:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:16', None]`; intent=`move`; callback_event=`p5:20261013:A:7:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:1` / `CONTINUE`; source=`actor_evidence[1].log[19]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:1:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:17', None]`; intent=`move`; callback_event=`p5:20261013:B:7:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:19`; commitment `self:7469:routine_route:2:7466`
- NPC `B`: `move` receipt `p3:7470:0:20`; commitment `self:7470:routine_route:1:7465`

## Minute 8

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:3` / `ACCEPTED`; source=`actor_evidence[0].log[21]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:3:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:8:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:2` / `ACCEPTED`; source=`actor_evidence[1].log[22]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:2:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:8:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:22`; commitment `self:7469:routine_route:3:7466`
- NPC `B`: `move` receipt `p3:7470:0:23`; commitment `self:7470:routine_route:2:7465`

## Minute 9

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:3` / `CONTINUE`; source=`actor_evidence[0].log[24]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:3:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:22', None]`; intent=`move`; callback_event=`p5:20261013:A:9:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:2` / `CONTINUE`; source=`actor_evidence[1].log[25]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:2:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:23', None]`; intent=`move`; callback_event=`p5:20261013:B:9:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:25`; commitment `self:7469:routine_route:3:7466`
- NPC `B`: `move` receipt `p3:7470:0:26`; commitment `self:7470:routine_route:2:7465`

## Minute 10

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:4` / `ACCEPTED`; source=`actor_evidence[0].log[27]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:4:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:10:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:3` / `ACCEPTED`; source=`actor_evidence[1].log[28]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:3:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:10:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:28`; commitment `self:7469:routine_route:4:7466`
- NPC `B`: `move` receipt `p3:7470:0:29`; commitment `self:7470:routine_route:3:7465`

## Minute 11

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:4` / `CONTINUE`; source=`actor_evidence[0].log[30]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:4:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:28', None]`; intent=`move`; callback_event=`p5:20261013:A:11:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:3` / `CONTINUE`; source=`actor_evidence[1].log[31]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:3:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:29', None]`; intent=`move`; callback_event=`p5:20261013:B:11:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:31`; commitment `self:7469:routine_route:4:7466`
- NPC `B`: `move` receipt `p3:7470:0:32`; commitment `self:7470:routine_route:3:7465`

## Minute 12

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:5` / `ACCEPTED`; source=`actor_evidence[0].log[33]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:5:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:12:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:4` / `ACCEPTED`; source=`actor_evidence[1].log[34]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:4:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:12:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:34`; commitment `self:7469:routine_route:5:7466`
- NPC `B`: `move` receipt `p3:7470:0:35`; commitment `self:7470:routine_route:4:7465`

## Minute 13

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:5` / `CONTINUE`; source=`actor_evidence[0].log[36]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:5:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:34', None]`; intent=`move`; callback_event=`p5:20261013:A:13:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:4` / `CONTINUE`; source=`actor_evidence[1].log[37]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:4:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:35', None]`; intent=`move`; callback_event=`p5:20261013:B:13:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:37`; commitment `self:7469:routine_route:5:7466`
- NPC `B`: `move` receipt `p3:7470:0:38`; commitment `self:7470:routine_route:4:7465`

## Minute 14

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:6` / `ACCEPTED`; source=`actor_evidence[0].log[39]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:6:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:14:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:5` / `ACCEPTED`; source=`actor_evidence[1].log[40]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:5:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:14:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:40`; commitment `self:7469:routine_route:6:7466`
- NPC `B`: `move` receipt `p3:7470:0:41`; commitment `self:7470:routine_route:5:7465`

## Minute 15

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:6` / `CONTINUE`; source=`actor_evidence[0].log[42]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:6:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:40', None]`; intent=`move`; callback_event=`p5:20261013:A:15:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:5` / `CONTINUE`; source=`actor_evidence[1].log[43]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:5:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:41', None]`; intent=`move`; callback_event=`p5:20261013:B:15:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:43`; commitment `self:7469:routine_route:6:7466`
- NPC `B`: `move` receipt `p3:7470:0:44`; commitment `self:7470:routine_route:5:7465`

## Minute 16

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:7` / `ACCEPTED`; source=`actor_evidence[0].log[45]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:7:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:16:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:6` / `ACCEPTED`; source=`actor_evidence[1].log[46]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:6:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:16:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:46`; commitment `self:7469:routine_route:7:7466`
- NPC `B`: `move` receipt `p3:7470:0:47`; commitment `self:7470:routine_route:6:7465`

## Minute 17

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:7` / `CONTINUE`; source=`actor_evidence[0].log[48]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:7:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:46', None]`; intent=`move`; callback_event=`p5:20261013:A:17:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:6` / `CONTINUE`; source=`actor_evidence[1].log[49]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:6:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:47', None]`; intent=`move`; callback_event=`p5:20261013:B:17:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:49`; commitment `self:7469:routine_route:7:7466`
- NPC `B`: `move` receipt `p3:7470:0:50`; commitment `self:7470:routine_route:6:7465`

## Minute 18

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:8` / `ACCEPTED`; source=`actor_evidence[0].log[51]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:8:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:18:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:7` / `ACCEPTED`; source=`actor_evidence[1].log[52]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:7:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:18:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:52`; commitment `self:7469:routine_route:8:7466`
- NPC `B`: `move` receipt `p3:7470:0:53`; commitment `self:7470:routine_route:7:7465`

## Minute 19

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:8` / `CONTINUE`; source=`actor_evidence[0].log[54]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:8:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:52', None]`; intent=`move`; callback_event=`p5:20261013:A:19:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:7` / `CONTINUE`; source=`actor_evidence[1].log[55]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:7:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:53', None]`; intent=`move`; callback_event=`p5:20261013:B:19:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:55`; commitment `self:7469:routine_route:8:7466`
- NPC `B`: `move` receipt `p3:7470:0:56`; commitment `self:7470:routine_route:7:7465`

## Minute 20

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:9` / `ACCEPTED`; source=`actor_evidence[0].log[57]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:9:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:20:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:8` / `ACCEPTED`; source=`actor_evidence[1].log[58]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:8:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:20:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:58`; commitment `self:7469:routine_route:9:7466`
- NPC `B`: `move` receipt `p3:7470:0:59`; commitment `self:7470:routine_route:8:7465`

## Minute 21

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:9` / `CONTINUE`; source=`actor_evidence[0].log[60]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:9:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:58', None]`; intent=`move`; callback_event=`p5:20261013:A:21:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:8` / `CONTINUE`; source=`actor_evidence[1].log[61]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:8:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:59', None]`; intent=`move`; callback_event=`p5:20261013:B:21:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:61`; commitment `self:7469:routine_route:9:7466`
- NPC `B`: `move` receipt `p3:7470:0:62`; commitment `self:7470:routine_route:8:7465`

## Minute 22

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:10` / `ACCEPTED`; source=`actor_evidence[0].log[63]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:10:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:22:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:9` / `ACCEPTED`; source=`actor_evidence[1].log[64]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:9:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:22:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:64`; commitment `self:7469:routine_route:10:7466`
- NPC `B`: `move` receipt `p3:7470:0:65`; commitment `self:7470:routine_route:9:7465`

## Minute 23

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:10` / `CONTINUE`; source=`actor_evidence[0].log[66]`; retain existing actor commitment; commitment_id=`self:7469:routine_route:10:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`['p3:7469:0:64', None]`; intent=`move`; callback_event=`p5:20261013:A:23:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:9` / `CONTINUE`; source=`actor_evidence[1].log[67]`; retain existing actor commitment; commitment_id=`self:7470:routine_route:9:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`['p3:7470:0:65', None]`; intent=`move`; callback_event=`p5:20261013:B:23:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:67`; commitment `self:7469:routine_route:10:7466`
- NPC `B`: `move` receipt `p3:7470:0:68`; commitment `self:7470:routine_route:9:7465`

## Minute 24

### Actor-local decisions (source-log order)

- NPC `A`: SELF goal `self-goal:7469:routine_route:11` / `ACCEPTED`; source=`actor_evidence[0].log[69]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7469:routine_route:11:7466`; task_kind=`routine_route`; route_waypoints=`[7466, 7465]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:A:24:callback`
- NPC `B`: SELF goal `self-goal:7470:routine_route:10` / `ACCEPTED`; source=`actor_evidence[1].log[70]`; feasible offer selected by deadline then stable source/id ordering; commitment_id=`self:7470:routine_route:10:7465`; task_kind=`routine_route`; route_waypoints=`[7465, 7466]`; waypoint_receipts=`[None, None]`; intent=`move`; callback_event=`p5:20261013:B:24:callback`

### Settled native receipts (actor receipt-array order)

- NPC `A`: `move` receipt `p3:7469:0:70`; commitment `self:7469:routine_route:11:7466`
- NPC `B`: `move` receipt `p3:7470:0:71`; commitment `self:7470:routine_route:10:7465`

## Complete sealed-ledger index

The following appendix preserves every ledger source ID in its recorded sequence; routine ticks/callbacks are omitted from the story body only.

- minute `1`, sequence `1`: `TIME_ADVANCED` — `p4:20261013:1:time`
- minute `1`, sequence `2`: `P5_INTERVENTION` — `p5:20261013:1:intervention:player_native_command`
- minute `1`, sequence `3`: `P5_DIRECTOR_DECISION` — `p5:20261013:1:director:v1`
- minute `1`, sequence `4`: `P5_NPC_CALLBACK` — `p5:20261013:A:1:callback`
- minute `1`, sequence `5`: `P5_NPC_CALLBACK` — `p5:20261013:B:1:callback`
- minute `1`, sequence `6`: `P5_WORLD_SNAPSHOT` — `p5:20261013:1:snapshot`
- minute `2`, sequence `7`: `TIME_ADVANCED` — `p4:20261013:2:time`
- minute `2`, sequence `8`: `P5_DIRECTOR_DECISION` — `p5:20261013:2:director:v1`
- minute `2`, sequence `9`: `P5_NPC_CALLBACK` — `p5:20261013:A:2:callback`
- minute `2`, sequence `10`: `P5_NPC_CALLBACK` — `p5:20261013:B:2:callback`
- minute `2`, sequence `11`: `P5_WORLD_SNAPSHOT` — `p5:20261013:2:snapshot`
- minute `3`, sequence `12`: `TIME_ADVANCED` — `p4:20261013:3:time`
- minute `3`, sequence `13`: `P5_DIRECTOR_DECISION` — `p5:20261013:3:director:v1`
- minute `3`, sequence `14`: `p5_delivery_settled` — `p5:delivery:20261013033010-0b39f5:B:p3:7470:0:8`
- minute `3`, sequence `15`: `P5_NPC_CALLBACK` — `p5:20261013:A:3:callback`
- minute `3`, sequence `16`: `P5_NPC_CALLBACK` — `p5:20261013:B:3:callback`
- minute `3`, sequence `17`: `P5_WORLD_SNAPSHOT` — `p5:20261013:3:snapshot`
- minute `4`, sequence `18`: `TIME_ADVANCED` — `p4:20261013:4:time`
- minute `4`, sequence `19`: `P5_DIRECTOR_DECISION` — `p5:20261013:4:director:v1`
- minute `4`, sequence `20`: `P5_NPC_CALLBACK` — `p5:20261013:A:4:callback`
- minute `4`, sequence `21`: `P5_NPC_CALLBACK` — `p5:20261013:B:4:callback`
- minute `4`, sequence `22`: `P5_WORLD_SNAPSHOT` — `p5:20261013:4:snapshot`
- minute `5`, sequence `23`: `TIME_ADVANCED` — `p4:20261013:5:time`
- minute `5`, sequence `24`: `P5_DIRECTOR_DECISION` — `p5:20261013:5:director:v1`
- minute `5`, sequence `25`: `P5_NPC_CALLBACK` — `p5:20261013:A:5:callback`
- minute `5`, sequence `26`: `P5_NPC_CALLBACK` — `p5:20261013:B:5:callback`
- minute `5`, sequence `27`: `P5_WORLD_SNAPSHOT` — `p5:20261013:5:snapshot`
- minute `6`, sequence `28`: `TIME_ADVANCED` — `p4:20261013:6:time`
- minute `6`, sequence `29`: `P5_DIRECTOR_DECISION` — `p5:20261013:6:director:v1`
- minute `6`, sequence `30`: `P5_NPC_CALLBACK` — `p5:20261013:A:6:callback`
- minute `6`, sequence `31`: `P5_NPC_CALLBACK` — `p5:20261013:B:6:callback`
- minute `6`, sequence `32`: `P5_WORLD_SNAPSHOT` — `p5:20261013:6:snapshot`
- minute `7`, sequence `33`: `TIME_ADVANCED` — `p4:20261013:7:time`
- minute `7`, sequence `34`: `P5_DIRECTOR_DECISION` — `p5:20261013:7:director:v1`
- minute `7`, sequence `35`: `P5_NPC_CALLBACK` — `p5:20261013:A:7:callback`
- minute `7`, sequence `36`: `P5_NPC_CALLBACK` — `p5:20261013:B:7:callback`
- minute `7`, sequence `37`: `P5_WORLD_SNAPSHOT` — `p5:20261013:7:snapshot`
- minute `8`, sequence `38`: `TIME_ADVANCED` — `p4:20261013:8:time`
- minute `8`, sequence `39`: `P5_DIRECTOR_DECISION` — `p5:20261013:8:director:v1`
- minute `8`, sequence `40`: `P5_NPC_CALLBACK` — `p5:20261013:A:8:callback`
- minute `8`, sequence `41`: `P5_NPC_CALLBACK` — `p5:20261013:B:8:callback`
- minute `8`, sequence `42`: `P5_WORLD_SNAPSHOT` — `p5:20261013:8:snapshot`
- minute `9`, sequence `43`: `TIME_ADVANCED` — `p4:20261013:9:time`
- minute `9`, sequence `44`: `P5_DIRECTOR_DECISION` — `p5:20261013:9:director:v1`
- minute `9`, sequence `45`: `P5_NPC_CALLBACK` — `p5:20261013:A:9:callback`
- minute `9`, sequence `46`: `P5_NPC_CALLBACK` — `p5:20261013:B:9:callback`
- minute `9`, sequence `47`: `P5_WORLD_SNAPSHOT` — `p5:20261013:9:snapshot`
- minute `10`, sequence `48`: `TIME_ADVANCED` — `p4:20261013:10:time`
- minute `10`, sequence `49`: `P5_DIRECTOR_DECISION` — `p5:20261013:10:director:v1`
- minute `10`, sequence `50`: `P5_NPC_CALLBACK` — `p5:20261013:A:10:callback`
- minute `10`, sequence `51`: `P5_NPC_CALLBACK` — `p5:20261013:B:10:callback`
- minute `10`, sequence `52`: `P5_WORLD_SNAPSHOT` — `p5:20261013:10:snapshot`
- minute `11`, sequence `53`: `TIME_ADVANCED` — `p4:20261013:11:time`
- minute `11`, sequence `54`: `P5_DIRECTOR_DECISION` — `p5:20261013:11:director:v1`
- minute `11`, sequence `55`: `P5_NPC_CALLBACK` — `p5:20261013:A:11:callback`
- minute `11`, sequence `56`: `P5_NPC_CALLBACK` — `p5:20261013:B:11:callback`
- minute `11`, sequence `57`: `P5_WORLD_SNAPSHOT` — `p5:20261013:11:snapshot`
- minute `12`, sequence `58`: `TIME_ADVANCED` — `p4:20261013:12:time`
- minute `12`, sequence `59`: `P5_DIRECTOR_DECISION` — `p5:20261013:12:director:v1`
- minute `12`, sequence `60`: `P5_NPC_CALLBACK` — `p5:20261013:A:12:callback`
- minute `12`, sequence `61`: `P5_NPC_CALLBACK` — `p5:20261013:B:12:callback`
- minute `12`, sequence `62`: `P5_WORLD_SNAPSHOT` — `p5:20261013:12:snapshot`
- minute `13`, sequence `63`: `TIME_ADVANCED` — `p4:20261013:13:time`
- minute `13`, sequence `64`: `P5_DIRECTOR_DECISION` — `p5:20261013:13:director:v1`
- minute `13`, sequence `65`: `P5_NPC_CALLBACK` — `p5:20261013:A:13:callback`
- minute `13`, sequence `66`: `P5_NPC_CALLBACK` — `p5:20261013:B:13:callback`
- minute `13`, sequence `67`: `P5_WORLD_SNAPSHOT` — `p5:20261013:13:snapshot`
- minute `14`, sequence `68`: `TIME_ADVANCED` — `p4:20261013:14:time`
- minute `14`, sequence `69`: `P5_DIRECTOR_DECISION` — `p5:20261013:14:director:v1`
- minute `14`, sequence `70`: `P5_NPC_CALLBACK` — `p5:20261013:A:14:callback`
- minute `14`, sequence `71`: `P5_NPC_CALLBACK` — `p5:20261013:B:14:callback`
- minute `14`, sequence `72`: `P5_WORLD_SNAPSHOT` — `p5:20261013:14:snapshot`
- minute `15`, sequence `73`: `TIME_ADVANCED` — `p4:20261013:15:time`
- minute `15`, sequence `74`: `P5_DIRECTOR_DECISION` — `p5:20261013:15:director:v1`
- minute `15`, sequence `75`: `P5_NPC_CALLBACK` — `p5:20261013:A:15:callback`
- minute `15`, sequence `76`: `P5_NPC_CALLBACK` — `p5:20261013:B:15:callback`
- minute `15`, sequence `77`: `P5_WORLD_SNAPSHOT` — `p5:20261013:15:snapshot`
- minute `16`, sequence `78`: `TIME_ADVANCED` — `p4:20261013:16:time`
- minute `16`, sequence `79`: `P5_DIRECTOR_DECISION` — `p5:20261013:16:director:v1`
- minute `16`, sequence `80`: `P5_NPC_CALLBACK` — `p5:20261013:A:16:callback`
- minute `16`, sequence `81`: `P5_NPC_CALLBACK` — `p5:20261013:B:16:callback`
- minute `16`, sequence `82`: `P5_WORLD_SNAPSHOT` — `p5:20261013:16:snapshot`
- minute `17`, sequence `83`: `TIME_ADVANCED` — `p4:20261013:17:time`
- minute `17`, sequence `84`: `P5_DIRECTOR_DECISION` — `p5:20261013:17:director:v1`
- minute `17`, sequence `85`: `P5_NPC_CALLBACK` — `p5:20261013:A:17:callback`
- minute `17`, sequence `86`: `P5_NPC_CALLBACK` — `p5:20261013:B:17:callback`
- minute `17`, sequence `87`: `P5_WORLD_SNAPSHOT` — `p5:20261013:17:snapshot`
- minute `18`, sequence `88`: `TIME_ADVANCED` — `p4:20261013:18:time`
- minute `18`, sequence `89`: `P5_DIRECTOR_DECISION` — `p5:20261013:18:director:v1`
- minute `18`, sequence `90`: `P5_NPC_CALLBACK` — `p5:20261013:A:18:callback`
- minute `18`, sequence `91`: `P5_NPC_CALLBACK` — `p5:20261013:B:18:callback`
- minute `18`, sequence `92`: `P5_WORLD_SNAPSHOT` — `p5:20261013:18:snapshot`
- minute `19`, sequence `93`: `TIME_ADVANCED` — `p4:20261013:19:time`
- minute `19`, sequence `94`: `P5_DIRECTOR_DECISION` — `p5:20261013:19:director:v1`
- minute `19`, sequence `95`: `P5_NPC_CALLBACK` — `p5:20261013:A:19:callback`
- minute `19`, sequence `96`: `P5_NPC_CALLBACK` — `p5:20261013:B:19:callback`
- minute `19`, sequence `97`: `P5_WORLD_SNAPSHOT` — `p5:20261013:19:snapshot`
- minute `20`, sequence `98`: `TIME_ADVANCED` — `p4:20261013:20:time`
- minute `20`, sequence `99`: `P5_DIRECTOR_DECISION` — `p5:20261013:20:director:v1`
- minute `20`, sequence `100`: `P5_NPC_CALLBACK` — `p5:20261013:A:20:callback`
- minute `20`, sequence `101`: `P5_NPC_CALLBACK` — `p5:20261013:B:20:callback`
- minute `20`, sequence `102`: `P5_WORLD_SNAPSHOT` — `p5:20261013:20:snapshot`
- minute `21`, sequence `103`: `TIME_ADVANCED` — `p4:20261013:21:time`
- minute `21`, sequence `104`: `P5_DIRECTOR_DECISION` — `p5:20261013:21:director:v1`
- minute `21`, sequence `105`: `P5_NPC_CALLBACK` — `p5:20261013:A:21:callback`
- minute `21`, sequence `106`: `P5_NPC_CALLBACK` — `p5:20261013:B:21:callback`
- minute `21`, sequence `107`: `P5_WORLD_SNAPSHOT` — `p5:20261013:21:snapshot`
- minute `22`, sequence `108`: `TIME_ADVANCED` — `p4:20261013:22:time`
- minute `22`, sequence `109`: `P5_DIRECTOR_DECISION` — `p5:20261013:22:director:v1`
- minute `22`, sequence `110`: `P5_NPC_CALLBACK` — `p5:20261013:A:22:callback`
- minute `22`, sequence `111`: `P5_NPC_CALLBACK` — `p5:20261013:B:22:callback`
- minute `22`, sequence `112`: `P5_WORLD_SNAPSHOT` — `p5:20261013:22:snapshot`
- minute `23`, sequence `113`: `TIME_ADVANCED` — `p4:20261013:23:time`
- minute `23`, sequence `114`: `P5_DIRECTOR_DECISION` — `p5:20261013:23:director:v1`
- minute `23`, sequence `115`: `P5_NPC_CALLBACK` — `p5:20261013:A:23:callback`
- minute `23`, sequence `116`: `P5_NPC_CALLBACK` — `p5:20261013:B:23:callback`
- minute `23`, sequence `117`: `P5_WORLD_SNAPSHOT` — `p5:20261013:23:snapshot`
- minute `24`, sequence `118`: `TIME_ADVANCED` — `p4:20261013:24:time`
- minute `24`, sequence `119`: `P5_DIRECTOR_DECISION` — `p5:20261013:24:director:v1`
- minute `24`, sequence `120`: `P5_NPC_CALLBACK` — `p5:20261013:A:24:callback`
- minute `24`, sequence `121`: `P5_NPC_CALLBACK` — `p5:20261013:B:24:callback`
- minute `24`, sequence `122`: `P5_WORLD_SNAPSHOT` — `p5:20261013:24:snapshot`

## Outcome boundary

A proposal is not an accepted commitment; an accepted commitment is not a settled action. Only the native ledger, receipt, and independent database readback establish physical effects.
