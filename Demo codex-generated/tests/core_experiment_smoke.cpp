#include "candidate_scoring.h"
#include <cmath>
#include <iostream>
int main(){
 Personality p; CharacterState s; Appraisal a; a.semantic_signals.push_back({AppraisalSignalKind::GoalCompletion,1,1,1,1,"fixture"}); auto u=update_state(s,a,p,0);
 if(!(u.semantic_contribution.task_pressure<0 && s.task_pressure<.55)){std::cerr<<"X-U-S failed\n";return 1;}
 auto scores=score_external_candidates({{"work",{1,0,0,0,0,0,0},0},{"scroll",{0,1,0,0,0,0,0},0}},s,p); double z=0; for(auto& x:scores)z+=x.probability; if(scores.size()!=2||std::abs(z-1)>1e-9)return 1; std::cout<<"core experiment smoke OK\n";
}
