#include "continuous_runtime.h"
#include "reference_rule_dynamics_v0.h"

#include <iostream>

static void print_action(const char* label, const std::optional<RunningAction>& action) {
    std::cout << label << "=";
    if (!action) { std::cout << "none\n"; return; }
    std::cout << to_string(action->action) << ":" << action->target_object_id
              << "@" << action->started_at_total_minutes << "+" << action->elapsed_minutes << "\n";
}

int main() {
    World world;
    world.time.minute_of_day = 9 * 60 + 20;
    RuntimeScheduler scheduler(9 * 60 + 20);
    Observation observation = refresh_observation({}, world, {});
    ReferenceRuleDynamicsV0 dynamics;
    ContinuousRuntime runtime(scheduler, world, observation, dynamics, {}, 12345U);
    if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 1;
    CharacterState state;
    Personality personality;
    const RuntimeExecutionResult tick = runtime.execute_next_boundary(state, personality);
    if (tick.policy_seed != 12345U || tick.runtime.boundary.at_total_minutes <= tick.runtime.boundary.from_total_minutes
        || !tick.runtime.boundary.action_after_boundary.has_value()
        || tick.continuous_state.applied.elapsed_minutes <= 0
        || scheduler.now_total_minutes() != total_minutes(world.time)) return 2;
    std::cout << "trace seed=" << tick.policy_seed
              << " boundary=" << tick.runtime.boundary.from_total_minutes << "->"
              << tick.runtime.boundary.at_total_minutes << "\n";
    print_action("running_before", tick.running_action_before);
    print_action("running_after", tick.running_action_after);
    std::cout << "world_events=" << tick.runtime.world_events.size()
              << " delta_o=" << tick.observation_deltas.size()
              << " appraisal_tags=" << tick.appraisal.tags.size()
              << " continuous_elapsed=" << tick.continuous_state.applied.elapsed_minutes
              << " impulse_elapsed=" << tick.impulse_state.applied.elapsed_minutes
              << " gate_open=" << tick.runtime.boundary.decision_gate.open
              << " selected=" << (tick.selected_action ? to_string(*tick.selected_action) : "none")
              << ":" << tick.selected_target_object_id
              << " pre_outcome=" << (tick.pre_policy_outcome ? tick.pre_policy_outcome->provenance : "none")
              << " post_outcome=" << (tick.post_policy_outcome ? tick.post_policy_outcome->provenance : "none")
              << "\n";
    std::cout << "gate_reasons=";
    for (const auto reason : tick.runtime.boundary.decision_gate.reasons) std::cout << to_string(reason) << ",";
    std::cout << " replacement_validation=" << tick.replacement_validation_performed
              << "/" << tick.replacement_validation_accepted << "\n";
    return 0;
}
