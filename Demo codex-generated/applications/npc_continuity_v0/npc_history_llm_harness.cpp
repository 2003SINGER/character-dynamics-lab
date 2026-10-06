#include "history_llm_policy_v0.h"
#include "npc_continuity_application_v0.h"
#include "continuous_runtime.h"
#include "simulation_time.h"

#include <filesystem>
#include <iostream>
#include <stdexcept>

namespace {
constexpr int kStartMinute = 8 * 60 + 45;
constexpr int kHorizonMinutes = 90;
constexpr int kMaxPolicyCalls = 8;
constexpr unsigned int kScenarioSeed = 0U;
constexpr unsigned int kPolicySeed = 17U;

struct Options { std::string run_directory; std::string model_id = "npc-qwen3-4b-q4km"; int max_calls = kMaxPolicyCalls; int timeout_ms = 45000; };

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (key == "--run-directory" && i + 1 < argc) options.run_directory = argv[++i];
        else if (key == "--model-id" && i + 1 < argc) options.model_id = argv[++i];
        else if (key == "--max-calls" && i + 1 < argc) options.max_calls = std::stoi(argv[++i]);
        else if (key == "--timeout-ms" && i + 1 < argc) options.timeout_ms = std::stoi(argv[++i]);
        else throw std::invalid_argument("usage: harness --run-directory NEW_DIR [--model-id ID] [--max-calls 1..8] [--timeout-ms N]");
    }
    if (options.run_directory.empty() || options.max_calls < 1 || options.max_calls > kMaxPolicyCalls
        || options.timeout_ms < 1000 || options.timeout_ms > 90000)
        throw std::invalid_argument("usage: harness --run-directory NEW_DIR [--model-id ID] [--max-calls 1..8] [--timeout-ms 1000..90000]");
    return options;
}

void print_running(const std::optional<RunningAction>& action) {
    if (!action) { std::cout << "null"; return; }
    std::cout << "{\"action\":\"" << to_string(action->action) << "\",\"target\":\""
        << json_escape_history_llm_v0(action->target_object_id) << "\",\"started_at_total_minutes\":"
        << action->started_at_total_minutes << ",\"elapsed_minutes\":"
        << action->elapsed_minutes << ",\"planned_minutes\":" << action->planned_duration_minutes
        << ",\"status\":\"" << to_string(action->status) << "\"}";
}

const char* rejection_reason_name(RejectionReason reason) {
    switch (reason) {
    case RejectionReason::None: return "none";
    case RejectionReason::TargetAbsent: return "target_absent";
    case RejectionReason::TargetUnusable: return "target_unusable";
    case RejectionReason::PreconditionFailed: return "precondition_failed";
    case RejectionReason::ResourceInsufficient: return "resource_insufficient";
    }
    return "unknown";
}

void print_outcome(const std::optional<WorldOutcome>& outcome) {
    if (!outcome) { std::cout << "null"; return; }
    std::cout << "{\"action\":\"" << to_string(outcome->action)
        << "\",\"accepted\":" << (outcome->accepted ? "true" : "false")
        << ",\"rejection_reason\":\"" << rejection_reason_name(outcome->failure_reason)
        << "\",\"provenance\":\"" << json_escape_history_llm_v0(outcome->provenance)
        << "\",\"task_completed\":" << (outcome->task_completed ? "true" : "false")
        << ",\"interrupted\":" << (outcome->task_session_interrupted ? "true" : "false")
        << ",\"elapsed_minutes\":" << outcome->elapsed_minutes
        << ",\"action_elapsed_minutes\":" << outcome->action_elapsed_minutes << '}';
}

void print_step(const RuntimeExecutionResult& step, int call_count) {
    std::cout << "{\"kind\":\"step\",\"minute\":" << step.runtime.boundary.at_total_minutes
        << ",\"elapsed_minutes\":" << step.runtime.boundary.elapsed_minutes
        << ",\"policy_evaluated\":" << (step.policy_evaluated ? "true" : "false")
        << ",\"policy_call_count\":" << call_count << ",\"gate_reasons\":[";
    for (std::size_t i = 0; i < step.runtime.boundary.decision_gate.reasons.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << '"' << to_string(step.runtime.boundary.decision_gate.reasons[i]) << '"';
    }
    std::cout << "],\"running_before\":";
    print_running(step.running_action_before);
    std::cout << ",\"replacement_validation\":{\"performed\":"
        << (step.replacement_validation_performed ? "true" : "false")
        << ",\"accepted\":";
    if (step.replacement_validation_performed)
        std::cout << (step.replacement_validation_accepted ? "true" : "false");
    else std::cout << "null";
    std::cout << "},\"world_event_ids\":[";
    for (std::size_t i = 0; i < step.runtime.world_events.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << '"' << json_escape_history_llm_v0(step.runtime.world_events[i].id) << '"';
    }
    std::cout << "],\"pre_policy_outcome\":";
    print_outcome(step.pre_policy_outcome);
    std::cout << ",\"post_policy_outcome\":";
    print_outcome(step.post_policy_outcome);
    std::cout << ",\"selected_action\":\""
        << (step.selected_action ? to_string(*step.selected_action) : "none")
        << "\",\"selected_target\":\"" << json_escape_history_llm_v0(step.selected_target_object_id)
        << "\",\"running_after\":";
    print_running(step.running_action_after);
    std::cout << ",\"candidate_signature\":\""
        << (step.policy_evaluated ? candidate_signature(step.decision) : std::string{})
        << "\",\"policy_id\":\"" << json_escape_history_llm_v0(step.policy_id)
        << "\",\"policy_provenance\":\"" << json_escape_history_llm_v0(step.policy_selection_provenance)
        << "\",\"o_deltas\":[";
    for (std::size_t i = 0; i < step.observation_deltas.size(); ++i) {
        if (i) std::cout << ',';
        const ObservationFact& delta = step.observation_deltas[i];
        std::cout << "{\"key\":\"" << json_escape_history_llm_v0(delta.key)
            << "\",\"value\":\"" << json_escape_history_llm_v0(delta.value) << "\"}";
    }
    std::cout << "]}\n";
}
} // namespace

int main(int argc, char** argv) {
    Options options;
    try { options = parse_options(argc, argv); }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }

    std::error_code filesystem_error;
    if (!std::filesystem::create_directory(options.run_directory, filesystem_error)) {
        std::cout << "{\"kind\":\"error\",\"stage\":\"run_directory\",\"type\":\"not_new_or_unavailable\"}\n";
        return 3;
    }

    World world(kScenarioSeed);
    world.time.minute_of_day = kStartMinute;
    RuntimeScheduler scheduler(kStartMinute);
    scheduler.schedule({"application-horizon", kStartMinute + kHorizonMinutes, false,
                        std::nullopt, std::nullopt});
    Observation observation = refresh_observation({}, world, {});
    NpcContinuityApplicationModelV0 model;
    int calls = 0;
    HistoryLlmPolicyV0 policy([&](const std::string& request, const std::vector<std::string>& ids) {
        ++calls;
        return run_history_llm_worker_v0(request, ids, options.run_directory, options.model_id, options.timeout_ms);
    });
    ContinuousRuntime runtime(scheduler, world, observation, model, {}, kPolicySeed, &policy);
    CharacterState state;
    Personality personality;
    const WorldOutcome started = runtime.submit_action_intent(ActionType::StudyFocused, "desk",
        action_definition(ActionType::StudyFocused).default_duration_minutes);
    if (!started.accepted) return 4;

    std::cout << "{\"kind\":\"harness\",\"scenario\":\"natural_scheduled_event_during_self_task\","
        << "\"application_model\":\"" << model.identity() << "\",\"policy\":\"" << policy.identity()
        << "\",\"requested_model_id\":\"" << json_escape_history_llm_v0(options.model_id) << "\","
        << "\"endpoint\":\"http://127.0.0.1:8080/v1/chat/completions\",\"scenario_seed\":" << kScenarioSeed
        << ",\"policy_seed\":" << kPolicySeed << ",\"history_window\":\"runtime actor ledger, already pruned to 48h\","
        << "\"horizon_minutes\":" << kHorizonMinutes << ",\"policy_call_limit\":" << options.max_calls
        << ",\"temperature\":0,\"temperature_is_cross_platform_deterministic\":false"
        << ",\"compiled_git_revision\":\"" << CHARACTER_DYNAMICS_GIT_REVISION
        << "\",\"initial_action\":\"study_focused\",\"initial_action_source\":\"scenario_setup\","
        << "\"initial_action_target\":\"desk\",\"initial_action_planned_minutes\":"
        << action_definition(ActionType::StudyFocused).default_duration_minutes
        << ",\"initial_action_world_accepted\":true"
        << ",\"run_directory\":\"" << json_escape_history_llm_v0(options.run_directory)
        << "\",\"source_tree_state\":\"not_verified_clean_at_build\"}\n";

    const int start = scheduler.now_total_minutes();
    std::string termination = "horizon";
    for (int steps = 0; steps < 1000; ++steps) {
        if (scheduler.now_total_minutes() - start >= kHorizonMinutes) { termination = "horizon"; break; }
        try {
            const RuntimeExecutionResult step = runtime.execute_next_boundary(state, personality);
            print_step(step, calls);
            if (scheduler.now_total_minutes() - start >= kHorizonMinutes) {
                termination = "horizon";
                break;
            }
            if (calls >= options.max_calls) {
                termination = "call_limit";
                break;
            }
        } catch (const std::exception& error) {
            const std::string message = error.what();
            termination = message.find("CallLimit") != std::string::npos ? "call_limit" : "errors";
            std::cout << "{\"kind\":\"error\",\"stage\":\"policy_or_runtime\",\"type\":\""
                << json_escape_history_llm_v0(message) << "\",\"policy_calls\":" << calls << "}\n";
            break;
        }
    }
    std::cout << "{\"kind\":\"termination\",\"reason\":\"" << termination
        << "\",\"policy_calls\":" << calls << ",\"simulated_minutes\":"
        << scheduler.now_total_minutes() - start << "}\n";
    return termination == "errors" ? 5 : 0;
}
