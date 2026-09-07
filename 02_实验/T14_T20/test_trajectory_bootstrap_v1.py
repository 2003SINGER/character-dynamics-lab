import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from run_trajectory_bootstrap_v1 import trajectory_bootstrap

def test_bootstrap_resamples_trajectories_not_rows():
    rows=[{"trajectory_id":"a"},{"trajectory_id":"a"},{"trajectory_id":"b"}]
    result=trajectory_bootstrap(rows,[1.0,3.0,5.0],seed=7,replicates=100)
    assert result["rows"]==3 and result["trajectories"]==2
    assert result["point_estimate"]==3.0
    assert 0.0 <= result["fraction_positive"] <= 1.0

if __name__=="__main__":
    test_bootstrap_resamples_trajectories_not_rows(); print("trajectory bootstrap tests passed")
