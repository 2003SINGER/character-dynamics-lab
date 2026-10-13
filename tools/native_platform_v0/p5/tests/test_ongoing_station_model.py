import copy
from hashlib import sha256
import json
import unittest

from tools.native_platform_v0.p5.ongoing_station.model import (
    AUTHOR_SCHEMA, PROFILE_SCHEMA, compile_projection, load_profile,
    station_work_entity_catalog,
)


def profile(author=None, horizon=24):
    return {"schema": PROFILE_SCHEMA, "station_id": "station-1", "profile_version": 1,
            "horizon": horizon, "author": author}


def author():
    bundle = {"schema": "native-author-bundle-v1", "bundle_id": "station-author-1",
              "version": 1, "source": "station-fixture", "constraints": [
                  {"id": "archive-goal", "kind": "event_by_deadline", "event": "note_archived",
                   "filters": {"item": "note"}, "start": 0, "deadline": 24, "hard": True},
                  {"id": "response-before-archive", "kind": "event_order",
                   "before": {"event": "note_response", "filters": {"item": "note"}},
                   "after": {"event": "note_archived", "filters": {"item": "note"}},
                   "order": "EVENT_KEY", "start": 0, "deadline": 24, "hard": True}],
              "branches": [], "permissions": {"world_opportunities": [],
                  "force_npc_response": False, "max_opportunities": 1, "cost_budget": 0}}
    binding = lambda cid: {"constraint_id": cid,
                           "control": {"mode": "result_only", "file_actor": None,
                                       "allowed_methods": ["file_by_B", "return_then_file_by_A"],
                                       "source": "SYSTEM"}, "locked_fragment": None}
    return {"schema": AUTHOR_SCHEMA, "bundle": bundle,
            "bindings": [binding("archive-goal"), binding("response-before-archive")]}


class OngoingStationModelTests(unittest.TestCase):
    def test_null_author_still_enables_valid_profile_and_preserves_explicit_horizon(self):
        value = load_profile(profile())
        self.assertEqual(value.horizon, 24)
        self.assertIsNone(value.author)
        self.assertEqual(load_profile(profile(horizon=48)).horizon, 48)

    def test_station_work_profile_is_explicit_and_unknown_content_fails_closed(self):
        from tools.native_platform_v0.p5.bundle import BundleError, load_bundle
        value = profile()
        value["game_content"] = "station_work_v1"
        self.assertEqual(load_profile(value).game_content, "station_work_v1")
        value["game_content"] = "other"
        with self.assertRaisesRegex(ValueError, "game_content"):
            load_profile(value)
        station_event = {"schema": "native-author-bundle-v1", "bundle_id": "station-work",
                         "version": 1, "source": "test", "constraints": [{
                             "id": "repair", "kind": "event_by_deadline",
                             "event": "station_passage_repaired",
                             "filters": {"actor": "B", "tool": "station_tool",
                                         "exit": "pickup_to_side_south"},
                             "start": 0, "deadline": 24, "hard": True}],
                         "branches": [], "permissions": {"world_opportunities": [],
                             "force_npc_response": False, "max_opportunities": 1, "cost_budget": 0}}
        with self.assertRaises(BundleError):
            load_bundle(station_event)

    def test_station_work_projection_uses_registered_events_and_existing_order_dsl(self):
        work_events = [
            ("inspect", "station_supply_inspected",
             {"actor": "A", "item": "courier_supply", "tool": "station_tool"}),
            ("repair", "station_passage_repaired",
             {"actor": "B", "tool": "station_tool", "exit": "pickup_to_side_south"}),
            ("store", "station_supply_stored",
             {"actor": "A", "item": "courier_supply", "storage": "station_storage"}),
        ]
        constraints = [{"id": cid, "kind": "event_by_deadline", "event": event,
                        "filters": filters, "start": 0, "deadline": 24, "hard": True}
                       for cid, event, filters in work_events]
        constraints.append({"id": "repair-before-store", "kind": "event_order",
                            "before": {"event": "station_passage_repaired",
                                       "filters": {"actor": "B", "tool": "station_tool",
                                                   "exit": "pickup_to_side_south"}},
                            "after": {"event": "station_supply_stored",
                                      "filters": {"actor": "A", "item": "courier_supply",
                                                  "storage": "station_storage"}},
                            "order": "EVENT_KEY", "start": 0, "deadline": 24, "hard": True})
        bundle = {"schema": "native-author-bundle-v1", "bundle_id": "station-work",
                  "version": 1, "source": "test", "constraints": constraints,
                  "branches": [], "permissions": {"world_opportunities": [],
                      "force_npc_response": False, "max_opportunities": 1, "cost_budget": 0}}
        bindings = [{"constraint_id": row["id"],
                     "control": {"mode": "result_only", "file_actor": None,
                                 "allowed_methods": ["inspect_then_repair", "repair_then_inspect"],
                                 "source": "SYSTEM"}, "locked_fragment": None}
                    for row in constraints]
        value = profile({"schema": AUTHOR_SCHEMA, "bundle": bundle, "bindings": bindings})
        value["game_content"] = "station_work_v1"
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
        # A pre-scene legacy actor catalog must be merged with symbolic station
        # aliases; it must not be mistaken for generated station object IDs.
        compiled = compile_projection(load_profile(value),
                                      entities={"A": DEFAULT_ENTITIES["A"],
                                                "B": DEFAULT_ENTITIES["B"]})
        self.assertEqual(compiled.bundle_id, "station-work")
        self.assertEqual(station_work_entity_catalog()["station_tool"].stable_id, "station_tool")
        self.assertEqual({row["constraint_id"] for row in compiled.constraints},
                         {row["id"] for row in constraints})

    def test_station_locked_fragment_is_hashed_registered_work_only(self):
        bundle = {"schema": "native-author-bundle-v1", "bundle_id": "station-lock",
                  "version": 1, "source": "test", "constraints": [{
                      "id": "repair", "kind": "event_by_deadline",
                      "event": "station_passage_repaired",
                      "filters": {"actor": "B", "tool": "station_tool",
                                  "exit": "pickup_to_side_south"},
                      "start": 0, "deadline": 24, "hard": True}],
                  "branches": [], "permissions": {"world_opportunities": [],
                      "force_npc_response": False, "max_opportunities": 1, "cost_budget": 0}}
        sequence = [{"actor_alias": "B", "task_kind": "repair_passage",
                     "tool_ref": "station_tool", "target_ref": "pickup_to_side_south"}]
        digest = sha256(json.dumps(sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        binding = {"constraint_id": "repair",
                   "control": {"mode": "locked_fragment", "file_actor": None,
                               "allowed_methods": ["repair_then_inspect"], "source": "SYSTEM"},
                   "locked_fragment": {"sequence": sequence, "sequence_sha256": digest,
                       "entry_guard": {"task_grant_required": True, "tool_alias": "station_tool",
                                       "tool_at_room": "pickup"},
                       "abort_policy": "ABORT_LOCKED_CORE"}}
        value = profile({"schema": AUTHOR_SCHEMA, "bundle": bundle, "bindings": [binding]})
        value["game_content"] = "station_work_v1"
        loaded = load_profile(value)
        self.assertEqual(loaded.game_content, "station_work_v1")
        bad = copy.deepcopy(value)
        bad["author"]["bindings"][0]["locked_fragment"]["sequence"][0]["target_ref"] = "other-exit"
        # Keep the hash valid so the semantic alias validator is the rejecting layer.
        sequence[0]["target_ref"] = "other-exit"
        bad["author"]["bindings"][0]["locked_fragment"]["sequence_sha256"] = sha256(
            json.dumps(sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "registered station tool"):
            load_profile(bad)

    def test_store_only_lock_guard_does_not_require_unused_shared_tool(self):
        bundle = {"schema": "native-author-bundle-v1", "bundle_id": "store-lock",
                  "version": 1, "source": "test", "constraints": [{
                      "id": "store", "kind": "event_by_deadline",
                      "event": "station_supply_stored",
                      "filters": {"actor": "A", "item": "courier_supply",
                                  "storage": "station_storage"},
                      "start": 0, "deadline": 24, "hard": True}],
                  "branches": [], "permissions": {"world_opportunities": [],
                      "force_npc_response": False, "max_opportunities": 1, "cost_budget": 0}}
        sequence = [{"actor_alias": "A", "task_kind": "store_item",
                     "item_ref": "courier_supply", "destination_ref": "station_storage"}]
        digest = sha256(json.dumps(sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        binding = {"constraint_id": "store",
                   "control": {"mode": "locked_fragment", "file_actor": None,
                               "allowed_methods": ["inspect_then_repair"], "source": "SYSTEM"},
                   "locked_fragment": {"sequence": sequence, "sequence_sha256": digest,
                       "entry_guard": {"task_grant_required": True,
                                       "supply_alias": "courier_supply",
                                       "storage_alias": "station_storage",
                                       "inspection_receipt_required": True},
                       "abort_policy": "ABORT_LOCKED_CORE"}}
        value = profile({"schema": AUTHOR_SCHEMA, "bundle": bundle, "bindings": [binding]})
        value["game_content"] = "station_work_v1"
        loaded = load_profile(value)
        self.assertEqual(loaded.author["bindings"][0]["locked_fragment"]["sequence"], sequence)
        bad = copy.deepcopy(value)
        bad["author"]["bindings"][0]["locked_fragment"]["entry_guard"]["tool_alias"] = "station_tool"
        with self.assertRaisesRegex(ValueError, "exact keys"):
            load_profile(bad)

    def test_future_store_lock_uses_new_order_binding_and_preserves_result_mode(self):
        from tools.native_platform_v0.p5.ongoing_station.native import (
            activate_author, edit_author, initialize_station,
        )

        sequence = [{"actor_alias": "A", "task_kind": "store_item",
                     "item_ref": "courier_supply", "destination_ref": "station_storage"}]
        digest = sha256(json.dumps(sequence, sort_keys=True,
                                   separators=(",", ":")).encode()).hexdigest()
        fragment = {"sequence": sequence, "sequence_sha256": digest,
                    "entry_guard": {"task_grant_required": True,
                                    "supply_alias": "courier_supply",
                                    "storage_alias": "station_storage",
                                    "inspection_receipt_required": True},
                    "abort_policy": "ABORT_LOCKED_CORE"}
        bundle = {"schema": "native-author-bundle-v1", "bundle_id": "station-work-cas",
            "version": 1, "source": "test", "constraints": [{
                "id": "supply-stored-by-horizon", "kind": "event_by_deadline",
                "event": "station_supply_stored",
                "filters": {"actor": "A", "item": "courier_supply", "storage": "station_storage"},
                "start": 1, "deadline": 24, "hard": True}],
            "branches": [], "permissions": {"world_opportunities": [],
                "force_npc_response": False, "max_opportunities": 1, "cost_budget": 0}}
        result_control = {"mode": "result_only", "file_actor": None,
                          "allowed_methods": ["inspect_then_repair", "repair_then_inspect"],
                          "source": "SYSTEM"}
        v1 = {"schema": AUTHOR_SCHEMA, "bundle": bundle, "bindings": [{
            "constraint_id": "supply-stored-by-horizon", "control": result_control,
            "locked_fragment": None}]}
        raw_profile = {**profile(v1), "game_content": "station_work_v1"}

        class Attributes:
            def __init__(self): self.values = {}
            def add(self, key, value, category=None): self.values[(category, key)] = value
            def get(self, key, category=None, default=None):
                return self.values.get((category, key), default)
        class Pickup:
            def __init__(self): self.attributes = Attributes()

        pickup = Pickup()
        initialize_station(pickup, {}, raw_profile)
        self.assertTrue(activate_author(pickup, expected_version=1, now=1)["ok"])

        v2 = copy.deepcopy(v1)
        v2["bundle"]["version"] = 2
        v2["bundle"]["constraints"].append({
            "id": "repair-before-storage", "kind": "event_order",
            "before": {"event": "station_passage_repaired",
                       "filters": {"actor": "B", "tool": "station_tool",
                                   "exit": "pickup_to_side_south"}},
            "after": {"event": "station_supply_stored",
                      "filters": {"actor": "A", "item": "courier_supply",
                                  "storage": "station_storage"}},
            "order": "EVENT_KEY", "start": 3, "deadline": 24, "hard": True})
        v2["bindings"].append({"constraint_id": "repair-before-storage",
            "control": {"mode": "locked_fragment", "file_actor": "A",
                        "allowed_methods": ["inspect_then_repair", "repair_then_inspect"],
                        "source": "SYSTEM"}, "locked_fragment": copy.deepcopy(fragment)})
        result = edit_author(pickup, v2, expected_version=1, now=2)
        self.assertEqual(result["status"], "UPDATED")
        projection = compile_projection(load_profile({**raw_profile, "author": v2}))
        self.assertEqual(projection.bindings["supply-stored-by-horizon"]["control"]["mode"],
                         "result_only")
        self.assertIsNone(projection.bindings["supply-stored-by-horizon"]["locked_fragment"])
        self.assertEqual(projection.bindings["repair-before-storage"]["control"]["mode"],
                         "locked_fragment")

        invalid = copy.deepcopy(v2)
        invalid["bundle"]["version"] = 3
        invalid["bindings"][0]["control"]["mode"] = "direct"
        invalid["bindings"][0]["control"]["source"] = "AUTHORED"
        self.assertEqual(edit_author(pickup, invalid, expected_version=2, now=3)["status"],
                         "CONTROL_MODE_IMMUTABLE")

    def test_bundle_constraints_are_the_projection_owner_and_binding_changes_hash(self):
        value = load_profile(profile(author()))
        first = compile_projection(value)
        self.assertEqual(first.bundle_id, "station-author-1")
        self.assertEqual(first.version, 1)
        self.assertEqual({row["constraint_id"] for row in first.constraints},
                         {"archive-goal", "response-before-archive"})
        changed = copy.deepcopy(value.raw)
        changed["author"]["bindings"][0]["control"]["file_actor"] = "B"
        second = compile_projection(load_profile(changed))
        self.assertNotEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.constraints[0]["source_constraint"],
                         second.constraints[0]["source_constraint"])

    def test_unregistered_or_weakened_archive_semantics_fail_closed(self):
        from tools.native_platform_v0.p5.bundle import BundleError, load_bundle
        raw = author()["bundle"]
        with self.assertRaises(BundleError):
            load_bundle(raw)
        value = author()
        # Response-before-archive is a native domain precondition, not a
        # mandatory author clause. An archive-only AuthorBundle is valid.
        value["bundle"]["constraints"] = value["bundle"]["constraints"][:1]
        value["bindings"] = value["bindings"][:1]
        compiled = compile_projection(load_profile(profile(value)))
        self.assertEqual([row["constraint_id"] for row in compiled.constraints], ["archive-goal"])
        requirements = __import__(
            "tools.native_platform_v0.p5.ongoing_station.model", fromlist=["derive_story_requirements"]
        ).derive_story_requirements(compiled, compiled.constraints[0], 777)
        self.assertIsNone(requirements["required_handover"])
        self.assertEqual(requirements["residual_constraints"], [])
        value["bundle"]["constraints"][0]["hard"] = False
        with self.assertRaises((BundleError, ValueError)):
            compile_projection(load_profile(profile(value)))

    def test_same_note_handover_occurrence_and_order_compile_as_bound_requirements(self):
        from tools.native_platform_v0.p5.ongoing_station.model import derive_story_requirements
        value = author()
        value["bundle"]["constraints"].append({
            "id": "handover-occurs", "kind": "event_by_deadline", "event": "note_handed_over",
            "filters": {"actor": "B", "recipient": "A", "item": "note"},
            "start": 6, "deadline": 24, "hard": True, "min_count": 1, "max_count": 1})
        value["bundle"]["constraints"].append({
            "id": "handover-before-archive", "kind": "event_order",
            "before": {"event": "note_handed_over",
                       "filters": {"actor": "B", "recipient": "A", "item": "note"}},
            "after": {"event": "note_archived", "filters": {"item": "note"}},
            "order": "EVENT_KEY", "start": 6, "deadline": 24, "hard": True})
        binding = value["bindings"][0]
        value["bindings"].extend([
            {**copy.deepcopy(binding), "constraint_id": "handover-occurs"},
            {**copy.deepcopy(binding), "constraint_id": "handover-before-archive"},
        ])
        compiled = compile_projection(load_profile(profile(value)))
        archive = next(row for row in compiled.constraints if row["constraint_id"] == "archive-goal")
        requirements = derive_story_requirements(compiled, archive, 777)
        self.assertEqual(requirements["required_handover"]["start_minute"], 6)
        self.assertEqual(requirements["required_handover"]["deadline_minute"], 24)
        self.assertEqual(requirements["required_handover"]["actor_alias"], "B")
        self.assertEqual(requirements["required_handover"]["recipient_alias"], "A")
        self.assertEqual(requirements["residual_constraints"], [])

    def test_invalid_locked_core_is_rejected(self):
        value = author()
        value["bindings"][0]["control"] = {"mode": "locked_fragment", "file_actor": None,
                "allowed_methods": ["file_by_B"], "source": "SYSTEM"}
        value["bindings"][0]["locked_fragment"] = {"sequence": [{"actor_alias": "B",
                "task_kind": "archive_note", "item_ref": "objective.note",
                "destination_ref": "archive"}], "sequence_sha256": "bad",
                "entry_guard": {"response_required": True, "note_holder_alias": "B"},
                "abort_policy": "ABORT_LOCKED_CORE"}
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_profile(profile(value))


if __name__ == "__main__":
    unittest.main()
