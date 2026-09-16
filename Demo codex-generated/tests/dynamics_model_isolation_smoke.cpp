#include "continuous_runtime.h"
#include "reference_rule_dynamics_v0.h"
#include "demo_living_dynamics_v0.h"
#include <string>

int main() {
    World reference_world(17), demo_world(17);
    reference_world.time.minute_of_day = demo_world.time.minute_of_day = 480;
    Observation reference_observation = refresh_observation({}, reference_world, {});
    Observation demo_observation = refresh_observation({}, demo_world, {});
    RuntimeScheduler reference_scheduler(480), demo_scheduler(480);
    ReferenceRuleDynamicsV0 reference_model;
    DemoLivingDynamicsV0 demo_model;
    ContinuousRuntime reference_runtime(reference_scheduler, reference_world, reference_observation, reference_model, {}, 101);
    ContinuousRuntime demo_runtime(demo_scheduler, demo_world, demo_observation, demo_model, {}, 101);
    if (std::string(reference_model.identity()) == std::string(demo_model.identity())) return 1;
    reference_runtime.submit_action_intent(ActionType::Idle, "", 10);
    demo_runtime.submit_action_intent(ActionType::Idle, "", 10);
    CharacterState reference_state, demo_state; Personality personality;
    const auto reference_step = reference_runtime.execute_next_boundary(reference_state, personality);
    const auto demo_step = demo_runtime.execute_next_boundary(demo_state, personality);
    if (reference_step.runtime.boundary.at_total_minutes != demo_step.runtime.boundary.at_total_minutes
        || reference_step.runtime.boundary.elapsed_minutes != demo_step.runtime.boundary.elapsed_minutes
        || reference_scheduler.now_total_minutes() != demo_scheduler.now_total_minutes()) return 2;
    // Both models use the same W/O/scheduler kernel; only their behavior-law
    // outputs are allowed to differ.
    if (reference_world.time_summary() != demo_world.time_summary()
        || reference_observation.facts.size() != demo_observation.facts.size()) return 3;
    return 0;
}
