#pragma once

#include "character_policy.h"

#include <functional>
#include <string>
#include <vector>

struct HistoryLlmTransportResultV0 {
    bool ok = false;
    std::string candidate_id;
    std::string request_sha256;
    std::string stage;
    std::string error_type;
    std::string api_status;
    int elapsed_ms = 0;
    int prompt_tokens = -1;
    int completion_tokens = -1;
};

using HistoryLlmTransportV0 = std::function<HistoryLlmTransportResultV0(
    const std::string& request_json, const std::vector<std::string>& candidate_ids)>;

struct HistoryLlmCandidateV0 {
    std::string id;
    const CandidateAction* candidate = nullptr;
    int planned_minutes = 0;
    bool retains_progress = false;
};

struct HistoryLlmRequestV0 {
    std::string json;
    std::vector<HistoryLlmCandidateV0> candidates;
};

HistoryLlmRequestV0 build_history_llm_request_v0(const DecisionContext&,
    const Observation&, const ActorHistory&, const RunningAction*);

class HistoryLlmPolicyV0 final : public CharacterPolicy {
public:
    explicit HistoryLlmPolicyV0(HistoryLlmTransportV0 transport)
        : transport_(std::move(transport)) {}
    PolicySelection select(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937&) override;
    PolicySelection select_with_history(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, const ActorHistory&,
                           const RunningAction*, std::mt19937&) override;
    const char* identity() const override { return "npc-continuity-history-llm-v0"; }
private:
    HistoryLlmTransportV0 transport_;
};

HistoryLlmTransportResultV0 run_history_llm_worker_v0(
    const std::string& request_json, const std::vector<std::string>& candidate_ids,
    const std::string& run_directory, const std::string& model_id,
    int timeout_ms = 45000,
    const std::string& endpoint = "http://127.0.0.1:8080/v1/chat/completions");

std::string json_escape_history_llm_v0(const std::string&);
