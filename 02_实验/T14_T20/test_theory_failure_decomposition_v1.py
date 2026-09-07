import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from run_theory_failure_decomposition_v1 import row_analysis, corr

def test_row_loss_decomposition_and_correlations():
    model={"weights_theta":[0.0,0.0],"weights_w":[1.0,-1.0],"means":[0.0,0.0],"scales":[1.0,1.0]}
    row={"features":[[1.0,0.0],[0.0,1.0]],"gold_index":0,"state":0.5,"fresh_signal":1.0}
    out=row_analysis(model,row)
    assert out["correct_nll"] < out["base_nll"] and out["zero_delta"] > 0
    assert out["s_opt"] >= 0
    assert corr([0.0,1.0],[1.0,0.0])["pearson"] == -1.0

if __name__=="__main__":
    test_row_loss_decomposition_and_correlations(); print("theory decomposition tests passed")
