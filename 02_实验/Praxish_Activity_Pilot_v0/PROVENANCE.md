# Provenance and source boundary

## Upstream release

- Repository: <https://github.com/mkremins/praxish>
- Release: `aiide-23` — <https://github.com/mkremins/praxish/releases/tag/aiide-23>
- Release tag commit reported by GitHub: `4729b0c469a7ecb423622f543ca116315616a76b`
- Downloaded release asset: `Praxish_AIIDE2023_Artifact.zip`
- Release archive SHA-256: `a5418432db8f2af8387a8eead2e4ad1392465833d862eda9273c614b883a8c77`

The archive is the publisher-attached demo package for this release, not a locally constructed `git archive`. Its bytes and the three noninteractive runtime/test files used here are pinned independently. The artifact remains in the ignored project output cache; no upstream source is copied into this tracked pilot.

| Release-archive path | SHA-256 |
|---|---|
| `noninteractive/db.js` | `acb98656dcc0fe461ba7d6b2875bd3429ae4068735b1795297a5722d0469c46c` |
| `noninteractive/praxish.js` | `ef2f77999b08dd24c9893a531ae2096ef33189a9cf46bf342d024ffa44e1c088` |
| `noninteractive/tests.js` | `7b9a41281ec8620d43bcf0062b39cbcbaad22349483fe9cae55b3ef823486947` |

`fetch` verifies these recorded values before use. The scenario harness does not load the upstream `tests.js`; that file is retained and hash-checked as part of the untouched source package. The harness defines its own small practice data and calls the upstream API.

## License

The downloaded release archive contains no license file. The pinned tag was separately checked and has no `LICENSE.txt`. We have not established whether the license on the current `master` branch covers this older release. Therefore this repository does not claim MIT licensing for the pinned release, does not vendor or redistribute its source, and keeps the fetched package only in the local ignored output cache for this inspection. The GitHub release page is cited as the source, not as a substitute for an absent license grant.

## Local execution and trace

The upstream noninteractive page loads `db.js`, `praxish.js`, and `tests.js` in that order. The initial source check ran that sequence with Node `v26.8.2` in a VM and a fixed random seed. This confirms the script path executes in that runtime; browser rendering and UI behavior remain unverified.

Pilot traces are newly generated typed observations from the original API. They contain no copied upstream source. Each trace identifies the release pin and marks `upstream_source_modified: false`. The VM observer replaces only the global `randNth` reference to observe the selected candidate, and the harness independently calculates per-goal score breakdowns by applying each candidate to a cloned database. These observations are engineering evidence for this fixture, not a paper reproduction or behavioral-validity result.
