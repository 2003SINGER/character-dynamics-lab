#pragma once

#include "appraisal.h"
#include "decision.h"
#include "state.h"

// Replaceable behavior-law slot. The Runtime owns time, W/O, boundaries,
// validation, and policy sampling; a model owns X/U/S evolution and π
// construction. Implementations must not read hidden World state.
class CharacterDynamicsModel {
public:
    virtual ~CharacterDynamicsModel() = default;
    virtual StateUpdate advance_continuous(CharacterState& state,
                                           const Personality& personality,
                                           const RunningAction* running_action,
                                           int elapsed_minutes) const = 0;
    virtual Appraisal appraise(const Observation& observation,
                               const CharacterState& state,
                               const Personality& personality) const = 0;
    virtual StateUpdate apply_impulse(CharacterState& state,
                                      const Appraisal& appraisal,
                                      const Personality& personality) const = 0;
    virtual void update_persistent_intention(CharacterState& state,
                                              const Observation& observation,
                                              int settled_at_total_minutes) const = 0;
    virtual DecisionContext build_policy(const Observation& observation,
                                         const CharacterState& state,
                                         const Personality& personality) const = 0;
    virtual const char* identity() const = 0;
};
