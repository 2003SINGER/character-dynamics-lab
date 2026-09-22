#pragma once

#include "character_policy.h"

#include <string>

// A deliberately narrow local transport for DemoLayaPolicyV0. The companion
// Python proxy owns model calls/cassette replay. This client transmits only
// O/S/P and eligible A^O candidates over loopback and rejects malformed or
// out-of-support answers rather than silently falling back to RulePolicy.
class LayaSocketPolicyV0 final : public CharacterPolicy {
public:
    explicit LayaSocketPolicyV0(int port = 8742) : port_(port) {}
    PolicySelection select(const DecisionContext&, const Observation&,
                           const CharacterState&, const Personality&, std::mt19937&) override;
    const char* identity() const override { return "laya-policy-v0"; }
private:
    int port_;
    unsigned long long request_index_ = 0;
};
