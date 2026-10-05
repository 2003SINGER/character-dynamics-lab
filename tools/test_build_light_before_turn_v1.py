from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("build_light_before_turn_v1.py")
SPEC = importlib.util.spec_from_file_location("light_before_turn_builder", MODULE_PATH)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(builder)


def synthetic_episode() -> dict:
    return {
        "_source_episode_index": 17,
        "action": ["self-old-0", "partner-old-1", "self-old-2", "partner-old-3", "gold-target", "future-action"],
        "context": [f"environment-{i}" for i in range(6)],
        "available_actions": [[f"support-{i}"] for i in range(6)],
        "character": ["Ada", "Bert", "Ada", "Bert", "Ada", "Bert"],
        "speech": ["self speech old 0", "partner speech old 1", "self speech old 2",
                   "partner speech old 3", "CURRENT_SPEECH_POISON", "FUTURE_SPEECH_POISON"],
        "emote": ["self emote old 0", "partner emote old 1", "self emote old 2",
                  "partner emote old 3", "CURRENT_EMOTE_POISON", "FUTURE_EMOTE_POISON"],
        "room_objects": [["object"] for _ in range(6)],
        "room_agents": [["Ada", "Bert"] for _ in range(6)],
        "carrying": [[] for _ in range(6)],
        "wearing": [[] for _ in range(6)],
        "wielding": [[] for _ in range(6)],
        "agents": [{"name": "Ada", "persona": "Ada persona"},
                   {"name": "Bert", "persona": "Bert persona"}],
        "all_descriptions": "descriptions that must not enter candidate features",
    }


def synthetic_row(episode: dict | None = None) -> dict:
    episode = episode or synthetic_episode()
    return {
        "trajectory_id": "light::episode-00017",
        "actor": " ada ",
        "target_step_index": 4,
        "previous_same_actor_t": 2,
        "previous2_same_actor_t": 0,
        "actor_history_depth": 2,
        "source_O": episode["context"][4],
        "source_action_A_star": episode["action"][4],
        "candidate_set_factual": episode["available_actions"][4],
        "previous_source_O": episode["context"][2],
        "previous_source_action_A_star": episode["action"][2],
        "previous2_source_O": episode["context"][0],
        "previous2_source_action_A_star": episode["action"][0],
    }


class GuardedSequence(list):
    def __init__(self, values, max_index: int, name: str):
        super().__init__(values)
        self.max_index = max_index
        self.name = name
        self.reads: list[int] = []

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise AssertionError(f"{self.name}: only point indexing is permitted")
        if index < 0:
            index += len(self)
        if index > self.max_index:
            raise AssertionError(f"{self.name}: forbidden access to turn {index} > {self.max_index}")
        if index < 0:
            raise AssertionError(f"{self.name}: negative index is invalid")
        self.reads.append(index)
        return super().__getitem__(index)

    def __iter__(self):
        raise AssertionError(f"{self.name}: future-capable iteration is forbidden")


class BeforeTurnBuilderTests(unittest.TestCase):
    def test_synthetic_future_and_same_turn_poison_never_enters_serialized_candidate_payload(self):
        passed = builder.run_functional_negative_controls()
        self.assertEqual(passed["status"], "PASS_SYNTHETIC_ONLY")
        self.assertTrue(all(passed["checks"].values()))
        self.assertEqual(passed["past_channel_changes_payload"],
                         {"speech": True, "action": True, "emote": True})

        episode = synthetic_episode()
        inputs = builder.build_candidate_inputs(episode, 4, "Ada")
        serialized = builder.candidate_features(inputs).decode("utf-8")
        for poison in ("CURRENT_SPEECH_POISON", "CURRENT_EMOTE_POISON", "future-action",
                       "FUTURE_SPEECH_POISON", "FUTURE_EMOTE_POISON",
                       "Bert persona", "descriptions that must not enter candidate features"):
            self.assertNotIn(poison, serialized)
        # The current recorded action is only a separate supervision field after a validated join.
        record = builder.validate_row_and_build(synthetic_row(episode), episode)
        self.assertEqual(record["supervision"]["recorded_action"], "gold-target")
        self.assertNotIn("supervision", inputs)
        self.assertFalse(record["admission"]["training_authorized"])

    def test_history_is_grouped_by_raw_turn_and_keeps_both_roles_without_channel_order_claim(self):
        episode = synthetic_episode()
        record = builder.validate_row_and_build(synthetic_row(episode), episode)
        payload = record["candidate_model_payload"]
        history = payload["prior_interaction_history"]
        refs = record["provenance"]["payload_history_turn_refs"]
        self.assertEqual([item["role"] for item in history], ["self", "partner", "self", "partner"])
        self.assertEqual([ref["raw_turn_index"] for ref in refs], [0, 1, 2, 3])
        self.assertEqual([ref["role"] for ref in refs], [item["role"] for item in history])
        self.assertEqual(history[1], {"role": "partner", "speech": "partner speech old 1",
                                      "action": "partner-old-1", "emote": "partner emote old 1"})
        self.assertEqual(set(payload["prior_interaction_history"][0]), {"role", "speech", "action", "emote"})
        self.assertEqual(payload["recorded_environment_snapshot"], "environment-4")
        self.assertEqual(record["candidate_surface"], {"recorded_support": ["support-4"]})
        self.assertNotIn("recorded_support", payload)
        self.assertNotIn("actor", payload)
        self.assertNotIn("raw_turn_index", payload)
        self.assertEqual(record["provenance"]["target_raw_turn_index"], 4)
        self.assertEqual(record["provenance"]["target_physical_index"], 4)

    def test_reference_join_rejects_target_mismatch_separately_from_noninterference(self):
        episode = synthetic_episode()
        row = synthetic_row(episode)
        row["source_action_A_star"] = "wrong-target"
        with self.assertRaisesRegex(ValueError, "gold/action mismatch"):
            builder.validate_row_and_build(row, episode)
        # The functional noninterference test above compares payload bytes under mutations;
        # this rejection is only evidence that the reference join fails closed.
        controls = builder.run_functional_negative_controls()
        self.assertTrue(controls["checks"][
            "current_action_speech_emote_mutation_does_not_change_candidate_features"])

    def test_target_speaker_persona_and_per_turn_alignment_fail_closed(self):
        episode = synthetic_episode()
        with self.assertRaisesRegex(ValueError, "actor mismatch"):
            builder.validate_row_and_build(dict(synthetic_row(episode), actor="Bert"), episode)

        ambiguous = copy.deepcopy(episode)
        ambiguous["agents"].append({"name": " ADA ", "persona": "duplicate"})
        with self.assertRaisesRegex(ValueError, "match must be unique"):
            builder.build_candidate_inputs(ambiguous, 4, "Ada")

        misaligned = copy.deepcopy(episode)
        misaligned["speech"].pop()
        with self.assertRaisesRegex(ValueError, "misaligned"):
            builder.build_candidate_inputs(misaligned, 4, "Ada")

        unknown_speaker = copy.deepcopy(episode)
        unknown_speaker["character"][1] = "Unregistered"
        with self.assertRaisesRegex(ValueError, "uniquely match an agent"):
            builder.build_candidate_inputs(unknown_speaker, 4, "Ada")

        missing_speaker = copy.deepcopy(episode)
        missing_speaker["character"][1] = None
        with self.assertRaisesRegex(ValueError, "no character/speaker"):
            builder.build_candidate_inputs(missing_speaker, 4, "Ada")

    def test_future_turns_and_partner_persona_are_noninterfering_but_past_changes_are_not(self):
        base = synthetic_episode()
        original = builder.candidate_features(builder.build_candidate_inputs(base, 4, "Ada"))

        future = copy.deepcopy(base)
        for key in builder.PER_TURN_KEYS:
            future[key][5] = [f"FUTURE_POISON_{key}"] if key in {
                "available_actions", "room_objects", "room_agents", "carrying", "wearing", "wielding"
            } else f"FUTURE_POISON_{key}"
        future["agents"][1]["persona"] = "PARTNER_PERSONA_POISON"
        future["all_descriptions"] = "ALL_DESCRIPTIONS_POISON"
        changed = builder.candidate_features(builder.build_candidate_inputs(future, 4, "Ada"))
        self.assertEqual(original, changed)
        for poison in (b"FUTURE_POISON", b"PARTNER_PERSONA_POISON", b"ALL_DESCRIPTIONS_POISON"):
            self.assertNotIn(poison, original)

        for channel in builder.CHANNELS:
            past = copy.deepcopy(base)
            past[channel][2] = f"CHANGED_PAST_{channel}"
            changed_past = builder.candidate_features(builder.build_candidate_inputs(past, 4, "Ada"))
            self.assertNotEqual(original, changed_past)

    def test_instrumented_projection_never_reads_current_or_future_target_channels(self):
        target = 4
        episode = synthetic_episode()
        allowed_max = {key: target - 1 for key in builder.PER_TURN_KEYS}
        allowed_max.update({"character": target, "context": target, "available_actions": target})
        guarded = dict(episode)
        wrapped = {}
        for key in builder.PER_TURN_KEYS:
            wrapped[key] = GuardedSequence(episode[key], allowed_max[key], key)
            guarded[key] = wrapped[key]
        inputs = builder.build_candidate_inputs(guarded, target, "Ada")
        self.assertTrue(inputs["candidate_model_payload"]["prior_interaction_history"])
        self.assertEqual(sorted(set(wrapped["action"].reads)), [0, 1, 2, 3])
        self.assertNotIn(target, wrapped["speech"].reads)
        self.assertNotIn(target, wrapped["emote"].reads)
        self.assertNotIn(target, wrapped["action"].reads)
        for key in builder.PER_TURN_KEYS:
            self.assertTrue(all(index <= allowed_max[key] for index in wrapped[key].reads), key)
        guarded_action = GuardedSequence(episode["action"], target - 1, "action-negative-test")
        with self.assertRaisesRegex(AssertionError, "forbidden access"):
            _ = guarded_action[-1]

    def test_split_matches_frozen_prediction_baseline_and_output_path_is_exclusive(self):
        trajectory_id = "light::episode-00017"
        expected = int(__import__("hashlib").sha256(trajectory_id.encode()).hexdigest()[:8], 16) % 10
        bucket, split = builder.split_for_episode(trajectory_id)
        self.assertEqual(bucket, expected)
        self.assertEqual(split, "train" if expected < 7 else "validation" if expected < 9 else "excluded_bucket9")
        self.assertEqual(len(builder.input_contract_sha256()), 64)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.bin"
            source.write_bytes(b"unchanged")
            occupied = root / "occupied"
            occupied.mkdir()
            with self.assertRaises(FileExistsError):
                builder.output_path_guard((source,), occupied)
            with self.assertRaises(ValueError):
                builder.output_path_guard((source,), source)
            self.assertEqual(source.read_bytes(), b"unchanged")


if __name__ == "__main__":
    unittest.main()
