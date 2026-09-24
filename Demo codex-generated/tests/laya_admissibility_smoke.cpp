#include "continuous_runtime.h"
#include "demo_living_dynamics_v1.h"
#include "local_model_policy_v0.h"
#include "simulation_time.h"

#include <cstdlib>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    const int port = std::atoi(argv[1]);
    constexpr int start = 8572;
    World world;
    world.time = SimTime{6, 22 * 60 + 52};
    Observation observation = refresh_observation({}, world, {});
    RuntimeScheduler scheduler(start, 1);
    scheduler.schedule(ScheduledRuntimeEvent{"initial-laya-choice", start + 1, false, std::nullopt,
                                               DecisionGateReason::Initial});
    DemoLivingDynamicsV1 dynamics;
    LayaTypedPolicyV0 policy(port);
    ContinuousRuntime runtime(scheduler, world, observation, dynamics, {}, 77, &policy);
    CharacterState state;
    state.boredom = .611577921066;
    state.fatigue = .669499209547;
    state.task_pressure = .0474118001676;
    state.satisfaction = .775081031933;
    state.hunger = .720940431162;
    state.bathroom_urge = .6165536954;
    state.anxiety = .069180455437;
    state.screen_strain = .319666666667;
    Personality personality;
    personality.name = "anxious";
    personality.procrastination = .55;
    personality.self_control = .5;
    personality.rest_preference = .55;
    personality.stimulation_seeking = .5;
    personality.task_anxiety_sensitivity = .85;
    personality.screen_strain_sensitivity = .55;
    personality.need_response = .65;
    personality.action_noise = .4;

    const RuntimeExecutionResult result = runtime.execute_next_boundary(state, personality);
    bool saw_soft_sleep = false;
    for (const CandidateAction& candidate : result.decision.candidates) {
        if (candidate.action == ActionType::SleepAtBed) {
            saw_soft_sleep = !candidate.rule_soft_eligible && candidate.hard_admissible;
        }
    }
    if (!result.policy_evaluated || !saw_soft_sleep
        || !result.selected_action || *result.selected_action != ActionType::SleepAtBed
        || !result.running_action_after
        || result.running_action_after->action != ActionType::SleepAtBed
        || result.running_action_after->planned_duration_minutes != 480) return 2;
    int clock_minutes = -1;
    const ObservationFact* clock = find_fact(observation, FactKey::ClockTime);
    if (!known_int(observation, "clock.total_minutes", clock_minutes)
        || clock_minutes != start + 1 || !clock || clock->value != "Day 6 22:53") return 3;
    return 0;
}
