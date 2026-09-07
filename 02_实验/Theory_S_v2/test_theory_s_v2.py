from __future__ import annotations

import unittest
import torch

from theory_s_v2 import (ACTION_FEATURES, STATE_FIELDS, X_FIELDS, TheoryS,
                         permuted_s, synthetic_gradient_smoke)


class TheorySV2Tests(unittest.TestCase):
    def test_shapes_bounds_and_fixed_signs(self):
        m = TheoryS()
        state = torch.full((2, 3), .5)
        x = torch.full((2, 6), .5)
        ns = m.transition(state, x)
        self.assertEqual(ns.shape, (2, 3))
        self.assertTrue(bool(torch.all((ns >= 0) & (ns <= 1))))
        self.assertTrue(bool(torch.all(m.w_xs[m.topology_xs > 0] >= 0)))
        self.assertTrue(bool(torch.all(m.w_xs[m.topology_xs < 0] <= 0)))

    def test_permuted_control_equal_capacity(self):
        m, p = TheoryS(), permuted_s()
        self.assertEqual(m.parameter_count(), p.parameter_count())
        self.assertEqual(int((m.topology_xs != 0).sum()), int((p.topology_xs != 0).sum()))
        self.assertEqual(int((m.topology_sa != 0).sum()), int((p.topology_sa != 0).sum()))
        self.assertNotEqual(m.topology_xs.tolist(), p.topology_xs.tolist())

    def test_smoke_gradient_path(self):
        result = synthetic_gradient_smoke()
        self.assertTrue(result["bounded_state"])
        self.assertTrue(result["no_candidate_leakage"])
        self.assertTrue(all(v > 0 for v in result["gradient_path"].values()))


if __name__ == "__main__":
    unittest.main()
