#include "demo_living_dynamics_v1.h"
#include "living_dynamics.h"
#include "runtime_scheduler.h"

namespace DemoLivingV0 {
StateUpdate advance_continuous_state(CharacterState&, const Observation&, const Personality&, const RunningAction*, int, const ParameterConfig&);
Appraisal appraise(const Observation&, const CharacterState&, const Personality&);
StateUpdate apply_appraisal_impulse(CharacterState&, const Appraisal&, const Personality&, const ParameterConfig&);
void update_commitment(CharacterState&, const Observation&, int);
DecisionContext decide(const Observation&, const CharacterState&, const Personality&, const ParameterConfig&);
}

StateUpdate DemoLivingDynamicsV1::advance_continuous(CharacterState& s, const Observation& o, const Personality& p, const RunningAction* a, int m) const {
    return DemoLivingV0::advance_continuous_state(s, o, p, a, m, ParameterConfig::defaults());
}
Appraisal DemoLivingDynamicsV1::appraise(const Observation& o, const CharacterState& s, const Personality& p) const { return DemoLivingV0::appraise(o, s, p); }
StateUpdate DemoLivingDynamicsV1::apply_impulse(CharacterState& s, const Appraisal& a, const Personality& p) const { return DemoLivingV0::apply_appraisal_impulse(s, a, p, ParameterConfig::defaults()); }
void DemoLivingDynamicsV1::update_persistent_intention(CharacterState& s, const Observation& o, int t) const { DemoLivingV0::update_commitment(s, o, t); }
DecisionContext DemoLivingDynamicsV1::build_policy(const Observation& o, const CharacterState& s, const Personality& p) const { return DemoLivingV0::decide(o, s, p, ParameterConfig::defaults()); }
DynamicsReconsideration DemoLivingDynamicsV1::reconsider_running_action(
    const Observation&, const CharacterState& before, const CharacterState& after,
    const RunningAction& action, const Personality& personality) const {
    const double urgent_threshold=LivingDynamics::urgent_bodily_need_threshold(personality);
    const bool urgent_hunger=LivingDynamics::perceived_hunger(before,personality)<urgent_threshold
        && LivingDynamics::perceived_hunger(after,personality)>=urgent_threshold;
    const bool urgent_bathroom=LivingDynamics::perceived_bathroom(before,personality)<urgent_threshold
        && LivingDynamics::perceived_bathroom(after,personality)>=urgent_threshold;
    if (urgent_hunger || urgent_bathroom) return {true, urgent_hunger ? "urgent_hunger" : "urgent_bathroom"};
    if (action.action==ActionType::SleepAtBed && before.fatigue>.45 && after.fatigue<=.45)
        return {true,"sleep_recovery_satisfied"};
    return {};
}
