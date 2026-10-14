from __future__ import annotations

from pathlib import Path
import json
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from tools.llm_admission_v0.audit import collect
from tools.llm_admission_v0.binding import compile_candidate, parse_candidate, validate_e
from tools.llm_admission_v0.packet import assert_lossless, shared_rules
from tools.open_adventure_planning_v0.search import Goal


def valid():
    return {"schema": "oa-author-binding-v0", "goal": {"required": [
        ["at", "player", "WESTBANK"], ["bridge"], ["carrying", "keys"],
        ["carrying", "lamp"], ["lamp_on"]], "forbidden": []},
        "trajectory_obligations": [{"kind": "no_death_ever", "hard": True}],
        "bindings": [{"capability_sources": ["movement", "rod", "items", "lamp"]}],
        "residual_obligations": []}


class AdmissionTests(unittest.TestCase):
    def test_full_rule_export_round_trip(self):
        packet = shared_rules()
        assert_lossless(packet)
        self.assertEqual(packet["ground_operator_count"], 326)
        packet["operator_groups"].pop()
        with self.assertRaises(ValueError): assert_lossless(packet)

    def test_exact_json_only(self):
        for raw in ('```json\n{}\n```', '{"schema":"oa-author-binding-v0","schema":"oa-author-binding-v0"}', '[]'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, json.JSONDecodeError)):
                parse_candidate(raw)
        self.assertEqual(parse_candidate(json.dumps(valid())), valid())

    def test_every_original_atom_required_no_controller_fill(self):
        for i in range(5):
            candidate = valid()
            candidate["goal"]["required"].pop(i)
            report = validate_e(candidate)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["controller_added_atoms"], [])
        self.assertEqual(validate_e(valid())["status"], "PASS")

    def test_survival_separate_and_hard_residual_blocks(self):
        candidate = valid()
        candidate["trajectory_obligations"] = []
        self.assertEqual(validate_e(candidate)["status"], "FAIL")
        candidate = valid()
        candidate["residual_obligations"] = [{"hard": True, "requirement_text": "unknown"}]
        self.assertEqual(validate_e(candidate)["status"], "FAIL")

    def test_unknown_predicate_and_source_rejected(self):
        candidate = valid()
        candidate["goal"]["required"].append(["trust", "pirate"])
        with self.assertRaises(ValueError): compile_candidate(candidate)
        candidate = valid()
        candidate["bindings"][0]["capability_sources"] = ["magic"]
        self.assertEqual(validate_e(candidate)["status"], "FAIL")

    def test_extra_hard_route_constraint_rejected(self):
        candidate = valid()
        candidate["goal"]["required"].append(["carrying", "rod"])
        self.assertEqual(validate_e(candidate)["status"], "FAIL")

    def test_actual_external_goal_reaches_frozen_search(self):
        from tools.open_adventure_planning_v0 import execute as ex
        class SearchReached(Exception): pass
        with tempfile.TemporaryDirectory() as tmp:
            class Session:
                run_dir = Path(tmp)
                log_path = Path(tmp) / "events.jsonl"
                _initial_input_boundary = True
                _initial_timed_out = False
                def reset(self, config): self.config = config; return ""
                def step(self, *a, **k):
                    return SimpleNamespace(input_boundary_reached=True, error=None, timed_out=False, observation="", sequence=1)
                def close(self): pass
            session = Session()
            external = Goal(frozenset({("at", "player", "BUILDING")}))
            with patch.object(ex, "OpenAdventureSession", return_value=session), patch.object(ex, "uniform_cost_search", side_effect=SearchReached) as search:
                with self.assertRaises(SearchReached):
                    ex.run_episode("E", scenario="clean", execute_native=True, external_goal=external)
            self.assertIs(search.call_args.args[1], external)
            self.assertEqual(session.config["goal_origin"], "external_validated_candidate")

    def test_invalid_candidate_never_executes(self):
        from tools.llm_admission_v0.binding import execute_validated
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.txt"
            candidate = valid(); candidate["goal"]["required"].pop()
            path.write_text(json.dumps(candidate))
            with patch("tools.open_adventure_planning_v0.execute.run_episode") as run:
                with self.assertRaises(ValueError): execute_validated(path)
                run.assert_not_called()

    def test_runtime_final_phase_and_private_context_filter(self):
        rows = [{"type": "session_meta", "payload": {"id": "fixture", "agent_path": "/root/test"}},
                {"type": "turn_context", "payload": {"model": "gpt-6-luna", "effort": "medium"}},
                {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"text": "PRIVATE_AGENTS_CONTENT"}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "assistant", "phase": "final_answer", "content": [{"text": "{\"unaltered\":true}"}]}}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            out = Path(tmp) / "out"
            report = collect(path, "/root/test", out)
            self.assertEqual(report["classification"], "AGENT_CONFOUNDED")
            self.assertEqual((out / "response.raw.txt").read_text(), '{"unaltered":true}')
            self.assertNotIn("PRIVATE_AGENTS_CONTENT", (out / "audit.json").read_text())
            rows.append({"type": "response_item", "payload": {"type": "function_call", "name": "exec", "arguments": "{}"}})
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            self.assertEqual(collect(path, "/root/test", Path(tmp) / "leak")["classification"], "INVALID_LEAKAGE")

    def test_frozen_implementation_not_replaced(self):
        root = Path(__file__).resolve().parents[3]
        # SHA256 from git-show 90ee524; runnable in a shallow CI checkout.
        frozen = {
            "domain.py": "0791a68dbcc1543a299b24327188c1341e4489fb961d7740f3acc45e8a85294b",
            "search.py": "3de2c4d6fff56f2462f3a17d88aa8d2c6266c8ca84e320b8301460c99937dcfe",
            "observe.py": "e490e3441a7537061f900332e020f8bc587faef622c9f24139bab6e017242a7c",
            "verify.py": "d4ec863ca0b05722a05c94323e4782a8a00a801e108c0882078c20c9f30fbba2",
        }
        for name, expected in frozen.items():
            rel = "tools/open_adventure_planning_v0/" + name
            self.assertEqual(hashlib.sha256((root / rel).read_bytes()).hexdigest(), expected)

    def test_recorded_model_failure_is_not_repaired(self):
        root = Path(__file__).resolve().parents[3]
        raw = root / "02_实验/LLM_Admission_v0/calls/e/response.raw.txt"
        candidate = parse_candidate(raw.read_text())
        report = validate_e(candidate)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["missing_atoms"], [("bridge",)])
        self.assertEqual(report["controller_added_atoms"], [])


if __name__ == "__main__": unittest.main()
