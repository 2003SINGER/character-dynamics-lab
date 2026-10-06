#include "npc_continuity_application_v0.h"
#include "continuous_runtime.h"

#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

PolicySelection choose(const DecisionContext& decision, const Observation& observation,
                       const ActorHistory& history = {}, const RunningAction* running = nullptr) {
    UtilityPolicyV0 policy;
    CharacterState state;
    Personality personality;
    std::mt19937 rng(1);
    return policy.select_with_history(decision, observation, state, personality, history, running, rng);
}
}

int main() {
    try {
        NpcContinuityApplicationModelV0 model;
        World world(0);
        world.time.minute_of_day = 525;
        Observation o = refresh_observation({}, world, {});
        CharacterState state;
        Personality personality;
        DecisionContext baseline = model.build_policy(o, state, personality);
        const std::string signature = candidate_signature(baseline);
        require(!signature.empty(), "candidate surface is empty");
        for (const CandidateAction& candidate : baseline.candidates) {
            require(!candidate.rule_soft_eligible, "application surface inherited a Rule soft score");
            require(candidate.reason == "shared O-known hard candidate; no utility score",
                    "candidate reason leaked a scoring rule");
        }
        CharacterState alternate_state = state;
        alternate_state.fatigue = 0.99;
        alternate_state.task_pressure = 0.0;
        Personality alternate_personality;
        alternate_personality.procrastination = 1.0;
        alternate_personality.self_control = 0.0;
        require(candidate_signature(model.build_policy(o, alternate_state, alternate_personality)) == signature,
                "S/P changed the shared application candidate surface");

        // Hidden W-only alarm mutation must not change the shared candidate
        // surface or the utility decision while O remains byte-for-byte same.
        World hidden_world = world;
        hidden_world.current_room().alarm_ringing = true;
        DecisionContext hidden_view = model.build_policy(o, state, personality);
        require(candidate_signature(hidden_view) == signature, "hidden W changed the candidate surface");
        require(choose(hidden_view, o).action == choose(baseline, o).action,
                "hidden W changed the policy choice");
        RunningAction study{ActionType::StudyFocused, "desk", 525, 35, 12, true, RunningActionStatus::Running};
        require(!model.reconsider_running_action(o, state, state, study, personality).requested,
                "hidden alarm opened a reconsideration gate without an O delta");

        // A visible alarm delta is the common reconsideration opportunity. The
        // policy, not the model, decides whether to replace the ongoing study.
        Observation visible = o;
        apply_observable_runtime_event(visible, "room.alarm", "ringing", "world_event:alarm-rings", "09:00");
        DecisionContext alarm_decision = model.build_policy(visible, state, personality);
        require(candidate_signature(alarm_decision) != signature, "visible alarm did not update O-known candidates");
        require(contains_candidate(alarm_decision, ActionType::TurnOffAlarm), "visible alarm action absent");
        require(model.reconsider_running_action(visible, state, state, study, personality).requested,
                "visible alarm delta failed to open shared reconsideration gate");
        const PolicySelection alarm_pick = choose(alarm_decision, visible, {}, &study);
        require(alarm_pick.action == ActionType::TurnOffAlarm,
                "utility did not prefer the known ringing alarm in this fixture");

        // Completing the goal removes study actions through O's existing
        // known-precondition projection, avoiding a forced resume.
        Observation completed = visible;
        apply_observable_runtime_event(completed, "task.coursework.status", "completed",
                                       "self_action_feedback:task-completed", "09:01");
        DecisionContext completed_decision = model.build_policy(completed, state, personality);
        require(!contains_candidate(completed_decision, ActionType::StudyFocused),
                "completed task remained a study candidate");
        require(choose(completed_decision, completed).action != ActionType::StudyFocused,
                "utility forced resume after observed task completion");

        // O-side hard constraints rebuild the exact same admissibility surface
        // for every policy; the application model adds no hidden repair rule.
        Observation constrained = o;
        constrained.action_constraints.push_back({ActionType::StudyFocused, "desk",
            ActionConstraintType::Precondition, false, "observed_rejection", "06:30"});
        DecisionContext constrained_decision = model.build_policy(constrained, state, personality);
        require(!contains_candidate(constrained_decision, ActionType::StudyFocused),
                "unsatisfied O constraint remained a shared hard candidate");

        // Real scheduler-backed same-intent continuation: the model opens the
        // same gate on a visible alarm delta, while a high inertia setting lets
        // Utility retain the study action and preserve its elapsed time.
        World runtime_world(0);
        runtime_world.time.minute_of_day = 525;
        RuntimeScheduler scheduler(525);
        Observation runtime_o = refresh_observation({}, runtime_world, {});
        UtilityPolicyV0 inertial_policy(2.0, 0.08);
        ContinuousRuntime runtime(scheduler, runtime_world, runtime_o, model, {}, 1U, &inertial_policy);
        require(runtime.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted,
                "could not start continuity fixture action");
        bool retained_progress = false;
        for (int i = 0; i < 40 && !retained_progress; ++i) {
            const RuntimeExecutionResult step = runtime.execute_next_boundary(state, personality);
            bool reconsider = false;
            for (DecisionGateReason reason : step.runtime.boundary.decision_gate.reasons)
                if (reason == DecisionGateReason::DynamicsReconsideration) reconsider = true;
            if (!reconsider) continue;
            require(step.selected_action == ActionType::StudyFocused,
                    "inertia fixture did not select the same action");
            require(step.running_action_before && step.running_action_after
                    && step.running_action_after->started_at_total_minutes
                        == step.running_action_before->started_at_total_minutes
                    && step.running_action_after->elapsed_minutes
                        == step.runtime.boundary.action_after_boundary->elapsed_minutes
                    && step.running_action_after->elapsed_minutes > 0,
                    "same-intent reconsideration reset action progress");
            retained_progress = true;
        }
        require(retained_progress, "visible-alarm same-intent gate was not exercised");

        // Interruptions are accounted as fixed action cost in the frozen
        // Runtime: no partial W task effort is settled before completion.
        std::cout << "npc_continuity_application_contract: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "npc_continuity_application_contract: " << error.what() << '\n';
        return 1;
    }
}
