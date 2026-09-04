#include "simulation.h"

#include "appraisal.h"
#include "decision.h"
#include "observation.h"
#include "state.h"
#include "world.h"

#include <algorithm>
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

std::string action_space_summary(const std::vector<ActionType>& world_actions) {
    std::ostringstream output;
    output << "A^W=";
    for (ActionType action : world_actions) {
        output << to_string(action) << ' ';
    }
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
    for (Object& object : unavailable_computer.current_room().objects) {
        if (object.id == "computer") {
            object.usable = false;
        }
    }
    const WorldOutcome rejected = unavailable_computer.execute(ActionType::UseComputer);

    World primitive_world;
    const CharacterActionPlan study_plan = primitive_world.expand_action(ActionType::StudyAtDesk);
    const WorldOutcome settled_study = primitive_world.settle(study_plan);

    World sleeping_world;
    sleeping_world.time.minute_of_day = 10 * 60 + 46;
    const WorldOutcome interrupted_sleep = sleeping_world.settle(
        sleeping_world.expand_action(ActionType::SleepAtBed));
    const bool sleep_primitive_shortened = std::any_of(interrupted_sleep.settled_primitives.begin(),
        interrupted_sleep.settled_primitives.end(), [](const WorldPrimitive& primitive) {
            const auto* advance = std::get_if<AdvanceSimulationTime>(&primitive.payload);
            return advance != nullptr && advance->minutes == 314;
        });

    const bool reproducible = first_run == repeated_first_run;
    const bool profile_sensitive = first_run != second_run;
    const bool validates_world = !rejected.accepted && !rejected.provenance.empty();
    const bool has_primitives = first_run.find("a^world") != std::string::npos;
    const bool primitives_settle = settled_study.accepted && primitive_world.task_progress == 1
                                && settled_study.settled_primitives.size() == study_plan.world_primitives.size();
    const bool handles_interruption = interrupted_sleep.accepted && interrupted_sleep.woke_early
                                   && sleep_primitive_shortened;

    output << "verify: reproducible=" << reproducible
           << ", profile_sensitive=" << profile_sensitive
           << ", rejects_illegal_action=" << validates_world
           << ", trace_has_primitives=" << has_primitives
           << ", primitives_settle=" << primitives_settle
           << ", interruption_rewrites_plan=" << handles_interruption << '\n';
    return reproducible && profile_sensitive && validates_world && has_primitives
        && primitives_settle && handles_interruption;
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
        const std::vector<ActionType> world_actions = world.available_actions();
        const Appraisal appraisal = appraise(observation, state, personality);
        clear_pending_appraisal_updates(observation);
        const StateDelta state_delta = update_state(state, appraisal, personality, previous_outcome.elapsed_minutes);
        const DecisionContext decision = decide(observation, state, personality);
        const ActionType chosen_action = sample_action(decision, rng);
        const std::string state_at_decision = state_summary(state);
        const std::string world_before = world.summary();
        const std::string decision_time = world.time_summary();
        const CharacterActionPlan action_plan = world.expand_action(chosen_action);
        const WorldOutcome outcome = world.settle(action_plan);
        if (outcome.accepted) {
            update_intention(state, chosen_action);
        }

        output << "\n[Decision point " << step << " | " << decision_time << "]\n"
               << "  W before action: " << world_before << '\n'
               << "  X input: Delta-O / O + old S + P"
               << " | self_action=" << to_string(observation.last_self_action.action) << '\n'
               << (previous_outcome.observation_frozen_during_action
                       ? "  O refresh boundary: W advanced during sleep while O was frozen; current room perception now reconciles O.\n"
                       : "")
               << "  " << observation_summary(observation) << '\n'
               << "  " << action_space_summary(world_actions) << '\n'
               << "  " << appraisal_summary(appraisal) << '\n'
               << "  " << state_delta_summary(state_delta) << '\n'
               << "  " << state_at_decision << '\n'
               << "  " << decision_summary(decision)
               << "  chosen A^char: " << to_string(chosen_action) << '\n'
               << "  planned a^world: " << world_primitives_summary(action_plan.world_primitives) << '\n'
               << "  W settlement: " << (outcome.accepted ? "accepted" : "rejected")
               << " | provenance=" << outcome.provenance;
        if (!outcome.object_id.empty()) {
            output << " | object=" << outcome.object_id;
        }
        output << '\n';
        output << "  settled a^world: " << world_primitives_summary(outcome.settled_primitives) << '\n';
        output << "  persistent intention after settlement: " << state_summary(state) << '\n';
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
