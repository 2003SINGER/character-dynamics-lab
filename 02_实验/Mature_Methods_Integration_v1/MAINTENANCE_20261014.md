# Bounded Python maintenance — 2026-10-14

## Scope and result

This maintenance pass is limited to Python station code debt. At the fixed
baseline `8ca0a45f64c3cebd65651fc0caef40c2f51f4d97` on
`codex/native-game-admission-20261014`, `ongoing_station/actor.py` defined
`_repair_before_storage_constraint` twice (lines 72 and 118) and
`_locally_knows_repair_witness` twice (lines 89 and 136). Python used the later
definition in each pair. The earlier definitions were removed; the later
definitions remain bytecode-equivalent to the last definitions at HEAD. No
candidate ordering, loan policy, receipt guard, task behavior, timing rule,
experiment input, or saved run was changed.

The regression suite now checks that each of these helpers has exactly one
module-level definition. Existing repair-order actor coverage remains in place.

## Responsibility map

| Layer | Actual owner | Examples and boundary |
|---|---|---|
| Game engine | Evennia | Native rooms, objects, exits, attributes, command validation, persistence, and world callbacks. These are engine facilities, not the station's gameplay rules. |
| Station game content | `ongoing_station/work.py` | `initialize_content`, `request_tool_loan`, `start_work`, `_finish_effect`, `store_supply`, and `advance_work` implement the tool lease, task durations, inspection/repair/storage effects, receipts, and loan outcomes. These are hand-authored game rules. |
| Existing planning runtime | pinned GTPyhop 2.0.2 runtime/DFS, called through P3 | Reused algorithm/runtime; it does not provide this profile's task meaning. |
| Project task and execution integration | `p3/planning.py`, `p3/agency.py`, plus P5 task adapters | P3 observations, route helper, pending-action dispatcher, and native primitive boundary are reused; station task decompositions and route usage are project code. Evennia validation decides whether a submitted action is legal. |
| Actor policy | `ongoing_station/actor.py` | `_self_offers`, the repair-order/witness helpers, `_still_authorized`, and `advance_actor` implement local candidate generation, commitment arbitration, witness retention, and permission checks. They explicitly bind A/B, `station_tool`, `pickup_to_side_south`, `courier_supply`, and `station_storage`; these are profile-specific conditions, not generic NPC interfaces. |
| Author control | `ongoing_station/model.py`, `native.py`, and `controller.py` | Validated `AuthorBundle` constraints and registered grants are the source of author goals and permissions. The controller builds offers and reconciles future edits; offers are proposals, not execution or receipts. |
| Story-process planning | `story_process/planning.py` | General note-method planning shares a file with the station-specific `_station_*` helpers and `plan_station_work_order`. Those task requests, duration estimates, method candidates, and order checks are hand-authored domain additions, not Evennia mechanics or generic GTPyhop capability. |
| Audit | station/P5 audit modules | Checks readback and evidence for actual receipts, state, and author verdicts. Audit does not choose actions or grant execution authority. |

The responsibility map is also in the ongoing-station README. A top-level AST
scan of `actor.py`, `controller.py`, and `story_process/planning.py` found no
other repeated function definitions. Similar but differently named helpers
were left untouched; this was not a broad deduplication or module split.

## Equivalence and regression evidence

The HEAD comparison explicitly selected the last definition of each helper,
then compared its AST and executed function code fields against the cleaned
definition. AST, bytecode, constants, names, locals, and argument counts were
identical for both helpers. Two paired fixtures (string and truthy non-string
receipt IDs) produced identical constraint matches and witness dictionaries;
both retained the current `observed_minute` field. The earlier shadowed witness
guard was not substituted: it had required a string receipt ID and omitted
`observed_minute`, so removing it preserves the behavior Python actually ran.

Full offline regression used the project's pinned Evennia virtual environment
both at the exact detached HEAD baseline and after cleanup:

- P5 baseline: 228 tests run, 227 passed; 1 skipped because the native Django/Evennia saver
  environment is not configured.
- P5 cleaned: 229 tests run, 228 passed; the same 1 skip. The additional test is the
  focused AST regression for the duplicate helper definitions.
- P3 baseline and cleaned: 56 tests passed in each run.
- The focused AST regression is included in the 229 cleaned P5 tests and passed.

Baseline tests ran in a temporary detached checkout at `8ca0a45`; it was removed
after the run. Test stdout and direct equivalence output are preserved in the
unique run directory (only the listed maintenance evidence is published):
`runs/maintenance-code-debt-20261014T0100Z/`.

Parent acceptance independently compared the entire cleaned module AST with
the baseline after retaining each name's last definition: all remaining
module statements were identical. Parent reruns reproduced P5 229 run / 228
passed / 1 skipped and P3 56 passed; logs are in
`runs/maintenance-parent-review-20261014/`. No native scenario was rerun.

These offline tests and helper-level equivalence checks establish this local
cleanup only. They are not a rerun of native game episodes or a claim that all
game behavior is equivalent under every untested state.

## Remaining debt and exclusions

Station aliases and task rules remain embedded in actor, controller, work, and
story-process planning code. This pass only records their ownership and
profile-specific nature; it does not extract a generic game adapter or redesign
data flow. Testing proves the Python regression suite, not a second game's
integration. Historical RESULTS, prior run directories, C++/E0 code, and native
service state were not modified.
