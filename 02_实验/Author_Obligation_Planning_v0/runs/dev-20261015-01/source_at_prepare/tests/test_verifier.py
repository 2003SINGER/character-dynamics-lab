import base64
import unittest

from tools.author_obligation_planning_v0.verify import inspect_rows


def row(sequence, command, text):
    return {"event": "step", "sequence": sequence, "command": command,
            "raw_output_b64": base64.b64encode(text.encode()).decode(),
            "input_boundary_reached": True, "timed_out": False, "error": None,
            "sent_bytes_b64": "eA==", "intended_bytes_b64": "eA=="}


def ledger():
    initial = {"event": "initial_observation", "raw_b64": "eA==", "complete": True,
               "input_boundary_reached": True, "timed_out": False, "error": None}
    return [initial,
            row(1, "on lamp", "Your lamp is now on."),
            row(2, "forwa", "You're on east bank of fissure."),
            row(3, "wave rod", "A crystal bridge now spans the fissure."),
            row(4, "over", "You're on west bank of fissure."),
            row(5, "over", "You're on east bank of fissure."),
            row(6, "wave rod", "The crystal bridge has vanished!"),
            row(7, "look", "You're on east bank of fissure."),
            row(8, "inventory", "You are currently holding the following:\nSet of keys\nBrass lantern\nBlack rod\n\n"),
            {"event": "close", "terminated": True, "error": None}]


def task():
    return {"id": "synthetic", "goal": {"required": [["at", "player", "EASTBANK"],
             ["carrying", "keys"], ["lamp_on"], ["unbridged"]], "forbidden": []},
            "obligations": [{"type": "in_order", "events": ["create_bridge", "arrive_west", "return_east", "destroy_bridge"]}],
            "always_no_death": True}


class VerifierTests(unittest.TestCase):
    def test_history_is_not_final_bridge(self):
        result = inspect_rows(ledger(), task())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([e["name"] for e in result["events"]],
                         ["create_bridge", "arrive_west", "return_east", "destroy_bridge"])

    def test_missing_receipt_unknown(self):
        rows = ledger()
        del rows[3]
        self.assertEqual(inspect_rows(rows, task())["status"], "UNKNOWN")

    def test_bridge_presence_not_creation(self):
        rows = ledger()
        rows[3] = row(3, "look", "A crystal bridge spans the fissure.")
        self.assertEqual(inspect_rows(rows, task())["status"], "FAIL")

    def test_death_even_if_revived_fails(self):
        rows = ledger()
        rows[1] = row(1, "on lamp", "Your lamp is now on. Oh dear, you seem to have gotten yourself killed. You revive.")
        self.assertEqual(inspect_rows(rows, task())["status"], "FAIL")

    def test_unknown_bridge_reply_not_completion(self):
        rows = ledger()
        rows[3] = row(3, "wave rod", "Unrecognized new game response")
        self.assertEqual(inspect_rows(rows, task())["status"], "UNKNOWN")

    def test_unmentioned_bridge_remains_free(self):
        spec = task()
        spec["goal"]["required"].remove(["unbridged"])
        spec["obligations"] = []
        rows = ledger()
        rows[7] = row(7, "look", "You're on east bank of fissure. A crystal bridge spans the fissure.")
        self.assertEqual(inspect_rows(rows, spec)["status"], "PASS")

    def test_ended_unsealed_unknown(self):
        self.assertEqual(inspect_rows(ledger()[:-1], task())["status"], "UNKNOWN")

    def test_negative_inventory_and_rod_positive(self):
        spec = task()
        spec["goal"]["required"].remove(["carrying", "keys"])
        spec["goal"]["required"].append(["carrying", "rod"])
        spec["goal"]["forbidden"] = [["carrying", "keys"]]
        rows = ledger()
        rows[8] = row(8, "inventory", "You are currently holding the following:\nBrass lantern\nBlack rod\n\n")
        self.assertEqual(inspect_rows(rows, spec)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
