"""Source-level P4 note-response regressions using the isolated native runner."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from tools.native_platform_v0.p3 import p4_social


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "tools/native_platform_v0/ensemble/runner.mjs"
PINNED_HASHES = {
    "ensemble.js": "a29e66d87608726db4bbb7e432959659acb7e5b5ffb1428f37bfc31c94399c4e",
    "data/schema.json": "a8e0d5e7486676b993326cb09b58fc7845e43ac17c7cf62ae760fad17e29a335",
    "data/cast.json": "ff022e810853163a9f1248e3c139c1c500d81a983cd24e309783569d05076fa5",
    "data/triggerRules.json": "6e5e842517fc405f682e42b59504f18506fdda00b72ac40cfba622bbd351f4c2",
    "data/volitionRules.json": "be235331b0f7fb0dd580c6543b3f1ead659ff7cac2b9e87758a23df87cbf8d38",
    "data/actions.json": "ffee5331f4960214d89778b6175cd5235e6dfc30ca49daf6d60b1903584ce8b8",
    "data/history.json": "1864ccaa1d0fe9a76d17b365ca136e333d582bfced2f5be42845dda5b820d95b",
}


def run_native(messages):
    payload = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in messages)
    result = subprocess.run(["node", str(RUNNER)], input=payload, text=True,
                            capture_output=True, check=True, timeout=10)
    return [json.loads(line) for line in result.stdout.splitlines()]


class P4NativeSourceTests(unittest.TestCase):
    def test_pinned_example_files_match_source_hashes(self):
        manifest = p4_social.native_source_manifest()
        self.assertEqual(manifest["sha256"], PINNED_HASHES)
        self.assertFalse(manifest["initial_history_mutated"])

    def test_clean_history_drives_responder_owned_note_rejection(self):
        request_id = "p4:0:hero:note-request:episode1"
        request, response = run_native([
            {"op": "request_note", "requestId": request_id,
             "eventId": "p4:0:hero:note-source:episode1", "actor": "hero", "responder": "love"},
            {"op": "respond_note", "requestId": request_id,
             "eventId": "p4:0:love:note-response:episode1", "actor": "hero", "responder": "love"},
        ])
        self.assertEqual(request["status"], "PROPOSED")
        self.assertEqual(request["native_intent"]["weight"], 20)
        self.assertEqual(request["trace"]["calls"], ["calculateVolition"])
        self.assertFalse(request["trace"]["getActionsCalled"])
        self.assertTrue(request["socialRecordUnchanged"])
        self.assertEqual(response["status"], "PROPOSED")
        self.assertEqual(response["decision"], "rejected")
        self.assertEqual(response["selected"]["name"], "writeLoveNoteReject")
        self.assertEqual({row["name"] for row in response["native_candidates"]},
                         {"writeLoveNoteReject", "kissFail"})
        self.assertEqual(response["selection"]["supported_note_winning_tie_names"],
                         ["writeLoveNoteReject"])
        self.assertEqual(response["selection"]["unsupported_native_winners"], ["kissFail"])
        self.assertEqual(response["responderVolitions"][0]["first"], "love")
        self.assertEqual(response["responderVolitions"][0]["weight"], -10)
        self.assertEqual(response["trace"]["calls"], ["calculateVolition", "getActions"])
        self.assertFalse(response["trace"]["doActionCalled"])

    def test_one_way_initiator_closeness_does_not_override_responder_rejection(self):
        result, = run_native([{
            "op": "propose", "eventId": "one-way-initiator-closeness",
            "actor": "hero", "responder": "love",
            "facts": [{"category": "feeling", "type": "closeness", "first": "hero",
                       "second": "love", "value": 1}],
        }])
        self.assertEqual(result["volitions"][0]["weight"], 25)
        self.assertIn("writeLoveNoteReject", [row["name"] for row in result["actions"]])
        self.assertNotIn("writeLoveNoteAccept", [row["name"] for row in result["actions"]])

    def test_native_intelligence_fact_is_an_isolated_acceptance_contrast(self):
        result, = run_native([{
            "op": "propose", "eventId": "isolated-acceptance-contrast",
            "actor": "hero", "responder": "love",
            "facts": [{"category": "attribute", "type": "intelligence", "first": "hero", "value": 30}],
        }])
        names = [row["name"] for row in result["actions"]]
        self.assertIn("writeLoveNoteAccept", names)
        self.assertNotIn("writeLoveNoteReject", names)
        self.assertTrue(result["socialRecordUnchanged"])


class _Attributes:
    def __init__(self, values=None):
        self.values = {(category, key): value for category, key, value in (values or [])}

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class _Room:
    def __init__(self):
        self.contents = []
        self.id = 5


class _Actor:
    def __init__(self):
        self.id = 10
        self.attributes = _Attributes([
            ("native_p3", "activity_profile", "p4_story_v0"),
            ("native_p3", "mode", "b"), ("native_p3", "drive_mode", "manual"),
            ("native_p3", "scene_id", "s1"), ("native_p3", "scenario_seed", 0),
            ("native_p3", "task_item_id", 99), ("native_p3", "task_destination_id", 8),
            ("native_p3", "p3_social_target_id", 11),
            ("native_p3", "native_receipts", [{"kind": "drop", "settled": True,
                "item_id": 99, "after_item_room_id": 8}]),
            ("native_p3", "log", []),
            ("ensemble_bridge", "ensemble_character_id", "hero"),
        ])
        self.location = _Room()
        self.location.contents.append(self)


class _VisibleTarget:
    def __init__(self):
        self.id = 11
        self.location = None

    def access(self, _actor, _access_type, default=True):
        return default


class P4FailureHandlingTests(unittest.TestCase):
    def test_initiator_timeout_records_unavailable_without_note_reference_error(self):
        actor = _Actor()
        target = _VisibleTarget()
        actor.location.contents.append(target)

        class TimedOut:
            proc = type("Proc", (), {"poll": lambda self: None})()

            def request(self, _payload):
                raise TimeoutError("bounded test timeout")

        with patch.object(p4_social, "_client", return_value=TimedOut()):
            self.assertTrue(p4_social.step_social(actor))
        self.assertEqual(actor.attributes.get("p4_social_status", category="native_p3"), "UNAVAILABLE")
        self.assertTrue(actor.attributes.get("p4_social_attempted", category="native_p3"))
        self.assertIn("p4_social_request", [row["kind"] for row in actor.attributes.get("log", category="native_p3")])


class SceneProfileIsolationTests(unittest.TestCase):
    def test_legacy_b_keeps_two_characters_and_a_keeps_destination_marker(self):
        class Attrs:
            def __init__(self):
                self.rows = {}

            def add(self, key, value, category=None):
                self.rows[(category, key)] = value

        class Obj:
            next_id = 1

            def __init__(self, cls, **kwargs):
                self.typeclass = cls
                self.id = Obj.next_id
                Obj.next_id += 1
                self.dbref = f"#{self.id}"
                self.key = kwargs.get("key", "")
                self.location = kwargs.get("location")
                self.destination = kwargs.get("destination")
                self.contents = []
                self.exits = []
                self.attributes = Attrs()
                for key, value, category in kwargs.get("attributes", []):
                    self.attributes.add(key, value, category=category)
                if self.location is not None:
                    self.location.contents.append(self)
                if self.destination is not None:
                    self.location.exits.append(self)

        class Script:
            next_id = 1

            def __init__(self, _path, **kwargs):
                self.id = Script.next_id
                Script.next_id += 1

        class Character: pass
        class Exit: pass
        class Object: pass
        class Room: pass
        evennia = ModuleType("evennia")
        evennia.create_object = lambda cls, **kwargs: Obj(cls, **kwargs)
        evennia.create_script = lambda path, **kwargs: Script(path, **kwargs)
        typeclasses = ModuleType("typeclasses")
        typeclasses.__path__ = []
        modules = {"evennia": evennia, "typeclasses": typeclasses}
        for name, cls in (("characters", Character), ("exits", Exit), ("objects", Object), ("rooms", Room)):
            submodule = ModuleType(f"typeclasses.{name}")
            setattr(submodule, cls.__name__, cls)
            modules[f"typeclasses.{name}"] = submodule
        with patch.dict("sys.modules", modules):
            from tools.native_platform_v0.p3 import scene as scene_module

            owner = SimpleNamespace(account=SimpleNamespace(id=77))
            legacy_b = scene_module.create_scene(owner, mode="b", drive_mode="manual")
            self.assertIs(legacy_b["resident"].typeclass, Character)
            self.assertEqual(legacy_b["return_parcel"].attributes.rows[("native_p3", "p3_role")],
                             "resident_assigned_parcel")
            self.assertEqual(legacy_b["resident"].attributes.rows[("native_p3", "task_item_id")],
                             legacy_b["return_parcel"].id)
            legacy_a = scene_module.create_scene(owner, mode="a", drive_mode="manual")
            self.assertIs(legacy_a["resident"].typeclass, Object)
            self.assertEqual(legacy_a["resident"].attributes.rows[("native_p3", "p3_role")],
                             "delivery_destination_marker")


if __name__ == "__main__":
    unittest.main()
