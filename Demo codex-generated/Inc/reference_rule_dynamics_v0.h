#pragma once
#include "character_dynamics_model.h"

class ReferenceRuleDynamicsV0 final : public CharacterDynamicsModel {
public:
    StateUpdate advance_continuous(CharacterState&, const Personality&, const RunningAction*, int) const override;
    Appraisal appraise(const Observation&, const CharacterState&, const Personality&) const override;
    StateUpdate apply_impulse(CharacterState&, const Appraisal&, const Personality&) const override;
    void update_persistent_intention(CharacterState&, const Observation&, int) const override;
    DecisionContext build_policy(const Observation&, const CharacterState&, const Personality&) const override;
    const char* identity() const override { return "reference-rule-v0"; }
};
