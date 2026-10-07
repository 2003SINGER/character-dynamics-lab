# AGAIN dynamics audit v0

Status: **development-only / complete**

No `alpha`, `beta`, `b`, or `W` was trained. Source arousal remains an annotation-derived proxy; no Theory-S claim is made.

## Summary

### participant_held_out
- folds: 18; held-out trajectories: 20
- no-state MAE median/IQR: 14.228477241029543 / [4.786236886325446, 53.54277002527195]
- no-state RMSE median/IQR: 26.06865516752518 / [6.638482335412668, 65.52831971630172]
- AR(1) phi=0.0 MAE median/IQR: 14.228477241029543 / [4.786236886325446, 53.54277002527195]
- AR(1) phi=0.5 MAE median/IQR: 2.65770936205696 / [0.9836108741976346, 9.706515228958018]
- AR(1) phi=0.8 MAE median/IQR: 1.286192898060564 / [0.4130239367554312, 3.9501178545256224]
- AR(1) phi=0.95 MAE median/IQR: 0.6956063318951528 / [0.19950607206518695, 1.7545319982556369]

### game_held_out
- folds: 9; held-out trajectories: 20
- no-state MAE median/IQR: 14.228477241029543 / [5.206713758431971, 53.54277002527195]
- no-state RMSE median/IQR: 26.06865516752518 / [6.681250411998294, 65.52831971630172]
- AR(1) phi=0.0 MAE median/IQR: 14.228477241029543 / [5.206713758431971, 53.54277002527195]
- AR(1) phi=0.5 MAE median/IQR: 2.65770936205696 / [0.9867829655690669, 9.706515228958018]
- AR(1) phi=0.8 MAE median/IQR: 1.286192898060564 / [0.4130239367554312, 3.9501178545256224]
- AR(1) phi=0.95 MAE median/IQR: 0.6956063318951528 / [0.19950607206518695, 1.7545319982556369]

## Frozen envelope

Channels were audited separately using the pre-registered binary-onset rule; tau grid was 0.5, 1.0, 2.0, 5.0 seconds. Event lag/decay/recovery are descriptive and retain undefined/censored cases.

### Event support (participant_held_out)
- player_respawn: event-bearing trajectories 4/20; event-bearing folds 4/18
- player_death: event-bearing trajectories 6/20; event-bearing folds 6/18
- player_damaged: event-bearing trajectories 13/20; event-bearing folds 12/18
- player_healing: event-bearing trajectories 4/20; event-bearing folds 4/18
- player_shooting: event-bearing trajectories 11/20; event-bearing folds 10/18
- player_reloading: event-bearing trajectories 4/20; event-bearing folds 4/18
- player_is_crashing: event-bearing trajectories 7/20; event-bearing folds 7/18
- player_is_looping: event-bearing trajectories 2/20; event-bearing folds 2/18
- player_is_falling: event-bearing trajectories 7/20; event-bearing folds 7/18
- player_is_jumping: event-bearing trajectories 4/20; event-bearing folds 4/18
- player_has_collisions: event-bearing trajectories 7/20; event-bearing folds 7/18
- player_point_pickup: event-bearing trajectories 5/20; event-bearing folds 5/18
- player_power_pickup: event-bearing trajectories 2/20; event-bearing folds 2/18
- player_boost_pickup: event-bearing trajectories 3/20; event-bearing folds 3/18

### Event support (game_held_out)
- player_respawn: event-bearing trajectories 4/20; event-bearing folds 2/9
- player_death: event-bearing trajectories 6/20; event-bearing folds 3/9
- player_damaged: event-bearing trajectories 13/20; event-bearing folds 6/9
- player_healing: event-bearing trajectories 4/20; event-bearing folds 2/9
- player_shooting: event-bearing trajectories 11/20; event-bearing folds 5/9
- player_reloading: event-bearing trajectories 4/20; event-bearing folds 2/9
- player_is_crashing: event-bearing trajectories 7/20; event-bearing folds 3/9
- player_is_looping: event-bearing trajectories 2/20; event-bearing folds 1/9
- player_is_falling: event-bearing trajectories 7/20; event-bearing folds 3/9
- player_is_jumping: event-bearing trajectories 4/20; event-bearing folds 2/9
- player_has_collisions: event-bearing trajectories 7/20; event-bearing folds 3/9
- player_point_pickup: event-bearing trajectories 5/20; event-bearing folds 2/9
- player_power_pickup: event-bearing trajectories 2/20; event-bearing folds 1/9
- player_boost_pickup: event-bearing trajectories 3/20; event-bearing folds 1/9

## Stability

Persistence is a repeatable descriptive signal on this slice: lag correlation remains high at short native-time lags and both hold-out views retain the same trajectory-level pattern. The event-driven relaxation family is **not admitted as stable**: event support is sparse and strongly channel/game dependent, while lag/decay/recovery remain undefined or censored for many folds. This is not a population estimate or formal test. Inspect per-fold `event_summary` and `trajectory_metrics` in `results.json`; do not promote any stable-looking shape to Theory-S training.
