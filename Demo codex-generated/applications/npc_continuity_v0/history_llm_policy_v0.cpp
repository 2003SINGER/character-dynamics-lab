#include "history_llm_policy_v0.h"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <fstream>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>

#ifndef _WIN32
#include <cerrno>
#include <cstdio>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

#ifndef NPC_HISTORY_LLM_PYTHON
#define NPC_HISTORY_LLM_PYTHON "python3"
#endif
#ifndef NPC_HISTORY_LLM_WORKER
#define NPC_HISTORY_LLM_WORKER "history_llm_worker_v0.py"
#endif

namespace {
std::string quote(const std::string& value) {
    return "\"" + json_escape_history_llm_v0(value) + "\"";
}

void append_fact_json(std::ostringstream& out, const ObservationFact& fact, bool& first) {
    if (!first) out << ',';
    first = false;
    out << "{\"key\":" << quote(fact.key) << ",\"value\":" << quote(fact.value)
        << ",\"status\":\""
        << (fact.status == KnowledgeStatus::Known ? "known" : "stale") << "\"}";
}

std::string result_provenance(const HistoryLlmTransportResultV0& result) {
    std::ostringstream out;
    out << "history-llm-v0 status=" << result.api_status
        << " sha256=" << result.request_sha256
        << " elapsed_ms=" << result.elapsed_ms
        << " prompt_tokens=" << result.prompt_tokens
        << " completion_tokens=" << result.completion_tokens;
    return out.str();
}

#ifndef _WIN32
void close_if_valid(int fd) { if (fd >= 0) ::close(fd); }

HistoryLlmTransportResultV0 execute_worker(const std::string& request_json,
    const std::string& run_directory, const std::string& model_id, int timeout_ms,
    const std::string& endpoint) {
    std::FILE* request_file = std::tmpfile();
    if (!request_file) throw std::runtime_error("history-llm worker setup/tmpfile failure");
    const auto file_close = [](std::FILE* file) { if (file) std::fclose(file); };
    std::unique_ptr<std::FILE, decltype(file_close)> request_holder(request_file, file_close);
    if (std::fwrite(request_json.data(), 1, request_json.size(), request_file) != request_json.size()
        || std::fflush(request_file) != 0 || std::fseek(request_file, 0, SEEK_SET) != 0)
        throw std::runtime_error("history-llm worker setup/request spool failure");
    int output_pipe[2] = {-1, -1};
    if (::pipe(output_pipe) != 0) {
        close_if_valid(output_pipe[0]); close_if_valid(output_pipe[1]);
        throw std::runtime_error("history-llm worker setup/pipe failure");
    }
    posix_spawn_file_actions_t actions;
    posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_adddup2(&actions, ::fileno(request_file), STDIN_FILENO);
    posix_spawn_file_actions_adddup2(&actions, output_pipe[1], STDOUT_FILENO);
    posix_spawn_file_actions_addclose(&actions, ::fileno(request_file));
    posix_spawn_file_actions_addclose(&actions, output_pipe[1]);
    posix_spawn_file_actions_addclose(&actions, output_pipe[0]);
    std::string timeout_text = std::to_string(timeout_ms);
    char* argv[] = {const_cast<char*>(NPC_HISTORY_LLM_PYTHON),
        const_cast<char*>(NPC_HISTORY_LLM_WORKER), const_cast<char*>("--run-directory"),
        const_cast<char*>(run_directory.c_str()), const_cast<char*>("--model"),
        const_cast<char*>(model_id.c_str()), const_cast<char*>("--timeout-ms"),
        const_cast<char*>(timeout_text.c_str()), const_cast<char*>("--endpoint"),
        const_cast<char*>(endpoint.c_str()), nullptr};
    pid_t child = -1;
    const int spawn_error = posix_spawnp(&child, NPC_HISTORY_LLM_PYTHON, &actions, nullptr, argv, environ);
    posix_spawn_file_actions_destroy(&actions);
    close_if_valid(output_pipe[1]);
    if (spawn_error != 0) {
        close_if_valid(output_pipe[0]);
        throw std::runtime_error("history-llm worker setup/spawn failure: " + std::string(std::strerror(spawn_error)));
    }

    const auto began = std::chrono::steady_clock::now();
    std::string envelope;
    bool timed_out = false;
    for (;;) {
        const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - began).count();
        const int remaining = timeout_ms + 5000 - static_cast<int>(elapsed);
        if (remaining <= 0) { timed_out = true; break; }
        pollfd descriptor{output_pipe[0], POLLIN | POLLHUP, 0};
        const int ready = ::poll(&descriptor, 1, std::min(remaining, 1000));
        if (ready < 0 && errno == EINTR) continue;
        if (ready < 0) break;
        if (ready == 0) {
            int status = 0;
            if (::waitpid(child, &status, WNOHANG) == child) break;
            continue;
        }
        char buffer[512];
        const ssize_t count = ::read(output_pipe[0], buffer, sizeof(buffer));
        if (count == 0) break;
        if (count < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (count < 0) break;
        envelope.append(buffer, static_cast<std::size_t>(count));
        if (envelope.size() > 4096) {
            ::kill(child, SIGKILL); timed_out = false; envelope.clear(); break;
        }
    }
    close_if_valid(output_pipe[0]);
    if (timed_out) ::kill(child, SIGKILL);
    int status = 0;
    while (::waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    if (timed_out) return {false, {}, {}, "transport", "Timeout", "timeout", timeout_ms, -1, -1};

    // Worker stdout is a fixed tab protocol; model text never enters this channel.
    std::vector<std::string> fields;
    std::istringstream lines(envelope);
    std::string line;
    if (!std::getline(lines, line))
        return {false, {}, {}, "worker", "EmptyEnvelope", "error", 0, -1, -1};
    std::istringstream parts(line);
    std::string field;
    while (std::getline(parts, field, '\t')) fields.push_back(field);
    try {
        if (fields.size() == 7 && fields[0] == "ok" && WIFEXITED(status) && WEXITSTATUS(status) == 0)
            return {true, fields[1], fields[2], {}, {}, fields[3], std::stoi(fields[4]),
                    std::stoi(fields[5]), std::stoi(fields[6])};
        if (fields.size() == 5 && fields[0] == "error")
            return {false, {}, fields[4], fields[1], fields[2], "error", 0, -1, -1};
    } catch (const std::exception&) {}
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
        return {false, {}, {}, "worker", "WorkerFailure", "error", 0, -1, -1};
    return {false, {}, {}, "worker", "MalformedEnvelope", "error", 0, -1, -1};
}
#endif
} // namespace

std::string json_escape_history_llm_v0(const std::string& value) {
    std::ostringstream out;
    for (unsigned char c : value) {
        switch (c) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (c < 0x20) {
                static const char hex[] = "0123456789abcdef";
                out << "\\u00" << hex[c >> 4] << hex[c & 0x0f];
            } else out << static_cast<char>(c);
        }
    }
    return out.str();
}

HistoryLlmRequestV0 build_history_llm_request_v0(const DecisionContext& decision,
    const Observation& observation, const ActorHistory& history, const RunningAction* running) {
    const ObservationFact* clock = find_fact(observation, "clock.total_minutes");
    if (!clock || clock->status != KnowledgeStatus::Known)
        throw std::runtime_error("history-llm request/O-clock/missing_or_stale");
    int clock_minutes = -1;
    const char* clock_begin = clock->value.data();
    const char* clock_end = clock_begin + clock->value.size();
    const auto clock_parse = std::from_chars(clock_begin, clock_end, clock_minutes);
    if (clock_parse.ec != std::errc{} || clock_parse.ptr != clock_end || clock_minutes < 0)
        throw std::runtime_error("history-llm request/O-clock/invalid_integer");
    const ObservationFact* clock_time = find_fact(observation, "clock.time");
    std::size_t admissible = 0;
    std::set<ActionType> unique_actions;
    for (const CandidateAction& candidate : decision.candidates)
        if (candidate.hard_admissible) {
            ++admissible;
            if (!unique_actions.insert(candidate.action).second)
                throw std::runtime_error("history-llm request/candidate_surface/UnsupportedAmbiguousActionSurface");
        }
    if (admissible == 0) throw std::runtime_error("history-llm request/candidates/empty");

    HistoryLlmRequestV0 request;
    std::ostringstream out;
    out << "{\"protocol\":\"npc-history-llm-request-v1\",\"clock_total_minutes\":"
        << clock_minutes << ",\"clock_time\":{\"value\":"
        << quote(clock_time ? clock_time->value : std::string{}) << ",\"status\":\""
        << (clock_time && clock_time->status == KnowledgeStatus::Known ? "known"
            : clock_time && clock_time->status == KnowledgeStatus::Stale ? "stale" : "unknown") << "\"}"
        << ",\"observation_history_window\":\"runtime_actor_ledger_48h\",\"observation_known_facts\":[";
    bool first = true;
    for (const ObservationFact& fact : observation.facts)
        if (fact.status == KnowledgeStatus::Known || fact.status == KnowledgeStatus::Stale)
            append_fact_json(out, fact, first);
    out << "],\"actor_history\":{\"ledger_window\":\"runtime_pruned_to_48h\",\"episodes\":[";
    first = true;
    for (const ActorEpisode& episode : history.episodes) {
        if (!first) out << ',';
        first = false;
        out << "{\"action\":" << quote(to_string(episode.action))
            << ",\"target\":" << quote(episode.target)
            << ",\"start_total_minutes\":" << episode.start_total_minutes
            << ",\"end_total_minutes\":" << episode.end_total_minutes
            << ",\"planned_minutes\":" << episode.planned_minutes
            << ",\"actual_minutes\":" << episode.actual_minutes
            << ",\"accepted\":" << (episode.accepted ? "true" : "false")
            << ",\"interrupted\":" << (episode.interrupted ? "true" : "false")
            << ",\"outcome\":" << quote(episode.outcome)
            << ",\"task_id\":" << quote(episode.task_id) << '}';
    }
    out << "],\"observed_events\":[";
    first = true;
    for (const ActorObservedEvent& event : history.events) {
        if (!first) out << ',';
        first = false;
        out << "{\"total_minutes\":" << event.total_minutes << ",\"key\":" << quote(event.key)
            << ",\"value\":" << quote(event.value) << '}';
    }
    out << "]},\"running_action\":";
    if (running && running->status == RunningActionStatus::Running) {
        const int remaining = std::max(0, running->planned_duration_minutes - running->elapsed_minutes);
        out << "{\"action\":" << quote(to_string(running->action))
            << ",\"target\":" << quote(running->target_object_id)
            << ",\"start_total_minutes\":" << running->started_at_total_minutes
            << ",\"elapsed_minutes\":" << running->elapsed_minutes
            << ",\"planned_minutes\":" << running->planned_duration_minutes
            << ",\"remaining_minutes\":" << remaining << '}';
    } else out << "null";
    out << ",\"candidates\":[";
    first = true;
    for (const CandidateAction& candidate : decision.candidates) {
        if (!candidate.hard_admissible) continue;
        if (!first) out << ',';
        first = false;
        const std::string id = "c" + std::to_string(request.candidates.size());
        const bool same_running = running && running->status == RunningActionStatus::Running
            && candidate.action == running->action && candidate.target_object_id == running->target_object_id;
        const int planned = same_running
            ? std::max(0, running->planned_duration_minutes - running->elapsed_minutes)
            : action_definition(candidate.action).default_duration_minutes;
        request.candidates.push_back({id, &candidate, planned, same_running});
        out << "{\"candidate_id\":" << quote(id)
            << ",\"action\":" << quote(to_string(candidate.action))
            << ",\"hard_admissible\":true"
            << ",\"target\":" << quote(candidate.target_object_id)
            << ",\"planned_minutes\":" << planned
            << ",\"nominal_default_minutes\":" << action_definition(candidate.action).default_duration_minutes
            << ",\"retains_progress\":" << (same_running ? "true" : "false") << '}';
    }
    out << "]}";
    request.json = out.str();
    return request;
}

PolicySelection HistoryLlmPolicyV0::select(const DecisionContext& decision, const Observation& observation,
    const CharacterState&, const Personality&, std::mt19937& rng) {
    static const ActorHistory empty;
    return select_with_history(decision, observation, CharacterState{}, Personality{}, empty, nullptr, rng);
}

PolicySelection HistoryLlmPolicyV0::select_with_history(const DecisionContext& decision,
    const Observation& observation, const CharacterState&, const Personality&,
    const ActorHistory& history, const RunningAction* running, std::mt19937&) {
    if (!transport_) throw std::runtime_error("history-llm transport/setup/missing");
    const HistoryLlmRequestV0 request = build_history_llm_request_v0(decision, observation, history, running);
    std::vector<std::string> ids;
    for (const HistoryLlmCandidateV0& candidate : request.candidates) ids.push_back(candidate.id);
    const HistoryLlmTransportResultV0 result = transport_(request.json, ids);
    if (!result.ok) {
        throw std::runtime_error("history-llm " + (result.stage.empty() ? "selection" : result.stage)
            + "/" + (result.error_type.empty() ? "failure" : result.error_type));
    }
    const bool valid_hash = result.request_sha256.size() == 64
        && std::all_of(result.request_sha256.begin(), result.request_sha256.end(),
            [](unsigned char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); });
    if (!valid_hash) throw std::runtime_error("history-llm response/request_sha256/invalid");
    const auto selected = std::find_if(request.candidates.begin(), request.candidates.end(),
        [&result](const HistoryLlmCandidateV0& item) { return item.id == result.candidate_id; });
    if (selected == request.candidates.end())
        throw std::runtime_error("history-llm response/candidate_id/unknown");
    if (!selected->candidate || !selected->candidate->hard_admissible)
        throw std::runtime_error("history-llm response/candidate_id/not_hard_admissible");
    return {selected->candidate->action, identity(), result_provenance(result),
        {{selected->candidate->action, 1.0}}};
}

HistoryLlmTransportResultV0 run_history_llm_worker_v0(const std::string& request_json,
    const std::vector<std::string>& candidate_ids, const std::string& run_directory,
    const std::string& model_id, int timeout_ms, const std::string& endpoint) {
#ifdef _WIN32
    (void)request_json; (void)candidate_ids; (void)run_directory; (void)model_id; (void)timeout_ms; (void)endpoint;
    return {false, {}, {}, "transport", "UnsupportedPlatform", "error", 0, -1, -1};
#else
    if (timeout_ms <= 0) return {false, {}, {}, "transport", "InvalidTimeout", "error", 0, -1, -1};
    // The JSON request already contains the complete hard-admissible candidate surface;
    // worker receives the IDs separately to enforce a strict enum response schema.
    std::ostringstream wrapper;
    wrapper << "{\"policy_request\":" << request_json << ",\"candidate_ids\":[";
    for (std::size_t i = 0; i < candidate_ids.size(); ++i) {
        if (i) wrapper << ',';
        wrapper << quote(candidate_ids[i]);
    }
    wrapper << "]}";
    return execute_worker(wrapper.str(), run_directory, model_id, timeout_ms, endpoint);
#endif
}
