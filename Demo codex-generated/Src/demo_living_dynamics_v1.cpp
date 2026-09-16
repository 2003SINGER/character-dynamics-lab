#include "demo_living_dynamics_v1.h"

namespace DemoLivingV0 {
StateUpdate advance_continuous_state(CharacterState&, const Personality&, const RunningAction*, int, const ParameterConfig&);
Appraisal appraise(const Observation&, const CharacterState&, const Personality&);
StateUpdate apply_appraisal_impulse(CharacterState&, const Appraisal&, const Personality&, const ParameterConfig&);
void update_commitment(CharacterState&, const Observation&, int);
DecisionContext decide(const Observation&, const CharacterState&, const Personality&, const ParameterConfig&);
}

StateUpdate DemoLivingDynamicsV1::advance_continuous(CharacterState& s, const Personality& p, const RunningAction* a, int m) const {
    return DemoLivingV0::advance_continuous_state(s, p, a, m, ParameterConfig::defaults());
}
Appraisal DemoLivingDynamicsV1::appraise(const Observation& o, const CharacterState& s, const Personality& p) const { return DemoLivingV0::appraise(o, s, p); }
StateUpdate DemoLivingDynamicsV1::apply_impulse(CharacterState& s, const Appraisal& a, const Personality& p) const { return DemoLivingV0::apply_appraisal_impulse(s, a, p, ParameterConfig::defaults()); }
void DemoLivingDynamicsV1::update_persistent_intention(CharacterState& s, const Observation& o, int t) const { DemoLivingV0::update_commitment(s, o, t); }
DecisionContext DemoLivingDynamicsV1::build_policy(const Observation& o, const CharacterState& s, const Personality& p) const { return DemoLivingV0::decide(o, s, p, ParameterConfig::defaults()); }
