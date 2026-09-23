# Historical QwenActionPolicyV0

The earlier adapter called `DemoLayaPolicyV0` was **not Laya**: its live
backend was Qwen3-4B GGUF through a local `llama-server`. It returned one
action, not a typed probability distribution. The C++ implementation and
bridge are now named `QwenSocketPolicyV0` and `qwen_action_proxy.py`, with
trace id `qwen-action-policy-v0`. Old cassettes may retain the historical row
marker `laya_decision`; that marker is not evidence of Laya inference.

The adapter sends only known/stale O, S, P/I and eligible A^O over loopback.
It never reads hidden W; selected actions still pass World validation. It
never silently falls back to RulePolicy if the bridge is unavailable.

Historical 2026-09-22 local Qwen evidence: scenario seed `1000`, policy seed
`5000`, balanced P, 48-hour free-run horizon; 82 boundaries and 69 model
decisions. A local cassette replay reproduced the trace byte-for-byte. This
is operational evidence for the old Qwen action adapter only, not Laya or
human-character validity.

To reproduce the historical mode, start Qwen3-4B with a local `llama-server`
on `127.0.0.1:8080`, then run:

```sh
python3 tools/qwen_action_proxy.py --model /absolute/path/to/Qwen3-4B-Q4_K_M.gguf \
  --cassette /absolute/path/to/qwen-decisions.jsonl --port 8742
build/character_dynamics_free_run 1000 5000 /tmp/qwen-48h.json \
  balanced --qwen-port 8742
```

For the actual checkpoint, typed choice probabilities, seeded C++ sampling
and current evidence, see [LayaTypedPolicyV0](../laya_typed_policy_v0/README.md).
