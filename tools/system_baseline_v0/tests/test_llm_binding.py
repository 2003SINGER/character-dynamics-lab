"""LLM-binding contract tests; no model or network calls are made here."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.system_baseline_v0.llm_binding import (
    LLMConfig, Requirement, bind_author_request, build_prompt,
    validate_response_payload,
)


def candidate():
    return {
        "schema": "native-author-bundle-v1", "bundle_id": "binding-test", "version": 1,
        "source": "llm-candidate", "constraints": [
            {"id": "delivery-a", "kind": "event_by_deadline", "event": "delivery_settled",
             "filters": {"actor": "A", "item": "courier_supply"},
             "start": 0, "deadline": 8, "hard": True, "min_count": 1},
            {"id": "delivery-b", "kind": "event_by_deadline", "event": "delivery_settled",
             "filters": {"actor": "B", "item": "resident_parcel"},
             "start": 0, "deadline": 8, "hard": True, "min_count": 1},
            {"id": "note-no", "kind": "event_by_deadline", "event": "note_response",
             "filters": {"actor": "A", "recipient": "B", "item": "note", "response": "rejected"},
             "start": 0, "deadline": 12, "hard": True, "min_count": 1},
        ],
        "branches": [{"id": "rejection", "when": {"event": "note_response", "response": "rejected"},
                      "storylet": {"id": "after-rejection", "text": "A may take a side route."}}],
        "permissions": {"world_opportunities": ["open_side_passage"],
                        "force_npc_response": False, "max_opportunities": 1, "cost_budget": 2},
    }


def payload(requirements, *, residual=None):
    bundle = candidate()
    coverage = []
    for req in requirements:
        if req.requirement_id == "hard-worsening":
            statement = residual or "No registered predicate represents relationship worsening."
            coverage.append({"requirement_id": req.requirement_id, "candidate_refs": [],
                             "residual": statement})
        elif req.requirement_id == "deliveries":
            coverage.append({"requirement_id": req.requirement_id,
                             "candidate_refs": ["constraint/delivery-a", "constraint/delivery-b"],
                             "residual": None})
        else:
            coverage.append({"requirement_id": req.requirement_id,
                             "candidate_refs": ["constraint/note-no", "branch/rejection"],
                             "residual": None})
    residuals = ([{"requirement_id": "hard-worsening", "statement": residual or
                    "No registered predicate represents relationship worsening.",
                   "reason": "The closed P5 registry has no relationship-value observable."}]
                 if any(row["requirement_id"] == "hard-worsening" for row in coverage) else [])
    return {"schema": "system-baseline-llm-binding-response-v1", "candidate_bundle": bundle,
            "requirement_coverage": coverage, "residuals": residuals}


class LLMBindingContracts(unittest.TestCase):
    def setUp(self):
        self.positive = (
            Requirement("deliveries", "Both deliveries occur by the deadline.", True),
            Requirement("note", "B may reject the note; A may use a side route, not forced.", True),
        )

    def test_closed_capability_prompt_and_positive_candidate_remain_review_only(self):
        messages = build_prompt("Two deliveries; B may reject; allow side route, do not force.", self.positive)
        joined = "\n".join(message["content"] for message in messages)
        self.assertIn("native-author-bundle-v1", joined)
        self.assertIn("Do not force an NPC response", joined)
        self.assertIn('"event_order_template"', joined)
        self.assertIn('"json_templates"', joined)
        self.assertIn("never put entities or requirements inside the bundle", joined)
        self.assertIn('"stable_aliases"', joined)
        self.assertIn("omit filters.response", joined)
        self.assertIn('"required_top_level_fields"', joined)
        checked = validate_response_payload(payload(self.positive), self.positive)
        self.assertEqual(checked["status"], "NEEDS_HUMAN_REVIEW")
        self.assertIsNotNone(checked["typed_bundle"])
        self.assertFalse(checked["hard_residual"])

    def test_hard_relationship_worsening_residual_blocks_candidate_eligibility(self):
        requirements = self.positive + (
            Requirement("hard-worsening", "Relationship value must clearly worsen.", True),
        )
        checked = validate_response_payload(payload(requirements), requirements)
        self.assertEqual(checked["status"], "HARD_RESIDUAL")
        self.assertTrue(checked["hard_residual"])

    def test_typed_candidate_cannot_exceed_permission_ceiling(self):
        requirements = (Requirement("note", "A note response is observed.", True),)
        raw = payload(requirements)
        raw["candidate_bundle"]["permissions"]["world_opportunities"] = [
            "open_side_passage", "open_main_passage"]
        checked = validate_response_payload(raw, requirements, allowed_permissions={
            "world_opportunities": ["open_side_passage"], "force_npc_response": False,
            "max_opportunities": 1, "cost_budget": 2,
        })
        self.assertEqual(checked["status"], "INVALID_RESPONSE")
        self.assertIsNone(checked["typed_bundle"])

    def test_hard_requirement_cannot_map_only_to_soft_constraints(self):
        requirements = (Requirement("deliveries", "Both deliveries occur by the deadline.", True),)
        raw = payload(requirements)
        raw["candidate_bundle"]["constraints"][0]["hard"] = False
        raw["candidate_bundle"]["constraints"][1]["hard"] = False
        checked = validate_response_payload(raw, requirements)
        self.assertEqual(checked["status"], "INVALID_RESPONSE")
        self.assertTrue(any("maps only to soft constraints" in error for error in checked["errors"]))

    def test_bind_persists_request_raw_response_and_metadata_without_retry(self):
        requirements = (Requirement("note", "B may reject a note.", True),)
        envelope = {"choices": [{"message": {"content": "<think>\n\n</think>\n\n" +
                                                  json.dumps(payload(requirements))}}],
                    "usage": {"prompt_tokens": 9, "completion_tokens": 8}}
        calls = []

        def transport(request, config):
            calls.append(request)
            return json.dumps(envelope).encode("utf-8")

        with tempfile.TemporaryDirectory() as temp:
            outcome = bind_author_request("B may reject the note.", requirements,
                                          artifact_parent=temp,
                                          allowed_permissions={
                                              "world_opportunities": ["open_side_passage"],
                                              "force_npc_response": False,
                                              "max_opportunities": 1, "cost_budget": 2,
                                          }, transport=transport)
            self.assertEqual(outcome.status, "NEEDS_HUMAN_REVIEW")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["model"], "qwen3-4b-q4_k_m")
            self.assertEqual(calls[0]["max_tokens"], 2048)
            self.assertEqual(calls[0]["chat_template_kwargs"], {"enable_thinking": False})
            self.assertTrue((outcome.artifact_dir / "request.json").is_file())
            self.assertTrue((outcome.artifact_dir / "response.raw").is_file())
            normalization = json.loads((outcome.artifact_dir / "response_normalization.json").read_text())
            self.assertEqual(normalization["operation"], "strip_exact_empty_think_prefix")
            self.assertTrue(normalization["nonempty_think_content_is_not_stripped"])
            metadata = json.loads((outcome.artifact_dir / "metadata.json").read_text())
            self.assertEqual(metadata["cost"]["basis"], "LOCAL_UNPRICED")
            self.assertTrue(metadata["human_review_required"])

    def test_non_loopback_and_nonfinite_config_are_rejected(self):
        for config in (LLMConfig(base_url="https://example.invalid/v1"),
                       LLMConfig(temperature=float("nan")),
                       LLMConfig(timeout_seconds=float("inf"))):
            with self.subTest(config=config), self.assertRaises(ValueError):
                config.validate()

    def test_duplicate_candidate_json_keys_are_rejected(self):
        requirements = (Requirement("note", "B may reject a note.", True),)
        content = ('{"schema":"system-baseline-llm-binding-response-v1",'
                   '"candidate_bundle":{"schema":"native-author-bundle-v1",'
                   '"bundle_id":"x","version":1,"source":"model",'
                   '"constraints":[],"branches":[],"constraints":[],"permissions":{}},'
                   '"requirement_coverage":[],"residuals":[]}')
        envelope = {"choices": [{"message": {"content": content}}]}
        with tempfile.TemporaryDirectory() as temp:
            outcome = bind_author_request(
                "B may reject a note.", requirements, artifact_parent=temp,
                allowed_permissions={"world_opportunities": ["open_side_passage"],
                                     "force_npc_response": False,
                                     "max_opportunities": 1, "cost_budget": 2},
                transport=lambda _request, _config: json.dumps(envelope).encode(),
            )
        self.assertEqual(outcome.status, "INVALID_RESPONSE")
        self.assertTrue(any("duplicate JSON key: constraints" in error for error in outcome.errors))


if __name__ == "__main__":
    unittest.main()
