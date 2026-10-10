import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest.mock import patch
from collections.abc import Mapping, Sequence

from tools.native_platform_v0.p5 import world
from tools.trajectory_constraints_v0.trace import Event, Point, Trace
from tools.trajectory_constraints_v0.types import Owner, StableEntity, ValueRef


class Attrs:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class SaverMapping(Mapping):
    """Evennia-like nested mapping that is not a built-in dict."""
    def __init__(self, values):
        self.values = dict(values)

    def __getitem__(self, key):
        return self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)


class SaverSequence(Sequence):
    """Evennia-like nested list that is not a built-in list."""
    def __init__(self, values):
        self.values = tuple(values)

    def __getitem__(self, index):
        return self.values[index]

    def __len__(self):
        return len(self.values)


class FakeRoom:
    def __init__(self, ident):
        self.id = ident
        self.exits = []


class FakeExit:
    def __init__(self, ident, key, source, destination, scene_id):
        self.id, self.key, self.location, self.destination = ident, key, source, destination
        self.attributes = Attrs({("native_p3", "p3_scene_id"): scene_id,
                                 ("native_p5", "p5_route_id"): "side_passage"})
        source.exits.append(self)

    def access(self, actor, access_type, default=False):
        return True


class FakeObject:
    def __init__(self, ident, attrs):
        self.id = ident
        self.attributes = Attrs(attrs)
        self.contents = []
        self.exits = []


class FakeActor(FakeObject):
    def __init__(self):
        super().__init__(9, {("native_p3", "activity_profile"): "p5_story_v0",
                             ("native_p3", "status"): "RUNNING",
                             ("native_p3", "tick_count"): 0,
                             ("native_p3", "log"): [],
                             ("native_p3", "pending_action"): None,
                             ("native_p3", "native_receipts"): []})
        self.ndb = SimpleNamespace(p3_pending_operation_id=None)


class P5AdapterTests(unittest.TestCase):
    def test_persisted_saver_containers_are_recursively_normalized_before_strict_load(self):
        from tools.native_platform_v0.p5.bundle import BundleError, load_bundle
        from tools.native_platform_v0.p5.service import _bundle_for, _stable_entities
        from tools.native_platform_v0.p5.tests.test_p5_bundle import sample

        def saver(value):
            if isinstance(value, dict):
                return SaverMapping({key: saver(item) for key, item in value.items()})
            if isinstance(value, list):
                return SaverSequence(saver(item) for item in value)
            return value

        pickup = FakeObject(1, {("native_p5", "p5_active_bundle"): saver(sample()),
                                ("native_p5", "p5_entities"): saver(_stable_entities())})
        restored = _bundle_for(pickup)
        self.assertEqual(restored.bundle_id, "story-1")
        self.assertEqual(restored.constraints[0].event_type, "p5_note_response")
        with self.assertRaises(BundleError) as raised:
            load_bundle(saver(sample()))
        self.assertEqual(raised.exception.code, "INVALID_SCHEMA")

    def test_p5_scene_marker_uses_the_p4_world_owner_category(self):
        pickup = FakeObject(1, {("native_p5", "p5_scene_id"): "scene"})
        with patch("tools.native_platform_v0.p3.p4_world.pickup_for_scene", return_value=(pickup, [])):
            with self.assertRaisesRegex(ValueError, "not marked"):
                world.scene_objects("scene")
        pickup.attributes.add("p5_scene_id", "scene", category="native_p3")
        with patch("tools.native_platform_v0.p3.p4_world.pickup_for_scene", return_value=(pickup, [])):
            self.assertEqual(world.scene_objects("scene"), (pickup, []))

    def test_side_route_resolves_both_directions_and_three_room_topology(self):
        scene_id = "route-scene"
        pickup, side, destination = FakeRoom(1), FakeRoom(2), FakeRoom(3)
        attrs = {("native_p3", "p4_destination_id"): destination.id,
                 ("native_p5", "p5_scene_id"): scene_id,
                 ("native_p5", "p5_side_room_id"): side.id}
        pickup.attributes = Attrs(attrs)
        rows = [pickup, side, destination]
        edges = [FakeExit(11, "south", pickup, side, scene_id),
                 FakeExit(12, "north", side, pickup, scene_id),
                 FakeExit(13, "east", side, destination, scene_id),
                 FakeExit(14, "south", destination, side, scene_id)]
        with patch.object(world, "scene_objects", return_value=(pickup, rows)):
            self.assertEqual(world.route_edges(scene_id, "side_passage"), edges)

    def test_typed_trace_serializer_preserves_seal_and_stable_aliases(self):
        trace = Trace(scenario_start=Fraction(0), now=Fraction(1))
        actor = StableEntity("Actor", "A")
        item = StableEntity("Item", "note")
        trace.add_event(Event("e1", "p5_note_response", 1, 4,
                              {"actor": actor, "item": item, "response": "accepted"}))
        ref = ValueRef("p5_route_open", "p5-world-v1", {"route": "main_passage"}, Owner.WORLD)
        trace.add_point(Point(ref, 0, False, source="world_snapshot_projector"))
        trace.seal_events_through(1)
        trace.seal_values_through(ref, 0)
        encoded = world.serialize_typed_trace(trace)
        self.assertEqual(encoded["events"][0]["args"]["actor"],
                         {"entity_type": "Actor", "stable_id": "A"})
        self.assertEqual(encoded["events_sealed_through"], "1")
        self.assertEqual(encoded["points"][0]["value"], False)
        # Repeated refs have unhashable mapping args but share one stable key.
        trace.add_point(Point(ref, 1, True, source="world_snapshot_projector"))
        self.assertEqual(len(world.serialize_typed_trace(trace)["value_frontiers"]), 1)

    def test_edit_evidence_keeps_full_ledger_rows_and_pending_intent(self):
        from tools.native_platform_v0.p5.service import _ledger_prefix, _pending_identity

        ledger = [{"event_id": "e1", "event_type": "typed",
                   "minute": 0, "sequence": 2,
                   "typed_args": {"actor": "A", "response": "accepted"},
                   "provenance": "committed_ledger"}]
        actor = FakeActor()
        actor.attributes.add("pending_action", {
            "status": "planned", "operation_id": "op-7", "planned_at_tick": 4,
            "intent": {"operator": "move", "exit_key": "east", "destination_id": 3}},
            category="native_p3")
        pickup = FakeObject(1, {("native_p3", "p4_ledger"): ledger})
        prefix = _ledger_prefix(pickup, 1)
        self.assertEqual(prefix[0]["typed_args"]["response"], "accepted")
        mutated = [{**ledger[0], "typed_args": {"actor": "A", "response": "rejected"}}]
        pickup.attributes.add("p4_ledger", mutated, category="native_p3")
        self.assertNotEqual(prefix, _ledger_prefix(pickup, 1))
        pending = _pending_identity(actor)
        self.assertEqual(pending["operation_id"], "op-7")
        self.assertEqual(pending["planned_at_tick"], 4)
        self.assertEqual(pending["intent"]["exit_key"], "east")

    def test_reset_preserves_bundle_semantic_gap_without_creating_world_objects(self):
        from tools.native_platform_v0.p5.bundle import BundleError
        from tools.native_platform_v0.p5.service import reset_p5_scenario

        with (patch("tools.native_platform_v0.p5.service.load_bundle",
                    side_effect=BundleError("SEMANTIC_GAP", "unregistered event",
                                            details={"event": "unregistered"})),
              patch.dict("sys.modules", {"evennia": None})):
            result = reset_p5_scenario(owner=None, bundle={})
        self.assertEqual(result, {"ok": False, "scene_created": False,
                                  "error": {"code": "SEMANTIC_GAP",
                                            "details": {"event": "unregistered"}}})

    def test_typed_projection_seals_only_complete_snapshot_prefix(self):
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES

        scene_id = "sealed-prefix"
        pickup = FakeObject(1, {
            ("native_p3", "p5_scene_id"): scene_id,
            ("native_p3", "p4_clock"): {"now": 1},
            ("native_p3", "p4_ledger"): [],
            ("native_p3", "p5_event_coverage_minute"): 1,
            ("native_p3", "p5_completed_minutes"): [0, 1],
            ("native_p5", "p5_snapshot_coverage_minute"): 1,
            ("native_p5", "p5_world_snapshots"): [{
                "minute": 0, "holders": {},
                "routes": {"main_passage": True, "side_passage": False}}],
        })
        actors = [FakeObject(11, {("native_p3", "activity_profile"): "p5_story_v0",
                                  ("native_p5", "p5_actor_alias"): "A",
                                  ("native_p3", "native_receipts"): []}),
                  FakeObject(12, {("native_p3", "activity_profile"): "p5_story_v0",
                                  ("native_p5", "p5_actor_alias"): "B",
                                  ("native_p3", "native_receipts"): []})]
        with (patch.object(world, "scene_objects", return_value=(pickup, [pickup, *actors])),
              patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                    return_value={"now": 1, "deadline": 24})):
            with self.assertRaisesRegex(ValueError, "gap in its declared complete snapshot prefix"):
                world.build_typed_trace(scene_id, object(), DEFAULT_ENTITIES)

    def test_unknown_local_route_falls_back_to_visible_exit_without_replacing_delivery(self):
        from tools.native_platform_v0.p5 import agency

        actor = FakeActor()
        local_view = {"activity_contract": {"profile": "p5_story_v0"},
                      "observation": {"room_id": 1, "task_item": {"id": 17},
                                      "task_destination": 3, "item_location": 1,
                                      "item_held": False,
                                      "visible_items": [{"id": 17}],
                                      "exits": [{"key": "south", "destination_id": 2,
                                                 "traversable": True}]}}
        decision = {"view": local_view,
                    "goal": {"goal": "deliver_supply", "choice": "deliver_supply",
                             "status": "ACTIVE", "delivery_status": "ACTIVE",
                             "candidates": ["deliver_supply", "patrol"],
                             "reason": "delivery remains active"},
                    "planner": {"status": "NO_PLAN", "reason": "no route under local view"},
                    "intent": None}
        with (patch.object(agency.world, "assert_p5_actor", return_value="p5-scene"),
              patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                    return_value={"now": 1, "deadline": 24, "unit": "simulated-minute"}),
              patch("tools.native_platform_v0.p3.p4_social.step_social", return_value=False),
              patch("tools.native_platform_v0.p3.p4_agency.make_decision", return_value=decision)):
            agency.step_actor(actor)
        pending = actor.attributes.get("pending_action", category="native_p3")
        self.assertEqual(pending["intent"], {"operator": "move", "exit_key": "south",
                                               "destination_id": 2})
        self.assertEqual(pending["goal"]["goal"], "deliver_supply")
        self.assertEqual(pending["goal"]["delivery_status"], "UNKNOWN_LOCAL_ROUTE")
        self.assertIn("no route under local view", pending["goal"]["delivery_reason"])

    def test_no_plan_with_no_locally_traversable_route_waits_and_budget_does_not_explore(self):
        from tools.native_platform_v0.p5 import agency

        actor = FakeActor()
        local_view = {"activity_contract": {"profile": "p5_story_v0"},
                      "observation": {"room_id": 1, "task_item": {"id": 17},
                                      "task_destination": 3, "item_location": 1,
                                      "item_held": False, "visible_items": [{"id": 17}],
                                      "exits": [{"key": "east", "destination_id": 3,
                                                 "traversable": False}]}}
        goal = {"goal": "deliver_supply", "choice": "deliver_supply", "status": "ACTIVE",
                "delivery_status": "ACTIVE", "candidates": ["deliver_supply", "patrol"]}
        decision = {"view": local_view, "goal": goal,
                    "planner": {"status": "NO_PLAN", "reason": "no local path"}, "intent": None}
        with (patch.object(agency.world, "assert_p5_actor", return_value="p5-scene"),
              patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                    return_value={"now": 1, "deadline": 24, "unit": "simulated-minute"}),
              patch("tools.native_platform_v0.p3.p4_social.step_social", return_value=False),
              patch("tools.native_platform_v0.p3.p4_agency.make_decision", return_value=decision)):
            agency.step_actor(actor)
        self.assertIsNone(actor.attributes.get("pending_action", category="native_p3"))
        self.assertEqual(actor.attributes.get("status", category="native_p3"), "PATROL_WAITING")

        actor = FakeActor()
        budgeted = {**decision, "planner": {"status": "BUDGET", "reason": "watchdog"}}
        with (patch.object(agency.world, "assert_p5_actor", return_value="p5-scene"),
              patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                    return_value={"now": 1, "deadline": 24, "unit": "simulated-minute"}),
              patch("tools.native_platform_v0.p3.p4_social.step_social", return_value=False),
              patch("tools.native_platform_v0.p3.p4_agency.make_decision", return_value=budgeted)):
            agency.step_actor(actor)
        self.assertIsNone(actor.attributes.get("pending_action", category="native_p3"))
        self.assertEqual(actor.attributes.get("status", category="native_p3"), "BLOCKED")


if __name__ == "__main__":
    unittest.main()
