# Parent acceptance — 2026-10-14

Status: DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW, not CLOSED.

| Check | Parent result |
|---|---|
| Final runner tests | `python -B -m unittest tools.open_adventure_v0.tests.test_runner -v`: 8 run / 8 pass. Includes individual rejection of replay exit/stream/source/binary mismatches, exact tag/commit/clean source, timeout partial output, and failed main-flow evidence persistence. |
| No game required by unit suite | Failure-persistence test uses nonexistent temporary game/binary paths and mocks source/hash/execution. Luna also ran all 8 from a fresh temporary cwd without `_local_data`; parent checked the removed implicit installation dependency. Fake process capture is not a native-game test. |
| Official native tests | Parent `make check` with recorded SDK flags: exit 0, 115 tests / 0 failures. Optional lint tools were missing, not passed. Raw recorded build/test streams live in `BUILD_TEST_LOGS.json`; host machine name is omitted from publication. |
| Original three replay manifests | Parent recalculated exact stdin/stdout/stderr SHA256 and directly repeated all three inputs with the intermediate rebuild binary `0fa94664…91500b3`: exit 0 and matching stdout/stderr for each. The original run records remain unchanged. |
| Final real runner entry | Repeated the already selected bird fixture with final runner and latest recorded build, not a fourth scenario. [Record](runs/parent-review/parent-repeat-native-bird-20261014T012001Z-9b7df9/run.json): all 8 acceptance checks true, no errors, original bird stdout byte-identical. Includes both execution streams, source manifests and binary before/after hashes. |
| Upstream rule preservation | Exact tag/commit, tracked diff empty; source snapshots equal through build/test/replays. No NPC/item/command rules or YAML/templates changed. Generated sources/binaries remain ignored. |
| Mechanism interpretation | Parent reread native NPC/item handlers and corrected the initial audit's movement-only claim: `dwarfmove` is called even with unchanged player location; not one input line = one world tick. Native chase flags are not relationship memory. |

These checks establish the bounded build/replay integration. They do not
establish planner performance, LLM utility, human believability, complete save
support, an interactive step controller or generalized game interfaces.
