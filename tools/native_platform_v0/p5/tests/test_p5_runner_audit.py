import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.native_platform_v0.p3 import export_evidence, mcp_stdio
from tools.native_platform_v0.p5.audit import _check_world_and_edits, audit_document
from tools.native_platform_v0.p5.runner import SOURCE_FILES, load_suite, request_hashes, _normalize_run


ROOT = Path(__file__).resolve().parents[4]
SUITE = ROOT / "02_实验/Native_Platform_P5_v0/bundles/dev-matrix-v1.json"


class P5RunnerAuditTests(unittest.TestCase):
    def test_p5_export_is_opt_in_and_separate_from_legacy_categories(self):
        self.assertEqual(export_evidence.EXPORTED_CATEGORIES, {"native_p3", "native_social"})
        self.assertEqual(export_evidence.P5_EXPORTED_CATEGORIES,
                         {"native_p3", "native_social", "native_p5"})
        self.assertNotEqual(export_evidence.P5_RUNS_DIR, export_evidence.RUNS_DIR)
        self.assertIn("--p5", export_evidence.main.__code__.co_consts)

    def test_mcp_lists_exact_three_p5_tools_and_strict_inputs(self):
        by_name = {tool["name"]: tool for tool in mcp_stdio.TOOLS}
        p5_names = {name for name in by_name if name in {
            "reset_p5_scenario", "run_p5_scenario", "edit_author_bundle"}}
        self.assertEqual(p5_names, {"reset_p5_scenario", "run_p5_scenario", "edit_author_bundle"})
        for name in p5_names:
            schema = by_name[name]["inputSchema"]
            self.assertFalse(schema["additionalProperties"])
        run_schema = by_name["run_p5_scenario"]["inputSchema"]
        self.assertEqual(run_schema["properties"]["initial_social_preset"]["enum"],
                         ["native_default_reject_v0", "hero_intelligence_30_v0"])

    def test_tools_call_forwards_valid_registered_p5_operation(self):
        calls = []
        def rpc(name, args):
            calls.append((name, args))
            return {"ok": True, "run_status": "INCOMPLETE"}
        result = mcp_stdio.handle_message({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "run_p5_scenario", "arguments": {"bundle": {"version": 1}}},
        }, call_rpc=rpc)
        self.assertEqual(calls, [("run_p5_scenario", {"bundle": {"version": 1}})])
        self.assertEqual(result["result"]["structuredContent"]["run_status"], "INCOMPLETE")

    def test_suite_rows_load_and_only_exact_rpc_keys_are_sent_for_edits(self):
        suite, rows = load_suite(SUITE)
        self.assertEqual(suite["schema"], "native-p5-run-suite-v1")
        self.assertGreaterEqual(len(rows), 8)
        edit_row = next(row for row in rows if row.get("edits"))
        request, manifest = _normalize_run(edit_row, SUITE)
        self.assertEqual(set(request["edits"][0]), {"at", "expected_version", "raw_bundle"})
        self.assertIn("sha256", manifest["edit_bundles"][0])
        self.assertTrue(request_hashes(manifest)["edit_bundle_sha256"])
        self.assertNotIn(None, request_hashes(manifest)["edit_bundle_sha256"])
        self.assertIn("tools/native_platform_v0/p5/agency.py", SOURCE_FILES)
        self.assertIn("tools/native_platform_v0/p3/p4_agency.py", SOURCE_FILES)

    def test_auditor_checks_actual_edit_minute_and_nonempty_cas_evidence(self):
        prefix = [{"event_id": "prior-event", "sequence": 1}]
        accepted = {"ok": True, "pending_actions_before": {"A": {"operation_id": "pending-1"}},
                    "pending_actions_after": {"A": {"operation_id": "pending-1"}},
                    "pending_identity_preserved": True,
                    "active_bundle": {"version": 2},
                    "archive": {"prior_version": 1, "prior_verdicts": {"hard_status": "PENDING"}},
                    "ledger_prefix_before": prefix, "ledger_prefix_after": prefix}
        document = {"configuration": {"edits": [{"at": 2, "expected_version": 1}]},
                    "response": {"scene": {}, "rounds": [{"minute": 2, "edits": [accepted]}],
                                 "final": {"ledger": [], "verdicts": {}}}}
        findings = []
        _check_world_and_edits(document, findings)
        self.assertEqual(findings, [])
        document["response"]["rounds"][0]["minute"] = 3
        findings = []
        _check_world_and_edits(document, findings)
        self.assertTrue(any(row["code"] == "EDIT_MINUTE" for row in findings))

    def test_auditor_never_promotes_missing_evidence_to_pass(self):
        malformed = audit_document({"schema": "native-p5-run-artifact-v1"})
        self.assertIn(malformed["status"], {"FAIL", "INDETERMINATE"})
        self.assertNotEqual(malformed["status"], "PASS")
        codes = {row["code"] for row in malformed["findings"]}
        self.assertTrue({"RAW_BUNDLE_MISSING", "RUN_INCOMPLETE", "DB_READBACK_MISSING"} <= codes)

    def test_no_route_opportunity_does_not_imply_no_route_traversal(self):
        document = {"configuration": {"expect": {
            "route_traversed": "main_passage", "no_route_opportunity": True}},
            "response": {"scene": {}, "rounds": [], "final": {"ledger": [], "verdicts": {}}}}
        findings = []
        _check_world_and_edits(document, findings)
        self.assertFalse(any(row["code"] in {"ROUTE_OPPORTUNITY", "UNEXPECTED_ROUTE_OPPORTUNITY"}
                             for row in findings))

        document["response"]["final"]["ledger"].append({
            "event_type": "P5_OPPORTUNITY_SETTLED",
            "typed_args": {"route_id": "main_passage", "cost": 2}})
        findings = []
        _check_world_and_edits(document, findings)
        self.assertTrue(any(row["code"] == "UNEXPECTED_ROUTE_OPPORTUNITY" for row in findings))

    def test_p5_step_world_awaits_service_deferred(self):
        try:
            from twisted.internet import defer
            from tools.native_platform_v0.p3 import control_service
        except ImportError:
            self.skipTest("Twisted is available only in the initialized Evennia runtime")

        class Attributes:
            def get(self, key, category=None, default=None):
                if key == "p5_scene_id" and category == "native_p3":
                    return "p5-scene"
                return default

        pickup = type("Pickup", (), {"attributes": Attributes()})()
        expected = {"scene_id": "p5-scene", "rounds": [{"minute": 1}]}
        instance = object.__new__(control_service.P3Control)
        with patch("tools.native_platform_v0.p3.control_service._load_scene",
                   return_value=(object(), [pickup])), patch(
                       "tools.native_platform_v0.p5.service.step_world",
                       return_value=defer.succeed(expected)):
            result = instance.step_world({"scene_id": "p5-scene", "rounds": 1})
        observed = []
        result.addCallback(observed.append)
        self.assertEqual(observed, [expected])

    def test_player_get_receipt_uses_real_player_location_owner_id(self):
        get_receipt = {"actor_alias": "player", "provenance": "native_player_command",
                       "operation": "get", "item_id": 501, "before_location_id": 100,
                       "after_location_id": 901, "after_inventory_ids": [501]}
        drop_receipt = {"actor_alias": "player", "provenance": "native_player_command",
                        "operation": "drop", "item_id": 501, "before_location_id": 901,
                        "after_location_id": 100, "after_inventory_ids": []}
        rows = []
        for sequence, (operation, receipt) in enumerate((("get", get_receipt), ("drop", drop_receipt)), 1):
            rows.append({"event_type": "P5_INTERVENTION", "typed_args": {
                "kind": "player_native_command", "settlement": {"settled": True},
                "intervention": {"operation": operation, "item_alias": "courier_supply"},
                "command_receipt": receipt}})
        document = {"configuration": {"expect": {"player_interventions": [
            {"operation": "get", "item_alias": "courier_supply"},
            {"operation": "drop", "item_alias": "courier_supply"}]}},
            "response": {"scene": {"player": {"id": 901}, "rooms": {"origin": 100}},
                          "rounds": [], "final": {"ledger": rows, "verdicts": {}}}}
        findings = []
        _check_world_and_edits(document, findings)
        self.assertFalse(any(row["code"] == "PLAYER_INTERVENTION_PHYSICAL" for row in findings))
        rows[0]["typed_args"]["command_receipt"]["after_location_id"] = None
        findings = []
        _check_world_and_edits(document, findings)
        self.assertTrue(any(row["code"] == "PLAYER_INTERVENTION_PHYSICAL" for row in findings))


if __name__ == "__main__":
    unittest.main()
