from __future__ import annotations

import base64
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from tools.open_adventure_planning_v0.domain import OPERATORS, initial_state
from tools.open_adventure_planning_v0.execute import _decline_cave_hint, _expected_action, _native_question
from tools.open_adventure_planning_v0.observe import reconcile
from tools.open_adventure_planning_v0.search import Goal, SearchLimits, uniform_cost_search
from tools.open_adventure_planning_v0.verify import verify_ledger


def _row(seq: int, command: str, text: str) -> dict[str, object]:
    raw = text.encode()
    return {"event": "step", "sequence": seq, "command": command,
            "raw_output_b64": base64.b64encode(raw).decode(),
            "input_boundary_reached": True, "timed_out": False, "error": None,
            "sent_bytes_b64": base64.b64encode((command + "\n").encode()).decode(),
            "intended_bytes_b64": base64.b64encode((command + "\n").encode()).decode()}


class BaselineTests(unittest.TestCase):
    def test_search_supports_neutral_goal_variants(self) -> None:
        start = initial_state()
        goals = (
            Goal(frozenset({("at", "player", "START")})),
            Goal(frozenset({("at", "player", "BUILDING")})),
            Goal(frozenset({("at", "player", "START"), ("lamp_off",)})),
        )
        for goal in goals:
            with self.subTest(goal=goal):
                result = uniform_cost_search(start, goal)
                self.assertEqual(result.status, "FOUND")
                final = start
                for action in result.plan:
                    final = action.apply(final)
                self.assertTrue(goal.satisfied(final))

    def test_search_distinguishes_budget_and_finite_exhaustion(self) -> None:
        goal = Goal(frozenset({("never",)}))
        budgeted = uniform_cost_search(initial_state(), goal,
                                       limits=SearchLimits(max_expansions=0, max_seconds=2))
        self.assertEqual(budgeted.status, "BUDGET")
        exhausted = uniform_cost_search(initial_state(), goal, operators=(),
                                        limits=SearchLimits(max_expansions=10, max_seconds=2))
        self.assertEqual(exhausted.status, "EXHAUSTED_FINITE_MODEL")

    def test_wave_operator_toggles_with_exclusive_preconditions(self) -> None:
        waves = [op for op in OPERATORS if op.name == "wave_rod"]
        self.assertTrue(any(("unbridged",) in op.preconditions and ("bridge",) in op.add_effects
                            and ("unbridged",) in op.delete_effects for op in waves))
        self.assertTrue(any(("bridge",) in op.preconditions and ("unbridged",) in op.add_effects
                            and ("bridge",) in op.delete_effects for op in waves))

    def test_reconciliation_does_not_apply_unconfirmed_prediction(self) -> None:
        state = initial_state()
        result = reconcile(state, "Nothing happens.", command="unlock grate")
        self.assertEqual(result.state, state)
        self.assertEqual(result.status, "NO_NEW_EVIDENCE")

    def test_known_cave_hint_is_declined_then_unlock_feedback_remains_mismatch(self) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, str]] = []

            def step(self, command: str, *, controller: str, decision_source: str) -> SimpleNamespace:
                self.calls.append((command, controller, decision_source))
                return SimpleNamespace(sequence=19, input_boundary_reached=True,
                                       observation="The hint response is recorded.")

        question = "You have no keys!\r\n\r\nAre   you trying to get into the cave?\r\n> "
        self.assertEqual(_native_question(question), "cave_hint_confirmation")
        session = FakeSession()
        answer = _decline_cave_hint(session)  # type: ignore[arg-type]
        self.assertEqual(session.calls[0][0], "n")
        self.assertTrue(answer.input_boundary_reached)

        stale_unlock = SimpleNamespace(name="unlock", args=("GRATE", ("carrying", "keys")))
        feedback = reconcile(initial_state(), "You have no keys!\r\n\r\nAre you trying to get into the cave?")
        self.assertFalse(_expected_action(stale_unlock, feedback))

    def test_verifier_rejects_historical_goal_prefix_after_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "events.jsonl"
            rows = [
                _row(1, "look", "You're below the grate. A small chamber beneath a 3x3 steel grate."),
                _row(2, "inventory", "You are currently holding the following:\nSet of keys\nBrass lantern\n"),
                _row(3, "west", "You're in cobble crawl."),
            ]
            ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertNotEqual(verify_ledger(ledger, "D")["status"], "PASS")

    def test_verifier_rejects_malformed_latest_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "events.jsonl"
            rows = [
                _row(1, "look", "You're below the grate. A small chamber beneath a 3x3 steel grate."),
                _row(2, "inventory", "You are currently holding the following:\nSet of keys\nBrass lantern\n"),
            ]
            rows.append({**_row(3, "look", "partial"), "raw_output_b64": "%%%"})
            ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertEqual(verify_ledger(ledger, "D")["status"], "INDETERMINATE")

    def test_verifier_accepts_only_fresh_complete_native_goal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "events.jsonl"
            rows = [
                _row(1, "on lamp", "Your lamp is now on."),
                _row(2, "look", "You're below the grate. A small chamber beneath a 3x3 steel grate."),
                _row(3, "inventory", "You are currently holding the following:\nSet of keys\nBrass lantern\n"),
            ]
            ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertEqual(verify_ledger(ledger, "D")["status"], "PASS")

    def test_verifier_rejects_death_even_if_reincarnated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "events.jsonl"
            rows = [_row(1, "look", "You have broken your neck. You are reincarnating."),
                    _row(2, "inventory", "You're not carrying anything.")]
            ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertEqual(verify_ledger(ledger, "D")["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
