# Native Platform P1/P2 evidence snapshot

This directory is a public archival copy of the selected P1 Evennia, P2 Ensemble, live bridge, and LIGHT bounded-probe
evidence. The source artifacts remain in the local output cache and are the source-of-capture:

- Evennia: `outputs/native_platform_p1p2_v0/p1_evennia_20261010/`
- LIGHT: `outputs/native_platform_p1p2_v0/light_probe_20261010/`
- Ensemble: `outputs/native_platform_p1p2_v0/p2_ensemble_20261010/`
- Bridge: `outputs/native_platform_p1p2_v0/bridge_20261010/`

Treat the files copied here as an immutable snapshot. `MANIFEST.sha256` hashes the bytes at these
destination paths after copying; it does not hash source names or Git state. The original
`MANIFEST.sha256` covers P1/LIGHT; `MANIFEST_ALL.sha256` covers all selected runtime evidence.
Run `shasum -a 256 -c MANIFEST_ALL.sha256` from this directory.

The selection is intentionally narrow. `evennia/` contains the requested P1 evidence summary,
installed EvAdventure source hash and excerpts, environment/status/listener/info captures, movement
JSON and its failed first capture, the pre-shim server log, and the later verified bootstrap log.
`light/` contains the result and attempt 02/03 stdout/stderr. No generated database, credentials,
`secret_settings.py`, virtual environment, installed upstream source tree, or Git metadata was
copied.

`ensemble/` contains the native example, historical 23-assertion run, final 28-assertion run, and
its captured run note. That note is historical per-run evidence, not the current milestone owner;
the authoritative synthesis is [../RESULTS.md](../RESULTS.md). `bridge/first-live-success.json`
retains the first successful three-case execution. `bridge/final-live-20261010T1735Z/` contains
the parent-operated final four-case execution and independent actual-world DB readback. Its
cache-gap case is explicitly in-process, not a server-restart recovery claim. Later results do
not replace old success or failure evidence. Per-module text manifests additionally name source
paths. Every published raw evidence copy was compared byte-for-byte against its local original.

The selected files were scanned before copying for credential assignments, bearer credentials,
and the known local test passwords; no matches were found. The snapshot does not contain every raw
install or migration log. The first install and initial successful migration output were not saved
as files; `evennia/bootstrap.log` is the later bootstrap verification against an already-installed
environment, not a fresh-install transcript.
