"""Offline contract tests; none creates or mutates an Evennia scene."""
import unittest

from tools.planner_p0_v0.integration_v0 import contract as nw


def state(*, now=0, mode="direct", task=None, weather="clear", main_open=False,
          item_location="junction", item_holder=None, a_room="junction", b_room="junction"):
    routes = []
    for route, edges in nw.ROUTE_EDGES.items():
        routes.append({"id": route, "edges": [{"from": src, "to": dst,
                        "traversable": bool(main_open) if route == "main" else True}
                       for src, dst in edges]})
    active = task
    return {"clock": {"now": now, "deadline": nw.HORIZON}, "mode": mode,
            "weather": weather, "pending_cloud": None,
            "routes": routes, "actors": {
                "A": {"room": a_room, "active_task": active},
                "B": {"room": b_room, "active_task": None}},
            "item": {"location": item_location, "holder": item_holder},
            "task": active}


class NativeContractTests(unittest.TestCase):
    def test_action_objects_are_exact_and_closed(self):
        valid = [
            {"kind": "wait", "actor": "A"},
            {"kind": "move", "actor": "A", "from": "junction", "to": "inn"},
            {"kind": "get", "actor": "A", "item": "shelter_kit"},
            {"kind": "drop", "actor": "A", "item": "shelter_kit", "to": "inn"},
            {"kind": "look", "actor": "B"},
            {"kind": "meet", "actors": ["A", "B"]},
            {"kind": "cloud_seed"}, {"kind": "open_route", "route": "main"},
            {"kind": "offer_task", "actor": "A", "task": "deliver_shelter"},
            {"kind": "dispatch_task", "actor": "A", "task": "deliver_shelter"},
        ]
        for action in valid:
            self.assertEqual(nw.validate_action(action), action)
        for invalid in (valid[0] | {"surprise": 1},
                        {"kind": "move", "actor": "A", "from": "junction", "to": "void"},
                        {"kind": "get", "actor": "B", "item": "unknown"},
                        {"kind": "meet", "actors": ["A", "B"], "weather": "storm"}):
            with self.assertRaises(ValueError):
                nw.validate_action(invalid)

    def test_mode_driver_boundary_does_not_call_trusted_driver_an_npc(self):
        move = {"kind": "move", "actor": "A", "from": "junction", "to": "inn"}
        seed = {"kind": "cloud_seed"}
        self.assertEqual(nw.authorization("conditional", "trusted_driver", move), "")
        self.assertEqual(nw.authorization("direct", "trusted_driver", move), "ACL_DENIED")
        self.assertEqual(nw.authorization("direct", "direct_driver", move), "")
        self.assertEqual(nw.authorization("free", "direct_driver", move), "ACL_DENIED")
        self.assertEqual(nw.authorization("free", "author", seed), "ACL_DENIED")
        self.assertEqual(nw.authorization("conditional", "author", seed), "")
        self.assertEqual(nw.authorization("conditional", "npc", move), "ACL_DENIED")
        dispatch = {"kind": "dispatch_task", "actor": "A", "task": "deliver_shelter"}
        offer = {"kind": "offer_task", "actor": "A", "task": "deliver_shelter"}
        self.assertEqual(nw.authorization("conditional", "author", dispatch), "ACL_DENIED")
        self.assertEqual(nw.authorization("direct", "author", dispatch), "")
        self.assertEqual(nw.authorization("conditional", "author", offer), "")

    def test_stale_item_location_is_not_a_executor_precondition(self):
        active = {"actor": "A", "status": "active"}
        stale = state(task=active, item_location="inn", a_room="junction")
        self.assertEqual(nw.precondition(stale, {"kind": "get", "actor": "A",
                                                   "item": "shelter_kit"}), "")

    def test_get_requires_task_and_drop_requires_a_at_inn(self):
        no_task = state(item_location="junction")
        self.assertEqual(nw.precondition(no_task, {"kind": "get", "actor": "A",
                                                     "item": "shelter_kit"}), "ILLEGAL_ACTION")
        active = {"actor": "A", "status": "active"}
        not_at_inn = state(task=active, item_holder="A")
        self.assertEqual(nw.precondition(not_at_inn, {"kind": "drop", "actor": "A",
                                                       "item": "shelter_kit", "to": "inn"}),
                         "ILLEGAL_ACTION")
        at_inn = state(task=active, item_holder="A", a_room="inn")
        self.assertEqual(nw.precondition(at_inn, {"kind": "drop", "actor": "A",
                                                    "item": "shelter_kit", "to": "inn"}), "")

    def test_route_block_is_native_failure_not_symbolic_illegality(self):
        blocked = state(task={"actor": "A", "status": "active"}, a_room="junction")
        self.assertEqual(nw.precondition(blocked, {"kind": "move", "actor": "A",
                                                    "from": "junction", "to": "inn"}), "")

    def test_author_route_action_only_targets_closed_route(self):
        closed = state(main_open=False)
        opened = state(main_open=True)
        action = {"kind": "open_route", "route": "main"}
        self.assertEqual(nw.precondition(closed, action), "")
        self.assertEqual(nw.precondition(opened, action), "ILLEGAL_ACTION")

    def test_cloud_seed_sets_a_due_process_without_changing_weather(self):
        action = {"kind": "cloud_seed"}
        clear = state(now=0)
        self.assertEqual(nw.precondition(clear, action), "")
        self.assertEqual(nw.precondition(state(now=22), action), "")
        late = state(now=23, weather="clear")
        self.assertEqual(nw.precondition(late, action), "ILLEGAL_ACTION")

    def test_request_fingerprint_is_stable_and_payload_sensitive(self):
        action = {"kind": "wait", "actor": "A"}
        self.assertEqual(nw.request_fingerprint("direct_driver", action),
                         nw.request_fingerprint("direct_driver", dict(action)))
        self.assertNotEqual(nw.request_fingerprint("direct_driver", action),
                            nw.request_fingerprint("trusted_driver", action))
        self.assertNotEqual(nw.request_fingerprint("direct_driver", action),
                            nw.request_fingerprint("direct_driver", {"kind": "wait", "actor": "B"}))

    def test_horizon_is_absolute_and_never_resets(self):
        action = {"kind": "wait", "actor": "A"}
        self.assertEqual(nw.precondition(state(now=23), action), "")
        self.assertEqual(nw.precondition(state(now=24), action), "ILLEGAL_ACTION")


if __name__ == "__main__":
    unittest.main()
