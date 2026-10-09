import unittest
from copy import deepcopy

from e0_keyledger_v0.executor import Executor, _checkpoint_copy, intent
from e0_keyledger_v0.fixtures import CASE_IDS, initial_checkpoint
from e0_keyledger_v0.monitor_bridge import evaluate_goal
from e0_keyledger_v0.runner import _audit_transition, _forecast_transition


def _assert_alias_topology(testcase, source, clone):
    forward, reverse = {}, {}

    def visit(left, right):
        if type(left) not in (dict, list):
            return
        testcase.assertIs(type(left), type(right))
        left_id, right_id = id(left), id(right)
        if left_id in forward:
            testcase.assertEqual(forward[left_id], right_id)
            return
        if right_id in reverse:
            testcase.assertEqual(reverse[right_id], left_id)
            return
        forward[left_id], reverse[right_id] = right_id, left_id
        if type(left) is dict:
            testcase.assertEqual(list(left), list(right))
            for key in left:
                visit(left[key], right[key])
        else:
            testcase.assertEqual(len(left), len(right))
            for left_item, right_item in zip(left, right):
                visit(left_item, right_item)

    visit(source, clone)


def _assert_graph_equivalent(testcase, source, clone):
    seen = {}

    def visit(left, right):
        if type(left) in (dict, list):
            testcase.assertIs(type(left), type(right))
            left_id, right_id = id(left), id(right)
            if left_id in seen:
                testcase.assertEqual(seen[left_id], right_id)
                return
            seen[left_id] = right_id
            if type(left) is dict:
                testcase.assertEqual(list(left), list(right))
                for key in left:
                    visit(left[key], right[key])
            else:
                testcase.assertEqual(len(left), len(right))
                for left_item, right_item in zip(left, right):
                    visit(left_item, right_item)
        elif type(left) in (str, int, float, bool, type(None)):
            testcase.assertEqual(left, right)
        else:
            testcase.assertIs(type(left), type(right))
            testcase.assertIsNot(left, right)

    visit(source, clone)


def _successful_checkpoint():
    executor = Executor(initial_checkpoint("E0-P01"))
    executor.execute(intent("offer_loan", target="B", payment="payment"))
    offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
    for action in (
        intent("choose_accept", offer_id=offer_id),
        intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id),
        intent("unlock", item="key1"),
        intent("take_ledger", item="ledger"),
    ):
        receipt = executor.execute(action)
        if not receipt["accepted"] or receipt["status"] != "SUCCESS":
            raise AssertionError("expected successful prefix action: " + repr(receipt))
    return executor.checkpoint()


def _mid_unlock_checkpoint():
    executor = Executor(initial_checkpoint("E0-P02"))
    executor.execute(intent("offer_loan", target="B", payment="payment"))
    offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
    executor.execute(intent("choose_accept", offer_id=offer_id))
    executor.execute(intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id))
    executor.start(intent("unlock", item="key1"))
    executor.advance_minute()
    return executor.checkpoint()


class ExecutorBoundaryTests(unittest.TestCase):
    def test_u01_canonical_checkpoint_and_monitor_bridge_agree(self):
        checkpoint = initial_checkpoint("E0-U01")
        self.assertEqual([seal["sealed_through"] for seal in checkpoint["seals"]], [1, 2])
        self.assertEqual(checkpoint["monitor"]["status"], "PENDING")
        self.assertEqual(evaluate_goal(checkpoint)["status"], checkpoint["monitor"]["status"])

        evidence_copy = deepcopy(checkpoint)
        evidence_copy["seals"] = []
        self.assertEqual(evaluate_goal(evidence_copy)["status"], "INDETERMINATE")
        self.assertEqual([seal["sealed_through"] for seal in checkpoint["seals"]], [1, 2])

    def test_malformed_idle_is_rejected_without_world_change(self):
        executor = Executor(initial_checkpoint("E0-P01"))
        before = executor.checkpoint()["W"]
        receipt = executor.start({"operator": "idle", "actor": "A", "args": {"extra": "bad"}})
        self.assertFalse(receipt["accepted"])
        self.assertEqual(receipt["status"], "REJECTED")
        self.assertEqual(receipt["outcome"], "INVALID_TYPED_INTENT")
        self.assertEqual(executor.checkpoint()["W"], before)

    def test_valid_idle_forecast_matches_explicit_empty_observation_delta(self):
        before = initial_checkpoint("E0-H02")
        action = intent("idle")
        receipt, after, prediction = _forecast_transition(before, action)
        self.assertEqual(receipt["status"], "SUCCESS")
        self.assertEqual(receipt["delta_o"], {
            who: {field: {"added": [], "removed": []}
                  for field in ("known_entities", "known_facts")}
            for who in ("A", "B")
        })
        audit = _audit_transition(before, after, receipt, prediction)
        self.assertEqual(audit["status"], "MATCH", audit)

    def test_checkpoint_copier_matches_deepcopy_for_all_fixtures_and_real_histories(self):
        checkpoints = [initial_checkpoint(case_id) for case_id in CASE_IDS]
        checkpoints.extend((_successful_checkpoint(), _mid_unlock_checkpoint()))
        for index, source in enumerate(checkpoints):
            with self.subTest(index=index, fixture=source.get("fixture_id")):
                expected = deepcopy(source)
                copied = _checkpoint_copy(source)
                executor_snapshot = Executor(source).checkpoint()
                self.assertEqual(copied, expected)
                _assert_alias_topology(self, source, expected)
                _assert_alias_topology(self, source, copied)
                self.assertEqual(executor_snapshot, expected)
                _assert_alias_topology(self, source, executor_snapshot)
                copied["O"]["A"]["known_facts"].append("COPY_ONLY")
                self.assertNotIn("COPY_ONLY", source["O"]["A"]["known_facts"])

        successful = _successful_checkpoint()
        exchange = next(row for row in successful["receipts"]
                        if row["intent"]["operator"] == "accept_loan")
        self.assertIs(exchange["delta_w"]["holders"][1], successful["W"]["holders"])
        final_receipt = successful["receipts"][-1]
        self.assertIs(successful["outcome_history"][-1]["event_ids"], final_receipt["event_ids"])
        copied_success = _checkpoint_copy(successful)
        copied_exchange = next(row for row in copied_success["receipts"]
                               if row["intent"]["operator"] == "accept_loan")
        self.assertIs(copied_exchange["delta_w"]["holders"][1], copied_success["W"]["holders"])
        self.assertIs(copied_success["outcome_history"][-1]["event_ids"],
                      copied_success["receipts"][-1]["event_ids"])

    def test_checkpoint_copier_preserves_container_aliases_and_cycles(self):
        shared = []
        source = {"tuple_before_list": (shared,), "left": shared, "right": shared}
        source["self"] = source
        copied = _checkpoint_copy(source)
        expected = deepcopy(source)
        _assert_graph_equivalent(self, source, copied)
        _assert_graph_equivalent(self, source, expected)
        self.assertIs(copied["self"], copied)
        self.assertIs(copied["left"], copied["right"])
        self.assertIs(copied["left"], copied["tuple_before_list"][0])
        _assert_alias_topology(self, source, copied)

    def test_checkpoint_copier_falls_back_for_non_json_values_and_subclasses(self):
        class Payload:
            def __init__(self, value):
                self.value = value

        class ListSubclass(list):
            pass

        shared = [1, 2]
        payload = Payload(shared)
        subclass = ListSubclass(["kept-type"])
        source = {"payload": payload, "payload_again": payload,
                  "shared": shared, "subclass": subclass}
        copied = _checkpoint_copy(source)
        expected = deepcopy(source)
        self.assertEqual(copied["payload"].value, expected["payload"].value)
        self.assertEqual(copied["subclass"], expected["subclass"])
        self.assertIsNot(copied["payload"], payload)
        self.assertIs(copied["payload"], copied["payload_again"])
        self.assertIs(copied["payload"].value, copied["shared"])
        self.assertIsNot(copied["payload"].value, shared)
        self.assertIs(type(copied["subclass"]), ListSubclass)
        copied["payload"].value.append(3)
        self.assertEqual(payload.value, [1, 2])

    def _assert_advance_snapshot_parity_and_isolation(self, label, checkpoint, action=None):
        original = deepcopy(checkpoint)
        branch = Executor(checkpoint)
        if action is None:
            returned = branch.advance_minute()
        else:
            started = branch.start(action)
            self.assertTrue(started["accepted"], (label, started))
            returned = branch.advance_minute(started_action_id=started["action_id"])
        legacy_snapshot = branch.checkpoint()
        self.assertEqual(returned, legacy_snapshot, label)
        _assert_alias_topology(self, branch._c, returned)

        snapshot_time = returned["clock"]["now"]
        returned["W"]["holders"]["ledger"] = "SNAPSHOT_ONLY"
        returned["O"]["A"]["known_facts"].append("SNAPSHOT_ONLY")
        returned["action_history"][-1]["status"] = "SNAPSHOT_ONLY"
        returned["minute_history"][-1]["control"] = "SNAPSHOT_ONLY"
        returned["receipts"][-1]["delta_w"]["SNAPSHOT_ONLY"] = [False, True]
        returned["receipts"][-1]["event_payloads"].append({"event_id": "SNAPSHOT_ONLY"})
        returned["events"][-1]["typed_args"]["actor"] = "SNAPSHOT_ONLY"
        returned["outcome_history"][-1]["event_ids"].append("SNAPSHOT_ONLY")
        returned["seals"][-1]["sequence_frontier"] = -999
        returned["monitor"]["status"] = "SNAPSHOT_ONLY"

        next_snapshot = branch.advance_minute()
        live = branch.checkpoint()
        self.assertEqual(next_snapshot, live, label)
        self.assertNotEqual(live["clock"]["now"], snapshot_time)
        self.assertNotEqual(live["W"]["holders"]["ledger"], "SNAPSHOT_ONLY")
        self.assertNotIn("SNAPSHOT_ONLY", live["O"]["A"]["known_facts"])
        self.assertNotEqual(live["action_history"][-1]["status"], "SNAPSHOT_ONLY")
        self.assertNotEqual(live["minute_history"][-2]["control"], "SNAPSHOT_ONLY")
        self.assertNotIn("SNAPSHOT_ONLY", live["receipts"][-1]["delta_w"])
        self.assertNotIn("SNAPSHOT_ONLY", [event.get("event_id") for event in live["events"]])
        self.assertNotIn("SNAPSHOT_ONLY", live["outcome_history"][-1]["event_ids"])
        self.assertNotEqual(live["seals"][-2]["sequence_frontier"], -999)
        self.assertNotEqual(live["monitor"]["status"], "SNAPSHOT_ONLY")
        self.assertEqual(returned["clock"]["now"], snapshot_time)
        self.assertEqual(returned["W"]["holders"]["ledger"], "SNAPSHOT_ONLY")
        self.assertEqual(checkpoint, original)

    def test_advance_return_matches_legacy_snapshot_for_idle_actor_and_mid_r(self):
        self._assert_advance_snapshot_parity_and_isolation(
            "idle", initial_checkpoint("E0-H02"))

        actor_base = Executor(initial_checkpoint("E0-P01"))
        actor_base.execute(intent("offer_loan", target="B", payment="payment"))
        offer_id = actor_base.checkpoint()["W"]["offer_session"]["offer_id"]
        self._assert_advance_snapshot_parity_and_isolation(
            "actor_start", actor_base.checkpoint(), intent("choose_accept", offer_id=offer_id))

        self._assert_advance_snapshot_parity_and_isolation(
            "mid_R", _mid_unlock_checkpoint())

    def test_settlement_revalidates_resources_and_releases_reservation(self):
        executor = Executor(initial_checkpoint("E0-P02"))
        offer = executor.execute(intent("offer_loan", target="B", payment="payment"))
        self.assertEqual(offer["status"], "SUCCESS")
        offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        self.assertEqual(executor.execute(intent("choose_accept", offer_id=offer_id))["status"], "SUCCESS")
        self.assertEqual(executor.execute(intent("accept_loan", actor="A", item="key1",
                                                 payment="payment", offer_id=offer_id))["status"], "SUCCESS")
        started = executor.start(intent("unlock", item="key1"))
        self.assertTrue(started["accepted"])
        started_checkpoint = executor.checkpoint()
        running = started_checkpoint["W"]["running_action"]
        self.assertEqual(running["id"], started["action_id"])
        self.assertEqual(started_checkpoint["W"]["reservations"][0]["action_id"], started["action_id"])

        # Simulate a world-side resource change after start but before settlement.
        executor._c["W"]["holders"]["key1"] = None
        executor._c["W"]["destroyed"]["key1"] = True
        executor._c["W"]["intact"]["key1"] = False
        executor.advance_minute()
        executor.advance_minute()
        checkpoint = executor.advance_minute()
        receipt = next(row for row in checkpoint["receipts"] if row["receipt_id"] == started["receipt_id"])

        self.assertEqual(receipt["status"], "INTERRUPTED")
        self.assertEqual(receipt["outcome"], "INTERRUPTED_NO_EFFECT")
        self.assertEqual(receipt["delta_w"], {})
        self.assertEqual(receipt["event_ids"], [])
        self.assertFalse(checkpoint["W"]["archive_open"])
        self.assertFalse(checkpoint["W"]["action_used_bits"]["unlock"])
        self.assertIsNone(checkpoint["W"]["running_action"])
        self.assertEqual(checkpoint["W"]["reservations"], [])


if __name__ == "__main__":
    unittest.main()
