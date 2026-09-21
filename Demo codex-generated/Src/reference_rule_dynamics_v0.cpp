#include "reference_rule_dynamics_v0.h"

StateUpdate ReferenceRuleDynamicsV0::advance_continuous(CharacterState& s, const Observation&, const Personality& p,
                                                         const RunningAction* a, int minutes) const {
    return ::advance_continuous_state(s, p, a, minutes);
}
Appraisal ReferenceRuleDynamicsV0::appraise(const Observation& o, const CharacterState& s,
                                            const Personality& p) const { return ::appraise(o, s, p); }
StateUpdate ReferenceRuleDynamicsV0::apply_impulse(CharacterState& s, const Appraisal& a,
                                                   const Personality& p) const { return ::apply_appraisal_impulse(s, a, p); }
void ReferenceRuleDynamicsV0::update_persistent_intention(CharacterState& s, const Observation& o, int t) const {
    ::update_commitment(s, o, t);
}
DecisionContext ReferenceRuleDynamicsV0::build_policy(const Observation& o, const CharacterState& s,
                                                      const Personality& p) const { return ::decide(o, s, p); }
