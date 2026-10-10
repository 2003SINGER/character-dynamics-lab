"""P5 startup-only native social presets over the pinned Ensemble runner."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import unittest
from unittest.mock import patch

from tools.native_platform_v0.p3 import p4_social


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
RUNNER = os.path.join(ROOT, "tools/native_platform_v0/ensemble/runner.mjs")
PRESET_ENV = "ENSEMBLE_P5_SOCIAL_PRESET"
PRESETS = {
    "native_default_reject_v0": [],
    "hero_intelligence_30_v0": [{
        "category": "attribute", "type": "intelligence", "first": "hero", "value": 30,
    }],
}


def run_native(messages, preset=None, secret=None):
    payload = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in messages)
    env = os.environ.copy()
    env.pop(PRESET_ENV, None)
    if preset is not None:
        env[PRESET_ENV] = preset
    if secret is not None:
        env["ENSEMBLE_BRIDGE_SECRET"] = secret
    result = subprocess.run(["node", RUNNER], input=payload, text=True,
                            capture_output=True, check=True, timeout=10, env=env)
    return [json.loads(line) for line in result.stdout.splitlines()]


def social_exchange(prefix):
    request_id = f"{prefix}-request"
    return [
        {"op": "request_note", "requestId": request_id,
         "eventId": f"{prefix}-source", "actor": "hero", "responder": "love"},
        {"op": "respond_note", "requestId": request_id,
         "eventId": f"{prefix}-response", "actor": "hero", "responder": "love"},
    ]


class P5NativePresetTests(unittest.TestCase):
    def stop_client(self, client):
        if client is None:
            return
        client.invalidate()
        try:
            client.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            client.proc.kill()
            client.proc.wait(timeout=2)
        for stream in (client.proc.stdin, client.proc.stdout):
            if stream is not None:
                stream.close()

    def test_p5_reject_preset_is_explicit_and_blocks_runtime_fact_changes(self):
        results = run_native([
            {"op": "hello"},
            {"op": "propose", "eventId": "reject-runtime-change", "actor": "hero",
             "responder": "love", "facts": PRESETS["hero_intelligence_30_v0"]},
            *social_exchange("p5-reject"),
        ], preset="native_default_reject_v0")
        self.assertEqual(results[0], {"ok": True, "p5Preset": "native_default_reject_v0",
                                      "initialFacts": [], "initialStateApplied": True})
        self.assertFalse(results[1]["ok"])
        self.assertIn("runtime facts are forbidden", results[1]["error"])
        response = results[3]
        self.assertEqual(response["decision"], "rejected")
        self.assertEqual(response["selected"]["name"], "writeLoveNoteReject")

    def test_p5_accept_preset_is_applied_before_volition_and_blocks_runtime_facts(self):
        results = run_native([
            {"op": "hello"},
            {"op": "propose", "eventId": "accept-runtime-change", "actor": "hero",
             "responder": "love", "facts": [{"category": "attribute", "type": "intelligence",
                                                    "first": "hero", "value": 0}]},
            *social_exchange("p5-accept"),
        ], preset="hero_intelligence_30_v0")
        self.assertEqual(results[0], {"ok": True, "p5Preset": "hero_intelligence_30_v0",
                                      "initialFacts": PRESETS["hero_intelligence_30_v0"],
                                      "initialStateApplied": True})
        self.assertFalse(results[1]["ok"])
        self.assertIn("runtime facts are forbidden", results[1]["error"])
        response = results[3]
        self.assertEqual(response["decision"], "accepted")
        self.assertEqual(response["selected"]["name"], "writeLoveNoteAccept")
        self.assertEqual([row["weight"] for row in response["responderVolitions"]], [5, -10])

    def test_p5_commit_of_world_settled_native_action_remains_allowed(self):
        secret = "isolated-p5-test-secret"
        request_id = "p5-commit-request"
        response_event = "p5-commit-response"
        messages = [
            {"op": "hello"},
            {"op": "request_note", "requestId": request_id, "eventId": "p5-commit-source",
             "actor": "hero", "responder": "love"},
            {"op": "respond_note", "requestId": request_id, "eventId": response_event,
             "actor": "hero", "responder": "love"},
        ]
        initial = run_native(messages, preset="hero_intelligence_30_v0", secret=secret)
        proposal = initial[2]
        action_name = proposal["selected"]["name"]
        receipt_id = "synthetic-settled-receipt-for-native-bridge-test"
        signed = json.dumps([proposal["proposalId"], response_event, action_name, receipt_id],
                            separators=(",", ":"))
        proof = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
        committed = run_native([
            *messages,
            {"op": "authorize", "proposalId": proposal["proposalId"],
             "eventId": response_event, "actionName": action_name},
            {"op": "commit", "proposalId": proposal["proposalId"], "eventId": response_event,
             "settlementStatus": "settled", "settledActionName": action_name,
             "actionName": action_name, "settlementReceiptId": receipt_id,
             "settlementProof": proof},
        ], preset="hero_intelligence_30_v0", secret=secret)
        self.assertTrue(committed[3]["ok"])
        self.assertTrue(committed[4]["ok"])
        self.assertEqual(committed[4]["actionName"], "writeLoveNoteAccept")
        self.assertTrue(committed[4]["trace"]["doActionCalled"])

    def test_unknown_p5_preset_fails_closed(self):
        env = os.environ.copy()
        env[PRESET_ENV] = "accept-whatever"
        result = subprocess.run(["node", RUNNER], input="", text=True, capture_output=True,
                                timeout=10, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(PRESET_ENV, result.stderr)

    def test_no_p5_environment_preserves_legacy_fact_proposal_and_default_rejection(self):
        legacy = run_native([
            {"op": "propose", "eventId": "legacy-fact-proposal", "actor": "hero",
             "responder": "love", "facts": PRESETS["hero_intelligence_30_v0"]},
        ])
        self.assertTrue(legacy[0]["ok"])
        self.assertIn("writeLoveNoteAccept", [row["name"] for row in legacy[0]["actions"]])

        clean = run_native(social_exchange("legacy-clean"))
        self.assertEqual(clean[1]["decision"], "rejected")
        self.assertEqual(clean[1]["selected"]["name"], "writeLoveNoteReject")

    def test_p4_client_strips_inherited_p5_selector(self):
        client = None
        try:
            with patch.dict(os.environ, {PRESET_ENV: "hero_intelligence_30_v0"}):
                client = p4_social.P4EnsembleClient()
                hello = client.request({"op": "hello"})
            self.assertIsNone(hello["p5Preset"])
            self.assertEqual(hello["initialFacts"], [])
            self.assertFalse(hello["initialStateApplied"])
        finally:
            self.stop_client(client)

    def test_p5_client_confirms_startup_preset_handshake(self):
        client = None
        try:
            client = p4_social.P4EnsembleClient(p5_preset="hero_intelligence_30_v0")
            hello = client.request({"op": "hello"})
            self.assertEqual(hello["p5Preset"], "hero_intelligence_30_v0")
            self.assertEqual(hello["initialFacts"], PRESETS["hero_intelligence_30_v0"])
            self.assertTrue(hello["initialStateApplied"])
        finally:
            self.stop_client(client)

    def test_scene_runner_preset_cannot_change_after_creation(self):
        scene_id = "p5-preset-immutability-test"
        client = type("Client", (), {"p5_preset": "native_default_reject_v0",
                                     "proc": type("Proc", (), {"poll": lambda self: None})()})()
        p4_social._CLIENTS[scene_id] = client
        try:
            with self.assertRaisesRegex(RuntimeError, "cannot change within a scene runner"):
                p4_social._client(scene_id, "hero_intelligence_30_v0")
        finally:
            p4_social._CLIENTS.pop(scene_id, None)


if __name__ == "__main__":
    unittest.main()
