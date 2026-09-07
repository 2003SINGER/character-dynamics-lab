from __future__ import annotations
import sys
import unittest
from pathlib import Path
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "Replay"))
from theory_s_v2 import FEATURE_NAMES, TheoryS, synthetic_gradient_smoke, unroll
from replay_features_v1 import FEATURE_NAMES as CANONICAL_FEATURE_NAMES


class TheorySV2Tests(unittest.TestCase):
    def test_canonical_feature_basis(self):
        self.assertEqual(FEATURE_NAMES, CANONICAL_FEATURE_NAMES)

    def test_neutral_relaxation_and_bounds(self):
        m = TheoryS(); state = torch.tensor([[.2, .8, .1]])
        nxt = m.transition(state, torch.zeros(1, 6))
        self.assertTrue(bool(torch.all((nxt >= 0) & (nxt <= 1))))
        self.assertGreater(float(nxt[0, 0].detach()), .2); self.assertLess(float(nxt[0, 1].detach()), .8)
        self.assertTrue(bool(torch.all(m.alpha > 0)))

    def test_phase_a_and_b_freezing(self):
        m = TheoryS(); m.set_phase("A")
        self.assertTrue(m.theta.requires_grad); self.assertFalse(m.beta.requires_grad)
        m.set_phase("B")
        self.assertFalse(m.theta.requires_grad); self.assertTrue(m.beta.requires_grad)

    def test_current_gold_is_not_an_input(self):
        m = TheoryS(); state = torch.full((1, 3), .4); x = torch.full((1, 6), .3)
        features = torch.rand(1, 4, len(FEATURE_NAMES)); s1, z1 = m(state, x, features); s2, z2 = m(state, x, features)
        self.assertTrue(torch.equal(s1, s2)); self.assertTrue(torch.equal(z1, z2))

    def test_multistep_candidate_nll_smoke(self):
        result = synthetic_gradient_smoke()
        self.assertTrue(result["candidate_nll"]); self.assertTrue(result["multi_step"])
        self.assertLess(result["final_nll"], result["initial_nll"])
        self.assertTrue(all(v > 0 for v in result["gradient_path"].values()))

    def test_detaching_history_changes_earlier_gradient_path(self):
        torch.manual_seed(4); m = TheoryS(); m.set_phase("B")
        with torch.no_grad(): m.w_sa.uniform_(-.2, .2)
        x = torch.rand(5, 1, 6); f = torch.rand(5, 1, 4, len(FEATURE_NAMES)); y = torch.zeros(5, 1, dtype=torch.long)
        _, loss = unroll(m, torch.zeros(1, 3), x, f, y); loss.backward(); full = m.beta.grad.clone()
        m.zero_grad(); _, loss_detached = unroll(m, torch.zeros(1, 3), x, f, y, detach_state=True); loss_detached.backward()
        self.assertIsNone(m.beta.grad)
        self.assertGreater(float(full.norm()), 0.0)


if __name__ == "__main__":
    unittest.main()
