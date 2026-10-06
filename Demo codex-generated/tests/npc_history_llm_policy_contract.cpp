#include "history_llm_policy_v0.h"
#include "npc_continuity_application_v0.h"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

Observation make_observation() {
    World world(0);
    world.time.minute_of_day = 525;
    Observation observation = refresh_observation({}, world, {});
    apply_observable_runtime_event(observation, "clock.total_minutes", "525", "test", "08:45");
    apply_observable_runtime_event(observation, "clock.time", "08:45", "test", "08:45");
    apply_observable_runtime_event(observation, "task.coursework.status", "active", "test", "08:45");
    apply_observable_runtime_event(observation, "task.coursework.effort", "0", "test", "08:45");
    apply_observable_runtime_event(observation, "task.coursework.effort_target", "8", "test", "08:45");
    return observation;
}

std::vector<std::string> ids_of(const HistoryLlmRequestV0& request) {
    std::vector<std::string> ids;
    for (const auto& item : request.candidates) ids.push_back(item.id);
    return ids;
}

HistoryLlmTransportResultV0 selected_result(const std::string& id) {
    return {true, id, std::string(64, 'a'), {}, {}, "200", 17, 101, 9};
}
}

int main() {
    try {
        NpcContinuityApplicationModelV0 model;
        Observation observation = make_observation();
        CharacterState state;
        Personality personality;
        DecisionContext decision = model.build_policy(observation, state, personality);
        ActorHistory history;
        ActorEpisode episode;
        episode.action = ActionType::StudyFocused;
        episode.target = "desk";
        episode.start_total_minutes = 480;
        episode.end_total_minutes = 510;
        episode.planned_minutes = 35;
        episode.actual_minutes = 30;
        episode.interrupted = true;
        episode.outcome = "interrupted";
        episode.task_id = "coursework";
        history.episodes.push_back(episode);
        history.events.push_back({520, "room.alarm", "ringing"});
        RunningAction running{ActionType::StudyFocused, "desk", 510, 35, 15, true,
                              RunningActionStatus::Running};

        const HistoryLlmRequestV0 request = build_history_llm_request_v0(decision, observation, history, &running);
        require(request.json.find("npc-history-llm-request-v1") != std::string::npos,
                "request protocol was not upgraded");
        require(request.json.find("runtime_pruned_to_48h") != std::string::npos,
                "request omitted explicit Runtime history-window provenance");
        require(request.json.find("\"clock_total_minutes\":\"525\"") == std::string::npos,
                "clock unexpectedly serialized as a string");
        require(request.json.find("\"clock_total_minutes\":525") != std::string::npos,
                "request omitted current O clock");
        require(request.json.find("\"clock_time\":{\"value\":\"08:45\",\"status\":\"known\"}") != std::string::npos,
                "request omitted clock.time O status");
        require(request.json.find("\"task_id\":\"coursework\"") != std::string::npos,
                "request omitted actor-visible history");
        require(request.json.find("\"remaining_minutes\":20") != std::string::npos,
                "running action remaining duration missing");
        const auto resumed = std::find_if(request.candidates.begin(), request.candidates.end(),
            [](const HistoryLlmCandidateV0& item) { return item.candidate->action == ActionType::StudyFocused; });
        require(resumed != request.candidates.end() && resumed->planned_minutes == 20 && resumed->retains_progress,
                "same-intent choice did not advertise remaining duration/progress retention");
        require(request.json.find("\"hard_admissible\":true") != std::string::npos,
                "request omitted hard candidate marker");
        for (const char* forbidden : {"personality", "boredom", "fatigue", "utility_score", "probability", "rule_soft_eligible"})
            require(request.json.find(forbidden) == std::string::npos, "request leaked S/P or policy scores");

        CharacterState alternate_state;
        alternate_state.boredom = 0.9;
        Personality alternate_personality;
        alternate_personality.procrastination = 1.0;
        const HistoryLlmRequestV0 same_visible = build_history_llm_request_v0(decision, observation, history, &running);
        require(request.json == same_visible.json, "same O/history produced different request");
        ActorHistory changed_history = history;
        changed_history.events.push_back({524, "room.light", "off"});
        require(request.json != build_history_llm_request_v0(decision, observation, changed_history, &running).json,
                "visible history change did not change request");
        require(candidate_signature(model.build_policy(observation, alternate_state, alternate_personality))
                    == candidate_signature(decision), "S/P altered the shared hard candidate surface");

        std::string captured;
        HistoryLlmPolicyV0 policy([&](const std::string& body, const std::vector<std::string>& ids) {
            captured = body;
            require(ids == ids_of(request), "transport candidate-ID order differed from request");
            return selected_result(resumed->id);
        });
        std::mt19937 rng(7);
        const PolicySelection selected = policy.select_with_history(decision, observation, state,
            personality, history, &running, rng);
        require(selected.action == ActionType::StudyFocused, "valid candidate ID mapped to wrong action");
        require(captured == request.json, "policy transport received a different request contract");
        require(selected.provenance.find(std::string(64, 'a')) != std::string::npos,
                "selection provenance omitted request hash");
        const PolicySelection alternate = policy.select_with_history(decision, observation, alternate_state,
            alternate_personality, history, &running, rng);
        require(alternate.action == selected.action && captured == request.json,
                "S/P affected history-policy request or choice");

        HistoryLlmPolicyV0 invalid_id([](const std::string&, const std::vector<std::string>&) {
            return selected_result("not-a-candidate");
        });
        bool rejected_unknown = false;
        try { (void)invalid_id.select_with_history(decision, observation, state, personality, history, &running, rng); }
        catch (const std::runtime_error& error) {
            rejected_unknown = std::string(error.what()).find("candidate_id/unknown") != std::string::npos;
        }
        require(rejected_unknown, "unknown candidate ID was not explicitly rejected");

        HistoryLlmPolicyV0 failed_transport([](const std::string&, const std::vector<std::string>&) {
            return HistoryLlmTransportResultV0{false, {}, {}, "transport", "Timeout", "timeout", 1000, -1, -1};
        });
        bool timeout_reported = false;
        try { (void)failed_transport.select_with_history(decision, observation, state, personality, history, &running, rng); }
        catch (const std::runtime_error& error) {
            timeout_reported = std::string(error.what()).find("transport/Timeout") != std::string::npos;
        }
        require(timeout_reported, "timeout silently fell back or lost its failure status");

        Observation stale_clock = observation;
        for (ObservationFact& fact : stale_clock.facts)
            if (fact.key == "clock.total_minutes") fact.status = KnowledgeStatus::Stale;
        bool stale_rejected = false;
        try { (void)build_history_llm_request_v0(decision, stale_clock, history, &running); }
        catch (const std::runtime_error& error) {
            stale_rejected = std::string(error.what()).find("missing_or_stale") != std::string::npos;
        }
        require(stale_rejected, "stale O clock was accepted");

        DecisionContext ambiguous = decision;
        const auto focused = std::find_if(ambiguous.candidates.begin(), ambiguous.candidates.end(),
            [](const CandidateAction& item) { return item.hard_admissible && item.action == ActionType::StudyFocused; });
        require(focused != ambiguous.candidates.end(), "fixture lacks StudyFocused candidate");
        CandidateAction second_target = *focused;
        second_target.target_object_id = "library_desk";
        ambiguous.candidates.push_back(second_target);
        bool ambiguity_rejected = false;
        try { (void)build_history_llm_request_v0(ambiguous, observation, history, &running); }
        catch (const std::runtime_error& error) {
            ambiguity_rejected = std::string(error.what()).find("UnsupportedAmbiguousActionSurface") != std::string::npos;
        }
        require(ambiguity_rejected, "multiple targets for one ActionType were not rejected");

        const auto suffix = std::chrono::steady_clock::now().time_since_epoch().count();
        const std::filesystem::path worker_run = std::filesystem::temp_directory_path()
            / ("npc-history-llm-worker-contract-" + std::to_string(suffix));
        require(std::filesystem::create_directory(worker_run), "could not create isolated worker test run directory");
        const HistoryLlmTransportResultV0 unavailable = run_history_llm_worker_v0(
            request.json, ids_of(request), worker_run.string(), "contract-only-no-model-call", 1000,
            "http://127.0.0.1:1/v1/chat/completions");
        require(!unavailable.ok && unavailable.stage == "transport",
                "C++ worker transport did not preserve no-server connection failure stage");
        require(unavailable.request_sha256.size() == 64,
                "failed no-server request did not retain canonical request hash");
        std::ifstream call_log(worker_run / "history_llm_calls.jsonl");
        std::string log_line;
        std::getline(call_log, log_line);
        require(!log_line.empty() && log_line.find("\"request_sha256\"") != std::string::npos
                && log_line.find("\"status\":\"error\"") != std::string::npos,
                "failed worker request was not journaled");
        std::filesystem::remove(worker_run / "history_llm_calls.jsonl");
        std::filesystem::remove(worker_run);

        std::cout << "npc_history_llm_policy_contract: PASS (fake transport; not inference)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "npc_history_llm_policy_contract: " << error.what() << '\n';
        return 1;
    }
}
