#pragma once

#include "character_policy.h"

#include <string>

// Historical Qwen action selector. It returns one action, not Laya's typed
// probability distribution. Kept for the earlier demo cassette path.
class QwenSocketPolicyV0 final : public CharacterPolicy {
public:
    explicit QwenSocketPolicyV0(int port = 8742) : port_(port) {}
    PolicySelection select(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937&) override;
    const char* identity() const override { return "qwen-action-policy-v0"; }
private:
    int port_;
    unsigned long long request_index_ = 0;
};

// Actual local Laya typed-decisions adapter. It validates a complete choice
// distribution and samples it with the Runtime's seeded RNG; World stays hidden.
class LayaTypedPolicyV0 final : public CharacterPolicy {
public:
    explicit LayaTypedPolicyV0(int port = 8743, bool soft_gate_enabled = false)
        : port_(port), soft_gate_enabled_(soft_gate_enabled) {}
    PolicySelection select(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937&) override;
    const char* identity() const override { return "laya-typed-policy-v0"; }
    std::optional<SoftReconsideration> soft_reconsider(
        const Observation&, const CharacterState&, const Personality&,
        const RunningAction&, std::mt19937&) override;
private:
    int port_;
    bool soft_gate_enabled_ = false;
    unsigned long long request_index_ = 0;
};
