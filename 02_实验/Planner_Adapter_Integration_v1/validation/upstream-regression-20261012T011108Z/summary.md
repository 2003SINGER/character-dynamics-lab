# A8 upstream regression evidence

Run ID: `upstream-regression-20261012T011108Z`  
Scope: one existing P0 Integration Sabre domain plus one actual GTPyhop task decomposition. No native server, benchmark sweep, dependency update, or third-party source edit.

Exact command arguments, paths, versions, hashes, and the complete GTPyhop local-view input are in [exact-invocation-inputs.json](exact-invocation-inputs.json). Its note explains the integer key conversion needed when reconstructing the Python dict from JSON.

## Sabre

- Upstream source: `sgware/sabre` v0.8.0, commit `73a128123b10a57843068b69d0b0e0601f37488a`, license GPL-3.0; local checkout HEAD matched. Existing wrapper and unmodified locally compiled CLI were used with Temurin 17.0.20.1+1.
- Domain input: `02_实验/Planner_P0_v0/integration_v0/preflight/direct_clean.txt`, SHA-256 `f77ffcb41b44e9352a7026ac8c0489a5cdab45f04ff87239c92eb6b83a482af1`.
- Invocation: same arguments as the local runner (`-m bf -c t -h 'h+' -el 1 -vl 200 -gl 5000 -tl 5000 -g 1 -atl 24 -ctl 2`; `-Xss8m`).
- Process status: exit 0; native `Result: Success!`; utility 1; 12 visited / 164 generated nodes; actual grounded actions preserved in `sabre.stdout.txt`.
- Saved raw stdout SHA-256: `ed8a40134156c6460ffe417c5c305497e4419ff7b594143f77e964e31bab2979` (verified against `sabre.stdout.txt`).
- Sabre CLI class hash: `Main.class` SHA-256 `3835ffd623059aa0806974632675fc4acdf3d46243660270e48cb16fc6d97678`.

## GTPyhop

- Package: `gtpyhop-core==2.0.2`, declared Clear BSD License; project pin is `tools/native_platform_v0/p3/requirements.txt:2`. Installed distribution explicitly says it does not bundle example domains (`gtpyhop.examples` is not installed). Existing repo regression entry points are `tools/native_platform_v0/p3/tests/test_p4_agency.py` and `test_p3_actor_loop.py`; this run directly calls the repo's real `plan_next` adapter and package planner, not a mock planner.
- Input is a bounded actor-local view: parcel visible and at actor's room; destination is one locally known traversable edge away. The direct call returned `SOLVED`, plan `get → move(east) → drop`, and first intent `get`; output retains `prediction_only: true`. This validates real task decomposition only, not native execution or receipt settlement.
- Process status: exit 0; captured package stdout + adapter output preserved in `gtpyhop.stdout.txt`.
- Captured output SHA-256: `65949cb9af4af65817e4c5063b0da2dc2d8bb7deec66806ee31c2218f46b980c`.
- Relevant source hashes: `tools/native_platform_v0/p3/planning.py` `93c835cdd693cf37b80540246ccc33ca976f62bd9cc8ede4ffdbc4242b2336c4`; Sabre wrapper `tools/planner_p0_v0/sabre_baseline/runner.py` `b38a3058bdbd9992fe8d83e285793df430f097b6d284211bfbf5470701e5262d`; P0 renderer `tools/planner_p0_v0/integration_v0/sabre_export.py` `55b4d5c63bbd3b05c0a6d8d2a235568fe11413b10ce1c10def68dcf3d16cf87e`.

## Time-risk correction from native evidence

The successful matched side-route M1 run `C1-C2-side-C3-reject-20261011T164643Z-5b5c12` shows A's native rooms across minutes 1–16: initial move south, east, south (three exploration primitives), north back to pickup, GET, south, east, DROP. Every primitive follows its intent on a later minute callback; drop settles at minute 16. Therefore shortest-route move/get/drop arithmetic is only a conditional lower bound after local discovery, not a whole-run ETA. The exact trace, its hash, and the correction are referenced in `CAPABILITY_AUDIT.md`.
