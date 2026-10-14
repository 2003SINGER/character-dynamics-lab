from __future__ import annotations

import base64
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.author_constraint_diagnostic_v0.contracts import (
    Constraint, author_constraints, retire_plan, obligation_phase,
)
from tools.author_constraint_diagnostic_v0.monitor import inspect_rows, inspect_ledger
from tools.open_adventure_planning_v0.verify import verify_ledger
from tools.open_adventure_planning_v0.search import SearchResult


def receipt(seq, command, text):
    raw = base64.b64encode(text.encode()).decode()
    sent = base64.b64encode((command + "\n").encode()).decode()
    return {"event": "step", "sequence": seq, "command": command, "raw_output_b64": raw,
            "input_boundary_reached": True, "timed_out": False, "error": None,
            "sent_bytes_b64": sent, "intended_bytes_b64": sent}


def synthetic(*, vanish=False):
    init = {"event": "initial_observation", "sequence": 0,
            "raw_b64": base64.b64encode(b"Welcome to Adventure!! > ").decode(),
            "complete": True, "input_boundary_reached": True, "timed_out": False, "error": None}
    steps = [("on lamp", "Your lamp is now on."),
             ("wave rod", "A crystal bridge now spans the fissure."),
             ("over", "You're on west bank of fissure.")]
    if vanish: steps.append(("wave rod", "The crystal bridge has vanished!"))
    steps.extend((("look", "You're on west bank of fissure." + ("\nA crystal bridge spans the fissure." if not vanish else "")),
                  ("inventory", "You are currently holding the following:\nSet of keys\nBrass lantern\n\n")))
    return [init] + [receipt(i, c, t) for i, (c, t) in enumerate(steps, 1)] + [
        {"event": "close", "terminated": True, "error": None}]


class DiagnosticTests(unittest.TestCase):
    def test_temporal_success_from_native_shape(self):
        result = inspect_rows(synthetic(), ended=True)
        self.assertEqual(result["status"], "PASS")
        self.assertLess(result["bridge_created_sequences"][0], result["west_arrival_sequences"][0])

    def test_history_creation_not_final_bridge_and_old_gate_unchanged(self):
        rows = synthetic(vanish=True)
        self.assertEqual(inspect_rows(rows, ended=True)["status"], "PASS")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synthetic_not_native.jsonl"
            p.write_text("".join(json.dumps(r) + "\n" for r in rows))
            self.assertEqual(verify_ledger(p, "E")["status"], "FAIL")

    def test_visible_span_is_not_creation_and_arrival_order_matters(self):
        rows = synthetic()
        rows[2] = receipt(2, "look", "A crystal bridge spans the fissure.")
        self.assertEqual(inspect_rows(rows, ended=True)["obligations"]["author-build-bridge"], "FAIL")
        rows = synthetic()
        rows[2], rows[3] = receipt(2, "over", "You're on west bank of fissure."), receipt(3, "wave rod", "A crystal bridge now spans the fissure.")
        self.assertEqual(inspect_rows(rows, ended=True)["obligations"]["author-build-before-arrival"], "FAIL")

    def test_missing_corrupt_unsealed_receipt_is_unknown(self):
        variants = []
        rows = synthetic(); rows.pop(2); variants.append(rows)
        rows = synthetic(); rows[2]["raw_output_b64"] = "%%%"; variants.append(rows)
        rows = synthetic(); rows.pop(); variants.append(rows)
        for rows in variants:
            with self.subTest(rows=rows):
                result = inspect_rows(rows, ended=True)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertNotEqual(result["obligations"]["author-no-death"], "PASS")

    def test_known_death_fails_even_after_reincarnation(self):
        rows = synthetic()
        rows[1] = receipt(1, "on lamp", "Oh dear, you seem to have gotten yourself killed. You are reincarnating. Your lamp is now on.")
        self.assertEqual(inspect_rows(rows, ended=True)["status"], "FAIL")
        self.assertEqual(inspect_rows(rows, ended=True)["obligations"]["author-no-death"], "FAIL")

    def test_running_no_death_only_pending(self):
        result = inspect_rows(synthetic()[:-1], ended=False)
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual(result["obligations"]["author-no-death"], "PENDING")

    def test_unrecognized_bridge_or_final_room_feedback_is_unknown(self):
        rows = synthetic()
        rows[2] = receipt(2, "wave rod", "Something glimmers, but the result is unclear.")
        self.assertEqual(inspect_rows(rows, ended=True)["obligations"]["author-build-bridge"], "UNKNOWN")
        rows = synthetic()
        rows[-3] = receipt(4, "look", "Your position cannot be determined.")
        self.assertEqual(inspect_rows(rows, ended=True)["obligations"]["author-arrive-west"], "UNKNOWN")

    def test_retire_plan_preserves_author_game_and_executed_witness(self):
        author = author_constraints()
        future = Constraint("future", "PLANNER", "PLAN_DEPENDENCY", "BEFORE", ("bridge",), "model", plan_id="old")
        past = replace(future, id="past", status="PASS", witness_sequences=(2,))
        other = replace(future, id="other", plan_id="new")
        game = Constraint("law", "GAME", "MUST", "BEFORE", ("bridge",), "native")
        rows = retire_plan(author + (future, past, other, game), "old")
        self.assertEqual(rows[:len(author)], author)
        self.assertEqual(rows[-4].status, "CANCELLED")
        self.assertEqual(rows[-3], past)
        self.assertEqual(rows[-2], other)
        self.assertEqual(rows[-1], game)
        self.assertEqual(rows[-3].witness_sequences, (2,))

    def test_pending_verification_distinct_from_unsupported_and_unverifiable(self):
        pending = obligation_phase(capability=True, monitor=True, ended=False, verdict="UNKNOWN")
        absent = obligation_phase(capability=False, monitor=False, ended=False, verdict="UNKNOWN")
        unverified = obligation_phase(capability=True, monitor=False, ended=False, verdict="UNKNOWN")
        self.assertEqual(pending, {"binding": "BOUND", "verification": "PENDING"})
        self.assertEqual(absent["binding"], "UNSUPPORTED_CAPABILITY")
        self.assertEqual(unverified["binding"], "BOUND_BUT_UNVERIFIABLE")

    def test_actual_four_atom_input_and_budget_stops_without_native(self):
        from tools.author_constraint_diagnostic_v0 import run
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUT", Path(tmp)), patch.object(run, "protected_hashes", return_value={}):
            budget = SearchResult("BUDGET", (), 10000, 0, 0, 1, 0.01, "expansion_limit")
            with patch.object(run, "uniform_cost_search", return_value=budget) as ucs, patch.object(run, "run_episode") as native:
                result = run.run_once(execute_native=True)
                self.assertEqual(result["search"], "BUDGET")
                native.assert_not_called()
                self.assertEqual(ucs.call_count, 1)
                goal = ucs.call_args.args[1]
                self.assertEqual(len(goal.required), 4)
                self.assertNotIn(("bridge",), goal.required)
                input_record = json.loads((Path(tmp) / "execution/input.json").read_text())
                self.assertEqual(input_record["controller_added_atoms"], [])
                with self.assertRaises(FileExistsError): run.run_once(execute_native=True)
                self.assertEqual(ucs.call_count, 1)

    def test_unreadable_or_non_object_ledger_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "invalid.jsonl"
            p.write_text("[]\n")
            self.assertEqual(inspect_ledger(p, ended=True)["status"], "UNKNOWN")

    def test_protected_unicode_paths_are_nul_delimited(self):
        from tools.author_constraint_diagnostic_v0 import run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "中文.md").write_bytes(b"frozen")
            with patch.object(run, "ROOT", root), patch.object(run.subprocess, "check_output", side_effect=["中文.md\0".encode(), b"frozen"]) as git:
                self.assertIn("中文.md", run.protected_hashes())
                self.assertIn("-z", git.call_args_list[0].args[0])


if __name__ == "__main__": unittest.main()
