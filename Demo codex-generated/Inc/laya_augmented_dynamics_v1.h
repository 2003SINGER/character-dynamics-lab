#pragma once

#include "demo_living_dynamics_v1.h"
#include "laya_semantic_client_v0.h"

// Demo-only semantic frontend: Laya interprets Delta-O and makes typed
// intention choices. DemoLivingV1 remains the deterministic state updater,
// policy surface owner and physical/time law. Reference is never linked here.
class LayaAugmentedDynamicsV1 final : public CharacterDynamicsModel {
public:
    LayaAugmentedDynamicsV1(int port, bool typed_commitment, bool typed_appraisal)
        : client_(port), typed_commitment_(typed_commitment), typed_appraisal_(typed_appraisal),
          identity_(typed_commitment && typed_appraisal ? "demo-living-v1+laya-typed-xi"
                    : typed_commitment ? "demo-living-v1+laya-typed-i"
                    : "demo-living-v1+laya-typed-x") {}
    StateUpdate advance_continuous(CharacterState&, const Observation&, const Personality&,
                                   const RunningAction*, int) const override;
    Appraisal appraise(const Observation&, const CharacterState&, const Personality&) const override;
    StateUpdate apply_impulse(CharacterState&, const Appraisal&, const Personality&) const override;
    void update_persistent_intention(CharacterState&, const Observation&, int) const override;
    std::optional<CommitmentDecisionTrace> update_persistent_intention_typed(
        CharacterState&, const Observation&, const Personality&, int, std::mt19937&) const override;
    DecisionContext build_policy(const Observation&, const CharacterState&,
                                 const Personality&) const override;
    DynamicsReconsideration reconsider_running_action(const Observation&, const CharacterState&,
        const CharacterState&, const RunningAction&, const Personality&) const override;
    const char* identity() const override { return identity_.c_str(); }
private:
    DemoLivingDynamicsV1 base_;
    LayaSemanticClientV0 client_;
    bool typed_commitment_ = false;
    bool typed_appraisal_ = false;
    std::string identity_;
};
