import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("project_inputs", HERE / "project_inputs.py")
pi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pi)


def make_record():
    traj = "light::episode-fixture"
    bucket, split = pi._split(traj)
    hist = [
        {"role": "self", "speech": "prior self words", "action": "self action", "emote": None},
        {"role": "partner", "speech": "partner words", "action": "partner raw command", "emote": "smile"},
        {"role": "partner", "speech": None, "action": "command only", "emote": None},
        {"role": "self", "speech": None, "action": None, "emote": None},
    ]
    refs = [{"raw_turn_index": i, "physical_index": i if hist[i]["action"] else None,
             "role": hist[i]["role"], "speaker": "A" if hist[i]["role"] == "self" else "B",
             "source_ref": f"episode:4:turn:{i}"} for i in range(len(hist))]
    return {"schema": pi.SCHEMA,
            "candidate_model_payload": {"self_persona": "persona", "prior_interaction_history": hist,
                                        "recorded_environment_snapshot": "current environment"},
            "candidate_surface": {"recorded_support": ["Go North", "go north", "wait"]},
            "supervision": {"recorded_action": "go north", "admission": "SOURCE_LABEL_NOT_INPUT"},
            "source_history_holdback": {"partner_persona": "held", "all_descriptions": "held",
                                        "future_turns": "held", "same_turn_speech_action_emote": "held"},
            "admission": {"overall": "PENDING", "training_authorized": False,
                           "self_persona": "PENDING", "prior_self_speech": "PENDING",
                           "prior_self_action": "PENDING", "prior_self_emote": "PENDING",
                           "prior_partner_speech": "PENDING", "prior_partner_emote": "PENDING",
                           "prior_partner_action": "PENDING", "recorded_environment_snapshot": "PENDING",
                           "recorded_support": "PENDING", "time_safe_does_not_imply_information_authorized": True,
                           "not_claimed": []},
            "provenance": {"trajectory_id": traj, "episode_index": 4, "actor": "A",
                           "target_raw_turn_index": 8, "target_physical_index": 3,
                           "target_source_ref": "episode:4:turn:8", "split_bucket": bucket, "split": split,
                           "prior_same_actor_physical_turns": [], "payload_history_turn_refs": refs,
                           "self_persona_agent_index": 0, "self_persona_matched_name": "A",
                           "self_persona_source_ref": "episode:4:agents",
                           "source_fields": {"recorded_environment_snapshot": "episode:4:turn:8:context",
                                              "recorded_support": "episode:4:turn:8:available_actions",
                                              "recorded_action": "episode:4:turn:8:action"},
                           "model_must_not_read": ["provenance", "supervision", "admission"]}}


class ProjectionTests(unittest.TestCase):
    def test_features_exact_expected_and_metadata_poison_is_not_read(self):
        r = make_record()
        expected = {"self_persona": "persona", "history": [
            {"role": "self", "speech": "prior self words", "action": "self action", "emote": None},
            {"role": "partner", "speech": "partner words", "action": None, "emote": "smile"},
            {"role": "partner", "speech": None, "action": None, "emote": None},
            {"role": "self", "speech": None, "action": None, "emote": None}],
            "recorded_support": ["Go North", "go north", "wait"], "view": "core",
            "recorded_environment_snapshot": "current environment"}
        projected = pi.project_record(r)
        self.assertEqual(pi.features(projected), expected)
        class PoisonDict(dict):
            def __getitem__(self, key):
                if key in {"supervision", "provenance", "admission", "source_history_holdback"}:
                    raise AssertionError(f"feature entry read forbidden field {key}")
                return super().__getitem__(key)
        poison = PoisonDict(projected)
        poison["supervision"] = "GOLD POISON"; poison["provenance"] = "PROVENANCE POISON"
        poison["admission"] = "ADMISSION POISON"
        self.assertEqual(pi.features(poison), expected)
        self.assertEqual(pi.features(projected, include_context=False)["history"], expected["history"])
        self.assertNotIn("recorded_environment_snapshot", pi.features(projected, include_context=False))

    def test_diagnostic_and_core_partner_action_noninterference(self):
        r = pi.project_record(make_record())
        core_before = pi.features(r)
        diagnostic_before = pi.features(r, "diagnostic_plus_partner_raw_commands")
        changed = copy.deepcopy(r)
        changed["history_views"]["diagnostic_plus_partner_raw_commands"][1]["action"] = "changed command"
        changed["history_views"]["diagnostic_plus_partner_raw_commands"][2]["action"] = None
        changed["history_views"]["core"][1]["action"] = None
        self.assertEqual(pi.features(changed), core_before)
        self.assertNotEqual(pi.features(changed, "diagnostic_plus_partner_raw_commands"), diagnostic_before)
        self.assertEqual(len(core_before["history"]), 4)
        self.assertIsNone(core_before["history"][2]["action"])

    def test_self_prior_and_dialogue_are_positive_controls(self):
        r = pi.project_record(make_record()); baseline = pi.features(r)
        for channel in ("speech", "action", "emote"):
            changed = copy.deepcopy(r)
            changed["history_views"]["core"][0][channel] = "new prior"
            self.assertNotEqual(pi.features(changed), baseline)

    def test_projected_feature_boundary_and_gold_noninterference(self):
        source = make_record()
        before = pi.features(pi.project_record(source))
        changed_gold = copy.deepcopy(source)
        changed_gold["supervision"]["recorded_action"] = "some other action"
        self.assertEqual(pi.features(pi.project_record(changed_gold)), before)
        base = pi.project_record(source)
        cases = []
        x = copy.deepcopy(base); x["static_condition"]["private"] = "x"; cases.append(x)
        x = copy.deepcopy(base); x["history_views"]["core"][0]["private"] = "x"; cases.append(x)
        x = copy.deepcopy(base); x["history_views"]["core"][1]["action"] = "partner leak"; cases.append(x)
        x = copy.deepcopy(base); x["history_views"]["core"][0]["role"] = "observer"; cases.append(x)
        x = copy.deepcopy(base); x["history_views"]["core"][0]["speech"] = 7; cases.append(x)
        x = copy.deepcopy(base); x["static_condition"]["self_persona"] = None; cases.append(x)
        x = copy.deepcopy(base); x["candidate_surface"]["recorded_support"] = ["ok", None]; cases.append(x)
        for bad in cases:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError): pi.features(bad)

    def test_schema_role_text_alignment_split_and_refs_reject(self):
        cases = []
        x = make_record(); x["candidate_model_payload"]["private"] = "x"; cases.append(x)
        x = make_record(); x["candidate_model_payload"]["prior_interaction_history"][0]["private"] = "x"; cases.append(x)
        x = make_record(); x["candidate_model_payload"]["prior_interaction_history"][0]["role"] = "observer"; cases.append(x)
        x = make_record(); x["candidate_model_payload"]["prior_interaction_history"][0]["speech"] = 3; cases.append(x)
        x = make_record(); x["provenance"]["split"] = "train"; cases.append(x)
        x = make_record(); x["provenance"]["payload_history_turn_refs"][2]["raw_turn_index"] = 1; cases.append(x)
        x = make_record(); x["provenance"]["payload_history_turn_refs"][1]["raw_turn_index"] = 8; cases.append(x)
        x = make_record(); x["provenance"]["payload_history_turn_refs"].pop(); cases.append(x)
        x = make_record(); x["supervision"]["recorded_action"] = None; cases.append(x)
        x = make_record(); x["admission"] = None; cases.append(x)
        x = make_record(); x["provenance"]["target_raw_turn_index"] = True; cases.append(x)
        for bad in cases:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError): pi.validate_record(bad, 1)

    def test_support_and_supervision_eligibility_classification(self):
        self.assertEqual(pi._eligibility("go north", ["Go North", "wait"]), "unique")
        self.assertEqual(pi._eligibility("go  north", ["go north"]), "absent")
        self.assertEqual(pi._eligibility("missing", ["wait"]), "absent")
        self.assertEqual(pi._eligibility("go north", ["Go North", "go north"]), "ambiguous")
        self.assertEqual(pi._eligibility("", ["wait"]), "missing_or_invalid")
        self.assertEqual(pi.project_record(make_record())["candidate_surface"]["recorded_support"], ["Go North", "go north", "wait"])

    def test_pinned_hash_rejects_override_and_data_mismatch(self):
        with self.assertRaises(ValueError): pi.project_bytes(b"{}\n", pi.INPUT_SHA256)
        with self.assertRaises(ValueError): pi.project_bytes(b"{}\n", "0" * 64)

    def test_output_existing_overlap_and_symlink_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "outputs").mkdir()
            with patch.object(pi, "ROOT", root):
                source = root / "outputs" / "source.jsonl"; source.write_text("x")
                existing = root / "outputs" / "exists"; existing.mkdir()
                marker = existing / "keep"; marker.write_text("do not overwrite")
                before = hashlib.sha256(marker.read_bytes()).hexdigest()
                with self.assertRaises(FileExistsError): pi._safe_paths(source, existing)
                self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(), before)
                with self.assertRaises(ValueError): pi._safe_paths(source, source / "child")
                target = root / "outputs" / "real"; target.mkdir()
                link = root / "outputs" / "link"; link.symlink_to(target)
                with self.assertRaises(ValueError): pi._safe_paths(source, link / "child")
                source_link = root / "outputs" / "source-link.jsonl"; source_link.symlink_to(source)
                with self.assertRaises(ValueError): pi._safe_paths(source_link, root / "outputs" / "new")
                broken_link = root / "outputs" / "broken"; broken_link.symlink_to(root / "outputs" / "missing")
                with self.assertRaises(ValueError): pi._safe_paths(source, broken_link)
                source_dir = root / "outputs" / "source-dir"; source_dir.symlink_to(root / "outputs" / "real")
                with self.assertRaises(ValueError): pi._safe_paths(source_dir / "file", root / "outputs" / "new")
                outside = root.parent / "outside-contract-test"
                with self.assertRaises(ValueError): pi._safe_paths(source, outside)
                with self.assertRaises(ValueError): pi._safe_paths(outside, root / "outputs" / "new")

    def test_duplicate_row_key_rejected_by_pure_projection(self):
        r = make_record()
        with self.assertRaisesRegex(ValueError, "duplicate source row key"):
            pi.project_records([r, copy.deepcopy(r)])


if __name__ == "__main__":
    unittest.main()
