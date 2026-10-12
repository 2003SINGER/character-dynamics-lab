import copy
import hashlib
import json
import unittest
from collections.abc import MutableMapping, MutableSequence
from unittest.mock import patch

from tools.native_platform_v0.p5.story_process.actor import _local_choice_accepts, step_story_task
from tools.native_platform_v0.p5.story_process.model import load_request
from tools.native_platform_v0.p5.story_process.native import apply_story_decision
from tools.native_platform_v0.p5.story_process.planning import plan_story_process
from tools.native_platform_v0.p5.tests.test_story_process_planning import raw_request, sealed_state


class Attrs:
    def __init__(self, **values):
        self.values = values

    def get(self, key, category=None, default=None):
        return self.values.get(key, default)

    def add(self, key, value, category=None):
        self.values[key] = value


class FakeObject:
    def __init__(self, object_id, **values):
        self.id = object_id
        self.attributes = Attrs(**values)


class FakeRoom:
    def __init__(self, object_id):
        self.id = object_id
        self.contents = []
        self.exits = []


class FakeExit:
    def __init__(self, key, source, destination):
        self.key, self.location, self.destination = key, source, destination
        source.exits.append(self)

    def access(self, actor, access_type, default=True):
        return True


class FakeStoryActor(FakeObject):
    def __init__(self, object_id, alias, location, task=None):
        super().__init__(object_id, p5_actor_alias=alias,
                         p5_story_task=task or {"request_id": "handover-1", "task_kind": "handover_note",
                                                "status": "IN_PROGRESS", "item_id": 701,
                                                "destination_id": 12, "recipient_id": 23})
        self.dbref = f"#{object_id}"
        self.location = location
        self.contents = []
        self.location.contents.append(self)

    def execute_cmd(self, command):
        if command != "north":
            raise AssertionError(f"unexpected command: {command}")
        self.location.contents.remove(self)
        self.location = self.location.exits[0].destination
        self.location.contents.append(self)


class FakeStoryItem(FakeObject):
    def __init__(self, object_id, location):
        super().__init__(object_id)
        self.key = "exact note"
        self.location = location

    def access(self, actor, access_type, default=True):
        return True


class SaverMap(MutableMapping):
    """Attribute-like Mapping wrapper, deliberately not a built-in dict."""
    def __init__(self, values=()):
        self.values = dict(values)

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def __delitem__(self, key):
        del self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)


class SaverSequence(MutableSequence):
    """Attribute-like MutableSequence wrapper, deliberately not a built-in list."""
    def __init__(self, values=()):
        self.values = list(values)

    def __getitem__(self, index):
        return self.values[index]

    def __setitem__(self, index, value):
        self.values[index] = value

    def __delitem__(self, index):
        del self.values[index]

    def __len__(self):
        return len(self.values)

    def insert(self, index, value):
        self.values.insert(index, value)


class NativeStoryProcessTests(unittest.TestCase):
    @staticmethod
    def _saver(value):
        if isinstance(value, dict):
            return SaverMap({key: NativeStoryProcessTests._saver(item) for key, item in value.items()})
        if isinstance(value, list):
            return SaverSequence(NativeStoryProcessTests._saver(item) for item in value)
        return value

    def test_twisted_handover_callback_routes_when_recipient_is_not_colocated(self):
        from tools.native_platform_v0.p5.story_process import actor as story_actor

        current, target = FakeRoom(11), FakeRoom(12)
        FakeExit("north", current, target)
        actor = FakeStoryActor(22, "B", current)
        item = FakeStoryItem(701, actor)
        actor.contents.append(item)
        recipient = FakeObject(23, p5_actor_alias="A")
        recipient.contents = []
        recipient.location = target
        target.contents.append(recipient)

        # The recipient is known to the task but absent from B's current room.
        with patch("tools.native_platform_v0.p3.p4_world.clock_for_actor", return_value={"now": 19}):
            deferred = step_story_task(actor)

        self.assertTrue(deferred.called)
        result = deferred.result
        self.assertEqual(result["native_action"], "move")
        self.assertEqual(result["receipt"]["submitted_command"], "north")
        self.assertTrue(result["receipt"]["settled"])
        self.assertIs(actor.location, target)
        self.assertIn(item, actor.contents)
        self.assertNotIn(item, recipient.contents)
        self.assertNotEqual(result["native_action"], "give")

    def test_archive_actor_without_note_moves_one_native_edge_toward_rendezvous(self):
        current, transit, rendezvous = FakeRoom(11), FakeRoom(12), FakeRoom(13)
        FakeExit("north", current, transit)
        FakeExit("east", transit, rendezvous)
        task = {"request_id": "archive-a", "task_kind": "archive_note", "status": "ACCEPTED",
                "item_id": 701, "destination_id": 30, "rendezvous_destination_id": 13}
        actor = FakeStoryActor(22, "A", current, task=task)
        actor.attributes.add("p5_story_known_exits", {
            "12": [{"key": "east", "destination_id": 13, "traversable": True}]}, category="native_p5")

        with patch("tools.native_platform_v0.p3.p4_world.clock_for_actor", return_value={"now": 20}):
            deferred = step_story_task(actor)

        self.assertTrue(deferred.called)
        result = deferred.result
        self.assertEqual(result["native_action"], "move")
        self.assertTrue(result["settled"])
        self.assertIs(actor.location, transit)
        self.assertEqual(result["receipt"]["item_id"], None)
        self.assertEqual(result["receipt"]["action_destination_id"], 13)
        self.assertEqual(result["receipt"]["destination_id"], 30)
        self.assertEqual(result["receipt"]["submitted_command"], "north")
        self.assertEqual(actor.attributes.get("p5_story_task")["status"], "IN_PROGRESS")
        self.assertEqual(actor.attributes.get("p5_story_receipts")[0]["item_id"], None)

    def test_existing_pending_action_keeps_priority_over_rendezvous_offer(self):
        from tools.native_platform_v0.p5.story_process.actor import step_story_aware_actor

        current, rendezvous = FakeRoom(11), FakeRoom(12)
        FakeExit("north", current, rendezvous)
        actor = FakeStoryActor(22, "A", current,
                               task={"request_id": "old", "task_kind": "archive_note", "status": "SETTLED",
                                     "item_id": 701, "destination_id": 30})
        actor.attributes.add("pending_action", {"status": "planned"}, category="native_p3")
        actor.attributes.add("p5_story_offer", {
            "request_id": "archive-a", "task_kind": "archive_note", "proposal_status": "OFFERED_TO_ACTOR",
            "item_id": 701, "destination_id": 30, "rendezvous_destination_id": 12}, category="native_p5")
        sentinel = {"old_action": "kept"}

        with patch("tools.native_platform_v0.p5.agency.step_actor", return_value=sentinel) as legacy:
            deferred = step_story_aware_actor(actor)

        self.assertTrue(deferred.called)
        self.assertIs(deferred.result, sentinel)
        legacy.assert_called_once_with(actor)
        self.assertIs(actor.location, current)
        self.assertEqual(actor.attributes.get("p5_story_task")["status"], "SETTLED")

    def test_strict_request_roundtrips_from_abc_attribute_wrappers(self):
        def saver(value):
            if isinstance(value, dict):
                return SaverMap({key: saver(item) for key, item in value.items()})
            if isinstance(value, list):
                return SaverSequence(saver(item) for item in value)
            return value

        from tools.native_platform_v0.p5.service import _plain_json
        request_raw = raw_request(mode="result_only", scenario_id="scene", note_id=None)
        wrapped = saver(request_raw)
        self.assertIsInstance(wrapped["control"]["allowed_methods"], MutableSequence)
        self.assertNotIsInstance(wrapped["control"]["allowed_methods"], list)
        normalized = _plain_json(wrapped)
        self.assertIs(type(normalized["control"]["allowed_methods"]), list)
        request = load_request(normalized)
        self.assertIsNone(request.objective["note_id"])

    def test_actual_evennia_saver_classes_when_django_is_configured(self):
        try:
            from django.conf import settings
        except ImportError:
            self.skipTest("Django is not installed in this test environment")
        if not settings.configured:
            self.skipTest("real Evennia saver classes require the configured native Django environment")
        from evennia.utils.dbserialize import _SaverDict, _SaverList

        def saver(value):
            if isinstance(value, dict):
                wrapped = _SaverDict()
                wrapped._data.update({key: saver(item) for key, item in value.items()})
                return wrapped
            if isinstance(value, list):
                wrapped = _SaverList()
                wrapped._data.extend(saver(item) for item in value)
                return wrapped
            return value

        from tools.native_platform_v0.p5.service import _plain_json
        wrapped = saver(raw_request(mode="result_only", scenario_id="scene", note_id=None))
        wrapped_methods = wrapped["control"]["allowed_methods"]
        self.assertFalse(isinstance(wrapped_methods, list))
        self.assertTrue(isinstance(wrapped_methods, MutableSequence))
        self.assertEqual(list(wrapped_methods), ["file_by_B", "return_then_file_by_A"])
        request = load_request(_plain_json(wrapped))
        self.assertIsNone(request.objective["note_id"])

    def test_local_choice_defers_first_archive_offer_then_uses_local_conditions(self):
        actor = FakeObject(8, pending_action=None, p5_story_local_choice_history=[])
        first = {"request_id": "req:first", "task_kind": "archive_note", "deadline_minute": 24}
        accepted, reason = _local_choice_accepts(actor, first, 18, object())
        self.assertFalse(accepted)
        self.assertEqual(reason, "episode_local_choice_defers_first_archive_offer")
        self.assertEqual(actor.attributes.get("p5_story_local_choice_history")[0]["request_id"], "req:first")
        second = {"request_id": "req:repair", "task_kind": "archive_note", "deadline_minute": 24}
        accepted, reason = _local_choice_accepts(actor, second, 19, object())
        self.assertTrue(accepted)
        self.assertIsNone(reason)

    def test_result_only_native_apply_stores_planner_offer_not_effect(self):
        request = load_request(raw_request(mode="result_only", note_id=777))
        state = sealed_state(request, now=17, outcome="accepted", holder="B")
        decision = plan_story_process(request, state, strategy="event_driven")
        pickup = FakeObject(1, p5_story_request=copy.deepcopy(dict(request.raw)),
                           p5_story_meta={"controller_decisions": []})
        actors = [FakeObject(2, p5_actor_alias="A"), FakeObject(3, p5_actor_alias="B")]

        def scene_objects(_scene_id):
            return pickup, actors

        with patch("tools.native_platform_v0.p5.service._scene_objects", scene_objects):
            result = apply_story_decision(request.scenario_id, state, decision)

        self.assertFalse(result["effects_claimed"])
        self.assertTrue(result["queued_task_requests"])
        self.assertTrue(all(row["proposal_status"] == "OFFERED_TO_ACTOR"
                            for row in result["queued_task_requests"]))
        self.assertTrue(all(actor.attributes.get("p5_story_task") is None for actor in actors))

    def test_return_method_applies_only_registered_rendezvous_to_A_archive_offer(self):
        request = load_request(raw_request(mode="result_only", note_id=777,
                                           methods=["return_then_file_by_A"]))
        state = sealed_state(request, now=17, outcome="accepted", holder="B")
        decision = plan_story_process(request, state, strategy="event_driven")
        a = FakeObject(2, p5_actor_alias="A")
        b = FakeObject(3, p5_actor_alias="B")
        pickup = FakeObject(1, p5_story_request=copy.deepcopy(dict(request.raw)),
                           p5_story_meta={"controller_decisions": []})

        with patch("tools.native_platform_v0.p5.service._scene_objects", return_value=(pickup, [a, b])):
            result = apply_story_decision(request.scenario_id, state, decision)

        a_offer = a.attributes.get("p5_story_offer")
        self.assertEqual(result["effects_claimed"], False)
        self.assertEqual(a_offer["task_kind"], "archive_note")
        self.assertEqual(a_offer["destination_id"], state["destinations"]["archive"]["id"])
        self.assertEqual(a_offer["rendezvous_destination_id"], state["destinations"]["handover"]["id"])

        bad_decision = copy.deepcopy(decision)
        a_request = next(row for row in bad_decision["task_requests"] if row["actor_alias"] == "A")
        a_request["rendezvous_destination_id"] += 1
        with patch("tools.native_platform_v0.p5.service._scene_objects", return_value=(pickup, [a, b])):
            with self.assertRaisesRegex(ValueError, "registered handover destination"):
                apply_story_decision(request.scenario_id, state, bad_decision)

    def test_first_locked_controller_event_persists_from_saver_metadata(self):
        from tools.native_platform_v0.p5.story_process.native import apply_story_decision

        raw = raw_request(mode="locked_fragment", scenario_id="scene-meta", note_id=777)
        sequence = [{"actor_alias": "B", "task_kind": "archive_note",
                     "item_ref": "objective.note", "destination_ref": "archive"}]
        raw["locked_fragment"] = {
            "sequence": sequence,
            "sequence_sha256": hashlib.sha256(json.dumps(
                sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "entry_guard": {"response_required": True, "note_holder_alias": "A"},
            "abort_policy": "ABORT_LOCKED_CORE",
        }
        pickup = FakeObject(1, p5_story_request=raw,
                           p5_story_meta=self._saver({"controller_decisions": []}))
        a, b = FakeObject(2, p5_actor_alias="A"), FakeObject(3, p5_actor_alias="B")
        state = sealed_state(load_request(raw), now=17, outcome="accepted", holder="B")
        decision = {"schema": "story-process-decision-v1", "sealed_minute": 17,
                    "target_version": 1, "status": "LOCKED_ABORTED", "task_requests": [],
                    "outstanding_obligations": [{"kind": "locked_entry_guard", "status": "BLOCKED"}]}

        with patch("tools.native_platform_v0.p5.service._scene_objects", return_value=(pickup, [a, b])):
            result = apply_story_decision("scene-meta", state, decision)

        meta = pickup.attributes.get("p5_story_meta")
        self.assertEqual(len(meta["controller_events"]), 1)
        self.assertEqual(meta["controller_events"][0]["event_type"], "P5_STORY_LOCKED_FRAGMENT_ABORTED")
        self.assertEqual(result["controller_events"][0]["event_id"], meta["controller_events"][0]["event_id"])

    def test_first_stale_request_id_persists_from_saver_metadata_on_edit(self):
        from tools.native_platform_v0.p5.story_process.native import edit_story_request

        previous = raw_request(mode="result_only", scenario_id="scene-meta", note_id=777)
        updated = raw_request(mode="result_only", scenario_id="scene-meta", note_id=777, version=2)
        pickup = FakeObject(1, p5_story_request=previous,
                           p5_story_meta=self._saver({"controller_decisions": []}))
        a = FakeObject(2, p5_actor_alias="A", p5_story_offer={"request_id": "old:A"})
        b = FakeObject(3, p5_actor_alias="B", p5_story_offer=None)

        with patch("tools.native_platform_v0.p5.service._scene_objects", return_value=(pickup, [a, b])):
            result = edit_story_request("scene-meta", updated, expected_version=1)

        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(pickup.attributes.get("p5_story_meta")["stale_future_request_ids"], ["old:A"])
        self.assertIsNone(a.attributes.get("p5_story_offer"))


if __name__ == "__main__":
    unittest.main()
