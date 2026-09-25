#pragma once

#include "observation.h"
#include "personality.h"
#include "state.h"
#include "actor_history.h"

#include <map>
#include <random>
#include <string>
#include <utility>
#include <vector>

struct LayaTypedChoice {
    std::string selected;
    std::vector<std::pair<std::string, double>> probabilities;
    std::string provenance;
};

struct LayaTypedScores {
    std::map<std::string, double> values;
    std::string provenance;
};

// Demo-only client. Requests are strictly O/Delta-O/S/P/I and self feedback;
// the bridge never receives a World reference or authoritative W outcome.
class LayaSemanticClientV0 {
public:
    explicit LayaSemanticClientV0(int port) : port_(port) {}
    LayaTypedChoice choose_commitment(const Observation&, const CharacterState&,
                                      const Personality&, const std::vector<std::string>&,
                                      std::mt19937&) const;
    LayaTypedScores score_appraisal(const Observation&, const CharacterState&,
                                    const Personality&) const;
    LayaTypedChoice choose_commitment_with_history(const Observation&, const CharacterState&,
                                      const Personality&, const std::vector<std::string>&,
                                      const ActorHistory&, std::mt19937&) const;
    LayaTypedScores score_appraisal_with_history(const Observation&, const CharacterState&,
                                    const Personality&, const ActorHistory&) const;
private:
    int port_;
    mutable unsigned long long request_index_ = 0;
};
