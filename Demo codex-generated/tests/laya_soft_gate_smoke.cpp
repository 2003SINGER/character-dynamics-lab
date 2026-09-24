#include "continuous_runtime.h"
#include "reference_rule_dynamics_v0.h"

#include <algorithm>

namespace {
class ForcedSoftPolicy final : public CharacterPolicy {
public:
    PolicySelection select(const DecisionContext& decision, const Observation& observation,
                           const CharacterState& state, const Personality& personality,
                           std::mt19937& rng) override {
        return rule_.select(decision, observation, state, personality, rng);
    }
    const char* identity() const override { return "forced-soft-test"; }
    std::optional<SoftReconsideration> soft_reconsider(
        const Observation&, const CharacterState&, const Personality&,
        const RunningAction&, std::mt19937&) override {
        ++calls;
        return SoftReconsideration{1.0, true, "test:noul=1"};
    }
    int calls = 0;
private:
    RulePolicyV0 rule_;
};

bool has_reason(const RuntimeExecutionResult& result, DecisionGateReason reason) {
    const auto& reasons = result.runtime.boundary.decision_gate.reasons;
    return std::find(reasons.begin(), reasons.end(), reason) != reasons.end();
}
}

int main() {
    World world;
    world.time.minute_of_day = 9 * 60 + 20;
    RuntimeScheduler scheduler(9 * 60 + 20);
    Observation observation = refresh_observation({}, world, {});
    ReferenceRuleDynamicsV0 dynamics;
    ForcedSoftPolicy policy;
    ContinuousRuntime runtime(scheduler, world, observation, dynamics, {}, 15, &policy);
    CharacterState state;
    Personality personality;
    runtime.set_test_action_selector([](const DecisionContext&) { return ActionType::StudyFocused; });
    if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 1;
    const RuntimeExecutionResult soft = runtime.execute_next_boundary(state, personality);
    if (soft.runtime.boundary.elapsed_minutes != 10
        || !has_reason(soft, DecisionGateReason::ModelSoftReconsideration)
        || !soft.model_soft_reconsideration || !soft.model_soft_reconsideration->requested
        || !soft.policy_evaluated || policy.calls != 1
        || soft.post_policy_outcome || soft.replacement_validation_performed
        || !soft.running_action_after
        || soft.running_action_after->started_at_total_minutes != 9 * 60 + 20
        || soft.running_action_after->elapsed_minutes != 10) return 2;
    const RuntimeExecutionResult completion = runtime.execute_next_boundary(state, personality);
    if (completion.runtime.boundary.elapsed_minutes != 25
        || !has_reason(completion, DecisionGateReason::ActionCompleted)
        || completion.model_soft_reconsideration || policy.calls != 1
        || !completion.pre_policy_outcome || !completion.pre_policy_outcome->accepted
        || completion.pre_policy_outcome->task_effort_gained <= 0.0) return 3;
    return 0;
}
