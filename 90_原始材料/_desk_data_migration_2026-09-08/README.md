# Desk data migration — 2026-09-08

This directory is the local, non-pushed archive for data moved from the four
desk-side intake locations into `character-dynamics`.

## Source mapping

| Source | Destination | Status |
|---|---|---|
| `D:\desk\external_data_intake` | `external_data_intake/` | moved below |
| `D:\desk\research_raw_archive` | `research_raw_archive/` | moved below |
| `D:\desk\intents` | `intents/` | empty source tree; retained as provenance slot |
| `D:\desk\绉戠爺` | `绉戠爺/` | empty source tree; retained as provenance slot |

The imported assets are intentionally ignored by the project Git repository.
Nested repository metadata under `external_data_intake` is retained locally
for provenance but is not pushed as part of this project.

Verification after relocation: 31,056 files, 1,102,108,614 bytes. The three
data-bearing source roots (`external_data_intake`, `research_raw_archive`, and
`绉戠爺`) are gone from `D:\desk`; `D:\desk\intents` is empty but could not be
removed because another process currently holds the directory open.

## Handling boundary

This is a source-preserving relocation. No files were rewritten, normalized,
deduplicated, or deleted during intake. The source roots are removed only
after the moved tree is verified against the pre-move inventory.
