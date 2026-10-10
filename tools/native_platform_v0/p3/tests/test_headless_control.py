import unittest
import json
from collections import UserDict, UserList
from types import MappingProxyType
from unittest.mock import patch
from types import SimpleNamespace

from twisted.test.proto_helpers import StringTransport
from tools.native_platform_v0.p3.control_service import (P3ControlProtocol, _json_safe,
                                                          _reset_options, start_plugin_services)
from tools.native_platform_v0.p3.export_evidence import json_safe
from tools.native_platform_v0.p3.mcp_stdio import handle_message


class HeadlessSerializationTests(unittest.TestCase):
    def test_evennia_saver_mapping_and_sequence_shapes_serialize_recursively(self):
        value = UserDict({"events": UserList([UserDict({"kind": "drop", "settled": True})])})
        expected = {"events": [{"kind": "drop", "settled": True}]}
        self.assertEqual(_json_safe(value), expected)
        self.assertEqual(json_safe(value), expected)

    def test_mapping_proxy_and_sensitive_fields_are_bounded(self):
        value = MappingProxyType({"local": (1, 2), "session_token": "hidden", "nested": UserDict({"ok": 1})})
        self.assertEqual(_json_safe(value), {"local": [1, 2], "nested": {"ok": 1}})
        self.assertEqual(json_safe(value), {"local": [1, 2], "nested": {"ok": 1}})

    def test_evennia_service_is_parented_to_the_multi_service_received_by_hook(self):
        class FakeService:
            def __init__(self):
                self.parent = None
                self.name = None

            def setName(self, name):
                self.name = name

            def setServiceParent(self, parent):
                self.parent = parent

        parent = object()
        service = FakeService()
        with patch("tools.native_platform_v0.p3.control_service.internet.TCPServer",
                   return_value=service) as tcp_server:
            start_plugin_services(parent)
        tcp_server.assert_called_once()
        self.assertEqual(tcp_server.call_args.args[0], 14011)
        self.assertEqual(tcp_server.call_args.kwargs["interface"], "127.0.0.1")
        self.assertIs(service.parent, parent)
        self.assertEqual(service.name, "NativeP3LoopbackControl")


class McpStdioTests(unittest.TestCase):
    def test_initialize_negotiates_only_supported_protocol_version(self):
        response = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                    "params": {"protocolVersion": "unknown"}})
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(response["result"]["capabilities"], {"tools": {"listChanged": False}})

    def test_tools_list_has_lifecycle_and_scenario_controls(self):
        response = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, {"start_world", "stop_world", "health", "reset_scenario", "pause_scenario", "step_world",
                                 "inject_action", "observe_actor", "get_trace", "run_scenario", "run_c0_scenario",
                                 "run_c1a_scenario", "run_p4_scenario", "reset_p5_scenario",
                                 "run_p5_scenario", "edit_author_bundle"})
        self.assertTrue(all(tool["inputSchema"].get("additionalProperties") is False
                            for tool in response["result"]["tools"]))

    def test_tool_call_is_thin_rpc_and_keeps_structured_result(self):
        calls = []
        result = {"scene_id": "scene-1", "completed": True}
        response = handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                    "params": {"name": "run_scenario", "arguments": {"scenario": "Aclean"}}},
                                  lambda operation, args: calls.append((operation, args)) or result)
        self.assertEqual(calls, [("run_scenario", {"scenario": "Aclean"})])
        self.assertEqual(response["result"]["structuredContent"], result)
        self.assertFalse(response["result"]["isError"])

    def test_notifications_have_no_response_and_unknown_tool_is_invalid_params(self):
        self.assertIsNone(handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        response = handle_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                   "params": {"name": "arbitrary", "arguments": {}}})
        self.assertEqual(response["error"]["code"], -32602)

    def test_reset_supports_bounded_manual_or_timer_drive_and_pause_tool_is_scene_scoped(self):
        self.assertEqual(_reset_options({"mode": "a", "seed": 7,
                                         "drive_mode": "timer", "interval": 30}),
                         ("a", 7, "timer", 30, "legacy_delivery_v0", True, False))
        self.assertEqual(_reset_options({}), ("a", 0, "manual", 4, "legacy_delivery_v0", True, False))
        self.assertEqual(_reset_options({"activity_profile": "delivery_patrol_v0", "delivery_task": False}),
                         ("a", 0, "manual", 4, "delivery_patrol_v0", False, False))
        self.assertEqual(_reset_options({"activity_profile": "delivery_patrol_recovery_v0"}),
                         ("a", 0, "manual", 4, "delivery_patrol_recovery_v0", True, False))
        for invalid in ({"interval": 1}, {"interval": 31}, {"interval": True},
                        {"drive_mode": "automatic"}, {"extra": "value"},
                        {"delivery_task": False},
                        {"activity_profile": "delivery_patrol_v0", "delivery_task": False,
                         "patrol_exit_locked": True, "mode": "b"},
                        {"activity_profile": "delivery_patrol_recovery_v0", "mode": "b"},
                        {"activity_profile": "delivery_patrol_recovery_v0", "delivery_task": False}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                _reset_options(invalid)
        response = handle_message({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
        by_name = {tool["name"]: tool for tool in response["result"]["tools"]}
        self.assertEqual(by_name["reset_scenario"]["inputSchema"]["properties"]["interval"]["minimum"], 2)
        self.assertEqual(by_name["reset_scenario"]["inputSchema"]["properties"]["interval"]["maximum"], 30)
        self.assertIn("scene_id", by_name["pause_scenario"]["inputSchema"]["required"])
        self.assertEqual(by_name["run_c0_scenario"]["inputSchema"]["properties"]["scenario"]["enum"],
                         ["C0-no-delivery", "C0-delivery-priority", "C0-after-delivery"])
        self.assertEqual(by_name["run_c1a_scenario"]["inputSchema"]["properties"]["scenario"]["enum"],
                         ["C1a-blocked-switch", "C1a-observed-resume"])
        self.assertEqual(by_name["run_p4_scenario"]["inputSchema"]["properties"]["case"]["enum"],
                         ["open", "blocked-return", "blocked-held", "short-deadline"])


class TwistedLineProtocolTests(unittest.TestCase):
    def test_client_newline_request_is_framed_and_answered(self):
        class FakeControl:
            def dispatch(self, request):
                self.request = request
                return {"status": "READY"}

        protocol = P3ControlProtocol()
        factory = SimpleNamespace(control=FakeControl())
        protocol.factory = factory
        transport = StringTransport()
        protocol.makeConnection(transport)
        protocol.loopback = True
        request = {"token": "x" * 40, "request_id": "mcp-1", "op": "health", "args": {}}
        protocol.dataReceived((json.dumps(request) + "\n").encode("utf-8"))
        response = json.loads(transport.value().decode("utf-8").splitlines()[0])
        self.assertEqual(factory.control.request, request)
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"], {"status": "READY"})


if __name__ == "__main__":
    unittest.main()
