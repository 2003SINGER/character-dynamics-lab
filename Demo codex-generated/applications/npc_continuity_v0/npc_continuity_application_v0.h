#pragma once

#include "character_dynamics_model.h"
#include "character_policy.h"
#include "reference_rule_dynamics_v0.h"

#include <string>

// Application-only candidate contract for the one-room continuity harness.
// S/time/appraisal behavior delegates to the frozen engineering reference;
// this class contributes no action preference or scenario answer.
class NpcContinuityApplicationModelV0 final : public CharacterDynamicsModel {
public:
    StateUpdate advance_continuous(CharacterState&, const Observation&, const Personality&,
                                   const RunningAction*, int) const override;
    Appraisal appraise(const Observation&, const CharacterState&, const Personality&) const override;
    StateUpdate apply_impulse(CharacterState&, const Appraisal&, const Personality&) const override;
    void update_persistent_intention(CharacterState&, const Observation&, int) const override;
    DecisionContext build_policy(const Observation&, const CharacterState&,
                                 const Personality&) const override;
    DynamicsReconsideration reconsider_running_action(const Observation&, const CharacterState&,
        const CharacterState&, const RunningAction&, const Personality&) const override;
    const char* identity() const override { return "npc-continuity-application-v0"; }
private:
    ReferenceRuleDynamicsV0 reference_;
};

// A deliberately small, transparent utility baseline. It reads only O,
// candidate metadata, public RunningAction, and actor-visible ActorHistory.
class UtilityPolicyV0 final : public CharacterPolicy {
public:
    explicit UtilityPolicyV0(double running_action_inertia = 0.14,
                             double recent_action_inertia = 0.08)
        : running_action_inertia_(running_action_inertia),
          recent_action_inertia_(recent_action_inertia) {}
    PolicySelection select(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937&) override;
    PolicySelection select_with_history(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, const ActorHistory&,
                           const RunningAction*, std::mt19937&) override;
    const char* identity() const override { return "npc-continuity-utility-v0"; }

    double score(const CandidateAction&, const Observation&, const ActorHistory&,
                 const RunningAction*) const;
private:
    double running_action_inertia_ = 0.14;
    double recent_action_inertia_ = 0.08;
};

bool contains_candidate(const DecisionContext&, ActionType, bool require_hard_admissible = true);
std::string candidate_signature(const DecisionContext&);
