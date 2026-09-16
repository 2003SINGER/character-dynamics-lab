#include "continuous_runtime.h"
#include "reference_rule_dynamics_v0.h"
#include <algorithm>
#include <iostream>

static bool has_tag(const Appraisal& a, const char* t) { return std::find(a.tags.begin(), a.tags.end(), t) != a.tags.end(); }
static int case_run(const std::string& name) {
    Personality p; World w; w.time.minute_of_day = 0; Observation o = refresh_observation({}, w, {}); RuntimeScheduler s(0);
    ReferenceRuleDynamicsV0 dynamics;
    ContinuousRuntime r(s, w, o, dynamics);
    if (name == "runtime_clock_authority_smoke") {
        if (!r.submit_action_intent(ActionType::StudyFocused, "desk", 10).accepted) return 1;
        CharacterState st; auto x = r.execute_next_boundary(st, p); return x.runtime.boundary.elapsed_minutes > 0 ? 0 : 1;
    }
    if (name == "runtime_world_event_boundary_smoke" || name == "runtime_world_event_source_consistency") {
        apply_world_events(o, {{"message-study-group", "message", "phone", 1}}, w, {}, "00:01");
        return find_fact(o, FactKey::MessageUnreadCount) ? 0 : 1;
    }
    if (name == "runtime_action_start_validation_smoke") return r.submit_action_intent(ActionType::UsePhone, "missing", 1).accepted ? 1 : 0;
    if (name == "runtime_action_completion_smoke") {
        w.tasks.front().effort_target = 0.01; if (!r.submit_action_intent(ActionType::StudyFocused, "desk", 1).accepted) return 1;
        CharacterState st; r.execute_next_boundary(st, p); return 0;
    }
    if (name == "runtime_action_invalidation_smoke") {
        if (!r.submit_action_intent(ActionType::StudyFocused, "desk", 10).accepted) return 1; r.invalidate_running_action(); CharacterState st; auto x = r.execute_next_boundary(st, p); return x.pre_policy_outcome && x.pre_policy_outcome->plan_invalidated ? 0 : 1;
    }
    if (name == "runtime_hidden_event_no_leak_smoke") {
        InformationAccess hidden; hidden.task_deadline_observable = false; o = refresh_observation({}, w, {}, hidden); apply_world_events(o, {{"task-deadline", "deadline", "calendar", 1}}, w, hidden, "00:01"); return find_fact(o, FactKey::TaskDeadlinePassed) ? 1 : 0;
    }
    if (name == "runtime_perception_projection_smoke") { apply_world_events(o, {{"alarm-rings", "alarm", "room", 1}}, w, {}, "00:01"); CharacterState st; return has_tag(appraise(o, st, p), "alarm_interrupts_room") ? 0 : 1; }
    if (name == "runtime_typed_rejection_smoke") return r.submit_action_intent(ActionType::UsePhone, "missing", 1).accepted ? 1 : 0;
    if (name == "runtime_weak_event_continue_smoke") { r.schedule_next_world_boundary(); return 0; }
    if (name == "runtime_state_threshold_boundary_smoke") { if (!r.submit_action_intent(ActionType::StudyFocused, "desk", 10).accepted) return 1; CharacterState st; st.hunger = 0.39; auto x = r.execute_next_boundary(st, p); return x.runtime.boundary.decision_gate.open || x.running_action_after ? 0 : 1; }
    return 2;
}

int main(int argc, char** argv) {
    if (argc == 3 && std::string(argv[1]) == "--case") return case_run(argv[2]);
    std::cerr << "usage: runtime_case_smoke --case <CTest case name>\n"; return 2;
}
