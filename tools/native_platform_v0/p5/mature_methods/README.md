# P5 mature-method adapter

This package adds a bounded high-level GTPyhop method layer to the existing native P5 Director workflow. It is an application integration for the generated P5 world, not a general planner or a replacement for P5, NPC-local planning, or Evennia.

## Runtime path

1. `service._evidence` exposes a sealed native trace and authorized P5 planning view. `snapshot_from_native` validates scene, bundle, minute, prefix, and view identity, then invokes the unchanged P5 `planning.plan()` on that exact state.
2. `narrative_methods.plan_high_level` runs the registered high-level GTPyhop domain. It records one bounded support decision and obligations; the route opportunity selection still comes from P5. A proposal is not execution and does not satisfy author goals.
3. The existing P5 runner and world adapter validate and execute eligible support. Existing actor callbacks perform NPC-local planning/actions and the native social chain determines responses. Evennia remains authoritative for world effects and time; TypedIR monitors author constraints.
4. `orchestrator.advance_from_sealed` compares validated before/after snapshots for relevant bundle, verdict, event, receipt, and actor changes. It preserves obligations for unaffected actors; ordinary clock advances do not automatically trigger a new high-level root plan.

## Boundaries

- The high-level method domain is finite and P5-specific. P5 opportunity evaluation remains the existing `planning.plan()`; this package is not a complete DODM or independent route optimizer.
- The planning view is read-only and authorized. It does not grant characters high-level world knowledge or add an RPC, clock, or world-mutation path.
- GTPyhop high-level state/domain registration is isolated from the NPC GTPyhop domain and coordinated through the existing planning lock; the process-global current domain is restored after use.
- Waiting creates tracked obligations, not deliveries or social outcomes. Only native receipts/events and the existing monitor establish those outcomes.
- Native permission edits are not supported by the current `BundleStore` runtime contract; do not infer edit/reselection behavior from offline method tests.

For measured native behavior and current limitations, see [Mature-Methods Integration v1 RESULTS](../../../../02_实验/Mature_Methods_Integration_v1/RESULTS.md).
