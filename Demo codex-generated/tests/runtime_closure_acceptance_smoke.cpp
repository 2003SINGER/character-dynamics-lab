#include "continuous_runtime.h"
#include "observation.h"
#include "state.h"

#include <cmath>
#include <iostream>

int main() {
    // B2/B3: scheduler dedupes and W exposes the earliest event, including a deadline.
    World world;
    world.time.minute_of_day = 9 * 60 + 20;
    world.tasks.front().due_at_total_minutes = 9 * 60 + 25;
    const auto next = world.next_runtime_event_after(9 * 60 + 20);
    if (!next || next->id != "task-deadline" || next->occurred_at_total_minutes != 9 * 60 + 25) return 1;
    RuntimeScheduler scheduler(9 * 60 + 20);
    scheduler.schedule({"world_event:message-study-group", 9 * 60 + 30, false, false});
    scheduler.schedule({"world_event:message-study-group", 9 * 60 + 30, false, false});
    scheduler.schedule({"world_event:task-deadline", 9 * 60 + 25, false, false});
    const RuntimeBoundary boundary = scheduler.advance_to_next_boundary();
    if (boundary.at_total_minutes != 9 * 60 + 25 || boundary.events.size() != 1) return 2;

    // C1/E2: rejected intent is typed and reaches actor-local constraint belief.
    Observation observation = refresh_observation({}, world, {});
    world.time.minute_of_day = 9 * 60 + 25;
    ContinuousRuntime runtime(scheduler, world, observation);
    world.wallet = 0;
    const WorldOutcome rejected = runtime.submit_action_intent(ActionType::ShopOnPhone, "phone", 10);
    if (rejected.accepted || rejected.failure_reason != RejectionReason::ResourceInsufficient
        || rejected.provenance.empty()) return 3;
    CharacterState rejection_state;
    Personality rejection_personality;
    const RuntimeExecutionResult rejection_step = runtime.execute_next_boundary(rejection_state, rejection_personality);
    if (observation.action_constraints.empty() || !rejection_step.runtime.boundary.decision_gate.open) return 4;

    // D3/D4: projection respects curtain and uses actual unread state.
    world.current_room().curtain_open = false;
    world.unread_messages = 3;
    const ObservationFact* weather_before = find_fact(observation, "outside.weather");
    const std::string weather_value_before = weather_before ? weather_before->value : "";
    apply_world_events(observation, {WorldEvent{"weather-rain", "rain", "world/weather", 1}}, world, {}, "09:25");
    const ObservationFact* weather_after = find_fact(observation, "outside.weather");
    if ((weather_after ? weather_after->value : "") != weather_value_before) return 5;
    world.current_room().curtain_open = true;
    apply_world_events(observation, {WorldEvent{"message-study-group", "message", "phone", 1}}, world, {}, "09:25");
    const ObservationFact* unread = find_fact(observation, "message.unread_count");
    if (!unread || unread->value != "3") return 6;
    const std::string unread_before_hidden = unread->value;
    InformationAccess hidden_phone;
    hidden_phone.phone_presence_observable = false;
    world.unread_messages = 4;
    apply_world_events(observation, {WorldEvent{"message-study-group", "message", "phone", 1}}, world,
                       hidden_phone, "09:25");
    unread = find_fact(observation, "message.unread_count");
    if (!unread || unread->value != unread_before_hidden) return 7;
    CharacterState once_state;
    Personality once_personality;
    const Appraisal once_appraisal = appraise(observation, once_state, once_personality);
    const StateUpdate once_impulse = apply_appraisal_impulse(once_state, once_appraisal, once_personality);
    consume_appraisal_inputs(observation);
    const Appraisal replay_appraisal = appraise(observation, once_state, once_personality);
    const StateUpdate replay_impulse = apply_appraisal_impulse(once_state, replay_appraisal, once_personality);
    if (once_impulse.applied.elapsed_minutes != 0 || replay_impulse.applied.task_pressure != 0.0) return 8;
    RuntimeScheduler weak_scheduler(0);
    weak_scheduler.schedule({"hidden-weather", 5, false, false});
    const RuntimeBoundary weak_boundary = weak_scheduler.advance_to_next_boundary();
    if (weak_boundary.decision_gate.open) return 9;

    // F2: deterministic continuous dynamics is chunk-equivalent.
    Personality personality;
    CharacterState one_chunk;
    CharacterState three_chunks;
    RunningAction action{ActionType::StudyFocused, "desk", 0, 30, 0, true, RunningActionStatus::Running};
    advance_continuous_state(one_chunk, personality, &action, 30);
    advance_continuous_state(three_chunks, personality, &action, 10);
    advance_continuous_state(three_chunks, personality, &action, 10);
    advance_continuous_state(three_chunks, personality, &action, 10);
    if (std::abs(one_chunk.fatigue - three_chunks.fatigue) > 1e-9
        || std::abs(one_chunk.screen_strain - three_chunks.screen_strain) > 1e-9) return 10;

    // C4/G: invalidation is a distinct terminal outcome on the next boundary.
    World invalid_world;
    invalid_world.time.minute_of_day = 9 * 60;
    RuntimeScheduler invalid_scheduler(9 * 60);
    Observation invalid_observation = refresh_observation({}, invalid_world, {});
    ContinuousRuntime invalid_runtime(invalid_scheduler, invalid_world, invalid_observation);
    if (!invalid_runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 11;
    invalid_runtime.invalidate_running_action();
    CharacterState invalid_state;
    const RuntimeExecutionResult invalid_step = invalid_runtime.execute_next_boundary(invalid_state, personality);
    if (!invalid_step.outcome || !invalid_step.outcome->plan_invalidated
        || invalid_step.runtime.boundary.decision_gate.reasons.empty()) return 12;

    // B4: bounded steps expose a deterministic need-threshold opportunity.
    World threshold_world;
    threshold_world.time.minute_of_day = 1;
    RuntimeScheduler threshold_scheduler(1, 60);
    Observation threshold_observation = refresh_observation({}, threshold_world, {});
    ContinuousRuntime threshold_runtime(threshold_scheduler, threshold_world, threshold_observation);
    if (!threshold_runtime.submit_action_intent(ActionType::StudyFocused, "desk", 240).accepted) return 13;
    CharacterState threshold_state;
    threshold_state.hunger = 0.35;
    bool saw_threshold = false;
    bool saw_reconsideration = false;
    for (int step = 0; step < 8 && threshold_scheduler.running_action().has_value(); ++step) {
        const RuntimeExecutionResult tick = threshold_runtime.execute_next_boundary(threshold_state, personality);
        for (const DecisionGateReason reason : tick.runtime.boundary.decision_gate.reasons) {
            if (reason == DecisionGateReason::NeedThresholdCrossed) saw_threshold = true;
        }
        if (tick.outcome.has_value() && tick.outcome->plan_invalidated
            && tick.policy_evaluated) {
            saw_reconsideration = true;
        }
    }
    if (!saw_threshold || !saw_reconsideration) return 14;

    // Self-action completion feedback is immediate in runtime and must be consumed once.
    World completion_world;
    completion_world.time.minute_of_day = 9 * 60 + 20;
    completion_world.tasks.front().effort_target = 0.01;
    RuntimeScheduler completion_scheduler(9 * 60 + 20);
    Observation completion_observation = refresh_observation({}, completion_world, {});
    ContinuousRuntime completion_runtime(completion_scheduler, completion_world, completion_observation);
    if (!completion_runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 15;
    CharacterState completion_state;
    int completion_outcomes = 0;
    int completion_signals = 0;
    bool completion_task_completed = false;
    for (int step = 0; step < 4; ++step) {
        const RuntimeExecutionResult completion_tick =
            completion_runtime.execute_next_boundary(completion_state, personality);
        if (completion_tick.outcome.has_value()) {
            if (completion_tick.outcome->task_completed) {
                ++completion_outcomes;
                completion_task_completed = true;
                for (const AppraisalSignal& signal : completion_tick.appraisal.semantic_signals) {
                    if (signal.kind == AppraisalSignalKind::GoalCompletion) ++completion_signals;
                }
            }
        }
    }
    if (completion_outcomes != 1 || !completion_task_completed || completion_signals != 1
        || !completion_observation.pending_appraisal_updates.empty()) {
        return 16;
    }

    std::cout << "runtime closure acceptance smoke OK\n";
    return 0;
}
