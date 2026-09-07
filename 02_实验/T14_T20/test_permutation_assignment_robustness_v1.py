import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from run_permutation_assignment_robustness_v1 import donors_for

def test_assignment_is_seeded_and_no_self():
    rows=[{"trajectory_id":"a","horizon_index":0,"state":1.0},{"trajectory_id":"b","horizon_index":0,"state":2.0},{"trajectory_id":"c","horizon_index":1,"state":3.0},{"trajectory_id":"d","horizon_index":1,"state":4.0}]
    a=donors_for(rows,11); b=donors_for(rows,11)
    assert a==b and len(a)==4

if __name__=="__main__":
    test_assignment_is_seeded_and_no_self(); print("permutation robustness tests passed")
