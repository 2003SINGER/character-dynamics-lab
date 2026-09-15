#include "continuous_runtime.h"
#include "decision.h"

#include <algorithm>
#include <iostream>

int main() {
    Personality personality;

    // Scheduler-native Deadline: the event boundary precedes action completion.
    World deadline_world;
    deadline_world.time.minute_of_day = 9 * 60 + 20;
    deadline_world.tasks.front().due_at_total_minutes = 9 * 60 + 25;
    RuntimeScheduler deadline_scheduler(9 * 60 + 20);
    Observation deadline_observation = refresh_observation({}, deadline_world, {});
    ContinuousRuntime deadline_runtime(deadline_scheduler, deadline_world, deadline_observation);
    const WorldOutcome deadline_start = deadline_runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35);
    if (!deadline_start.accepted) { std::cerr << "deadline reject " << static_cast<int>(deadline_start.failure_reason) << "\n"; return 1; }
    CharacterState deadline_state;
    const RuntimeExecutionResult deadline_tick = deadline_runtime.execute_next_boundary(deadline_state, personality);
    if (deadline_tick.runtime.boundary.at_total_minutes != 9 * 60 + 25
        || std::none_of(deadline_tick.runtime.world_events.begin(), deadline_tick.runtime.world_events.end(),
                        [](const WorldEvent& event) { return event.id == "task-deadline"; })
        || !has_known_fact(deadline_observation, "task.deadline_passed", "1")) {
        std::cerr << "deadline t=" << deadline_tick.runtime.boundary.at_total_minutes
                  << " events=" << deadline_tick.runtime.world_events.size() << "\n";
        return 2;
    }

    // Scheduler-native Phone: hidden W absence remains an attempted intent and
    // becomes a typed rejection without creating an illegal RunningAction.
    World phone_world;
    phone_world.time.minute_of_day = 9 * 60 + 20;
    phone_world.current_room().objects.front().usable = false;
    RuntimeScheduler phone_scheduler(9 * 60 + 20);
    InformationAccess hidden_phone;
    hidden_phone.phone_presence_observable = false;
    Observation phone_observation = refresh_observation({}, phone_world, {}, hidden_phone);
    ContinuousRuntime phone_runtime(phone_scheduler, phone_world, phone_observation, hidden_phone);
    if (phone_runtime.submit_action_intent(ActionType::UsePhone, "phone", 10).accepted) return 3;
    CharacterState phone_state;
    const RuntimeExecutionResult phone_tick = phone_runtime.execute_next_boundary(phone_state, personality);
    if ((phone_scheduler.running_action().has_value()
         && phone_scheduler.running_action()->action == ActionType::UsePhone)
        || phone_observation.action_constraints.empty()
        || !phone_tick.policy_evaluated) {
        return 4;
    }

    // Scheduler-native Commitment consumer reads typed self-feedback before O
    // is consumed; hidden completion does not clear the commitment.
    World commitment_world;
    commitment_world.time.minute_of_day = 9 * 60 + 20;
    commitment_world.tasks.front().effort_target = 0.01;
    RuntimeScheduler commitment_scheduler(9 * 60 + 20);
    InformationAccess hidden_completion;
    hidden_completion.self_task_completion_observable = false;
    Observation commitment_observation = refresh_observation({}, commitment_world, {}, hidden_completion);
    ContinuousRuntime commitment_runtime(commitment_scheduler, commitment_world, commitment_observation,
                                          hidden_completion);
    if (!commitment_runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 5;
    CharacterState commitment_state;
    commitment_state.commitment = {CommitmentStatus::Active, "coursework", "fixture", 0, 0};
    commitment_runtime.execute_next_boundary(commitment_state, personality);
    commitment_runtime.execute_next_boundary(commitment_state, personality);
    if (commitment_state.commitment.status != CommitmentStatus::Active) return 6;
    return 0;
}
