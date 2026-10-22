from __future__ import annotations

import json
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.character_dynamics_online_v0.author_cli import (
    _read_jsonl, append_author_command, build_rally_command, main, read_run_snapshot,
)
from tools.character_dynamics_online_v0.contracts import ContractError
from tools.character_dynamics_online_v0.process_controller import new_process_session, step_process
from tools.character_dynamics_online_v0.process_runner import parse_author_input


def _jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")


class AuthorCliTests(unittest.TestCase):
    def _live_run(self, root: Path, *, external: bool = True):
        run_dir = root / "run"
        run_dir.mkdir()
        session = new_process_session([433, 476], goal_specs=[])
        _jsonl(run_dir / "session-checkpoints.jsonl", [
            {"event": "session_start", "game_time": 1.0, "session": session},
        ])
        _jsonl(run_dir / "decisions.jsonl", [
            {"event": "controller_decision", "game_time": 31.5,
             "actor_view_times": {"433": 31.4, "476": 31.45},
             "decision": {"sequence": 4,
                          "plans": [{"plan_key": "live-plan"}],
                          "author_obligations": [{"goal_id": "live-goal", "status": "PENDING"}],
                          "feedback_applied": []}},
        ])
        leader_view = {
            "event": "g1_actor_view", "actor_uid": 476, "time": 31.45,
            "markers": [{"marker_id": "recon_site_a", "label": "A"},
                        {"marker_id": "recon_site_b", "label": "B"}],
            "nearby": [{"uid": 442, "hired_by_uid": 476}],
        }
        stale_view = {**leader_view, "time": 20.0,
                      "markers": [{"marker_id": "stale-marker", "label": "stale"}],
                      "nearby": []}
        _jsonl(run_dir / "native-events.jsonl", [stale_view])
        _jsonl(run_dir / "g1-events.jsonl", [leader_view])
        _jsonl(run_dir / "status.jsonl", [{"event": "process_started"}])
        _jsonl(run_dir / "author-versions.jsonl", [])
        internal = run_dir / "author-input.jsonl"
        internal.touch()
        external_path = root / "operator-input.jsonl"
        if external:
            external_path.write_text("seed-record\n", encoding="utf-8")
        return run_dir, external_path, session

    def test_show_snapshot_uses_live_decision_and_native_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, input_path, _ = self._live_run(Path(tmp))
            snapshot = read_run_snapshot(run_dir, input_path)
            self.assertEqual(snapshot["run_state"], "RUNNING")
            self.assertEqual(snapshot["latest_game_time"], 31.5)
            self.assertEqual(snapshot["latest_observation_times"], {"433": 31.4, "476": 31.45})
            self.assertEqual(set(snapshot["known_markers"]), {"recon_site_a", "recon_site_b"})
            self.assertIn(442, snapshot["known_follower_uids"])
            self.assertEqual(snapshot["display_plans"], [{"plan_key": "live-plan"}])
            self.assertEqual(snapshot["display_author_obligations"][0]["goal_id"], "live-goal")

    def test_show_sections_are_compact_and_meet_alias_maps_to_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, input_path, _ = self._live_run(Path(tmp))
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["--run-dir", str(run_dir), "show", "--section", "plans"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue()), {"plans": [{"plan_key": "live-plan"}]})

            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["--run-dir", str(run_dir), "--author-input", str(input_path),
                             "append-meet", "--goal-id", "g-meet", "--actor-uid", "476",
                             "--marker", "A", "--follower-uid", "442", "--deadline", "100"])
            self.assertEqual(code, 0, output.getvalue())
            command = json.loads(input_path.read_text(encoding="utf-8").splitlines()[1])["command"]
            self.assertEqual(command["op"], "append")
            self.assertEqual(command["version"], 1)

    def test_typed_rally_appends_agent_provenance_without_overwriting_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, input_path, _ = self._live_run(Path(tmp))
            snapshot = read_run_snapshot(run_dir, input_path)
            command = build_rally_command(snapshot, op="append", goal_id="g2", actor_uid=476,
                                          marker="B", follower_uid=442, deadline=100.0)
            command["_issued_at_game_time"] = snapshot["latest_game_time"]
            row = append_author_command(run_dir, command, input_path=input_path,
                                        local_time="2026-10-22T12:00:00+08:00")
            lines = input_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "seed-record")
            payload = json.loads(lines[1])
            self.assertEqual(payload["source"], "AGENT_OPERATOR")
            self.assertEqual(payload["operator_kind"], "agent")
            self.assertEqual(payload["issued_at_game_time"], 31.5)
            self.assertEqual(payload["issued_local_time"], "2026-10-22T12:00:00+08:00")
            self.assertEqual(payload["command"]["ast"]["event"]["args"],
                             [476, "recon_site_b", 442])
            self.assertEqual(set(payload["command"]),
                             {"op", "goal_id", "version", "actor_uid", "ast"})
            self.assertEqual(row["source"], "AGENT_OPERATOR")

    def test_cli_append_round_trips_runner_parser_into_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, input_path, session = self._live_run(Path(tmp))
            input_path.write_text('{"seed":true}\n', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["--run-dir", str(run_dir), "--author-input", str(input_path),
                             "append-rally", "--goal-id", "g-roundtrip", "--actor-uid", "476",
                             "--marker", "B", "--follower-uid", "442", "--deadline", "100"])
            self.assertEqual(code, 0, output.getvalue())
            external_row = _read_jsonl(input_path)[1]
            parsed, error = parse_author_input(external_row, external_operator_mode=True,
                                               session=session)
            self.assertIsNone(error)
            self.assertEqual(set(parsed), {"op", "goal_id", "version", "actor_uid", "ast"})

            event_fact = {"predicate": "event:g1_rally_completed",
                          "args": [476, "recon_site_b", 442]}
            action_model = {
                "primitive": "rally_marker",
                "args": {"marker_id": "recon_site_b", "follower_uid": 442},
                "preconditions": [], "dispatch_preconditions": [],
                "effects": [event_fact], "estimated_cost": 1.0,
                "provenance": {"source": "test-native-catalog", "rule_version": "recon-v1"},
            }
            observations = {
                "schema": "character_dynamics_g1_observation_v0", "game_time": 31.5,
                "actors": [
                    {"actor_uid": 433, "observation_id": "roundtrip-scout", "facts": [], "action_models": []},
                    {"actor_uid": 476, "observation_id": "roundtrip-leader", "facts": [],
                     "action_models": [action_model]},
                ], "world_facts": [], "event_coverage_through": None,
            }
            result = step_process(session, observations, game_time=31.5, author_commands=[parsed])
            self.assertEqual(result["session"]["author_obligations"]["g-roundtrip"]["versions"][0]["version"], 1)
            self.assertEqual(result["decision"]["author_obligations"][0]["goal_id"], "g-roundtrip")
            self.assertEqual(result["decision"]["author_commands_applied"][0]["version"], 1)

    def test_marker_actor_and_follower_must_be_currently_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, input_path, _ = self._live_run(Path(tmp))
            snapshot = read_run_snapshot(run_dir, input_path)
            for args in (
                {"op": "append", "goal_id": "bad-marker", "actor_uid": 476,
                 "marker": "unseen", "follower_uid": 442, "deadline": 100.0},
                {"op": "append", "goal_id": "bad-actor", "actor_uid": 99,
                 "marker": "A", "follower_uid": 442, "deadline": 100.0},
                {"op": "append", "goal_id": "bad-follower", "actor_uid": 476,
                 "marker": "A", "follower_uid": 999, "deadline": 100.0},
            ):
                with self.assertRaises(ContractError):
                    build_rally_command(snapshot, **args)

    def test_missing_or_unstarted_run_does_not_create_or_claim_author_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            for name in ("session-checkpoints.jsonl", "decisions.jsonl", "native-events.jsonl",
                         "status.jsonl", "author-versions.jsonl"):
                (run_dir / name).touch()
            snapshot = read_run_snapshot(run_dir)
            self.assertEqual(snapshot["run_state"], "NOT_STARTED")
            self.assertIsNone(snapshot["latest_game_time"])
            self.assertIsNone(snapshot["session"])
            self.assertFalse((run_dir / "author-input.jsonl").exists())
            with self.assertRaises(ContractError):
                build_rally_command(snapshot, op="append", goal_id="g", actor_uid=476,
                                    marker="A", follower_uid=442, deadline=10.0)
            with self.assertRaises(ContractError):
                append_author_command(run_dir, {"op": "append"})
            self.assertFalse((run_dir / "author-input.jsonl").exists())

    def test_jsonl_reader_ignores_only_unterminated_partial_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            path.write_text('{"ok":1}\n{"partial":', encoding="utf-8")
            self.assertEqual(_read_jsonl(path), [{"ok": 1}])
            path.write_text('{"ok":1}\nnot-json\n', encoding="utf-8")
            with self.assertRaises(ContractError):
                _read_jsonl(path)

    def test_append_requires_real_observation_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, input_path, _ = self._live_run(Path(tmp))
            with self.assertRaises(ContractError):
                append_author_command(run_dir, {"op": "append"}, input_path=input_path)
            self.assertEqual(input_path.read_text(encoding="utf-8"), "seed-record\n")


if __name__ == "__main__":
    unittest.main()
