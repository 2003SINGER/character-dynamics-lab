import unittest

from tools.planner_p0_v0.integration_v0.tests.test_integration_contract import snapshot
from tools.planner_p0_v0.baseline_gate_v0.sabre_export import render_problem


class BaselineProjectionTests(unittest.TestCase):
    @staticmethod
    def _without_delivery_and_atomic_blocks(text):
        output, skipping = [], False
        for line in text.splitlines():
            if line.startswith("action "):
                skipping = any(name in line for name in
                               ("deliver_shelter(", "get_shelter_kit(", "drop_shelter_kit("))
            if not skipping and not line.startswith("property kit_at(") and not line.startswith("kit_at("):
                output.append(line)
            if skipping and line == "};":
                skipping = False
        return "\n".join(line for line in output if line.strip())

    def test_a_atomizes_delivery_while_b_retains_frozen_macro(self):
        state = snapshot(mode="direct", task={"status": "accepted"})
        atomic = render_problem(state, "A")
        htn = render_problem(state, "B")
        self.assertIn("action get_shelter_kit(source : place)", atomic)
        self.assertIn("action drop_shelter_kit()", atomic)
        self.assertNotIn("action deliver_shelter(", atomic)
        self.assertIn("action deliver_shelter(", htn)
        self.assertNotIn("action get_shelter_kit(", htn)
        self.assertIn("effect: !kit_held(A) & shelter_delivered()", htn)

    def test_shared_monitor_alignment_and_game_model(self):
        state = snapshot(mode="direct", task={"status": "accepted"})
        for variant in ("A", "B"):
            problem = render_problem(state, variant)
            self.assertIn("!knows_storm(actor)", problem)
            self.assertIn("!met_witness()", problem)
            self.assertIn("now() >= cloud_due()", problem)
            self.assertIn("path(Junction, Inn);", problem)
            self.assertIn("action dispatch_task()", problem)
            self.assertIn("shelter_delivered()", problem)

    def test_held_fresh_snapshot_has_identical_held_projection_and_no_item_location_fact(self):
        state = snapshot(mode="direct", task={"status": "active", "held": True}, holder="A")
        state["actors"]["A"]["local_view"]["observation"]["item_location"] = None
        for variant in ("A", "B"):
            problem = render_problem(state, variant)
            self.assertIn("kit_held(A);", problem)
            self.assertFalse(any(line.startswith("kit_at(") for line in problem.splitlines()))
        b = render_problem(state, "B")
        self.assertIn("effect: !kit_held(A) & shelter_delivered()", b)

    def test_common_domain_blocks_are_exactly_equal_outside_delivery_decomposition(self):
        state = snapshot(mode="direct", task={"status": "accepted"})
        a = self._without_delivery_and_atomic_blocks(render_problem(state, "A"))
        b = self._without_delivery_and_atomic_blocks(render_problem(state, "B"))
        self.assertEqual(a, b)

    def test_atomic_get_drop_each_advance_one_world_minute(self):
        problem = render_problem(snapshot(mode="direct", task={"status": "accepted"}), "A")
        self.assertIn("kit_at(source) & !kit_held(A) & now() < 24", problem)
        self.assertIn("kit_held(A) & !shelter_delivered() & now() < 24", problem)
        self.assertIn("effect: !kit_at(source) & kit_held(A) & now() = now() + 1;", problem)
        self.assertIn("effect: !kit_held(A) & shelter_delivered() & now() = now() + 1;", problem)

    def test_temporal_depth_limit_is_not_described_as_world_minutes(self):
        from pathlib import Path
        readme = Path(__file__).parents[1].joinpath("README.md").read_text()
        self.assertIn("Sabre `--cost t` is Sabre's temporal progression-depth measure", readme)
        self.assertIn("not proof of the native 24-minute deadline", readme)


if __name__ == "__main__":
    unittest.main()
