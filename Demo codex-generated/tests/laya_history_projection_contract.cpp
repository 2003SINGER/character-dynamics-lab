#include "local_model_policy_v0.h"
#include "world.h"

#include <cstdlib>
#include <random>

static DecisionContext make_decision(double rule_probability, const char* rule_reason) {
    DecisionContext decision;
    for (const ActionType action : {ActionType::SleepAtBed, ActionType::RestAtBed}) {
        CandidateAction candidate;
        candidate.action = action;
        candidate.target_object_id = "bed";
        candidate.eligible = true;
        candidate.hard_admissible = true;
        candidate.rule_soft_eligible = rule_probability > 0.5;
        candidate.probability = rule_probability;
        candidate.reason = rule_reason;
        decision.candidates.push_back(candidate);
    }
    return decision;
}

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    LayaTypedPolicyV0 policy(std::atoi(argv[1]));
    World hidden_world_a;
    World hidden_world_b = hidden_world_a;
    hidden_world_a.time = SimTime{2, 0};
    hidden_world_b.time = SimTime{2, 0};
    hidden_world_a.wallet = 1;
    hidden_world_b.wallet = 999;
    Observation observation_a = refresh_observation({}, hidden_world_a, {}, InformationAccess{});
    Observation observation_b = refresh_observation({}, hidden_world_b, {}, InformationAccess{});
    apply_observable_runtime_event(observation_a, "clock.total_minutes", "1440", "test", "Day 2 00:00");
    apply_observable_runtime_event(observation_b, "clock.total_minutes", "1440", "test", "Day 2 00:00");
    if (observation_a.known_actions != observation_b.known_actions
        || observation_a.facts.size() != observation_b.facts.size()) return 2;
    for (std::size_t i = 0; i < observation_a.facts.size(); ++i) {
        if (observation_a.facts[i].key != observation_b.facts[i].key
            || observation_a.facts[i].value != observation_b.facts[i].value
            || observation_a.facts[i].status != observation_b.facts[i].status) return 3;
    }
    CharacterState same_state;
    Personality same_personality;
    ActorHistory history;
    const auto add_rest = [&](int start, int end) {
        ActorEpisode episode;
        episode.action = ActionType::RestAtBed;
        episode.start_total_minutes = start;
        episode.end_total_minutes = end;
        episode.planned_minutes = end - start;
        episode.actual_minutes = end - start;
        episode.outcome = "completed";
        history.episodes.push_back(episode);
    };
    add_rest(-1500, -1400); // crosses the 48-hour aggregation boundary
    add_rest(300, 360);
    add_rest(720, 780);
    add_rest(1100, 1160);
    std::mt19937 rng(33);

    // The two calls model different hidden W (e.g. different inaccessible wallet
    // balances), while supplying exactly the same actor-visible O/S/P/AO/H.
    // Rule-only probability/reason are deliberately perturbed and must not cross
    // the Laya serialization boundary.
    policy.select_with_history(make_decision(0.9, "rule preferred"), observation_a,
        same_state, same_personality, history, nullptr, rng);
    policy.select_with_history(make_decision(0.1, "rule rejected"), observation_b,
        same_state, same_personality, history, nullptr, rng);

    // A history-only change with the same O/S/P/AO must change the wire request.
    history.episodes.pop_back();
    ActorEpisode sleep;
    sleep.action = ActionType::SleepAtBed;
    sleep.start_total_minutes = 900;
    sleep.end_total_minutes = 1380;
    sleep.planned_minutes = 480;
    sleep.actual_minutes = 480;
    sleep.outcome = "completed";
    history.episodes.push_back(sleep);
    policy.select_with_history(make_decision(0.9, "rule preferred"), observation_a,
        same_state, same_personality, history, nullptr, rng);
    return 0;
}
