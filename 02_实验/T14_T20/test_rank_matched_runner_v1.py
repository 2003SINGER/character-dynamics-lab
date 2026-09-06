import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import run_rank_matched_probe_v1 as runner

RULES=json.loads((Path(__file__).parents[1]/"T0c_LIGHT"/"compiled_semantics_v1.json").read_text(encoding="utf8"))
def rec():
    ctx=lambda carrying=None: {"actor":"a","room_objects":["sword"],"room_agents":[],"carrying":carrying or [],"wearing":[],"wielding":[]}
    return {"source_dataset":"LIGHT","trajectory_id":"t","source_episode_context":{"setting":{"name":"room"}},"steps":[
        {"t":0,"source_action_A_star":"take sword","source_O":"sword","candidate_set_factual":["take sword","look"],"source_step_context":ctx()},
        {"t":1,"source_action_A_star":None,"source_O":"sword","candidate_set_factual":[],"source_step_context":ctx(["sword"])},
        {"t":2,"source_action_A_star":"look","source_O":"sword","candidate_set_factual":["look","hug sword"],"source_step_context":ctx(["sword"])}]}

def test_current_state_uses_same_t_update_and_unscorable_step():
    rows=runner.state_rows(rec(),RULES); t2=[r for r in rows if r["horizon_index"]==2 and r["kind"]=="theory"][0]
    assert t2["state"] > 0.0

if __name__ == "__main__":
    test_current_state_uses_same_t_update_and_unscorable_step(); print("runner timing tests passed")
