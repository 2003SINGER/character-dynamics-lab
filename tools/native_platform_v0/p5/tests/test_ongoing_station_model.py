import copy
import unittest

from tools.native_platform_v0.p5.ongoing_station.model import (
    AUTHOR_SCHEMA, PROFILE_SCHEMA, compile_projection, load_profile,
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
