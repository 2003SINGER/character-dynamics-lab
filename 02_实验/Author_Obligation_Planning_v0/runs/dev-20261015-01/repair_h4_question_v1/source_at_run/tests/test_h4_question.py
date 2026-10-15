from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.open_adventure_v0.session import StepResult
from tools.author_obligation_planning_v0 import native
from tools.open_adventure_planning_v0.domain import initial_state
from tools.author_obligation_planning_v0.tasks import task_by_id


CAPTURED_H4_UNLOCK_FEEDBACK = (
    "You have no keys!\nAre you trying to get into the cave?"
)


def receipt(sequence, command, observation):
    raw = observation.encode("utf-8")
    return StepResult(
        episode_id="saved-h4-regression", sequence=sequence, command=command,
        intended_bytes=command.encode() + b"\n", sent_bytes=command.encode() + b"\n",
        before_observation="", raw_output=raw, observation=observation,
        input_boundary_reached=True, terminated=False, exit_code=None,
        timed_out=False, error=None,
    )


class MockSession:
    def __init__(self):
        self.commands = []
        self.rows = iter((
            receipt(15, "n", "No."),
            receipt(16, "look", "Fresh room view."),
            receipt(17, "inventory", "Fresh inventory view."),
        ))

    def step(self, command, **_kwargs):
        self.commands.append(command)
        row = next(self.rows)
        if command != row.command:
            raise AssertionError(f"expected {row.command}, got {command}")
        return row


class H4QuestionRegression(unittest.TestCase):
    def test_answer_known_question_before_fresh_state_reads(self):
        task_case = task_by_id("H4")
        task = task_case.task
        state = initial_state()
        unlock = receipt(14, "unlock grate", CAPTURED_H4_UNLOCK_FEEDBACK)
        session = MockSession()

        trace = Path("mock-trace.jsonl")
        rows = []

        def record_receipt(_path, row, *, input_count, role, delivered):
            rows.append({"event": "native_receipt_reference",
                         "sequence": row.sequence, "command": row.command,
                         "input_count": input_count, "role": role,
                         "delivered_to_strategy": delivered,
                         "raw_output_b64": "captured-by-mock"})

        record_receipt(trace, unlock, input_count=6,
                       role="h4_stale_planned_unlock", delivered=False)
        rows.append({
                "event": "h4_actual_unlock_feedback", "sequence": 14,
                "observation": unlock.observation,
                "rejection_text_observed": True,
            })

        def fake_reconcile(current, _observation, *, command, complete):
            self.assertTrue(complete)
            return SimpleNamespace(status="OK", state=current,
                                   evidence=("fresh-native-evidence",),
                                   observed_room=None)

        with (patch.object(native, "reconcile", side_effect=fake_reconcile),
              patch.object(native, "_append_receipt", side_effect=record_receipt),
              patch.object(native, "_append_jsonl",
                           side_effect=lambda _path, row: rows.append(row))):
                final_state, inputs, error = native._h4_refresh_after_feedback(
                    session, task=task, history=[], trace_path=trace,
                    state=state, unlock=unlock, task_inputs=6,
                )

        self.assertEqual(session.commands, ["n", "look", "inventory"])
        self.assertEqual(inputs, 9)  # 6 prior inputs + n/look/inventory.
        self.assertIsNone(error)
        self.assertEqual(final_state, state)

        rejection = next(row for row in rows
                         if row.get("event") == "h4_actual_unlock_feedback")
        self.assertEqual(rejection["observation"], CAPTURED_H4_UNLOCK_FEEDBACK)
        self.assertTrue(rejection["rejection_text_observed"])
        receipts = [row for row in rows
                    if row.get("event") == "native_receipt_reference"]
        self.assertEqual([row["sequence"] for row in receipts], [14, 15, 16, 17])
        self.assertEqual([row["command"] for row in receipts],
                         ["unlock grate", "n", "look", "inventory"])
        self.assertFalse(receipts[0]["delivered_to_strategy"])
        self.assertTrue(all(row["delivered_to_strategy"] for row in receipts[1:]))


if __name__ == "__main__":
    unittest.main()
