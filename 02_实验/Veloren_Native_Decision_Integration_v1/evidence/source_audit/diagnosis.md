# Veloren fixed-source routing diagnosis

## Scope and provenance

Official source is commit `1d12f35edd6cdbfc1fb921c167cdd7beeeffe248` (tag v0.18.0). The local `source_git_1d12f35e` checkout has A instrumentation as working-tree changes; official excerpts here were obtained from `git show HEAD:<path>`. The separate build-copy excerpts are A plus the frozen native-decision delta, not upstream code. The delta patch SHA-256 is `458c590d701561a0aee011348ed6823da943d4af0e203588fd2a7e8433fb5b7f`.

Excerpt index and SHA-256 of complete source files:

| Excerpt | Fixed path / lines | Whole-file SHA-256 |
|---|---|---|
| [official_rtsim_order.txt](official_rtsim_order.txt) | official `rtsim/src/lib.rs`, 199–209, 236–254, 298–336 | `b10f236733d737522a7854c5ee46f49bde8decff82846f940e25d74147b70217` |
| [official_simulate_npcs.txt](official_simulate_npcs.txt) | official `rtsim/src/rule/simulate_npcs.rs`, 118–138, 346–359 | `7ca4594f454cbb7a5bc2078044b27adc8352dd158a53f6546b791ef7b085517b` |
| [official_npcai_hire.txt](official_npcai_hire.txt) | official `rtsim/src/rule/npc_ai/mod.rs`, 1424–1449 | `6a7a3f547a9f7055c626b733df90ad4f84b65bf8b7e76fd476aabda3a2f1c0dd` |
| [a_delta_loaded_route.txt](a_delta_loaded_route.txt) | build-copy `server/src/rtsim/tick.rs`, 1228–1261; `server/src/sys/agent/behavior_tree/mod.rs`, 640–681 | tick `53ac63e65bfd97782e7692de1a1bab49957a25ba1a4549dd5408f88e95295a80`; Agent `5ffc8a633f78f55ea660fe9d8c2ab040d22b7f4dc55b863f31fbcd42c12cd2d4` |

## Static findings

1. The official default rule registration starts `SimulateNpcs` before `NpcAi`. Rule `bind` appends event handlers; `emit` iterates handlers in that stored order, and `tick` emits `OnTick`. For the same OnTick, SimulateNpcs therefore runs before NpcAi.
2. Official SimulateNpcs consumes `NpcAction::Msg`: for an NPC recipient it queues an `NpcInput::Msg` into a local vector, then removes the action. At the end of the pass, collected inputs are appended to each recipient inbox. In contrast, Say/Attack/Dialogue are retained only while the sender is `Loaded`; simulated-mode versions are removed. The same rule also mirrors `controller.job` to `npc.job`.
3. Official recipient logic handles `RequestHire` only when that Msg arrives through `NpcInput`; it schedules a native response action, which says acceptance and calls `set_newly_hired`. This is the intended native receiver/settlement path, not proof that a request was delivered.
4. In the A+delta Loaded server route, after the RTSim tick the server takes (`mem::take`) the sender's whole `controller.actions` vector and pushes actions into the Agent queue. Request correlation is attached only to Say; Msg still enters that queue as an ordinary action. Agent `handle_rtsim_actions` consumes Say by creating a Talk event, but the `NpcAction::Msg { .. }` match arm is empty. Since the action was taken from RTSim, the next SimulateNpcs pass cannot relay that Msg into the target inbox.

## Runtime boundary

The captured OFF/ON run reported six emitted recruitment messages and zero attributable `Job::Hired` observations. It did not instrument each message's Agent dequeue or recipient inbox delivery. Thus the Loaded drain + empty Agent Msg arm is a statically confirmed loss path **when the sender is Loaded**, and is a plausible explanation for the observed run only if those senders followed that route. The run evidence does not establish per-message sender mode or prove that all six messages were lost there. Simulated senders follow a different route and can remain in RTSim for SimulateNpcs delivery.

Job overwrite is not established as a cause: source ordering suggests a controller job written by the native recipient action is copied to `npc.job` by the next SimulateNpcs pass before NpcAi resets its controller from NPC state. Any initial-empty-controller overwrite concern remains an untested hypothesis, not a diagnosed defect.
