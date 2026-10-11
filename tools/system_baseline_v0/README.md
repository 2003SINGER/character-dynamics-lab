# System Baseline v0 binding seam

`llm_binding.py` is a proposal-only adapter from an author request plus a
pre-registered requirement checklist to a candidate P5 `native-author-bundle-v1`
and explicit residuals. Its prompt exposes only the existing P5 registry,
stable entity catalog, and caller-supplied permission ceiling. It adds no DSL or
general natural-language parser. The prompt includes `load_bundle`'s required
top-level keys and per-constraint/branch field shapes, selector syntax, stable
alias types, and the rule that an omitted `note_response.filters.response`
matches either registered response (there is no `"*"` wildcard token).

```python
from tools.system_baseline_v0.llm_binding import Requirement, bind_author_request

outcome = bind_author_request(
    author_text="Both deliveries happen. B may reject the note; allow a side route, do not force a response.",
    requirements=[
        Requirement("deliveries", "Both deliveries happen by the deadline.", hard=True),
        Requirement("note-and-route", "B may reject; A may use a side route without forcing B.", hard=True),
    ],
    artifact_parent=run_artifact_dir,
    allowed_permissions={
        "world_opportunities": ["open_side_passage"],
        "force_npc_response": False,
        "max_opportunities": 1,
        "cost_budget": 2,
    },
)
```

The default local request targets `http://127.0.0.1:8080/v1`, model
`qwen3-4b-q4_k_m`, `temperature=0`, `max_tokens=2048`, and
`chat_template_kwargs.enable_thinking=false`. Calls are one-at-a-time with no
automatic retry. Each invocation creates a unique `llm_binding_<id>` directory
containing the exact request, raw response, config/hash, usage/cost metadata,
candidate bundle (when typed-valid), and outcome. Cost is recorded as
`LOCAL_UNPRICED`; no local-model price is inferred. Prompt v2 includes a generic
empty bundle skeleton and registered field shapes. If the server nevertheless
wraps output in an exactly empty `<think></think>` prefix, a separate
normalization record documents stripping that prefix only; nonempty reasoning
is not stripped. Duplicate JSON keys are rejected rather than silently
overwritten.

`NEEDS_HUMAN_REVIEW` means only that the returned shape, requirement accounting,
P5 types, entity references, and permission ceiling passed validation. It does
not establish that the candidate preserved the request. A hard unsupported
residual yields `HARD_RESIDUAL`; callers must not pass that outcome to the
runner. Missing or malformed requirement coverage and typed/permission errors
yield `INVALID_RESPONSE`. Only a separate requirement-by-requirement human
semantic audit can decide whether a non-hard-residual candidate is suitable for
the matched native run. Unit contracts run with:

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.system_baseline_v0.tests.test_llm_binding -v
```

This contract layer is not evidence that M2 works. The authorized local calls
were recorded but all returned `INVALID_RESPONSE`; no candidate was sent to the
native runner. Overall milestone status and evidence ownership are maintained
in [System Baseline v0 RESULTS](../../02_实验/System_Baseline_v0/RESULTS.md),
with the small call archive in [public evidence](../../02_实验/System_Baseline_v0/public_evidence/llm-binding-20261012.tar.gz).
