# Veloren v0.18 native recruitment route: source audit

Fixed official commit: `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248` (tag `v0.18.0`). Official excerpts below are from `git show HEAD:<path>`, not the locally patched source worktree. Full-file SHA-256 values are included for rechecking.

## Official source excerpts and hashes

- `rtsim/src/lib.rs`, lines 199–209, 236–245, 307–310, 329–335; SHA-256 `b10f236733d737522a7854c5ee46f49bde8decff82846f940e25d74147b70217`. See [official_rtsim_order.txt](official_rtsim_order.txt). Default registration places SimulateNpcs before NpcAi; bind appends handlers and emit iterates them in insertion order on OnTick.
- `rtsim/src/rule/simulate_npcs.rs`, lines 118–138, 346–359; SHA-256 `7ca4594f454cbb7a5bc2078044b27adc8352dd158a53f6546b791ef7b085517b`. See [official_simulate_npcs.txt](official_simulate_npcs.txt). NPC Msg actions are converted to recipient inbox inputs and removed; non-Msg actions are retained only for Loaded NPCs. The same pass copies `controller.job` to `npc.job` and appends collected inputs to inboxes.
- `rtsim/src/rule/npc_ai/mod.rs`, lines 1424–1449; SHA-256 `6a7a3f547a9f7055c626b733df90ad4f84b65bf8b7e76fd476aabda3a2f1c0dd`. See [official_npcai_hire.txt](official_npcai_hire.txt). Recipient RequestHire is handled from inbox; native action waits 2 seconds, says acceptance, then calls `set_newly_hired`.

## A+delta Loaded route (not official HEAD)

The build-copy excerpts are official commit + frozen A + native-decision delta; delta patch SHA-256 `458c590d701561a0aee011348ed6823da943d4af0e203588fd2a7e8433fb5b7f`.

- `server/src/rtsim/tick.rs` lines 1228–1261; file SHA-256 `53ac63e65bfd97782e7692de1a1bab49957a25ba1a4549dd5408f88e95295a80`.
- `server/src/sys/agent/behavior_tree/mod.rs` lines 640–681; file SHA-256 `5ffc8a633f78f55ea660fe9d8c2ab040d22b7f4dc55b863f31fbcd42c12cd2d4`.
- Excerpts: [a_delta_loaded_route.txt](a_delta_loaded_route.txt). For Loaded NPCs, the server takes the whole RTSim action vector and pushes actions into the Agent queue; request correlation is attached only to Say. Agent turns Say into a Talk control event, but its `NpcAction::Msg { .. }` arm is empty. A transferred Msg is therefore absent from RTSim at the next SimulateNpcs pass and is not relayed to recipient inbox by this route.
- The same handoff and empty Msg arm predate A: official HEAD server excerpts and hashes are in [official_server_loaded_route.txt](official_server_loaded_route.txt), for `server/src/rtsim/tick.rs` lines 624–634 and `server/src/sys/agent/behavior_tree/mod.rs` line 658.

## Diagnosis boundary

The captured OFF/ON run recorded six recruitment messages and zero attributable `Job::Hired` observations. It did not instrument per-message Agent dequeue or recipient inbox delivery, and the source trace alone does not prove that all six senders were Loaded. Thus the Loaded route is a statically confirmed loss path for Loaded senders and a plausible explanation for the run, not confirmed per-message runtime causation. Simulated senders are not covered by this drain path.

Possible first-tick empty-controller Job overwrite remains an untested hypothesis, not a diagnosed cause. Source order suggests a newly set controller job is copied into `npc.job` by the next SimulateNpcs pass before NpcAi resets controller state from the NPC.
