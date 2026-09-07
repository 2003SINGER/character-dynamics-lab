# Dataset → Theory-S v2 capability matrix (development planning)

Status is an input/ownership audit, not a claim that a dataset is admitted or that persistent state is identifiable. `✓` means observed/exported; `△` means a proxy requiring semantic review; `—` means absent in the current audit. The v2 module never silently promotes a proxy to subjective `O`, `A*`, `P`, or `S`.

| Dataset | action / A* | transition | subjective O boundary | persistence | suitable v2 role now |
|---|---|---|---|---|---|
| LIGHT | ✓ physical-action steps; A* semantics audited | △ scene/object transition slice | — | △ episode traces | restricted development adapter; no formal persistent-S claim |
| OPeRA | ✓ event/action logs in local audit | ✓/△ session telemetry and timestamps | — | ✓ long sessions | priority semantic audit; candidate transition source |
| ClubFloyd | ✓ text player logs | △ world/dialogue context | △ only with explicit annotation | ✓ ordered transcript | adapter/provenance pilot |
| FarmQuest | ✓ extracted replay records | △ task/progress events | — | ✓ ordered sessions | external-state proxy |
| PowerWash | △ telemetry events/state fields | ✓ subtask/progress/time events | — | ✓ ordered sessions | transition/progress proxy; no subjective O |
| AGAIN | ✓ audited event records | △ session/task progression | — | ✓ timestamped timeline | persistence/progress audit |
| SOTOPIA | ✓ ordered synthetic agent actions | ✓ scenario/episode context | △ private goal boundary, not human O | ✓ episode sequence | external synthetic pilot only; not human ground truth |

For any future formal use, require trajectory/episode-disjoint splits, provenance for every inferred X, and matched-capacity theory-S versus naive-S and Permuted-S. Unknowns remain unknowns.
