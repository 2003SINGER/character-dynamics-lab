#include "continuous_runtime.h"
#include "demo_living_dynamics_v1.h"

#include <iostream>

int main() {
    World world(1000);
    Observation observation=refresh_observation({},world,{});
    RuntimeScheduler scheduler(480);
    DemoLivingDynamicsV1 model;
    ContinuousRuntime runtime(scheduler,world,observation,model,{},5000);
    CharacterState state;
    Personality p;
    if (!runtime.submit_action_intent(ActionType::TurnLightOff,"light",5).accepted) return 1;
    runtime.set_test_action_selector([](const DecisionContext&) { return ActionType::TurnLightOn; });
    const RuntimeExecutionResult off=runtime.execute_next_boundary(state,p);
    if (!off.pre_policy_outcome || !off.pre_policy_outcome->accepted
        || world.current_room().light_on || !has_known_fact(observation,"room.light","off")) return 2;
    if (!observation_knows_action(observation,ActionType::TurnLightOn)
        || observation_knows_action(observation,ActionType::StudyFocused)) return 3;
    if (!off.selected_action || *off.selected_action!=ActionType::TurnLightOn
        || !scheduler.running_action() || scheduler.running_action()->action!=ActionType::TurnLightOn) return 4;
    const RuntimeExecutionResult on=runtime.execute_next_boundary(state,p);
    if (!on.pre_policy_outcome || !on.pre_policy_outcome->accepted
        || !world.current_room().light_on || !has_known_fact(observation,"room.light","on")) return 5;
    if (!observation_knows_action(observation,ActionType::StudyFocused)) return 6;
    std::cout<<"room_control_feedback_smoke: PASS\n";
    return 0;
}
