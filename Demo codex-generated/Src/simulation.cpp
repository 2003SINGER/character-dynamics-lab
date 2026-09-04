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

namespace {
constexpr int kStepsPerRun = 12;

Personality procrastinating_profile() {
    return {"procrastinating / low self-control", 0.85, 0.20, 0.55};
}

Personality self_controlled_profile() {
    return {"self-controlled / task-oriented", 0.20, 0.85, 0.45};
}

std::string personality_summary(const Personality& personality) {
    std::ostringstream output;
    output << "P{name=" << personality.name
           << ", procrastination=" << std::fixed << std::setprecision(2) << personality.procrastination
           << ", self_control=" << personality.self_control
           << ", rest_preference=" << personality.rest_preference << '}';
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
    unavailable_computer.computer_available = false;
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

    if (include_header) {
        output << "============================================================\n"
               << personality_summary(personality) << "\n"
               << "============================================================\n";
    }

    for (int step = 1; step <= kStepsPerRun; ++step) {
        const Observation observation = refresh_observation(world, "SceneFilter(room) -> direct observation refresh");
        const Appraisal appraisal = appraise(observation);
        const StateDelta state_delta = update_state(state, appraisal, personality);
        const DecisionContext decision = decide(observation, state, personality);
        const ActionType chosen_action = sample_action(decision, rng);
        const std::string world_before = world.summary();
        const WorldOutcome outcome = world.execute(chosen_action);

        output << "\n[Step " << step << "]\n"
               << "  W before decision: " << world_before << '\n'
               << "  " << observation_summary(observation) << '\n'
               << "  " << appraisal_summary(appraisal) << '\n'
               << "  " << state_delta_summary(state_delta) << '\n'
               << "  " << state_summary(state) << '\n'
               << "  " << decision_summary(decision)
               << "  chosen A^char: " << to_string(chosen_action) << '\n'
               << "  W settlement: " << (outcome.accepted ? "accepted" : "rejected")
               << " | provenance=" << outcome.provenance << '\n';
        for (const std::string& effect : outcome.effects) {
            output << "    effect: " << effect << '\n';
        }
    }
    return output.str();
}
