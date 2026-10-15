from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.author_obligation_planning_v0.conflicts import (
    CONFLICT_PROVED,
    NO_CONFLICT_PROVED,
    static_conflicts,
)
from tools.author_obligation_planning_v0.contracts import (
    EvidenceEvent,
    MaxCount,
    Never,
    TaskSpec,
)
from tools.author_obligation_planning_v0.search import Goal
from tools.open_adventure_planning_v0.domain import initial_state


class StaticConflictTests(unittest.TestCase):
    @staticmethod
    def _task(*, required=(), forbidden=(), obligations=(),
              task_id="manual", always_no_death=False):
        return TaskSpec(
            task_id, "1", "Original author wording",
            Goal(frozenset(required), frozenset(forbidden)),
            tuple(obligations), always_no_death,
        )

    def test_required_and_forbidden_same_literal_has_direct_certificate(self):
        literal = ("carrying", "keys")
        task = SimpleNamespace(
            id="malformed-direct-call", version="1",
            goal=Goal(frozenset({literal}), frozenset({literal})),
            obligations=(), always_no_death=False,
        )
        report = static_conflicts(initial_state(), task)
        self.assertEqual(report["status"], CONFLICT_PROVED)
        proof = next(item for item in report["proofs"]
                     if item["kind"] == "required_and_forbidden_literal")
        self.assertEqual(proof["certificate"]["atoms"], [["carrying", "keys"]])

    def test_mutually_exclusive_goal_values_have_certificate(self):
        task = self._task(required={("bridge",), ("unbridged",)})
        report = static_conflicts(initial_state(), task)
        self.assertEqual(report["status"], CONFLICT_PROVED)
        self.assertIn("mutually_exclusive_required_literals",
                      {proof["kind"] for proof in report["proofs"]})

    def test_bridge_never_conflict_is_proved_without_task_id_special_case(self):
        task = self._task(required={("bridge",)}, obligations=(Never("create_bridge"),),
                          task_id="arbitrary-task-id")
        report = static_conflicts(initial_state(), task)
        self.assertEqual(report["status"], CONFLICT_PROVED)
        proof = next(item for item in report["proofs"]
                     if item["kind"] == "bridge_goal_conflicts_with_never_create")
        cert = proof["certificate"]
        self.assertEqual(cert["projection"]["reachable_without_forbidden_event"], [False])
        self.assertEqual(cert["projection"]["blocked_create_edges"],
                         [{"from": False, "to": True}])
        self.assertTrue(cert["producers"])
        self.assertTrue(all(item["source"] and item["args"] for item in cert["producers"]))
        self.assertEqual(cert["scope"], "frozen finite Open Adventure operator model only")

    def test_present_initial_bridge_does_not_trigger_creation_conflict(self):
        task = self._task(required={("bridge",)}, obligations=(Never("create_bridge"),))
        report = static_conflicts(initial_state(bridge=True), task)
        self.assertEqual(report["status"], NO_CONFLICT_PROVED)
        self.assertEqual(report["proofs"], [])

    def test_prior_never_max_count_and_death_violations_are_irreversible(self):
        initial = initial_state()
        never_task = self._task(required={("bridge",)}, obligations=(Never("create_bridge"),))
        never_report = static_conflicts(
            initial, never_task, (EvidenceEvent("create_bridge", "native-4", 4),))
        self.assertEqual(never_report["status"], CONFLICT_PROVED)
        self.assertIn("already_violated_history_obligation",
                      {proof["kind"] for proof in never_report["proofs"]})

        count_task = self._task(required={("unbridged",)}, obligations=(MaxCount("create_bridge", 1),))
        count_history = (
            EvidenceEvent("create_bridge", "native-5", 5),
            EvidenceEvent("create_bridge", "native-6", 6),
        )
        count_report = static_conflicts(initial, count_task, count_history)
        self.assertEqual(count_report["status"], CONFLICT_PROVED)
        self.assertIn("max_count:create_bridge>1",
                      count_report["history_check"]["violations"])

        death_task = self._task(required={("unbridged",)}, always_no_death=True)
        death_report = static_conflicts(
            initial, death_task, (EvidenceEvent("player_death", "native-7", 7),))
        self.assertEqual(death_report["status"], CONFLICT_PROVED)
        self.assertIn("always_no_death:player_death",
                      death_report["history_check"]["violations"])

    def test_no_certificate_is_not_reported_as_feasibility(self):
        task = self._task(required={("at", "player", "EASTBANK")})
        report = static_conflicts(initial_state(), task)
        self.assertEqual(report["status"], NO_CONFLICT_PROVED)
        self.assertEqual(report["proofs"], [])
        self.assertIn("no proof of whole-game infeasibility", report["scope"])


if __name__ == "__main__":
    unittest.main()
