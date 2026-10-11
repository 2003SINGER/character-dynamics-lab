"""Narrow local-LLM proposal channel for the P5 AuthorBundle.

This module proposes a typed candidate from author text. It never approves or
executes one: P5 validation is a schema/registry check, not proof that the
natural-language intent was preserved.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from tools.native_platform_v0.p5.bundle import (
    DEFAULT_ENTITIES,
    P5_INITIAL_PHYSICAL_BUDGET,
    WORLD_OPPORTUNITIES,
    AuthorBundle,
    BundleError,
    load_bundle,
)


PROMPT_VERSION = "system-baseline-author-binding-v2"
RESPONSE_SCHEMA = "system-baseline-llm-binding-response-v1"
DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_MODEL = "qwen3-4b-q4_k_m"
MAX_REQUIREMENTS = 32
MAX_RESPONSE_BYTES = 1_000_000


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.0
    timeout_seconds: float = 60.0
    max_tokens: int = 2048
    json_mode: bool = True
    enable_thinking: bool = False

    def validate(self) -> None:
        parts = urlsplit(self.base_url)
        if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "localhost"}
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment):
            raise ValueError("LLM endpoint must be a plain HTTP loopback URL")
        if not self.model or self.model.strip() != self.model:
            raise ValueError("model must be a nonempty alias")
        if not math.isfinite(self.temperature) or not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be in [0, 2]")
        if (not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
                or type(self.max_tokens) is not int or self.max_tokens <= 0):
            raise ValueError("timeout_seconds and max_tokens must be positive")


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    text: str
    hard: bool


@dataclass(frozen=True)
class BindingOutcome:
    status: str
    candidate_bundle: dict[str, Any] | None
    typed_bundle: AuthorBundle | None
    requirement_coverage: tuple[dict[str, Any], ...]
    residuals: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]
    artifact_dir: Path
    usage: Mapping[str, Any] | None

    @property
    def hard_residual(self) -> bool:
        return any(row.get("hard") is True for row in self.residuals)

    @property
    def requires_human_review(self) -> bool:
        return self.status == "NEEDS_HUMAN_REVIEW"

    @property
    def may_execute_after_human_review(self) -> bool:
        return (self.status == "NEEDS_HUMAN_REVIEW" and not self.hard_residual
                and self.candidate_bundle is not None and self.typed_bundle is not None)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def p5_capabilities(*, allowed_permissions: Mapping[str, Any] | None = None,
                    entities: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Expose only the currently registered P5 bundle surface to the model."""
    entity_catalog = DEFAULT_ENTITIES if entities is None else entities
    permissions = dict(allowed_permissions or {
        "world_opportunities": sorted(WORLD_OPPORTUNITIES),
        "force_npc_response": False,
        "max_opportunities": 1,
        "cost_budget": P5_INITIAL_PHYSICAL_BUDGET,
    })
    return {
        "bundle_schema": "native-author-bundle-v1",
        "bundle_shape": {
            "required_top_level_fields": {
                "schema": "native-author-bundle-v1",
                "bundle_id": "nonempty stable identifier",
                "version": "integer >= 1",
                "source": "nonempty identifier",
                "constraints": "array; may be empty only when no supported requirement needs a constraint",
                "branches": "array; content-only and may be empty",
                "permissions": {
                    "world_opportunities": "unique subset of the supplied permission ceiling",
                    "force_npc_response": False,
                    "max_opportunities": "integer 0..1",
                    "cost_budget": "integer 0..caller ceiling",
                },
            },
            "constraint_common_fields": {
                "id": "unique nonempty identifier", "kind": "one registered kind below",
                "start": "integer scenario minute", "deadline": "integer >= start",
                "hard": "boolean",
            },
            "event_by_deadline_template": {
                "required_fields": ["id", "kind", "event", "filters", "start", "deadline", "hard"],
                "optional_fields": {"min_count": "integer 0..1000; defaults to 1",
                                     "max_count": "integer >= min_count and <= 1000"},
            },
            "event_order_template": {
                "required_fields": ["id", "kind", "before", "after", "order", "start", "deadline", "hard"],
                "selector_shape": {"event": ["delivery_settled", "note_response"],
                                    "filters": "event-specific subset described below"},
                "order_values": ["EVENT_KEY", "PHYSICAL_TIME"],
            },
            "state_by_deadline_template": {
                "required_fields": ["id", "kind", "observable", "args", "value", "start", "deadline", "hard"],
                "value": "boolean",
            },
            "branch_template": {
                "required_fields": ["id", "when", "storylet"],
                "when": {"event": "note_response", "response": ["accepted", "rejected"]},
                "storylet": {"id": "unique nonempty identifier", "text": "nonempty content-only string"},
                "limits": ["branches cannot cause world effects", "branch only on an actual note_response"],
            },
        },
        "json_templates": {
            "bundle": {
                "schema": "native-author-bundle-v1", "bundle_id": "REPLACE_ID",
                "version": 1, "source": "author-request", "constraints": [], "branches": [],
                "permissions": {"world_opportunities": [], "force_npc_response": False,
                                "max_opportunities": 1, "cost_budget": 0},
            },
            "event_by_deadline": {
                "id": "REPLACE_UNIQUE_ID", "kind": "event_by_deadline",
                "event": "REGISTERED_EVENT_NAME", "filters": {"REGISTERED_FILTER": "STABLE_ENTITY_ALIAS"},
                "start": 0, "deadline": 1, "hard": "BOOLEAN",
            },
            "event_order": {
                "id": "REPLACE_UNIQUE_ID", "kind": "event_order",
                "before": {"event": "REGISTERED_EVENT_NAME", "filters": {"REGISTERED_FILTER": "STABLE_ENTITY_ALIAS"}},
                "after": {"event": "REGISTERED_EVENT_NAME", "filters": {"REGISTERED_FILTER": "STABLE_ENTITY_ALIAS"}},
                "order": "EVENT_KEY_OR_PHYSICAL_TIME", "start": 0, "deadline": 1, "hard": "BOOLEAN",
            },
            "state_by_deadline": {
                "id": "REPLACE_UNIQUE_ID", "kind": "state_by_deadline",
                "observable": "REGISTERED_OBSERVABLE", "args": {"REGISTERED_ARGUMENT": "REGISTERED_VALUE"},
                "value": "BOOLEAN", "start": 0, "deadline": 1, "hard": "BOOLEAN",
            },
            "branch": {
                "id": "REPLACE_UNIQUE_ID", "when": {"event": "note_response", "response": "accepted_OR_rejected"},
                "storylet": {"id": "REPLACE_UNIQUE_ID", "text": "content-only text"},
            },
            "response": {
                "schema": RESPONSE_SCHEMA,
                "candidate_bundle": "bundle object above",
                "requirement_coverage": [{"requirement_id": "EXACT_INPUT_ID",
                                           "candidate_refs": ["constraint/REPLACE_UNIQUE_ID"],
                                           "residual": None}],
                "residuals": [],
            },
        },
        "constraints": {
            "event_by_deadline": {
                "events": {
                    "delivery_settled": {"filters": {"actor": "Actor", "item": "Item"}},
                    "note_response": {"filters": {"actor": "Actor", "recipient": "Actor",
                                                      "item": "Item", "response": ["accepted", "rejected"]}},
                },
                "fields": ["id", "kind", "event", "filters", "start", "deadline", "hard",
                           "optional:min_count", "optional:max_count"],
            },
            "event_order": {
                "event_selectors": ["delivery_settled", "note_response"],
                "orders": ["EVENT_KEY", "PHYSICAL_TIME"],
                "fields": ["id", "kind", "before", "after", "order", "start", "deadline", "hard"],
            },
            "state_by_deadline": {
                "observables": {"holding": ["actor", "item"], "route_open": ["route"]},
                "fields": ["id", "kind", "observable", "args", "value", "start", "deadline", "hard"],
            },
        },
        "entities": {
            alias: {"entity_type": entity.entity_type, "stable_id": entity.stable_id}
            for alias, entity in entity_catalog.items()
        },
        "filter_rules": {
            "delivery_settled": {"actor": "Actor alias", "item": "Item alias"},
            "note_response": {"actor": "Actor alias", "recipient": "Actor alias",
                               "item": "Item alias", "response": ["accepted", "rejected"]},
            "omitted_filter": "unfiltered for that field; for either note response, omit response entirely (do not use '*')",
            "stable_aliases": {
                alias: "Actor" if entity.entity_type == "Actor" else "Item"
                for alias, entity in entity_catalog.items()
            },
        },
        "branches": {
            "when": {"event": "note_response", "response": ["accepted", "rejected"]},
            "storylet": "content only; cannot cause world effects",
        },
        "permissions_ceiling": permissions,
        "important_limits": [
            "P5 does not authorize forcing an NPC response.",
            "Only registered bundle events, state predicates, entities, routes, and permissions are valid.",
            "Typed bundle validation does not establish semantic completeness or truth.",
            "Map every supplied requirement ID to candidate refs or an explicit residual.",
            "Never omit, soften, or reinterpret a hard requirement to obtain a valid bundle.",
        ],
    }


def _normalize_requirements(requirements: Sequence[Requirement | Mapping[str, Any]]) -> tuple[Requirement, ...]:
    if not isinstance(requirements, Sequence) or isinstance(requirements, (str, bytes)):
        raise ValueError("requirements must be a sequence")
    if not 1 <= len(requirements) <= MAX_REQUIREMENTS:
        raise ValueError(f"requirements must contain 1..{MAX_REQUIREMENTS} items")
    rows: list[Requirement] = []
    for index, raw in enumerate(requirements):
        if isinstance(raw, Requirement):
            row = raw
        elif isinstance(raw, Mapping) and set(raw) == {"requirement_id", "text", "hard"}:
            row = Requirement(raw["requirement_id"], raw["text"], raw["hard"])
        else:
            raise ValueError(f"requirement {index} must contain requirement_id, text, hard")
        if (not isinstance(row.requirement_id, str) or not row.requirement_id
                or row.requirement_id.strip() != row.requirement_id):
            raise ValueError(f"requirement {index} has invalid requirement_id")
        if not isinstance(row.text, str) or not row.text.strip() or type(row.hard) is not bool:
            raise ValueError(f"requirement {row.requirement_id!r} needs nonempty text and boolean hard")
        rows.append(row)
    ids = [row.requirement_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("requirement_id values must be unique")
    return tuple(rows)


def build_prompt(author_text: str, requirements: Sequence[Requirement | Mapping[str, Any]], *,
                 allowed_permissions: Mapping[str, Any] | None = None,
                 entities: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    """Build a versioned prompt over the immutable P5 capability manifest."""
    if not isinstance(author_text, str) or not author_text.strip():
        raise ValueError("author_text must be nonempty")
    normalized = _normalize_requirements(requirements)
    system_text = (
        "You propose a P5 native-author-bundle-v1 candidate from an author's request. "
        "Return one JSON object and no markdown. Do not invent registry entries, entities, "
        "permissions, state, receipts, or outcomes. Preserve every requirement exactly in "
        "meaning. For each requirement_id in the supplied checklist, provide exactly one "
        "requirement_coverage row with candidate_refs that point to actual candidate bundle "
        "clauses/permissions, or a nonempty residual explaining why it is unsupported. "
        "A hard unsupported requirement must be a hard residual; never soften it. "
        "Do not force an NPC response. Candidate validation is not semantic approval.\n\n"
        "Follow the supplied json_templates literally: candidate_bundle has exactly its seven keys "
        "(schema, bundle_id, version, source, constraints, branches, permissions); never put entities "
        "or requirements inside the bundle. Requirement accounting belongs only in the outer "
        "requirement_coverage field. Constraint IDs must be unique. Do not copy template clauses unless they "
        "represent a stated requirement. The payload includes exact per-kind required/optional fields. "
        "For event_order, before and after are selector objects "
        "with event plus filters. For a selector over either note response, omit filters.response "
        "to match both registered responses; a literal '*' is invalid. Only aliases in the supplied "
        "stable_aliases map may be used, with their declared Actor/Item types.\n"
        "Required response shape:\n"
        '{"schema":"system-baseline-llm-binding-response-v1",'
        '"candidate_bundle":{...},'
        '"requirement_coverage":[{"requirement_id":"...",'
        '"candidate_refs":["constraint/<id>"],"residual":null}],'
        '"residuals":[{"requirement_id":"...","statement":"...",'
        '"reason":"..."}]}\n'
        "Use an empty candidate_refs list when residual is present. For a fully bound "
        "requirement use residual null. Every requirement ID must appear once, no extra IDs."
    )
    user_payload = {
        "prompt_version": PROMPT_VERSION,
        "author_request": author_text,
        "requirements": [asdict(row) for row in normalized],
        "registered_capabilities": p5_capabilities(
            allowed_permissions=allowed_permissions, entities=entities),
    }
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def _candidate_references(candidate: Mapping[str, Any]) -> set[str]:
    refs = {f"constraint/{row['id']}" for row in candidate.get("constraints", [])
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)}
    refs.update(f"branch/{row['id']}" for row in candidate.get("branches", [])
                if isinstance(row, Mapping) and isinstance(row.get("id"), str))
    permissions = candidate.get("permissions", {})
    if isinstance(permissions, Mapping):
        for field, value in permissions.items():
            refs.add(f"permission/{field}")
            if isinstance(value, list):
                refs.update(f"permission/{field}/{item}" for item in value if isinstance(item, str))
    return refs


def _constraint_hardness(candidate: Mapping[str, Any]) -> dict[str, bool]:
    constraints = candidate.get("constraints", [])
    if not isinstance(constraints, list):
        return {}
    return {f"constraint/{row['id']}": row.get("hard") is True
            for row in constraints
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)}


def _validate_permission_ceiling(candidate: Mapping[str, Any], allowed: Mapping[str, Any]) -> None:
    permissions = candidate.get("permissions")
    if not isinstance(permissions, Mapping):
        raise ValueError("candidate bundle has no permissions object")
    allowed_ops = allowed.get("world_opportunities")
    candidate_ops = permissions.get("world_opportunities")
    if (not isinstance(allowed_ops, (list, tuple, set, frozenset))
            or not isinstance(candidate_ops, list)
            or not set(candidate_ops) <= set(allowed_ops)):
        raise ValueError("candidate world_opportunities exceed the caller's permission ceiling")
    if permissions.get("force_npc_response") is not False or allowed.get("force_npc_response") is not False:
        raise ValueError("P5 and this task prohibit forced NPC responses")
    for key in ("max_opportunities", "cost_budget"):
        ceiling = allowed.get(key)
        value = permissions.get(key)
        if type(ceiling) is not int or type(value) is not int or not 0 <= value <= ceiling:
            raise ValueError(f"candidate {key} exceeds or violates the explicit permission ceiling")


def validate_response_payload(payload: Any, requirements: Sequence[Requirement | Mapping[str, Any]], *,
                              allowed_permissions: Mapping[str, Any] | None = None,
                              entities: Mapping[str, Any] | None = None,
                              physical_budget: int = P5_INITIAL_PHYSICAL_BUDGET) -> dict[str, Any]:
    """Check response shape, total requirement accounting, P5 types and permissions.

    A successful result is still only ``NEEDS_HUMAN_REVIEW``. Hard residuals,
    missing requirement mappings, and typed validation errors block eligibility.
    """
    normalized = _normalize_requirements(requirements)
    expected = {row.requirement_id: row for row in normalized}
    allowed = dict(allowed_permissions or {
        "world_opportunities": sorted(WORLD_OPPORTUNITIES),
        "force_npc_response": False,
        "max_opportunities": 1,
        "cost_budget": P5_INITIAL_PHYSICAL_BUDGET,
    })
    if not isinstance(payload, Mapping) or set(payload) != {
            "schema", "candidate_bundle", "requirement_coverage", "residuals"}:
        return {"status": "INVALID_RESPONSE", "errors": ["response has the wrong top-level shape"],
                "candidate_bundle": None, "typed_bundle": None, "requirement_coverage": [],
                "residuals": [], "hard_residual": False}
    if payload.get("schema") != RESPONSE_SCHEMA:
        return {"status": "INVALID_RESPONSE", "errors": ["response schema version mismatch"],
                "candidate_bundle": None, "typed_bundle": None, "requirement_coverage": [],
                "residuals": [], "hard_residual": False}
    candidate = payload.get("candidate_bundle")
    coverage_raw = payload.get("requirement_coverage")
    residual_raw = payload.get("residuals")
    if not isinstance(candidate, Mapping) or not isinstance(coverage_raw, list) or not isinstance(residual_raw, list):
        return {"status": "INVALID_RESPONSE", "errors": ["candidate, coverage, and residuals have invalid types"],
                "candidate_bundle": None, "typed_bundle": None, "requirement_coverage": [],
                "residuals": [], "hard_residual": False}

    errors: list[str] = []
    coverage: dict[str, dict[str, Any]] = {}
    for row in coverage_raw:
        if not isinstance(row, Mapping) or set(row) != {"requirement_id", "candidate_refs", "residual"}:
            errors.append("requirement coverage row has the wrong shape")
            continue
        req_id = row.get("requirement_id")
        refs, residual = row.get("candidate_refs"), row.get("residual")
        if not isinstance(req_id, str) or req_id not in expected or req_id in coverage:
            errors.append("requirement coverage has an unknown or duplicate requirement ID")
            continue
        if (not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs)
                or (residual is not None and (not isinstance(residual, str) or not residual.strip()))
                or bool(refs) == bool(residual)):
            errors.append(f"requirement {req_id!r} must map to refs or one explicit residual")
            continue
        coverage[req_id] = {"requirement_id": req_id, "candidate_refs": refs, "residual": residual,
                            "hard": expected[req_id].hard}
    missing = set(expected) - set(coverage)
    if missing:
        errors.append("requirement coverage incomplete: " + ", ".join(sorted(missing)))

    actual_residuals: dict[str, dict[str, Any]] = {}
    for row in residual_raw:
        if (not isinstance(row, Mapping)
                or set(row) != {"requirement_id", "statement", "reason"}
                or not isinstance(row.get("requirement_id"), str)
                or not isinstance(row.get("statement"), str) or not row["statement"].strip()
                or not isinstance(row.get("reason"), str) or not row["reason"].strip()):
            errors.append("residual row has the wrong shape")
            continue
        req_id = row["requirement_id"]
        if req_id not in expected or req_id in actual_residuals:
            errors.append("residual has an unknown or duplicate requirement ID")
            continue
        covered = coverage.get(req_id)
        if covered is None or covered["residual"] != row["statement"]:
            errors.append(f"residual for {req_id!r} does not match its coverage row")
            continue
        actual_residuals[req_id] = {**dict(row), "hard": expected[req_id].hard}
    for req_id, row in coverage.items():
        if row["residual"] is None and req_id in actual_residuals:
            errors.append(f"requirement {req_id!r} has a residual not declared by its coverage row")
        if row["residual"] is not None and req_id not in actual_residuals:
            errors.append(f"requirement {req_id!r} residual detail is missing")

    available_refs = _candidate_references(candidate)
    constraint_hardness = _constraint_hardness(candidate)
    for req_id, row in coverage.items():
        for ref in row["candidate_refs"]:
            if ref not in available_refs:
                errors.append(f"requirement {req_id!r} points to missing candidate ref {ref!r}")
        constraint_refs = [ref for ref in row["candidate_refs"] if ref in constraint_hardness]
        if (expected[req_id].hard and constraint_refs
                and not any(constraint_hardness[ref] for ref in constraint_refs)):
            errors.append(f"hard requirement {req_id!r} maps only to soft constraints")

    typed_bundle = None
    candidate_json = _plain(candidate)
    try:
        _validate_permission_ceiling(candidate_json, allowed)
        typed_bundle = load_bundle(candidate_json, entities=entities, physical_budget=physical_budget)
    except (BundleError, TypeError, ValueError) as exc:
        errors.append(f"P5 typed validation failed: {getattr(exc, 'code', type(exc).__name__)}")

    residuals = [actual_residuals[key] for key in sorted(actual_residuals)]
    hard_residual = any(row["hard"] for row in residuals)
    if errors:
        status = "INVALID_RESPONSE"
    elif hard_residual:
        status = "HARD_RESIDUAL"
    else:
        status = "NEEDS_HUMAN_REVIEW"
    return {
        "status": status,
        "errors": errors,
        "candidate_bundle": candidate_json if typed_bundle is not None and not errors else None,
        "typed_bundle": typed_bundle if not errors else None,
        "requirement_coverage": [coverage[key] for key in sorted(coverage)],
        "residuals": residuals,
        "hard_residual": hard_residual,
    }


def _post_chat_completion(payload: Mapping[str, Any], config: LLMConfig) -> bytes:
    endpoint = config.base_url.rstrip("/") + "/chat/completions"
    request = Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        body = exc.read(MAX_RESPONSE_BYTES + 1)
        raise RuntimeError(f"local chat endpoint returned HTTP {exc.code}: {body[:4000].decode('utf-8', 'replace')}") from exc
    except URLError as exc:
        raise RuntimeError(f"local chat endpoint unavailable: {exc.reason}") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("local chat response exceeded the configured size limit")
    return body


def _write_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)


def _write_json(path: Path, value: Any) -> bytes:
    data = (json.dumps(_plain(value), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _write_exclusive(path, data)
    return data


def bind_author_request(author_text: str, requirements: Sequence[Requirement | Mapping[str, Any]], *,
                        artifact_parent: str | Path,
                        allowed_permissions: Mapping[str, Any],
                        config: LLMConfig | None = None,
                        transport: Callable[[Mapping[str, Any], LLMConfig], bytes] | None = None,
                        entities: Mapping[str, Any] | None = None,
                        physical_budget: int = P5_INITIAL_PHYSICAL_BUDGET) -> BindingOutcome:
    """Request one candidate and save a non-overwriting, auditable artifact set.

    This makes exactly one model call and never retries automatically. A caller
    may elect one explicitly budgeted retry after inspecting the saved error.
    Even a typed-valid, fully mapped proposal remains unapproved pending human
    semantic review.
    """
    normalized = _normalize_requirements(requirements)
    llm = config or LLMConfig()
    llm.validate()
    parent = Path(artifact_parent)
    parent.mkdir(parents=True, exist_ok=True)
    artifact_dir = parent / f"llm_binding_{uuid4().hex}"
    artifact_dir.mkdir(exist_ok=False)
    messages = build_prompt(author_text, normalized, allowed_permissions=allowed_permissions, entities=entities)
    request_payload: dict[str, Any] = {
        "model": llm.model,
        "messages": messages,
        "temperature": llm.temperature,
        "max_tokens": llm.max_tokens,
        "chat_template_kwargs": {"enable_thinking": llm.enable_thinking},
    }
    if llm.json_mode:
        request_payload["response_format"] = {"type": "json_object"}
    prompt_bytes = _write_json(artifact_dir / "request.json", request_payload)
    config_data = asdict(llm)
    config_data.update({"prompt_version": PROMPT_VERSION, "request_sha256": sha256(prompt_bytes).hexdigest(),
                        "artifact_schema": RESPONSE_SCHEMA})
    _write_json(artifact_dir / "config.json", config_data)

    call = transport or _post_chat_completion
    started = time.monotonic()
    try:
        raw_response = call(request_payload, llm)
    except Exception as exc:
        elapsed = time.monotonic() - started
        error = f"{type(exc).__name__}: {exc}"
        _write_exclusive(artifact_dir / "transport_error.txt", (error + "\n").encode("utf-8"))
        metadata = {"status": "LLM_UNAVAILABLE", "elapsed_seconds": elapsed,
                    "cost": {"currency": "USD", "amount": None, "basis": "LOCAL_UNPRICED"},
                    "usage": None}
        _write_json(artifact_dir / "metadata.json", metadata)
        return BindingOutcome("LLM_UNAVAILABLE", None, None, (), (), (error,), artifact_dir, None)
    elapsed = time.monotonic() - started
    if not isinstance(raw_response, bytes) or len(raw_response) > MAX_RESPONSE_BYTES:
        raw_response = str(raw_response).encode("utf-8", "replace")[:MAX_RESPONSE_BYTES]
    _write_exclusive(artifact_dir / "response.raw", raw_response)

    usage: Mapping[str, Any] | None = None
    try:
        envelope = json.loads(raw_response.decode("utf-8"), object_pairs_hook=_unique_json_object)
        if isinstance(envelope, Mapping) and isinstance(envelope.get("usage"), Mapping):
            usage = dict(envelope["usage"])
        content = envelope["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("assistant content must be a JSON string")
        normalized_content = content
        stripped_empty_think = False
        match = re.match(r"^<think>\s*</think>\s*", content, flags=re.DOTALL)
        if match:
            normalized_content = content[match.end():]
            stripped_empty_think = True
        normalization = {
            "operation": "strip_exact_empty_think_prefix" if stripped_empty_think else "none",
            "raw_content_sha256": sha256(content.encode("utf-8")).hexdigest(),
            "normalized_content_sha256": sha256(normalized_content.encode("utf-8")).hexdigest(),
            "nonempty_think_content_is_not_stripped": True,
        }
        _write_json(artifact_dir / "response_normalization.json", normalization)
        payload = json.loads(normalized_content, object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        error = f"INVALID_RESPONSE: {type(exc).__name__}: {exc}"
        metadata = {"status": "INVALID_RESPONSE", "elapsed_seconds": elapsed, "usage": usage,
                    "cost": {"currency": "USD", "amount": None, "basis": "LOCAL_UNPRICED"},
                    "response_sha256": sha256(raw_response).hexdigest()}
        _write_json(artifact_dir / "metadata.json", metadata)
        _write_json(artifact_dir / "outcome.json", {"status": "INVALID_RESPONSE", "errors": [error]})
        return BindingOutcome("INVALID_RESPONSE", None, None, (), (), (error,), artifact_dir, usage)

    checked = validate_response_payload(payload, normalized, allowed_permissions=allowed_permissions,
                                        entities=entities, physical_budget=physical_budget)
    candidate = checked["candidate_bundle"]
    typed = checked["typed_bundle"]
    if candidate is not None:
        _write_json(artifact_dir / "candidate.bundle.json", candidate)
    elapsed_metadata = {
        "status": checked["status"],
        "elapsed_seconds": elapsed,
        "usage": usage,
        "cost": {"currency": "USD", "amount": None, "basis": "LOCAL_UNPRICED"},
        "response_sha256": sha256(raw_response).hexdigest(),
        "typed_validation": "PASS" if typed is not None else "FAIL",
        "human_review_required": True,
        "hard_residual": checked["hard_residual"],
    }
    _write_json(artifact_dir / "metadata.json", elapsed_metadata)
    _write_json(artifact_dir / "outcome.json", {
        key: value for key, value in checked.items() if key != "typed_bundle"
    })
    return BindingOutcome(checked["status"], candidate, typed,
                          tuple(checked["requirement_coverage"]), tuple(checked["residuals"]),
                          tuple(checked["errors"]), artifact_dir, usage)
