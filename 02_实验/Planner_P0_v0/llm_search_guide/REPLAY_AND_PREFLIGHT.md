# P0 Gramma: exact historical replay and local completion preflight

Date: 2026-10-11. This record contains bounded metadata and the five public search-cost rows only. Full source checkout, embedding CSV, author prompt/response transcript, compatibility build, and local-model raw response remain under ignored `_local_data/planner_p0_v0/`.

## Result labels

- `REPLAY`: the original cached Gramma transcript was fed through an offline, exact-prompt transport shim. It is not a new-model result.
- `SOURCE_COMPAT_BUILD`: the original source was compiled in an ignored copy using JDK 21 plus the single explicit-generic compatibility change below. The upstream checkout and bundled JAR were not modified.
- `ADAPTED_COMPLETION_PREFLIGHT`: two bounded local Qwen completion requests were made with the root prompt; this was not a planner/search run. The first response was not retained because the client failed on CSV decoding; the second was saved before cache comparison. Neither suggestion had an exact embedding-cache key, so the process stopped.
- `NOT_LIVE`: no new Qwen-guided search and no embedding request occurred. No cloud API was called.

## Upstream and build provenance

- Repository: `https://github.com/rac7hel/planning-stories-neurally`
- Checkout HEAD: `4a258be9e36bb4fedcee0f7eaec92652ed8e532f` (2025-06-23); Sabre README says v0.7.
- Bundled `lib/sabre.jar` SHA-256: `b74d1f73cad5a68a077794a99d97a7b0348739dcf0958b5b3d42c88e8ac2d526`; class-file major 64. JDK 17 could not load it; JDK 21 found the bundled jar missing `ProgressionPlanner$Method$4`.
- Unmodified whole-source JDK 21 build failed at `src/edu/uky/cs/nil/sabre/logic/Precondition.java:82` due generic type inference. A whole-source build in the ignored compatibility copy succeeded after only this explicit-type-argument edit:

  ```diff
  - return new Disjunction<>(new Clause<>(this));
  + return new Disjunction<Clause<Precondition>>(new Clause<Precondition>(this));
  ```

  This makes the already inferred `Disjunction`/`Clause` type arguments explicit; it does not change planner or search logic. The original checkout and jar hashes remained unchanged. Do not label this the original distributed-JAR run.
- The upstream checkout contains no `LICENSE`, `COPYING`, or `NOTICE` file. No upstream source, jar, full transcript, or embedding vectors are included in the project artifacts.

## Exact replay evidence

The run used the historical Gramma problem and upstream run-1 transcript/embedding cache in an ignored compatibility-build copy. The shim overrides only `r7.llmsearch.OpenAIComponent` by classpath order; it has no network code, requires exact prompt equality, returns only recorded suggestions, and throws if an embedding transport is requested. All five prompts matched. No embedding request was made; the upstream cache supplied the strings used to reconstruct costs.

The generated run-2 `search.txt` and `transcript.txt` were each byte-identical to historical run-1:

| Artifact | SHA-256 | Comparison |
|---|---|---|
| Search trace | `365e91de54695f86ec89dac6414014f86c663c1a184ec735dc2a28977d566fe0` | exact match |
| Full transcript | `55e77253e4c43e7bec02f87b3ad94579d87ed56f75e3820e0053b53224b1939f` | exact match |
| Gramma embedding CSV | `49a91db431e975c47770308367e18e4492c65efe6738b41451d33baad453c9e3` | input cache fingerprint |

The full five-row search trace is:

```text
0.0:
5.0: walk(Tom, Cottage, Crossroads)
5.0: walk(Bandit, Camp, Crossroads)
7.0: walk(Merchant, Market, Crossroads)
7.0: report(Merchant, Camp, Market)
```

The run ends at the source's hardcoded five-node cap (`SEARCH_NODE_LIMIT=5`); the CLI reports `Maximum nodes visited: 5` after those five expansions. `-atl 5` in the invocation is an author temporal-depth limit, not the node cap. Exit code alone is therefore not the acceptance check; exact artifact hashes and the five exact replay markers are. An earlier parser-debug run and its partial output are ignored local artifacts, not part of the accepted replay.

Scope note: during initial runtime diagnosis, one native `-m gf` CLI probe mistakenly treated `-atl 5` as a visit cap. It was not capped by nodes and completed 55,734 visits / 111,443 generated nodes in about 7.1 seconds. This is retained as an out-of-scope diagnostic fact only; it is not a P0 result or comparison and no public result file was created from it.

## Local Qwen preflight and stopping condition

The local endpoint was loopback-only `http://127.0.0.1:8080/v1`; request used model alias `qwen3-4b-q4_k_m`, the upstream default system role, the exact historical root prompt, `max_tokens=25`, `temperature=0.3`, and seed `20261011`. The auditable preflight-v2 response is stored privately at `_local_data/planner_p0_v0/qwen_preflight_v2_response.json`, SHA-256 `ddda197d2b1b5524c0c78571e7636a2ce9c6369b7f7861b5722247048feb6106`.

- Model fingerprint: `b10809-5266f24da`.
- Prompt SHA-256: `51d7df63069bb9db8d2d8a1c725c1c421e60eee812401377cac07f5692f52a7d`.
- Completion SHA-256: `562e07f7e5c0f314d2d3d538092d69585ade640a505b32d71ebe93d2c5a74ec9`.
- Usage: 296 prompt / 17 completion / 313 total tokens; 295 prompt tokens reported cached by server.
- Both response lines were checked as exact keys using JDK 21 UTF-8 default `FileReader` semantics and the upstream 1537-column cache filter: `0/2` exact hits.
- One earlier completion request returned, but the first client did not save it before failing to decode the cache. A single approved corrected retry persisted the response first. Total: two local completion calls; zero embedding calls; zero new-model search runs. This does not consume or alter the historical replay's five recorded turns.
- Those two calls are method preflights. The parent separately made one transport-readiness probe (16 prompt / 3 completion tokens); it is not a search input. Overall the temporary local service handled three completion requests, no cloud or embedding requests, and was stopped after this checkpoint.

Since Qwen's suggestions are not exact keys in the original `text-embedding-ada-002` cache, no cosine cost can be computed faithfully without requesting an embedding. No local-chat, string-similarity, or other vector substitute is acceptable. This is the current genuine blocker for `ADAPTED_METHOD_RUN`/`NOT_LIVE`.

## Reproduction files

- Offline shim: `tools/planner_p0_v0/llm_search_guide/replay_src/r7/llmsearch/OpenAIComponent.java`
- Mechanism and code/paper audit: `01_文献/算法积木/06_P0原始规划路线_2026-10-11/LLM_Sabre_Search.md`
- Full private inputs/build/raw outputs: ignored `_local_data/planner_p0_v0/`; do not stage them.
