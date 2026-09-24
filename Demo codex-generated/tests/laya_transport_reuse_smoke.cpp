#include "local_model_policy_v0.h"

#include <chrono>
#include <cstdlib>
#include <random>
#include <thread>

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    LayaTypedPolicyV0 policy(std::atoi(argv[1]));
    DecisionContext decision;
    CandidateAction idle;
    idle.action = ActionType::Idle;
    idle.eligible = true;
    idle.hard_admissible = true;
    idle.probability = 1.0;
    decision.candidates.push_back(idle);
    Observation observation;
    CharacterState state;
    Personality personality;
    std::mt19937 rng(13);
    if (policy.select(decision, observation, state, personality, rng).action != ActionType::Idle) return 2;
    std::this_thread::sleep_for(std::chrono::milliseconds(700));
    if (policy.select(decision, observation, state, personality, rng).action != ActionType::Idle) return 3;
    return 0;
}
