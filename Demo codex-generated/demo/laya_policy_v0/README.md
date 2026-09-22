# DemoLayaPolicyV0

`DemoLayaPolicyV0` is an optional **presentation/application policy adapter**.
It changes only how an already-open `DecisionGate` selects an action; it does
not change the Shared Runtime Kernel, World validation, `DemoLivingDynamicsV1`,
ReferenceRuleDynamicsV0, action schema, or the research track.

## Contract

At each policy boundary, C++ sends the local bridge only:

```text
O (known/stale facts) + S + P + eligible A^O
```

It never sends `W`, World primitives, hidden facts, or the rule policy's
probabilities. The bridge is hard-wired to `127.0.0.1:8080` and the C++ client
to `127.0.0.1:<port>`: there is no remote endpoint, API-key, or cloud fallback.
The returned action must be in the supplied eligible surface. It still goes
through ordinary Runtime/World validation; a rejected action remains a typed
World feedback event.

If the local bridge is unavailable or emits an invalid action, the run fails.
It never silently falls back to `RulePolicyV0`.

## Run locally

This Mac's current local model is Qwen3-4B in GGUF format. Start a loopback
`llama-server`, then the bridge in separate terminals:

```sh
llama-server -m /absolute/path/to/Qwen3-4B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 -c 4096 -ngl 99

python3 tools/laya_policy_proxy.py \
  --model /absolute/path/to/Qwen3-4B-Q4_K_M.gguf \
  --cassette /absolute/path/to/laya-decisions.jsonl --port 8742
```

Run a deterministic 48-hour scenario (scenario seeds `>=1000` use the
longer free-run horizon):

```sh
build/character_dynamics_free_run 1000 5000 /tmp/laya-48h.json \
  balanced --laya-port 8742
```

Qwen3's local chat template is called with `enable_thinking=false`, so the
bounded response contains the required action JSON rather than an unfinished
reasoning trace. The cassette records the local request hash, allowed surface,
chosen action, model id and response digest. Re-run using it without a model:

```sh
python3 tools/laya_policy_proxy.py \
  --model replay-only --replay /absolute/path/to/laya-decisions.jsonl \
  --cassette /tmp/laya-replay-audit.jsonl --port 8743
build/character_dynamics_free_run 1000 5000 /tmp/laya-replay-48h.json \
  balanced --laya-port 8743
```

The same trace inputs must replay byte-for-byte. This is replay determinism,
not a claim that an unconstrained local model is deterministic.

## Evidence and scope

`character_dynamics_laya_policy_loopback_smoke` uses a local stand-in to prove
the socket contract and trace provenance without requiring an LLM. A live
Qwen run is an opt-in demo probe. It is neither a human-character study nor a
reason to tune `DemoLivingDynamicsV1`; LayaMood and any memory/personality
rewrites are intentionally out of scope for v0.

## Local deployment read-back (2026-09-22)

The Mac-local Qwen3-4B deployment completed scenario seed `1000`, policy seed
`5000`, balanced `P` through the 48-hour free-run horizon: 82 boundaries and
69 Laya decisions, all attributed to `laya-policy-v0`. The chosen actions
included study, rest, sleep, meals, bathroom, phone use and room control. The
locally recorded cassette replayed the same run into a byte-identical 82-frame
trace without a model call. This is operational evidence for the adapter and
replay path only, not a behavior-quality or research result.
