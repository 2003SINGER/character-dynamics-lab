"""Independent adversarial checks for the bounded author-binding contract.

Synthetic traces in this file exercise TypedIR semantics only. They are not
native receipts and are never passed to the pinned-evidence evaluator.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from tools.planner_p0_v0.author_binding_v0.compiler import (
    AuthorBinding,
    AuthorClause,
    PINNED_RUNS,
    assert_plan_binding_current,
    classify_candidate_result,
    compile_binding,
    evaluate_binding,
    load_pinned_native_trace,
    p0_author_binding,
    plan_binding_metadata,
)
from tools.planner_p0_v0.integration_v0.monitor import (
    build_typed_trace,
    integration_registry,
)
from tools.trajectory_constraints_v0.ast import EventCount, EventOrder
from tools.trajectory_constraints_v0.monitor import Verdict, evaluate


REPO_ROOT = Path(__file__).resolve().parents[4]
SYNTHETIC_TRACE_LABEL = "synthetic typed-event test input; not native evidence"


def _receipt(sequence: int, event_type: str, minute: int, args: dict) -> dict:
    """Build a test-only receipt-shaped row for the frozen semantic projector."""
    source = ("native_meet_command" if event_type == "MEETING_WITNESS"
              else "native_evennia_readback")
    return {
        "sequence": sequence,
        "event_id": f"synthetic:{sequence}",
        "minute": minute,
        "event_type": event_type,
        "source": source,
        "accepted": True,
        "settled": True,
        "receipt_id": f"synthetic-receipt:{sequence}",
        "code": None,
        "typed_args": args,
    }


def _synthetic_trace(events: list[dict], *, now: int, known_weather: tuple[str, ...] = ()) -> dict:
    """Return a complete, sealed synthetic prefix; never authenticates receipts."""
    return {
        "snapshot": {
            "clock": {"now": now},
            "actors": {"B": {"known_weather": list(known_weather)}},
        },
        "events": events,
        "ledger_frontier": len(events),
        "sealed_through": now,
        "synthetic_label": SYNTHETIC_TRACE_LABEL,
    }


def _statuses(binding: AuthorBinding, trace_data: dict) -> dict[str, str]:
    """Evaluate the compiled TypedIR clauses on a test-only synthetic trace."""
    trace = build_typed_trace(trace_data)
    registry = integration_registry()
    compilation = compile_binding(binding, fixture_id="direct-clean-A", repo_root=REPO_ROOT)
    return {
        constraint.constraint_id: evaluate(constraint, trace, registry)[0].verdict.value
        for constraint in compilation.constraints
    }


def _constraint_signature(constraint):
    if isinstance(constraint, EventCount):
        return ("count", constraint.event_type, constraint.event_version,
                constraint.window, constraint.minimum, constraint.maximum,
                dict(constraint.event_filter or {}))
    if isinstance(constraint, EventOrder):
        return ("order", constraint.before_type, constraint.before_version,
                constraint.after_type, constraint.after_version, constraint.order,
                constraint.window, dict(constraint.before_filter or {}),
                dict(constraint.after_filter or {}))
    raise AssertionError(f"unexpected TypedIR constraint {type(constraint).__name__}")


class IndependentAuthorBindingSemanticsTests(unittest.TestCase):
    def test_delivery_receipt_does_not_prove_full_binding_without_observation(self):
        binding = p0_author_binding(8)
        trace = _synthetic_trace(
            [_receipt(1, "DROP_SETTLED", 8,
                      {"actor": "A", "item": "shelter_kit", "room": "inn"})],
            now=8,
            known_weather=("storm",),
        )
        self.assertEqual(trace["synthetic_label"], SYNTHETIC_TRACE_LABEL)
        statuses = _statuses(binding, trace)
        self.assertEqual(statuses["deliver-once"], Verdict.SATISFIED.value)
        self.assertEqual(statuses["observe-once"], Verdict.VIOLATED.value)
        self.assertEqual(statuses["meeting-once"], Verdict.VIOLATED.value)
        self.assertNotEqual(set(statuses.values()), {Verdict.SATISFIED.value})

    def test_deadline_uses_inclusive_native_event_minute(self):
        binding = AuthorBinding(
            "delivery-until-eight", p0_author_binding().version,
            "A delivers by minute eight", 8,
            (AuthorClause("deliver", "event_once", event="p0_delivery", actor="A"),),
        )
        at_deadline = _synthetic_trace(
            [_receipt(1, "DROP_SETTLED", 8,
                      {"actor": "A", "item": "shelter_kit", "room": "inn"})],
            now=8,
        )
        after_deadline = _synthetic_trace(
            [_receipt(1, "DROP_SETTLED", 9,
                      {"actor": "A", "item": "shelter_kit", "room": "inn"})],
            now=9,
        )
        self.assertEqual(_statuses(binding, at_deadline)["deliver"], Verdict.SATISFIED.value)
        self.assertEqual(_statuses(binding, after_deadline)["deliver"], Verdict.VIOLATED.value)

    def test_clause_ids_do_not_change_projection_semantics(self):
        binding = p0_author_binding()
        renamed = replace(binding, clauses=tuple(
            replace(clause, clause_id=f"independent-id-{index}")
            for index, clause in enumerate(binding.clauses)
        ))
        original = compile_binding(binding, fixture_id="direct-clean-A", repo_root=REPO_ROOT)
        changed_ids = compile_binding(renamed, fixture_id="direct-clean-A", repo_root=REPO_ROOT)
        self.assertEqual(original.sabre_problem, changed_ids.sabre_problem)
        self.assertEqual(tuple(map(_constraint_signature, original.constraints)),
                         tuple(map(_constraint_signature, changed_ids.constraints)))

    def test_same_version_content_change_invalidates_plan_digest(self):
        binding = p0_author_binding()
        compilation = compile_binding(binding, fixture_id="direct-clean-A", repo_root=REPO_ROOT)
        token = plan_binding_metadata(compilation)
        assert_plan_binding_current(token, binding, compilation)
        changed = replace(binding, deadline_minute=8)
        with self.assertRaisesRegex(ValueError, "STALE_BINDING_CONTENT"):
            assert_plan_binding_current(token, changed, compilation)

    def test_unsupported_hard_residual_prevents_sat_on_satisfied_fixture(self):
        binding = p0_author_binding()
        binding = replace(binding, clauses=binding.clauses +
                          (AuthorClause("unmodeled-relationship", "relationship_drop"),))
        compilation = compile_binding(binding, fixture_id="direct-clean-A", repo_root=REPO_ROOT)
        report = evaluate_binding(binding, compilation, repo_root=REPO_ROOT,
                                  fixture_id="direct-clean-A")
        self.assertEqual(report["status"], "INDETERMINATE")
        self.assertTrue(report["hard_residual_obligations"])
        self.assertEqual(classify_candidate_result({"status": "SUCCESS"}, compilation),
                         "UNBOUND_OR_RESIDUAL")

    def test_only_pinned_fixture_ids_are_evidence_inputs(self):
        self.assertIn("direct-clean-A", PINNED_RUNS)
        with self.assertRaisesRegex(ValueError, "UNKNOWN_FIXTURE"):
            load_pinned_native_trace(REPO_ROOT, "synthetic-receipt-json")
        binding = p0_author_binding()
        compilation = compile_binding(binding, fixture_id="direct-clean-A", repo_root=REPO_ROOT)
        self.assertEqual(evaluate_binding(binding, compilation, repo_root=REPO_ROOT)["status"],
                         "INDETERMINATE")


if __name__ == "__main__":
    unittest.main()
