import unittest
from research_dynamics_v1 import State, MODEL_ID, run_intervention

class ResearchDynamicsV1Test(unittest.TestCase):
    def test_accumulation_and_recovery(self):
        s = State(); s.step(minutes=60, action="study", deadline_signal=1)
        self.assertGreater(s.fatigue, 0); self.assertGreater(s.task_pressure, 0)
        before = s.fatigue; s.step(minutes=60, action="sleep")
        self.assertLess(s.fatigue, before)

    def test_intervention_changes_only_declared_path(self):
        zero = run_intervention("zero")["final_state"]
        perm = run_intervention("permuted")["final_state"]
        self.assertNotEqual(zero, perm)

    def test_bounds_and_identity(self):
        s = State(); s.step(minutes=10000, action="study", deadline_signal=1)
        self.assertTrue(all(0 <= v <= 1 for v in vars(s).values()))
        self.assertEqual(MODEL_ID, "ResearchDynamicsV1")

if __name__ == "__main__": unittest.main()
