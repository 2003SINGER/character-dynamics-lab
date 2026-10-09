# Ensemble native probe

Pinned upstream: `ensemble-engine/ensemble` commit `8b74bdec4ba2ef4e14795b7591df3b5d73f283e3`, version 1.1.1, BSD-4-Clause. Source cache: `_local_data/native_platform_v0/ensemble/` (ignored). Runtime: Node v26.8.2. This is an interface probe, not an Evennia integration.

Recreate the ignored source checkout and pin from the project root:

```sh
git clone https://github.com/ensemble-engine/ensemble.git _local_data/native_platform_v0/ensemble
git -C _local_data/native_platform_v0/ensemble checkout --detach 8b74bdec4ba2ef4e14795b7591df3b5d73f283e3
git -C _local_data/native_platform_v0/ensemble rev-parse HEAD
```

Run from the project root:

```sh
node tools/native_platform_v0/ensemble/reproduce.mjs
node tools/native_platform_v0/ensemble/run-upstream-tests.mjs
node tools/native_platform_v0/ensemble/interface-selftest.mjs
node tools/native_platform_v0/ensemble/runner.mjs
```

`reproduce.mjs` loads the original Lovers and Rivals `schema.json`, `cast.json`, `triggerRules.json`, `volitionRules.json`, `actions.json`, `history.json`, and the checked-in browser bundle. Its selected example path is `calculateVolition → getActions → doAction → runTriggerRules → setupNextTimeStep`.

## JSONL interface

One JSON object per input line; one JSON response per line. A long-running Node process retains Ensemble state and its proposal/idempotency ledger in memory.

Proposal:

```json
{"op":"propose","eventId":"source-event-001","actor":"hero","responder":"love","facts":[]}
```

`eventId` is required and unique within the process. `facts` is an optional array of `{category,type,first,second?,value}` predicates. The wrapper validates the complete batch before applying any predicate, checking cast membership, schema category/type, direction, value type, and numeric bounds (atomic prevalidation, not an engine transaction). It then projects supplied external facts before calculating. Response includes `proposalId`, `eventId`, `recordRevision`, contributing volitions, and bound terminal action candidates. Proposal never invokes `doAction`, triggers, or time-step advancement. Commit rejects proposals if another projected fact batch or commit has changed the social-record revision.

Commit only after the external game reports that the proposed action really settled:

```json
{"op":"commit","proposalId":"p1:source-event-001","eventId":"source-event-001","settlementStatus":"settled","settledActionName":"writeLoveNoteReject","actionName":"writeLoveNoteReject","settlementReceiptId":"#123"}
```

Commit requires a nonempty receipt id, matching source event id and action name, status `settled`, and an HMAC proof tied to proposal/event/action/receipt using `ENSEMBLE_BRIDGE_SECRET`. A successful commit invokes original Ensemble `doAction`, then explicit `runTriggerRules`, then `setupNextTimeStep`. Repeating the same commit in the same process returns `duplicate:true` without reapplying effects; a matching authorization retry after commit is also accepted as duplicate, allowing a bridge to finish its receipt journal after a cache gap. State and this idempotency ledger are process-local; restart persistence is outside this probe. Only the trusted bridge should hold the HMAC secret and issue proofs after real execution.

The JSONL process does not connect to Evennia, decide world state, or settle actions itself. Supplied facts are shared Ensemble social-record entries; this does not implement private actor observation.

## Results

- Native example trace: `outputs/native_platform_p1p2_v0/p2_ensemble_20261010/reproduction.json`.
- Official upstream core tests: 45 groups passed, zero failed. The old browser-only `ExternalApplicationTest` was excluded because it requires `document` events. Upstream `ActionLibraryUnitTests.js` explicitly comments out `testDoAction` as incompatible with the newer API.
- Wrapper-only self-tests: see `outputs/native_platform_p1p2_v0/p2_ensemble_20261010/native-test-evidence.json`; they cover atomic prevalidation, invalid cast/schema rejection, stale revision rejection, source-event binding, authorization, forged HMAC rejection, receipt gating, action membership, duplicate commit/authorization protection, and fresh proposal IDs.
- The latest standalone 28-assertion wrapper stdout is `outputs/native_platform_p1p2_v0/p2_ensemble_20261010/native-test-evidence-28.json`; do not mistake the older 23-assertion run in `native-test-evidence.json` for this final wrapper pass. To capture a new combined run, `capture-evidence.mjs` writes only to a fresh `runs/<RUN_ID>/` directory and refuses to reuse an existing ID.
- Public snapshot copies of the small example, test stdout, first live success rawlog, and source results are listed in [the evidence index](../../../02_实验/Native_Platform_P1P2_v0/evidence/README.md).
- The separately scoped Evennia bridge lives under `tools/native_platform_v0/bridge/`; its live scenario results are recorded separately and are not upstream tests.
