#include "continuous_runtime.h"
#include "demo_living_dynamics_v1.h"
#include "living_dynamics.h"
#include "simulation_time.h"

#include <algorithm>

namespace {
bool has_reason(const RuntimeExecutionResult& result, DecisionGateReason reason) {
    return std::find(result.runtime.boundary.decision_gate.reasons.begin(),
                     result.runtime.boundary.decision_gate.reasons.end(), reason)
        != result.runtime.boundary.decision_gate.reasons.end();
}

bool clock_projection(int start_minutes, int expected_minutes, const char* expected_text) {
    World world;
    world.time = SimTime{start_minutes / (24 * 60) + 1, start_minutes % (24 * 60)};
    Observation observation = refresh_observation({}, world, {});
    RuntimeScheduler scheduler(start_minutes, 1);
    scheduler.schedule(ScheduledRuntimeEvent{"clock-check", expected_minutes, false, std::nullopt,
                                               DecisionGateReason::Initial});
    DemoLivingDynamicsV1 dynamics;
    ContinuousRuntime runtime(scheduler, world, observation, dynamics);
    CharacterState state;
    Personality personality;
    const auto result = runtime.execute_next_boundary(state, personality);
    int numeric = -1;
    const ObservationFact* formatted = find_fact(observation, FactKey::ClockTime);
    const ObservationFact* numeric_fact = find_fact(observation, "clock.total_minutes");
    return result.runtime.boundary.at_total_minutes == expected_minutes
        && known_int(observation, "clock.total_minutes", numeric)
        && numeric == expected_minutes
        && formatted && formatted->value == expected_text
        && numeric_fact && numeric_fact->source == formatted->source
        && numeric_fact->observed_at == formatted->observed_at;
}

bool forked_midnight_clock_projection() {
    World world;
    world.time = SimTime{1, 23 * 60 + 58};
    Observation observation = refresh_observation({}, world, {});
    RuntimeScheduler scheduler(1438, 1);
    scheduler.schedule(ScheduledRuntimeEvent{"pre-midnight", 1439, false, std::nullopt,
                                               DecisionGateReason::Initial});
    DemoLivingDynamicsV1 dynamics;
    ContinuousRuntime runtime(scheduler, world, observation, dynamics);
    CharacterState state;
    Personality personality;
    runtime.execute_next_boundary(state, personality);
    if (scheduler.now_total_minutes() != 1439) return false;

    // An experiment fork copies O and the scheduler-owned instant; the child
    // projects the next formatted/numeric pair from that same timestamp.
    World fork_world = world;
    Observation fork_observation = observation;
    RuntimeScheduler fork_scheduler(scheduler.now_total_minutes(), 1);
    fork_scheduler.schedule(ScheduledRuntimeEvent{"midnight", 1440, false, std::nullopt,
                                                   DecisionGateReason::Initial});
    ContinuousRuntime fork_runtime(fork_scheduler, fork_world, fork_observation, dynamics);
    CharacterState fork_state = state;
    const auto result = fork_runtime.execute_next_boundary(fork_state, personality);
    int total = -1;
    const ObservationFact* formatted = find_fact(fork_observation, FactKey::ClockTime);
    const ObservationFact* numeric = find_fact(fork_observation, "clock.total_minutes");
    return result.runtime.boundary.at_total_minutes == 1440
        && known_int(fork_observation, "clock.total_minutes", total) && total == 1440
        && formatted && formatted->value == "Day 2 00:00"
        && numeric && numeric->source == formatted->source
        && numeric->observed_at == formatted->observed_at;
}
}

int main() {
    if (!clock_projection(489, 490, "Day 1 08:10")) return 61;
    if (!clock_projection(8572, 8573, "Day 6 22:53")) return 62;
    if (!clock_projection(1439, 1440, "Day 2 00:00")) return 63;
    if (!forked_midnight_clock_projection()) return 64;
    Personality personality;
    DemoLivingDynamicsV1 dynamics;

    // A long sleep is reconsidered as soon as fatigue crosses its V1
    // satiation boundary; selecting the same action preserves elapsed work.
    World sleep_world;
    Observation sleep_o = refresh_observation({}, sleep_world, {});
    RuntimeScheduler sleep_scheduler(total_minutes(sleep_world.time), 60);
    ContinuousRuntime sleep_runtime(sleep_scheduler, sleep_world, sleep_o, dynamics);
    CharacterState sleep_state;
    sleep_state.fatigue = .60;
    sleep_runtime.set_test_action_selector([](const DecisionContext&) { return ActionType::SleepAtBed; });
    if (!sleep_runtime.submit_action_intent(ActionType::SleepAtBed, "bed", 480).accepted) return 1;
    const RuntimeExecutionResult first = sleep_runtime.execute_next_boundary(sleep_state, personality);
    const RuntimeExecutionResult second = sleep_runtime.execute_next_boundary(sleep_state, personality);
    if (!has_reason(second, DecisionGateReason::DynamicsReconsideration)
        || second.dynamics_reconsideration_reason != "sleep_recovery_satisfied"
        || !second.policy_evaluated || !second.running_action_after.has_value()
        || second.running_action_after->action != ActionType::SleepAtBed
        || second.running_action_after->elapsed_minutes <= first.running_action_after->elapsed_minutes) return 2;
    int observed_clock = -1;
    if (!known_int(sleep_o, "clock.total_minutes", observed_clock)
        || observed_clock != sleep_scheduler.now_total_minutes()) return 3;

    // A later urgent crossing is not swallowed after the older .40 gate: it
    // causes another policy opportunity and can replace the long action.
    World urgent_world;
    Observation urgent_o = refresh_observation({}, urgent_world, {});
    RuntimeScheduler urgent_scheduler(total_minutes(urgent_world.time), 60);
    ContinuousRuntime urgent_runtime(urgent_scheduler, urgent_world, urgent_o, dynamics);
    CharacterState urgent_state;
    // Perceived urgency crosses the V1 boundary during the next sleep
    // integration interval rather than relying on a pre-saturated raw state.
    urgent_state.hunger = .85;
    urgent_runtime.set_test_action_selector([](const DecisionContext&) { return ActionType::GetMeal; });
    if (!urgent_runtime.submit_action_intent(ActionType::SleepAtBed, "bed", 480).accepted) return 4;
    RuntimeExecutionResult urgent;
    bool saw_urgent_gate = false;
    for (int boundary = 0; boundary < 12; ++boundary) {
        urgent = urgent_runtime.execute_next_boundary(urgent_state, personality);
        if (has_reason(urgent, DecisionGateReason::DynamicsReconsideration)) {
            saw_urgent_gate = true;
            break;
        }
    }
    if (!saw_urgent_gate) return 51;
    if (urgent.dynamics_reconsideration_reason != "urgent_hunger") return 52;
    if (!urgent.policy_evaluated) return 53;
    if (!urgent.post_policy_outcome.has_value()) return 54;
    if (!urgent.running_action_after.has_value()) return 55;
    if (urgent.running_action_after->action != ActionType::GetMeal) return 56;
    return 0;
}
