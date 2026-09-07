import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import run_frozen_base_incremental_v1 as run2
import replay_probe_v1 as probe

def _rows():
    return [
        {"features": [[0.0, 1.0], [1.0, 0.0]], "gold_index": 0, "state": 0.2},
        {"features": [[0.5, 0.2], [0.1, 0.7], [0.0, 0.0]], "gold_index": 1, "state": 0.8},
    ]

def test_zero_w_matches_no_state_probe():
    rows = _rows(); theta = np.array([0.3, -0.2]); means = np.zeros(2); scales = np.ones(2)
    model = {"theta": theta, "w": np.zeros(2), "means": means, "scales": scales}
    ref = {"weights_theta": theta.tolist(), "weights_w": [0.0, 0.0], "means": [0.0, 0.0], "scales": [1.0, 1.0]}
    for row in rows:
        got = run2.predict_frozen(theta, np.zeros(2), means, scales, row["features"], row["state"])
        expected = np.asarray(probe.predict(ref, row["features"], row["state"]))
        assert np.max(np.abs(got - expected)) <= 1e-12
    assert abs(run2.evaluate_frozen(model, rows) - probe.evaluate(ref, rows)) <= 1e-12

def test_fit_w_preserves_theta_and_normalization():
    rows = _rows(); theta = np.array([0.3, -0.2]); means = np.zeros(2); scales = np.ones(2)
    model = run2.fit_w(rows, theta, means, scales, 1e-3)
    assert np.array_equal(model["theta"], theta)
    assert np.array_equal(model["means"], means)
    assert np.array_equal(model["scales"], scales)

def test_donors_are_seeded_and_nonself():
    mapping = run2.cyclic_donors(["a", "b", "c"])
    assert mapping == run2.cyclic_donors(["a", "b", "c"])
    assert all(a != b for a, b in mapping.items())
    assert run2.cyclic_donors(["only"]) == {}

if __name__ == "__main__":
    test_zero_w_matches_no_state_probe(); test_fit_w_preserves_theta_and_normalization(); test_donors_are_seeded_and_nonself(); print("frozen-base tests passed")
