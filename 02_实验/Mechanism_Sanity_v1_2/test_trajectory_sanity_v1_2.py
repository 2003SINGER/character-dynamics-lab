import json
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


class TrajectorySanityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(HERE / "run_trajectory_sanity_v1_2.py")], check=True)
        cls.payload = json.loads((HERE / "trajectory_results.json").read_text(encoding="utf-8"))

    def test_all_controlled_trajectories_pass(self):
        self.assertEqual(self.payload["invariants"]["A_O_fixed"], True)
        self.assertEqual(self.payload["invariants"]["A_star_read"], False)
        self.assertTrue(all(row["checks"]["all_pass"] for row in self.payload["results"]))

    def test_state_has_inertia_not_instant_reset(self):
        for row in self.payload["results"]:
            states = [step["S_t_plus_1"] for step in row["steps"]]
            self.assertTrue(any(abs(states[0][field] - states[1][field]) > 1e-6 for field in states[0]))
            self.assertTrue(all(0.0 <= state[field] <= 1.0 for state in states for field in state))


if __name__ == "__main__":
    unittest.main()
