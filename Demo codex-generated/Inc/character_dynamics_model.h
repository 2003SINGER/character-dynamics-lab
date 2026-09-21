#pragma once

#include "appraisal.h"
#include "decision.h"
#include "state.h"

#include <string>

// A Dynamics Model owns the subjective condition for reconsideration.  The
// Runtime merely opens a generic decision gate and preserves the current
// RunningAction unless policy explicitly replaces it.
struct DynamicsReconsideration {
    bool requested = false;
    std::string reason;
};

// Replaceable behavior-law slot. The Runtime owns time, W/O, boundaries,
// validation, and policy sampling; a model owns X/U/S evolution and π
// construction. Implementations must not read hidden World state.
class CharacterDynamicsModel {
public:
    virtual ~CharacterDynamicsModel() = default;
    virtual StateUpdate advance_continuous(CharacterState& state,
                                           const Observation& observation,
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
    virtual DynamicsReconsideration reconsider_running_action(
        const Observation&, const CharacterState&, const CharacterState&,
        const RunningAction&, const Personality&) const { return {}; }
};
