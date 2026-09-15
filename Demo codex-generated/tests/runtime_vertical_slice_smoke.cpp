#include "appraisal.h"
#include "decision.h"
#include "observation.h"
#include "runtime_scheduler.h"
#include "state.h"
#include "world.h"
#include "world_runtime_adapter.h"

#include <algorithm>
#include <iostream>

namespace {
bool has_tag(const Appraisal& appraisal, const std::string& tag) {
    return std::find(appraisal.tags.begin(), appraisal.tags.end(), tag) != appraisal.tags.end();
}

const CandidateAction* highest_probability(const DecisionContext& decision) {
    const CandidateAction* selected = nullptr;
    for (const CandidateAction& candidate : decision.candidates) {
        if (candidate.probability > 0.0
            && (selected == nullptr || candidate.probability > selected->probability)) {
            selected = &candidate;
        }
    }
    return selected;
}
}

int main() {
    Personality personality;
    CharacterState state;
    World world;
    world.time.minute_of_day = 9 * 60 + 20;
    Observation observation = refresh_observation({}, world, {});
    RuntimeScheduler scheduler(9 * 60 + 20);
    WorldRuntimeAdapter world_runtime(world, scheduler);
    const WorldOutcome start = world.validate_runtime_start(ActionType::StudyFocused, "desk");
    if (!start.accepted) { std::cerr << "W rejected a legal study start\n"; return 1; }
    scheduler.start_action(ActionType::StudyFocused, "desk", 35, true);
    // This is only a temporal boundary request. The actual message payload is
    // produced by World::advance_runtime_by at its legacy deterministic 09:30
    // schedule, not hand-written by this caller.
    scheduler.schedule({"world_event_boundary", 9 * 60 + 30, false, false});

    // [09:00, 09:10): continuous S receives both elapsed duration and the
    // running study action, while policy remains closed at the weak event.
    const RuntimeBoundary message_boundary = scheduler.advance_to_next_boundary();
    const std::vector<WorldEvent> world_events = world_runtime.advance_to_boundary(message_boundary, scheduler);
    const StateUpdate study_first_leg = advance_continuous_state(
        state, personality, &*message_boundary.action_after_boundary, message_boundary.elapsed_minutes);
    const auto message = std::find_if(world_events.begin(), world_events.end(), [](const WorldEvent& event) {
        return event.id == "message-study-group";
    });
    if (message == world_events.end()) {
        std::cerr << "World did not emit the scheduled message at the runtime boundary\n";
        return 1;
    }
    apply_world_events(observation, world_events, world.time_summary());
    const Appraisal message_x = appraise(observation, state, personality);
    const StateUpdate message_impulse = update_state(state, message_x, personality, 0);
    observation.updates_this_refresh.clear();
    clear_pending_appraisal_updates(observation);

    if (message_boundary.elapsed_minutes != 10 || message_boundary.decision_gate.open
        || total_minutes(world.time) != scheduler.now_total_minutes()
        || study_first_leg.applied.fatigue <= 0.0
        || !has_known_fact(observation, "message.unread_count", "1")
        || !has_tag(message_x, "social_task_reminder")
        || message_impulse.applied.task_pressure <= 0.0) {
        std::cerr << "weak runtime event must traverse continuous S and O-X-S without reopening policy\n";
        return 1;
    }

    // [09:10, 09:35): the action continues. At completion, W settlement and
    // its typed self-feedback occur before the gate authorizes the next pi.
    const RuntimeBoundary completion_boundary = scheduler.advance_to_next_boundary();
    const std::vector<WorldEvent> completion_events = world_runtime.advance_to_boundary(completion_boundary, scheduler);
    const StateUpdate study_second_leg = advance_continuous_state(
        state, personality, &*completion_boundary.action_after_boundary, completion_boundary.elapsed_minutes);
    const WorldOutcome completion = world.settle_runtime_completion(
        ActionType::StudyFocused, "desk", completion_boundary.action_after_boundary->elapsed_minutes);
    apply_self_action_feedback(observation, completion, world.time_summary());
    const Appraisal completion_x = appraise(observation, state, personality);
    const StateUpdate completion_impulse = update_state(state, completion_x, personality, 0);
    const DecisionContext next_policy = decide(observation, state, personality);
    const CandidateAction* next = highest_probability(next_policy);
    if (next != nullptr) {
        scheduler.start_action(next->action, next->target_object_id,
                               action_definition(next->action).default_duration_minutes);
    }

    if (completion_boundary.elapsed_minutes != 25
        || !completion_boundary.decision_gate.open
        || completion_boundary.action_after_boundary->status != RunningActionStatus::Completed
        || study_second_leg.applied.fatigue <= 0.0
        || !completion_events.empty()
        || total_minutes(world.time) != scheduler.now_total_minutes()
        || !completion.accepted || completion.elapsed_minutes != 0
        || completion.time_advanced_by_settlement != 0
        || completion.action_elapsed_minutes != 35 || completion.task_effort_gained <= 0.0
        || completion_impulse.applied.elapsed_minutes != 0
        || next == nullptr || !scheduler.running_action().has_value()) {
        std::cerr << "completion must settle W/O/X/S before the gated next policy action\n";
        return 1;
    }
    std::cout << "runtime vertical slice smoke OK\n";
    return 0;
}
