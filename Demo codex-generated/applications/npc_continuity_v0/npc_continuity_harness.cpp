#include "npc_continuity_application_v0.h"

#include "simulation_time.h"
#include "continuous_runtime.h"

#include <algorithm>
#include <iostream>
#include <string>
#include <stdexcept>

namespace {
constexpr int kStartMinute = 8 * 60 + 45;
constexpr unsigned int kScenarioSeed = 0U; // legacy World tape: alarm at 09:00
constexpr unsigned int kPolicySeed = 17U;

void print_running(const std::optional<RunningAction>& action) {
    if (!action) { std::cout << "null"; return; }
    std::cout << "{\"action\":\"" << to_string(action->action)
              << "\",\"target\":\"" << action->target_object_id
              << "\",\"elapsed\":" << action->elapsed_minutes
              << ",\"planned\":" << action->planned_duration_minutes
              << ",\"status\":\"" << to_string(action->status) << "\"}";
}

const char* task_status(const Observation& observation) {
    if (has_known_fact(observation, "task.coursework.status", "active")) return "active";
    if (has_known_fact(observation, "task.coursework.status", "completed")) return "completed";
    return "unknown";
}

void print_step(const RuntimeExecutionResult& step, const World& world,
                const Observation& observation) {
    std::cout << "{\"minute\":" << step.runtime.boundary.at_total_minutes
              << ",\"event_count\":" << step.runtime.world_events.size()
              << ",\"alarm_visible\":" << (has_known_fact(observation, "room.alarm", "ringing") ? "true" : "false")
              << ",\"policy_evaluated\":" << (step.policy_evaluated ? "true" : "false")
              << ",\"gate_reasons\":[";
    for (std::size_t i = 0; i < step.runtime.boundary.decision_gate.reasons.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << '"' << to_string(step.runtime.boundary.decision_gate.reasons[i]) << '"';
    }
    std::cout << "],\"running_before\":";
    print_running(step.running_action_before);
    std::cout << ",\"selected\":\""
              << (step.selected_action ? to_string(*step.selected_action) : "none")
              << "\",\"selected_target\":\"" << step.selected_target_object_id
              << "\",\"running_after\":";
    print_running(step.running_action_after);
    std::cout << ",\"policy\":\"" << step.policy_id
              << "\",\"policy_provenance\":\"" << step.policy_selection_provenance
              << "\",\"task_status_in_O\":\"" << task_status(observation) << "\""
              << ",\"task_effort_in_W\":" << world.tasks.front().effort_done
              << ",\"task_effort_settled_this_step\":"
              << (step.pre_policy_outcome ? step.pre_policy_outcome->task_effort_gained : 0.0)
              << ",\"policy_replacement_interrupted\":"
              << (step.post_policy_outcome && step.post_policy_outcome->task_session_interrupted ? "true" : "false")
              << ",\"interrupted_action_elapsed_minutes\":"
              << (step.post_policy_outcome ? step.post_policy_outcome->action_elapsed_minutes : 0)
              << ",\"candidate_signature\":\""
              << (step.policy_evaluated ? candidate_signature(step.decision) : std::string{})
              << "\",\"observation_deltas\":[";
    for (std::size_t i = 0; i < step.observation_deltas.size(); ++i) {
        if (i) std::cout << ',';
        const auto& fact = step.observation_deltas[i];
        std::cout << "{\"key\":\"" << fact.key << "\",\"value\":\"" << fact.value << "\"}";
    }
    std::cout << "]}\n";
}
} // namespace

int main(int argc, char** argv) {
    const std::string scenario = argc > 1 ? argv[1] : "alarm";
    if (scenario != "alarm") {
        std::cerr << "supported scenario: alarm\n";
        return 2;
    }

    World world(kScenarioSeed);
    world.time.minute_of_day = kStartMinute;
    const int start = total_minutes(world.time);
    RuntimeScheduler scheduler(start);
    Observation observation = refresh_observation({}, world, {});
    NpcContinuityApplicationModelV0 model;
    UtilityPolicyV0 policy;
    ContinuousRuntime runtime(scheduler, world, observation, model, {}, 17U, &policy);
    CharacterState state;
    Personality personality;

    const WorldOutcome started = runtime.submit_action_intent(
        ActionType::StudyFocused, "desk", action_definition(ActionType::StudyFocused).default_duration_minutes);
    if (!started.accepted) return 3;
    std::cout << "{\"kind\":\"harness\",\"scenario\":\"natural_alarm_during_coursework\","
              << "\"scenario_seed\":" << kScenarioSeed
              << ",\"policy_seed\":" << kPolicySeed
              << ",\"task_effort_target\":" << world.tasks.front().effort_target
              << ",\"application_model\":\"" << model.identity() << "\""
              << ",\"runtime\":\"continuous-runtime-v1-frozen\","
              << "\"policy\":\"npc-continuity-utility-v0\","
              << "\"compiled_git_revision\":\"" << CHARACTER_DYNAMICS_GIT_REVISION << "\","
              << "\"source_tree_state\":\"not_verified_clean_at_build\","
              << "\"trace_protocol\":\"npc-continuity-trace-v0\","
              << "\"scope\":\"CLI trace only; no player UI or LLM comparison\"}\n";
    std::cout << "{\"kind\":\"initial_action\",\"action\":\"study_focused\","
              << "\"target\":\"desk\",\"source\":\"scenario_setup\","
              << "\"accepted\":true}\n";

    bool saw_visible_alarm = false;
    bool saw_alarm_reconsideration = false;
    bool saw_alarm_replacement = false;
    bool saw_study_after_alarm = false;
    bool alarm_action_seen = false;
    bool saw_fixed_interruption_cost = false;
    bool completed = false;
    for (int i = 0; i < 100; ++i) {
        RuntimeExecutionResult step = runtime.execute_next_boundary(state, personality);
        const bool alarm_now = has_known_fact(observation, "room.alarm", "ringing");
        if (alarm_now) saw_visible_alarm = true;
        for (DecisionGateReason reason : step.runtime.boundary.decision_gate.reasons)
            if (reason == DecisionGateReason::DynamicsReconsideration) saw_alarm_reconsideration = true;
        if (step.selected_action == ActionType::TurnOffAlarm && alarm_now) {
            saw_alarm_replacement = true;
            alarm_action_seen = true;
        }
        if (alarm_action_seen && step.selected_action
            && (*step.selected_action == ActionType::StudyFocused
                || *step.selected_action == ActionType::StudyHalfhearted
                || *step.selected_action == ActionType::StudyAtComputer))
            saw_study_after_alarm = true;
        if (step.post_policy_outcome && step.post_policy_outcome->action == ActionType::StudyFocused
            && step.post_policy_outcome->task_session_interrupted) {
            if (world.tasks.front().effort_done != 0.0
                || step.post_policy_outcome->action_elapsed_minutes <= 0) {
                std::cerr << "unexpected partial task settlement on interrupted action\n";
                return 5;
            }
            saw_fixed_interruption_cost = true;
        }
        print_step(step, world, observation);
        if (step.pre_policy_outcome && step.pre_policy_outcome->task_completed) {
            completed = true;
            break;
        }
    }
    if (!saw_visible_alarm || !saw_alarm_reconsideration || !saw_alarm_replacement
        || !saw_fixed_interruption_cost
        || !saw_study_after_alarm || !completed) {
        std::cerr << "trace contract failed: visible alarm, utility replacement, study, or completion missing\n";
        return 4;
    }
    return 0;
}
