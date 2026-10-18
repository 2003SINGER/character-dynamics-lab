import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.veloren_native_decision_v1.run_pair import (
    DISK_FLOOR_BYTES,
    TELEMETRY_BYTE_CAP,
    TELEMETRY_RECORD_CAP,
    CLEARED_INHERITED_ENV,
    JsonlTail,
    LoadedPrefixGate,
    validate_freeze,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JsonlTailTests(unittest.TestCase):
    def test_partial_line_is_retained_until_newline_arrives(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            path.write_bytes(b'{"event":"native_recruit_actor_')
            tail = JsonlTail(path)
            self.assertEqual(tail.read_rows(), [])
            with path.open("ab") as stream:
                stream.write(b'view","version":1}\n')
            self.assertEqual(tail.read_rows(), [{"event": "native_recruit_actor_view", "version": 1}])


class LoadedPrefixGateTests(unittest.TestCase):
    @staticmethod
    def baseline(uid, game_time, *, mode="loaded", position=True):
        return {
            "event": "native_npc_baseline", "npc_uid": uid, "time": game_time,
            "mode": mode, "alive": True, "brain_backtrace": ["native action"],
            "controller_activity": "Some(Goto)",
            "actual_world_state": {"ecs_position": [10.0 + uid, 20.0, 30.0] if position else None},
        }

    @staticmethod
    def view():
        return {"npc_uid": 476, "mode": "loaded", "eligible_recruits": [
            {"npc_uid": 475, "distance_3d": 4.0, "mode": "loaded"},
            {"npc_uid": 433, "distance_3d": 5.0, "mode": "loaded"},
            {"npc_uid": 450, "distance_3d": 7.0, "mode": "loaded"},
        ]}

    def test_requires_three_native_loaded_position_snapshots_over_two_wall_seconds(self):
        gate = LoadedPrefixGate()
        for game_time, wall_time in ((1.0, 0.0), (2.0, 1.0), (3.0, 2.1)):
            for uid in (476, 433, 450):
                gate.observe(self.baseline(uid, game_time), wall_time)
        result = gate.check(self.view(), 2.1)
        self.assertIsNotNone(result)
        self.assertEqual(result["loaded_candidate_uids"], [433, 450])
        self.assertEqual(len(result["distinct_game_times"]), 3)

    def test_simulated_or_missing_ecs_position_cannot_satisfy_prefix(self):
        gate = LoadedPrefixGate()
        for game_time, wall_time in ((1.0, 0.0), (2.0, 1.0), (3.0, 2.1)):
            for uid in (476, 433, 450):
                mode = "simulated" if uid == 433 else "loaded"
                position = uid != 450
                gate.observe(self.baseline(uid, game_time, mode=mode, position=position), wall_time)
        self.assertIsNone(gate.check(self.view(), 2.1))


class FreezeValidationTests(unittest.TestCase):
    def test_runner_clears_talk_and_userdata_override_environment(self):
        self.assertIn("VELOREN_NATIVE_REQUESTS", CLEARED_INHERITED_ENV)
        self.assertIn("VELOREN_RTSIM", CLEARED_INHERITED_ENV)
        self.assertIn("VELOREN_TERRAIN", CLEARED_INHERITED_ENV)
        self.assertIn("RTSIM_NOLOAD", CLEARED_INHERITED_ENV)

    def _freeze(self, root: Path) -> dict:
        source_dir = root / "source"
        source_dir.mkdir()
        patch = source_dir / "patch.diff"
        lock = source_dir / "Cargo.lock"
        binary = source_dir / "server-cli"
        assets = source_dir / "assets"
        assets.mkdir()
        for path, data in ((patch, b"reviewed source patch"), (lock, b"pinned lock"),
                           (binary, b"fixture binary; never executed")):
            path.write_bytes(data)

        trials = {}
        for mode in ("off", "on"):
            userdata = root / mode
            (userdata / "server").mkdir(parents=True)
            manifest_files = []
            for role, names in (("world", [f"world/input-{index}.bin" for index in range(6)]),
                                ("settings", ["server/settings.ron", "server/config.ron"])):
                for name in names:
                    path = userdata / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(f"{mode}:{name}".encode())
                    manifest_files.append({"path": name, "role": role,
                                           "size_bytes": path.stat().st_size,
                                           "sha256": digest(path)})
            manifest = userdata / "input-manifest.json"
            manifest.write_text(json.dumps({"schema_version": 1, "files": manifest_files}), encoding="utf-8")
            trials[mode] = {
                "userdata_path": str(userdata),
                "source_world_sha256": "a" * 64,
                "settings_contract_sha256": "b" * 64,
                "userdata_manifest_path": str(manifest),
                "userdata_manifest_sha256": digest(manifest),
            }

        return {
            "schema_version": 1,
            "source": {
                "commit": "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248",
                "source_patch_path": str(patch),
                "source_patch_sha256": digest(patch),
                "cargo_lock_path": str(lock),
                "cargo_lock_sha256": digest(lock),
                "binary_path": str(binary),
                "binary_sha256": digest(binary),
                "assets_path": str(assets),
            },
            "world": {
                "world_seed": 130626853,
                "source_world_sha256": "a" * 64,
                "settings_contract_sha256": "b" * 64,
            },
            "runtime": {
                "loopback_only": True,
                "query_address": None,
                "max_trial_wall_seconds": 360,
                "disk_free_floor_bytes": DISK_FLOOR_BYTES,
                "leader_uid": 476,
                "observe_npc_uids": [476, 433, 450, 451, 452, 459, 469, 472, 475],
                "native_persister_npc_uids": [476, 433, 450, 451, 452, 459, 469, 472, 475],
                "native_persister_view_distance_chunks": 8,
                "telemetry_record_cap": TELEMETRY_RECORD_CAP,
                "telemetry_byte_cap": TELEMETRY_BYTE_CAP,
                "telemetry_seconds_cap": 1800,
                "max_requests": 8,
                "request_ttl_seconds": 60,
                "loaded_prefix_min_game_times": 3,
                "loaded_prefix_min_wall_seconds": 2.0,
                "loaded_candidates_required": 2,
            },
            "trials": trials,
        }

    def test_pinned_inputs_and_independent_userdata_manifests_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            freeze = self._freeze(Path(temp))
            source, runtime, off, on = validate_freeze(freeze)
            self.assertEqual(source["commit"], "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248")
            self.assertEqual(runtime["leader_uid"], 476)
            self.assertNotEqual(off, on)

    def test_manifest_hash_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            freeze = self._freeze(Path(temp))
            freeze["trials"]["on"]["userdata_manifest_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "manifest does not match"):
                validate_freeze(freeze)

    def test_observer_lists_must_match_and_include_leader(self):
        with tempfile.TemporaryDirectory() as temp:
            freeze = self._freeze(Path(temp))
            freeze["runtime"]["native_persister_npc_uids"] = [433, 450]
            with self.assertRaisesRegex(ValueError, "include the configured leader"):
                validate_freeze(freeze)

    def test_world_payload_hash_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            freeze = self._freeze(Path(temp))
            manifest_path = Path(freeze["trials"]["on"]["userdata_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            first = manifest["files"][0]
            (manifest_path.parent / first["path"]).write_bytes(b"changed")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            freeze["trials"]["on"]["userdata_manifest_sha256"] = digest(manifest_path)
            with self.assertRaisesRegex(ValueError, "userdata input mismatch"):
                validate_freeze(freeze)

    def test_userdata_manifest_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as temp:
            freeze = self._freeze(Path(temp))
            manifest_path = Path(freeze["trials"]["on"]["userdata_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["path"] = "../outside.bin"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            freeze["trials"]["on"]["userdata_manifest_sha256"] = digest(manifest_path)
            with self.assertRaisesRegex(ValueError, "clean relative paths"):
                validate_freeze(freeze)


if __name__ == "__main__":
    unittest.main()
