#include "appraisal.h"
#include "continuous_runtime.h"
#include "reference_rule_dynamics_v0.h"
#include "decision.h"
#include "observation.h"
#include "runtime_scheduler.h"
#include "state.h"
#include "world.h"
#include "world_runtime_adapter.h"

#include <algorithm>
#include <iostream>
#include <random>

namespace {
bool has_tag(const Appraisal& appraisal, const std::string& tag) {
    return std::find(appraisal.tags.begin(), appraisal.tags.end(), tag) != appraisal.tags.end();
}

const CandidateAction* highest_probability(const DecisionContext& decision) {
    const CandidateAction* selected = nullptr;
    for (const CandidateAction& candidate : decision.candidates) {
        if (candidate.probability > 0.0
            && (selected == nullptr || candidate.probability > selected->probability)) {
            selected = &candidate;
        }
    }
    return selected;
}
}

int main() {
    Personality personality;
    CharacterState state;
    World world;
    world.time.minute_of_day = 9 * 60 + 20;
    RuntimeScheduler scheduler(9 * 60 + 20);
    Observation observation = refresh_observation({}, world, {});
    ReferenceRuleDynamicsV0 dynamics;
    ContinuousRuntime runtime(scheduler, world, observation, dynamics);
    const WorldOutcome start = runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35, true);
    if (!start.accepted) { std::cerr << "W rejected a legal study start\n"; return 1; }
    // [09:00, 09:10): continuous S receives both elapsed duration and the
    // running study action, while policy remains closed at the weak event.
    const RuntimeExecutionResult message_result = runtime.execute_next_boundary(state, personality);
    const RuntimeBoundary& message_boundary = message_result.runtime.boundary;
    const std::vector<WorldEvent>& world_events = message_result.runtime.world_events;
    const auto message = std::find_if(world_events.begin(), world_events.end(), [](const WorldEvent& event) {
        return event.id == "message-study-group";
    });
    if (message == world_events.end()) {
        std::cerr << "World did not emit the scheduled message at the runtime boundary\n";
        return 1;
    }
    if (message_boundary.elapsed_minutes != 10 || message_boundary.decision_gate.open
        || total_minutes(world.time) != scheduler.now_total_minutes()
        || message_result.continuous_state.applied.fatigue <= 0.0
        || !has_known_fact(observation, "message.unread_count", "1")
        || !has_tag(message_result.appraisal, "social_task_reminder")
        || message_result.impulse_state.applied.task_pressure <= 0.0) {
        std::cerr << "weak runtime event must traverse continuous S and O-X-S without reopening policy\n";
        return 1;
    }

    // [09:10, 09:35): the action continues. At completion, W settlement and
    // its typed self-feedback occur before the gate authorizes the next pi.
    const RuntimeExecutionResult completion_result = runtime.execute_next_boundary(state, personality);
    const RuntimeBoundary& completion_boundary = completion_result.runtime.boundary;
    const std::vector<WorldEvent>& completion_events = completion_result.runtime.world_events;
    const WorldOutcome& completion = *completion_result.pre_policy_outcome;
    std::mt19937 expected_rng(0x43445257U);
    const ActionType expected_sample = sample_action(completion_result.decision, expected_rng);

    if (completion_boundary.elapsed_minutes != 25
        || !completion_boundary.decision_gate.open
        || completion_boundary.action_after_boundary->status != RunningActionStatus::Completed
        || completion_result.continuous_state.applied.fatigue <= 0.0
        || !completion_events.empty()
        || total_minutes(world.time) != scheduler.now_total_minutes()
        || !completion.accepted || completion.elapsed_minutes != 0
        || completion.time_advanced_by_settlement != 0
        || completion.action_elapsed_minutes != 35 || completion.task_effort_gained <= 0.0
        || completion_result.impulse_state.applied.elapsed_minutes != 0
        || completion_result.decision.candidates.empty() || !completion_result.selected_action.has_value()
        || *completion_result.selected_action != expected_sample
        || !scheduler.running_action().has_value()) {
        std::cerr << "completion must settle W/O/X/S before the gated next policy action\n";
        return 1;
    }
    std::cout << "runtime vertical slice smoke OK\n";
    return 0;
}
