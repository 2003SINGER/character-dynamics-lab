import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from replay_features_v1 import FEATURE_NAMES, FEATURE_VERSION, compile_candidate_v1, vectorize

RULES = {"groups": [{"name":"manipulation", "verbs":["take"], "features":{"goal_progress":0.6,"environment_control":0.2}}]}
SNAP = {"actor_observation":"sword", "entities":[{"id":"s","label":"sword","facts":{}}], "possessions":[]}

def test_v1_is_raw_and_ordered():
    f, _, flags = compile_candidate_v1("take sword", SNAP, RULES)
    assert list(f) == list(FEATURE_NAMES)
    assert f["goal_progress"] == 1.0 and f["environment_control"] == 1.0
    assert "scene_bias" not in f and flags["contains_scene_bias"] is False
    assert len(vectorize(f)) == len(FEATURE_NAMES)

def test_scene_flags_do_not_change_semantic_tags():
    a, _, _ = compile_candidate_v1("take sword", SNAP, RULES)
    b, _, _ = compile_candidate_v1("take sword", {**SNAP, "entities":[], "actor_observation":""}, RULES)
    for key in ("goal_progress", "stimulation", "recovery", "short_term_reward", "environment_control"):
        assert a[key] == b[key]

def test_current_action_not_an_input():
    f1, _, _ = compile_candidate_v1("take sword", SNAP, RULES)
    f2, _, _ = compile_candidate_v1("take sword", {**SNAP, "source_action_A_star":"hug knight"}, RULES)
    assert f1 == f2 and FEATURE_VERSION == "replay-raw-features-v1"

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"): fn()
    print("replay feature v1 tests passed")
