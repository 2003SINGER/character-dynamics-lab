#include "continuous_runtime.h"
#include "decision.h"

#include <algorithm>
#include <iostream>

static bool has_fact(const Observation& observation, const char* key) {
    return find_fact(observation, key) != nullptr;
}

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
        || !has_known_fact(deadline_observation, "task.deadline_passed", "1")
        || std::find(deadline_tick.appraisal.tags.begin(), deadline_tick.appraisal.tags.end(),
                     "deadline_passed") == deadline_tick.appraisal.tags.end()) {
        std::cerr << "deadline t=" << deadline_tick.runtime.boundary.at_total_minutes
                  << " events=" << deadline_tick.runtime.world_events.size() << "\n";
        return 2;
    }
    InformationAccess hidden_deadline;
    hidden_deadline.task_deadline_observable = false;
    World hidden_deadline_world;
    hidden_deadline_world.time.minute_of_day = 9 * 60 + 20;
    hidden_deadline_world.tasks.front().due_at_total_minutes = 9 * 60 + 25;
    RuntimeScheduler hidden_deadline_scheduler(9 * 60 + 20);
    Observation hidden_deadline_observation = refresh_observation({}, hidden_deadline_world, {}, hidden_deadline);
    ContinuousRuntime hidden_deadline_runtime(hidden_deadline_scheduler, hidden_deadline_world,
                                              hidden_deadline_observation, hidden_deadline);
    if (!hidden_deadline_runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 7;
    CharacterState hidden_deadline_state;
    const RuntimeExecutionResult hidden_deadline_tick =
        hidden_deadline_runtime.execute_next_boundary(hidden_deadline_state, personality);
    if (has_fact(hidden_deadline_observation, "task.deadline_passed")
        || std::find(hidden_deadline_tick.appraisal.tags.begin(), hidden_deadline_tick.appraisal.tags.end(),
                     "deadline_passed") != hidden_deadline_tick.appraisal.tags.end()) return 8;

    // Scheduler-native Phone: hidden W absence remains an attempted intent and
    // becomes a typed rejection without creating an illegal RunningAction.
    World phone_world;
    phone_world.time.minute_of_day = 9 * 60 + 20;
    const Observation phone_prior = refresh_observation({}, phone_world, {});
    if (!observation_knows_action(phone_prior, ActionType::UsePhone)) return 9;
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
    const auto use_phone_candidate = std::find_if(phone_tick.decision.candidates.begin(),
                                                  phone_tick.decision.candidates.end(),
                                                  [](const CandidateAction& c) { return c.action == ActionType::UsePhone; });
    if (use_phone_candidate != phone_tick.decision.candidates.end() && use_phone_candidate->probability > 0.0) return 10;

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
