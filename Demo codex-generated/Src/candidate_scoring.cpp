#include "candidate_scoring.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
std::vector<ExternalCandidateScore> score_external_candidates(const std::vector<ExternalCandidate>& cs,const CharacterState& s,const Personality& p){
 if(cs.empty()) throw std::invalid_argument("external candidate set is empty");
 double task=s.task_pressure*(.7+.8*p.self_control)+.2*s.anxiety, distract=.65*s.boredom+.25*p.procrastination+.2*p.stimulation_seeking, recover=.75*s.fatigue+.5*s.screen_strain+.18*p.rest_preference, hunger=s.hunger*(.85+.25*p.need_response), bath=s.bathroom_urge*(.9+.2*p.need_response), temp=std::max(.05,.45+p.action_noise), mx=-INFINITY;
 std::vector<ExternalCandidateScore> out; for(auto& c:cs){auto& f=c.semantics; double a=c.bias+f.goal_progress*task+f.stimulation*distract+f.recovery*recover+f.hunger_relief*hunger+f.bathroom_relief*bath+f.short_term_reward*(.35+.65*s.purchase_urge)+f.environment_control*(.15*task+.1*recover); out.push_back({c.id,a,0}); mx=std::max(mx,a/temp);} double z=0; for(auto& x:out){x.probability=std::exp(x.activation/temp-mx); z+=x.probability;} for(auto& x:out)x.probability/=z; return out;
}
