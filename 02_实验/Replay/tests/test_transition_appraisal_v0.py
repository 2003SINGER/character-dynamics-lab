import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
import transition_appraisal_v0 as ta

def snap(place="room", entities=None, possessions=None, obs="sword"):
    return {"place": place, "entities": ([{"id":"sword","label":"sword","facts":{}}] if entities is None else entities), "possessions": possessions or [], "actor_observation": obs}

def test_same_empty(): assert ta.diff_scene_snapshots(snap(), snap()) == []
def test_possession_added():
    e=ta.diff_scene_snapshots(snap(), snap(possessions=[{"entity":"sword","relation":"carrying"}]))
    assert [x["kind"] for x in e] == ["possession_added"]
def test_entity_left(): assert ta.diff_scene_snapshots(snap(), snap(entities=[]))[0]["kind"] == "entity_left_scene"
def test_hidden_source_not_present(): assert ta.diff_scene_snapshots(snap(), snap()) == []
def test_unconfirmed_not_obstruction():
    x=ta.appraise_transition(snap(), snap(obs=""), "take sword")
    assert x["negative_conduciveness"] == 0.0 and x["goal_relevance"] == 1.0
def test_positive_negative_channels():
    s=ta.zero_state(); s=ta.update_state(s,{"goal_relevance":1,"positive_conduciveness":1,"negative_conduciveness":1})
    assert s["positive_conduciveness_trace"] > 0 and s["negative_conduciveness_trace"] > 0

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"): fn()
    print("transition appraisal tests passed")
