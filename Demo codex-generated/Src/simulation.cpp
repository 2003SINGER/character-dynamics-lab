#include "simulation.h"

#include "appraisal.h"
#include "decision.h"
#include "observation.h"
#include "state.h"
#include "world.h"

#include <iomanip>
#include <ostream>
#include <random>
#include <sstream>
#include <utility>

namespace {
constexpr int kStepsPerRun = 12;

Personality procrastinating_profile() {
    return {"procrastinating / low self-control", 0.85, 0.20, 0.55, 0.75, 0.70, 0.45, 0.55, 0.70};
}

Personality self_controlled_profile() {
    return {"self-controlled / task-oriented", 0.20, 0.85, 0.45, 0.35, 0.45, 0.60, 0.65, 0.35};
}

std::string personality_summary(const Personality& personality) {
    std::ostringstream output;
    output << "P{name=" << personality.name
           << ", procrastination=" << std::fixed << std::setprecision(2) << personality.procrastination
           << ", self_control=" << personality.self_control
           << ", rest_preference=" << personality.rest_preference
           << ", stimulation_seeking=" << personality.stimulation_seeking
           << ", task_anxiety_sensitivity=" << personality.task_anxiety_sensitivity
           << ", screen_strain_sensitivity=" << personality.screen_strain_sensitivity
           << ", need_response=" << personality.need_response
           << ", action_noise=" << personality.action_noise << '}';
    return output.str();
}

std::string outcome_summary(const WorldOutcome& outcome) {
    std::ostringstream output;
    output << "last_outcome{action=" << to_string(outcome.action)
           << ", accepted=" << outcome.accepted
           << ", elapsed_minutes=" << outcome.elapsed_minutes
           << ", O_frozen=" << outcome.observation_frozen_during_action
           << ", woke_early=" << outcome.woke_early
           << ", provenance=" << outcome.provenance << '}';
    return output.str();
}
} // namespace

void Simulation::run_all(std::ostream& output) const {
    output << "Character Dynamics Reference\n"
           << "A deterministic, rule-based reading aid. It is not an LLM or a validated psychological model.\n\n";
    output << run_profile(procrastinating_profile(), 20260904U, true) << '\n';
    output << run_profile(self_controlled_profile(), 20260904U, true);
}

bool Simulation::verify(std::ostream& output) const {
    const Personality first = procrastinating_profile();
    const Personality second = self_controlled_profile();

    const std::string first_run = run_profile(first, 20260904U, false);
    const std::string repeated_first_run = run_profile(first, 20260904U, false);
    const std::string second_run = run_profile(second, 20260904U, false);

    World unavailable_computer;
    for (RoomObject& object : unavailable_computer.room_objects) {
        if (object.id == "computer") {
            object.usable = false;
        }
    }
    const WorldOutcome rejected = unavailable_computer.execute(ActionType::UseComputer);

    const bool reproducible = first_run == repeated_first_run;
    const bool profile_sensitive = first_run != second_run;
    const bool validates_world = !rejected.accepted && !rejected.provenance.empty();
    const bool has_provenance = first_run.find("World::execute(") != std::string::npos;

    output << "verify: reproducible=" << reproducible
           << ", profile_sensitive=" << profile_sensitive
           << ", rejects_illegal_action=" << validates_world
           << ", trace_has_provenance=" << has_provenance << '\n';
    return reproducible && profile_sensitive && validates_world && has_provenance;
}

std::string Simulation::run_profile(const Personality& personality,
                                    unsigned int seed,
                                    bool include_header) const {
    World world;
    CharacterState state;
    std::mt19937 rng(seed);
    std::ostringstream output;
    Observation observation;
    WorldOutcome previous_outcome;
    previous_outcome.action = ActionType::Idle;
    previous_outcome.accepted = true;
    previous_outcome.provenance = "initial_world";

    if (include_header) {
        output << "============================================================\n"
               << personality_summary(personality) << "\n"
               << "============================================================\n";
    }

    for (int step = 1; step <= kStepsPerRun; ++step) {
        observation = refresh_observation(std::move(observation), world, previous_outcome);
        const Appraisal appraisal = appraise(observation, previous_outcome);
        const StateDelta state_delta = update_state(state, appraisal, personality, previous_outcome.elapsed_minutes);
        const DecisionContext decision = decide(observation, world, state, personality);
        const ActionType chosen_action = sample_action(decision, rng);
        const std::string state_at_decision = state_summary(state);
        update_intention(state, decision, chosen_action);
        const std::string world_before = world.summary();
        const std::string decision_time = world.time_summary();
        const WorldOutcome outcome = world.execute(chosen_action);

        output << "\n[Decision point " << step << " | " << decision_time << "]\n"
               << "  W before action: " << world_before << '\n'
               << "  X input: " << outcome_summary(previous_outcome) << '\n'
               << (previous_outcome.observation_frozen_during_action
                       ? "  O refresh boundary: W advanced during sleep while O was frozen; current room perception now reconciles O.\n"
                       : "")
               << "  " << observation_summary(observation) << '\n'
               << "  " << appraisal_summary(appraisal) << '\n'
               << "  " << state_delta_summary(state_delta) << '\n'
               << "  " << state_at_decision << '\n'
               << "  " << decision_summary(decision)
               << "  chosen A^char: " << to_string(chosen_action) << '\n'
               << "  W settlement: " << (outcome.accepted ? "accepted" : "rejected")
               << " | provenance=" << outcome.provenance;
        if (!outcome.object_id.empty()) {
            output << " | object=" << outcome.object_id;
        }
        output << '\n';
        output << "  persistent intention after choice: " << state_summary(state) << '\n';
        for (const std::string& effect : outcome.effects) {
            output << "    effect: " << effect << '\n';
        }
        for (const WorldEvent& event : outcome.events) {
            output << "    event: id=" << event.id << " | source=" << event.source
                   << " | " << event.description << '\n';
        }
        if (!outcome.sleeping_sensory_events.empty()) {
            observation = apply_sleep_sensory_update(std::move(observation), outcome, world);
            output << "  O partial update while asleep: " << observation_updates_summary(observation) << '\n';
        }
        output << "  W after action: " << world.summary() << '\n';
        previous_outcome = outcome;
    }
    return output.str();
}
