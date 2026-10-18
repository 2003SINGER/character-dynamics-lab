import hashlib
import json
import tempfile
from types import SimpleNamespace
from unittest import mock
from pathlib import Path
import unittest

from tools.veloren_native_decision_v1.loaded_msg_pair import (
    EVENT_CHAIN, LoadedMsgChain, OnTrialPolicy, actor_view_is_fresh,
    assets_tree_sha256, follow_evidence, run_trial,
)


def request():
    return {"request_id": "hire-1", "target_uid": 475, "leader_uid": 476,
            "source": "character-dynamics-htn-v1"}


def base_event(event, **extra):
    row = {
        "event": event, "request_id": "hire-1", "source_uid": 476,
        "target_uid": 475, "leader_uid": 476, "recipient_uid": 475,
        "time": 50.0, "decision_source": "character-dynamics-htn-v1",
    }
    row.update(extra)
    return row


def complete_chain(chain):
    chain.register_request(request())
    chain.observe(base_event("native_recruit_request_accepted"))
    chain.observe(base_event("native_recruit_started"))
    chain.observe(base_event("native_recruit_message_sent"))
    for event in EVENT_CHAIN[:3]:
        chain.observe(base_event(event, msg_kind="RequestHire"))
    chain.observe(base_event(EVENT_CHAIN[3], hire_until="infinity"))
    return base_event(EVENT_CHAIN[4], job_actor_uid=476, hired_by_uid=476, hire_until="infinity",
                      leader_npc_id="NpcId(11)", recipient_npc_id="NpcId(19)")


class ProvenanceTests(unittest.TestCase):
    def test_message_sent_alone_never_confirms_hire(self):
        chain = LoadedMsgChain()
        chain.register_request(request())
        chain.observe(base_event("native_recruit_request_accepted"))
        chain.observe(base_event("native_recruit_started"))
        chain.observe(base_event("native_recruit_message_sent"))
        self.assertEqual(chain.trusted_hires, [])

    def test_complete_exact_message_effect_and_job_chain_confirms(self):
        chain = LoadedMsgChain()
        job = complete_chain(chain)
        self.assertEqual(chain.observe(job), job)
        self.assertEqual(len(chain.trusted_hires), 1)
        self.assertEqual(chain.violations, [])

    def test_job_without_recipient_consumption_and_effect_is_not_attributed(self):
        chain = LoadedMsgChain()
        chain.register_request(request())
        chain.observe(base_event("native_recruit_request_accepted"))
        chain.observe(base_event("native_recruit_started"))
        chain.observe(base_event("native_recruit_message_sent"))
        job = base_event("native_recruit_job_observed", job_actor_uid=476, hired_by_uid=476,
                         hire_until="infinity", leader_npc_id="NpcId(11)",
                         recipient_npc_id="NpcId(19)")
        self.assertIsNone(chain.observe(job))
        self.assertIn("job_observed_without_complete_message_effect_chain",
                      [row["reason"] for row in chain.violations])

    def test_receipt_with_wrong_recipient_or_changed_source_is_rejected(self):
        chain = LoadedMsgChain()
        chain.register_request(request())
        chain.observe(base_event("native_recruit_request_accepted"))
        chain.observe(base_event("native_recruit_started"))
        chain.observe(base_event("native_recruit_message_sent"))
        bad = base_event(EVENT_CHAIN[0], msg_kind="RequestHire", recipient_uid=999)
        chain.observe(bad)
        self.assertEqual(chain.trusted_hires, [])
        self.assertTrue(chain.violations)

    def test_duplicate_delivery_is_an_immediate_provenance_violation(self):
        chain = LoadedMsgChain()
        chain.register_request(request())
        chain.observe(base_event("native_recruit_request_accepted"))
        chain.observe(base_event("native_recruit_started"))
        chain.observe(base_event("native_recruit_message_sent"))
        chain.observe(base_event(EVENT_CHAIN[0], msg_kind="RequestHire"))
        delivered = base_event(EVENT_CHAIN[1], msg_kind="RequestHire")
        chain.observe(delivered)
        chain.observe(delivered)
        chain.observe(base_event(EVENT_CHAIN[2], msg_kind="RequestHire"))
        chain.observe(base_event(EVENT_CHAIN[3], hire_until="infinity"))
        chain.observe(base_event(EVENT_CHAIN[4], job_actor_uid=476, hired_by_uid=476,
                                 hire_until="infinity", leader_npc_id="NpcId(11)",
                                 recipient_npc_id="NpcId(19)"))
        self.assertIn("duplicate_message_provenance_stage",
                      [row["reason"] for row in chain.violations])
        self.assertEqual(chain.trusted_hires, [])


class RunPolicyTests(unittest.TestCase):
    def test_insufficient_choices_only_stops_after_prefix_and_stops_immediately(self):
        policy = OnTrialPolicy("on")
        self.assertFalse(policy.may_plan())
        policy.qualify_prefix()
        self.assertTrue(policy.may_plan())
        policy.record_planner_result("INSUFFICIENT_CHOICES")
        self.assertEqual(policy.stop_reason(1.0, 0.0), "insufficient_choices_after_qualified_prefix")
        self.assertFalse(policy.may_plan())

    def test_six_requests_is_a_hard_submission_cap(self):
        policy = OnTrialPolicy("on")
        policy.qualify_prefix()
        for _ in range(6):
            self.assertTrue(policy.may_plan())
            policy.record_planner_result("SOLVED_NEXT_SUBTASK", submitted=True)
        self.assertEqual(policy.request_count, 6)
        self.assertFalse(policy.may_plan())
        with self.assertRaises(RuntimeError):
            policy.record_planner_result("SOLVED_NEXT_SUBTASK", submitted=True)

    def test_first_trusted_hire_freezes_requests_and_right_censors_at_30_seconds(self):
        policy = OnTrialPolicy("on")
        policy.qualify_prefix()
        policy.trusted_hire(12.0)
        self.assertFalse(policy.may_plan())
        self.assertIsNone(policy.stop_reason(41.9, 0.0))
        self.assertEqual(policy.stop_reason(42.0, 0.0),
                         "first_trusted_hire_plus_30s_native_observation")

    def test_full_wall_cap_is_right_censor_not_a_success(self):
        policy = OnTrialPolicy("on")
        self.assertEqual(policy.stop_reason(360.0, 0.0), "trial_wall_cap")
        self.assertEqual(policy.request_count, 0)
        self.assertEqual(policy.first_trusted_hire_mono, None)

    def test_off_mode_never_plans(self):
        policy = OnTrialPolicy("off")
        self.assertFalse(policy.may_plan())

    def test_cached_actor_view_must_be_fresh_even_when_baselines_are_fresh(self):
        self.assertTrue(actor_view_is_fresh(10.0, 11.5))
        self.assertFalse(actor_view_is_fresh(10.0, 11.5001))


class MockRunLoopTests(unittest.TestCase):
    def test_stale_cached_view_cannot_plan_even_as_fresh_loaded_baselines_arrive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            userdata = root / "userdata"
            (userdata / "server").mkdir(parents=True)
            run_dir = root / "stale-view-run"
            binary, assets = root / "fake-server", root / "assets"
            binary.write_bytes(b"not executed")
            assets.mkdir()
            runtime = {"observe_npc_uids": [476, 475, 433],
                       "native_persister_npc_uids": [476, 475, 433],
                       "native_persister_view_distance_chunks": 8}

            native_batches = []
            for game_time in (1.0, 2.0, 3.0):
                native_batches.append([
                    {"event": "native_npc_baseline", "npc_uid": uid, "time": game_time,
                     "mode": "loaded", "alive": True,
                     "actual_world_state": {"ecs_position": [float(uid), 0.0, 0.0]}}
                    for uid in (476, 475, 433)
                ])
            stale_view = {"event": "native_recruit_actor_view", "version": 1, "time": 1.0,
                          "npc_uid": 476, "mode": "loaded",
                          "eligible_recruits": [
                              {"npc_uid": 475, "mode": "loaded"},
                              {"npc_uid": 433, "mode": "loaded"}]}

            class FakeTail:
                def __init__(self, path):
                    self.native = Path(path).name == "native-events.jsonl"
                    self.index, self.pending = 0, b""
                def read_rows(self):
                    if self.native and self.index < len(native_batches):
                        rows = native_batches[self.index]
                        self.index += 1
                        return rows
                    if not self.native and self.index == 0:
                        self.index += 1
                        return [stale_view]
                    return []

            class FakeServer:
                def __init__(self):
                    self.pid, self.returncode = 99124, None
                def poll(self):
                    return self.returncode
                def send_signal(self, _signal):
                    self.returncode = 0
                def wait(self, timeout=None):
                    self.returncode = 0
                    return 0

            clock = [0.0]
            def monotonic():
                clock[0] += 1.0
                return clock[0]

            with mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.JsonlTail", FakeTail), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.subprocess.Popen",
                            return_value=FakeServer()), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.time.monotonic",
                            side_effect=monotonic), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.time.sleep"), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.shutil.disk_usage",
                            return_value=SimpleNamespace(free=10 * 1024**3)):
                manifest = run_trial("on", binary, assets, userdata, run_dir, runtime)

            self.assertEqual(manifest["stop_reason"], "trial_wall_cap")
            self.assertEqual(manifest["request_rows_written"], 0)
            self.assertEqual((run_dir / "recruit-requests.jsonl").read_text(), "")
            self.assertNotIn("planner_proposal", (run_dir / "controller.jsonl").read_text())

    def test_run_loop_waits_for_prefix_locks_after_first_trusted_hire_and_stops_on_recipient_follow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            userdata = root / "userdata"
            (userdata / "server").mkdir(parents=True)
            run_dir = root / "on-run"
            binary, assets = root / "fake-server", root / "assets"
            binary.write_bytes(b"not executed")
            assets.mkdir()
            runtime = {
                "observe_npc_uids": [476, 475, 433], "native_persister_npc_uids": [476, 475, 433],
                "native_persister_view_distance_chunks": 8,
            }

            def baseline(uid, game_time, npc_id, position, backtrace=None, activity="Some(Goto)"):
                return {"event": "native_npc_baseline", "npc_uid": uid, "npc_id": npc_id,
                        "time": game_time, "mode": "loaded", "alive": True,
                        "brain_backtrace": backtrace or ["native idle"],
                        "controller_activity": activity,
                        "actual_world_state": {"ecs_position": position}}

            def view(game_time):
                return {"event": "native_recruit_actor_view", "version": 1, "time": game_time,
                        "npc_uid": 476, "mode": "loaded",
                        "role": {"kind": "civilised", "profession": "pirate", "is_leader": True},
                        "job": None, "home_site_id": "site", "current_site_id": "site",
                        "leader_at_home": True, "native_recruit_population_guard": True,
                        "native_recruit_raid_site_available": True, "hired_members": [],
                        "hired_member_count": 0, "eligible_recruits": [
                            {"npc_uid": 475, "distance_3d": 5.0, "mode": "loaded"},
                            {"npc_uid": 433, "distance_3d": 6.0, "mode": "loaded"}]}

            native_batches = []
            for game_time in (1.0, 2.0, 3.0):
                native_batches.append([
                    baseline(476, game_time, "NpcId(11)", [0, 0, 0]),
                    baseline(475, game_time, "NpcId(19)", [2, 0, 0]),
                    baseline(433, game_time, "NpcId(23)", [3, 0, 0]),
                ])
            trace = ["Hired by Actor::Npc(NpcId(11))",
                     "Following actor Actor::Npc(NpcId(11))"]
            native_batches.append([
                baseline(476, 14.0, "NpcId(11)", [0, 0, 0]),
                baseline(475, 14.0, "NpcId(19)", [3, 0, 0], trace),
                baseline(476, 15.0, "NpcId(11)", [0, 0, 0]),
                baseline(475, 15.0, "NpcId(19)", [4, 0, 0], trace),
            ])

            class FakeTail:
                instances = []
                def __init__(self, path):
                    self.path = Path(path)
                    self.rows = []
                    self.pending = b""
                    self.index = 0
                    self.kind = "native" if self.path.name == "native-events.jsonl" else "recruit"
                    self.instances.append(self)

                def read_rows(self):
                    if self.kind == "native":
                        if self.index < len(native_batches):
                            result = native_batches[self.index]
                            self.index += 1
                            return result
                        return []
                    if self.index < 3:
                        result = [view(float(self.index + 1))]
                        self.index += 1
                        return result
                    if self.index == 3:
                        self.index += 1
                        request_path = self.path.with_name("recruit-requests.jsonl")
                        req = json.loads(request_path.read_text().splitlines()[0])
                        rid, target = req["request_id"], req["target_uid"]
                        def event(name, t, **extra):
                            row = {"event": name, "request_id": rid, "source_uid": 476,
                                   "target_uid": target, "leader_uid": 476,
                                   "recipient_uid": target, "time": t,
                                   "decision_source": "character-dynamics-htn-v1"}
                            row.update(extra)
                            return row
                        rows = [
                            event("native_recruit_request_accepted", 10.0),
                            event("native_recruit_started", 10.1),
                            event("native_recruit_message_sent", 10.2),
                            event(EVENT_CHAIN[0], 10.3, msg_kind="RequestHire"),
                            event(EVENT_CHAIN[1], 10.4, msg_kind="RequestHire"),
                            event(EVENT_CHAIN[2], 10.5, msg_kind="RequestHire"),
                            event(EVENT_CHAIN[3], 10.6, hire_until="infinity"),
                            event(EVENT_CHAIN[4], 10.7, job_actor_uid=476, hired_by_uid=476,
                                  hire_until="infinity", leader_npc_id="NpcId(11)",
                                  recipient_npc_id="NpcId(19)"),
                            view(10.8),
                        ]
                        return rows
                    return []

            class FakeServer:
                def __init__(self):
                    self.pid, self.returncode = 99123, None
                def poll(self):
                    return self.returncode
                def send_signal(self, _signal):
                    self.returncode = 0
                def wait(self, timeout=None):
                    self.returncode = 0
                    return 0

            class FakeController:
                def __init__(self, mode, run_id, **_kwargs):
                    self.mode, self.run_id, self.pending = mode, run_id, None
                def feed(self, row):
                    if self.mode != "on" or row.get("event") != "native_recruit_actor_view":
                        return []
                    request_row = {"version": 1, "kind": "RecruitMember",
                                   "request_id": f"{self.run_id}-recruit-01",
                                   "source": "character-dynamics-htn-v1", "leader_uid": 476,
                                   "target_uid": 475, "observed_time": row["time"], "ttl_seconds": 60.0}
                    self.pending = request_row
                    return [{"event": "planner_proposal", "status": "SOLVED_NEXT_SUBTASK"},
                            {"event": "native_request_proposed", "request": request_row}]

            clock = [0.0]
            def monotonic():
                clock[0] += 1.0
                return clock[0]

            with mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.JsonlTail", FakeTail), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.RecruitmentController", FakeController), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.subprocess.Popen",
                            return_value=FakeServer()), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.time.monotonic",
                            side_effect=monotonic), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.time.sleep"), \
                 mock.patch("tools.veloren_native_decision_v1.loaded_msg_pair.shutil.disk_usage",
                            return_value=SimpleNamespace(free=10 * 1024**3)):
                manifest = run_trial("on", binary, assets, userdata, run_dir, runtime)

            self.assertEqual(manifest["request_rows_written"], 1)
            self.assertEqual(manifest["trusted_hire_count"], 1)
            self.assertEqual(manifest["stop_reason"], "recipient_native_follow_evidence_observed")
            self.assertEqual(manifest["follow_evidence"]["status"], "observed")
            self.assertEqual(manifest["server_exit_code"], 0)
            controller_rows = [json.loads(line) for line in (run_dir / "controller.jsonl").read_text().splitlines()]
            prefix_idx = next(i for i, row in enumerate(controller_rows)
                              if row["event"] == "loaded_native_prefix_satisfied")
            proposal_idx = next(i for i, row in enumerate(controller_rows)
                                if row["event"] == "planner_proposal")
            self.assertLess(prefix_idx, proposal_idx)
            self.assertEqual(len((run_dir / "recruit-requests.jsonl").read_text().splitlines()), 1)


class FollowEvidenceTests(unittest.TestCase):
    @staticmethod
    def row(game_time, pos, backtrace):
        return {"event": "native_npc_baseline", "npc_uid": 475, "time": game_time,
                "npc_id": "NpcId(19)", "mode": "loaded", "alive": True, "brain_backtrace": backtrace,
                "controller_activity": "Some(Goto)",
                "actual_world_state": {"ecs_position": pos}}

    @staticmethod
    def leader_mapping(game_time=5.0):
        return {"event": "native_npc_baseline", "npc_uid": 476, "npc_id": "NpcId(11)",
                "time": game_time, "mode": "loaded", "alive": True}

    def test_follow_requires_recipient_native_trace_targeting_job_receipt_leader_and_motion(self):
        trace = ["Hired by Actor::Npc(NpcId(11))", "Following actor Actor::Npc(NpcId(11))"]
        rows = [self.leader_mapping(), self.row(5.0, [1, 2, 3], trace), self.row(6.0, [2, 2, 3], trace)]
        result = follow_evidence(rows, 475, "NpcId(19)", "NpcId(11)", 4.0)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["horizontal_displacement_meters"], 1.0)

    def test_leader_side_trace_or_wrong_actor_does_not_count_as_member_follow(self):
        trace = ["Hired by Actor::Npc(NpcId(11))", "Following actor Actor::Npc(NpcId(11))"]
        rows = [self.leader_mapping(), self.row(5.0, [1, 2, 3], trace),
                {**self.row(6.0, [2, 2, 3], ["Hired by Actor::Npc(NpcId(11))",
                                             "Following actor Actor::Npc(NpcId(99))"]),
                 "npc_uid": 476}]
        result = follow_evidence(rows, 475, "NpcId(19)", "NpcId(11)", 4.0)
        self.assertEqual(result["status"], "not_observed")

    def test_pre_hire_and_vertical_only_motion_do_not_count_as_continuation(self):
        trace = ["Hired by Actor::Npc(NpcId(11))", "Following actor Actor::Npc(NpcId(11))"]
        pre_hire = self.row(4.0, [1, 2, 3], trace)
        after_hire = self.row(5.0, [1, 2, 3], trace)
        vertical = self.row(6.0, [1, 2, 4], trace)
        rows = [self.leader_mapping(), pre_hire, after_hire]
        self.assertEqual(follow_evidence(rows, 475, "NpcId(19)", "NpcId(11)", 4.5)["status"],
                         "not_observed")
        self.assertEqual(follow_evidence([self.leader_mapping(), after_hire, vertical], 475,
                                         "NpcId(19)", "NpcId(11)", 4.5)["status"],
                         "follow_task_without_horizontal_progress")

    def test_native_follow_brain_without_recipient_controller_execution_is_partial(self):
        trace = ["Hired by Actor::Npc(NpcId(11))", "Following actor Actor::Npc(NpcId(11))"]
        first, second = self.row(5.0, [1, 2, 3], trace), self.row(6.0, [2, 2, 3], trace)
        first["controller_activity"] = second["controller_activity"] = "Some(Idle)"
        self.assertEqual(follow_evidence([self.leader_mapping(), first, second], 475,
                                         "NpcId(19)", "NpcId(11)", 4.0)["status"],
                         "not_observed")


class AssetsManifestTests(unittest.TestCase):
    @staticmethod
    def _manifest(files):
        canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        return {"schema_version": "veloren-assets-tree-v1", "files": files,
                "tree_sha256": hashlib.sha256(canonical).hexdigest()}

    def test_exact_complete_assets_tree_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "assets"
            root.mkdir()
            payload = b"asset"
            (root / "one.bin").write_bytes(payload)
            rows = [{"path": "one.bin", "size_bytes": len(payload),
                     "sha256": hashlib.sha256(payload).hexdigest()}]
            manifest = self._manifest(rows)
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            self.assertEqual(assets_tree_sha256(root, manifest_path), manifest["tree_sha256"])

    def test_manifest_missing_or_extra_files_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "assets"
            root.mkdir()
            payload = b"asset"
            (root / "one.bin").write_bytes(payload)
            (root / "extra.bin").write_bytes(payload)
            rows = [{"path": "one.bin", "size_bytes": len(payload),
                     "sha256": hashlib.sha256(payload).hexdigest()}]
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(self._manifest(rows)))
            with self.assertRaisesRegex(ValueError, "exactly every actual file"):
                assets_tree_sha256(root, manifest_path)


if __name__ == "__main__":
    unittest.main()
