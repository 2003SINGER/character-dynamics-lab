# Author Constraint Diagnostic v0

One fixed diagnostic of the existing raw Luna four-atom candidate. No model calls, new planner, world model, author bundle or director. [Protocol](../../02_实验/Author_Constraint_Diagnostic_v0/PROTOCOL.md), [results](../../02_实验/Author_Constraint_Diagnostic_v0/RESULTS.md).

- `run.py`: reads the original unedited output, passes its actual Goal directly into frozen UCS once; if FOUND, permits one P1/B0 external-goal episode. Search predictions and native receipts are separate. The existing controller still re-searches each input under its frozen budgets. An execution directory/attempt claim prevents accidental repetition; a guard failure before any search/native call is retained separately.
- `monitor.py`: native-byte-only E temporal checker; source-based bridge creation requires successful `wave rod` feedback, not a final bridge description or predicted effect. Contiguous complete input receipts, fresh final look/inventory and sealed observed interval are required for success. Uses frozen verifier extraction helpers, never its final-bridge condition or planner state updates.
- `contracts.py`: experiment-local AUTHOR/PLANNER/GAME records. Source, strength and time are independent. Only unexecuted dependencies of a retired plan can be cancelled; author requirements and historical witnesses persist. Native plan bookkeeping is retrospective, not a new online Director. Its dependency PASS refers to a modeled dependency's accepted consumer, not independently proven native preconditions.

Offline contracts (no real searches, game or inference):

```sh
python -B -m unittest discover -s tools/author_constraint_diagnostic_v0/tests -v
```

The real search and episode have already run. **Do not rerun** `python -m tools.author_constraint_diagnostic_v0.run --execute-native` for this round; immutable execution artifacts intentionally reject a second attempt. Inspect/re-monitor the existing ledger instead. Offline synthetic vanished-bridge receipts are labeled as such and are not a second native episode.

Old semantic admission is still FAIL. The diagnostic uses its four valid terminal atoms only under explicit separate authorization; it does not delete residual fields, relax the old validator, or claim B2 admission. Upstream source, frozen B0/P1 and all old results remain byte-identical.
