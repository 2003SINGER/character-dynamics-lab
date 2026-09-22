#include "continuous_runtime.h"
#include "demo_living_dynamics_v1.h"

#include <cmath>
#include <iostream>

int main() {
    World first(1000), same(1000);
    first.enable_life_tape(); same.enable_life_tape();
    if (first.tasks.front().effort_target != same.tasks.front().effort_target
        || first.tasks.front().due_at_total_minutes != same.tasks.front().due_at_total_minutes) return 1;
    const int assignment=480+3*1440;
    if (!first.next_runtime_event_after(assignment-1).has_value()
        || first.next_runtime_event_after(assignment-1)->id!="task-assigned"
        || first.next_runtime_event_after(assignment-1)->occurred_at_total_minutes!=assignment) return 2;

    first.time.day=4; first.time.minute_of_day=479;
    Observation observation=refresh_observation({},first,{});
    RuntimeScheduler scheduler(assignment-1);
    DemoLivingDynamicsV1 model;
    ContinuousRuntime runtime(scheduler,first,observation,model,{},5000);
    CharacterState state;
    state.commitment={CommitmentStatus::Active,"coursework","old episode",480,0};
    if (!runtime.submit_action_intent(ActionType::StudyFocused,"desk",35).accepted) return 3;
    const RuntimeExecutionResult step=runtime.execute_next_boundary(state,Personality{});
    bool assigned=false;
    for (const auto& event:step.runtime.world_events) assigned=assigned || event.id=="task-assigned";
    if (!assigned || scheduler.now_total_minutes()!=assignment || first.life_tape_episode!=1) return 4;
    if (!step.pre_policy_outcome || !step.pre_policy_outcome->plan_invalidated) return 5;
    if (state.commitment.status!=CommitmentStatus::None) return 6;
    if (!has_known_fact(observation,"task.coursework.episode","1")
        || !has_known_fact(observation,"task.coursework.status","active")
        || !has_known_fact(observation,"task.coursework.effort","0.000000")) return 7;
    if (first.tasks.front().due_at_total_minutes!=assignment+2*1440
        || first.tasks.front().effort_done!=0.0) return 8;
    std::cout<<"life_tape_smoke: PASS\n";
    return 0;
}
