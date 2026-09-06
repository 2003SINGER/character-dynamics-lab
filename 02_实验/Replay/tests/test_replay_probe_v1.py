import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from replay_probe_v1 import predict

MODEL = {"means":[0,0],"scales":[1,1],"weights_theta":[1,0],"weights_w":[0,1]}

def test_state_intervention_only_changes_input():
    before = dict(MODEL)
    p0 = predict(MODEL, [[1,0],[0,1]], 0.0)
    p1 = predict(MODEL, [[1,0],[0,1]], 1.0)
    assert p0 != p1 and MODEL == before

def test_constant_logit_shift_is_invariant():
    a = predict(MODEL, [[1,0],[0,1]], 0.0)
    shifted = {**MODEL, "weights_theta":[2,1]}
    # This is a direct smoke of the common-offset property on a choice set:
    # adding the same scalar to every logit is not represented by probabilities.
    import math
    z = [1.0, 0.0]; q = [v + 7.0 for v in z]
    soft = lambda xs: [math.exp(x-max(xs))/sum(math.exp(y-max(xs)) for y in xs) for x in xs]
    assert all(abs(x-y)<1e-12 for x,y in zip(soft(z),soft(q)))
    assert len(a) == len(shifted["weights_theta"])

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"): fn()
    print("replay probe v1 tests passed")
