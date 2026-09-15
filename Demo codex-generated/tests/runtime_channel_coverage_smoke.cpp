#include "appraisal.h"
#include "observation.h"
#include "state.h"
#include "personality.h"
#include <algorithm>

static bool has(const Observation& o, const char* k) { return find_fact(o, k) != nullptr; }
static bool has_tag(const Appraisal& a, const char* t) { return std::find(a.tags.begin(), a.tags.end(), t) != a.tags.end(); }
static bool event_case(const WorldEvent& e, const char* fact_key, const char* tag_name, const InformationAccess& access = {}) {
    World w; w.unread_messages = 1; w.current_room().temperature_celsius = 15.0; Observation o = refresh_observation({}, w, {}, access);
    apply_world_events(o, {e}, w, access, "09:00");
    if (!has(o, fact_key)) return false;
    CharacterState s; s.boredom = 0.8; s.commitment = {CommitmentStatus::Active, "coursework", "coverage", 0, 0};
    Personality p; return has_tag(appraise(o, s, p), tag_name);
}

int main() {
    if (!event_case({"message-study-group", "message", "phone", 1}, "message.unread_count", "social_task_reminder")) return 1;
    if (!event_case({"alarm-rings", "alarm", "room", 1}, "room.alarm", "alarm_interrupts_room")) return 2;
    if (!event_case({"weather-rain", "rain", "window", 1}, "outside.weather", "rain_observed_through_window")) return 3;
    if (!event_case({"room-temperature-shift", "temperature", "room", 1}, "room.temperature_celsius", "cold_interrupts_sleep")) return 4;
    if (!event_case({"task-reminder", "reminder", "calendar", 1}, "task.reminder", "deadline_salience")) return 5;
    World dw; dw.tasks.front().due_at_total_minutes = 1;
    Observation d = refresh_observation({}, dw, {}); apply_observable_runtime_event(d, FactKey::TaskDeadlinePassed, "1", "world_event:task-deadline", "09:00");
    CharacterState ds; ds.commitment = {CommitmentStatus::Active, "coursework", "coverage", 0, 0}; Personality dp;
    if (!has(d, "task.deadline_passed") || !has_tag(appraise(d, ds, dp), "deadline_passed")) return 6;
    { World ew; Observation eo = refresh_observation({}, ew, {}); apply_world_events(eo, {{"evening", "evening", "clock", 1}}, ew, {}, "09:00"); if (!has(eo, "world.time_phase")) return 7; }

    WorldOutcome completion; completion.accepted = true; completion.action = ActionType::StudyFocused;
    completion.task_id = "coursework"; completion.task_completed = true; completion.provenance = "fixture";
    Observation co; apply_self_action_feedback(co, completion, "09:00", true, false);
    CharacterState cs; Personality cp; const Appraisal ca = appraise(co, cs, cp);
    if (ca.semantic_signals.empty()) return 8;
    WorldOutcome rejection; rejection.accepted = false; rejection.action = ActionType::UsePhone;
    rejection.failure_reason = RejectionReason::TargetAbsent; rejection.provenance = "fixture";
    Observation ro; apply_self_action_feedback(ro, rejection, "09:00", true, false);
    CharacterState rs; Personality rp; if (!has_tag(appraise(ro, rs, rp), "action_rejected")) return 9;
    WorldOutcome interruption; interruption.accepted = false; interruption.action = ActionType::StudyFocused;
    interruption.plan_invalidated = true; interruption.task_session_interrupted = true; interruption.provenance = "fixture";
    Observation io; apply_self_action_feedback(io, interruption, "09:00", true, false);
    CharacterState is; Personality ip; if (!has_tag(appraise(io, is, ip), "action_rejected")) return 10;

    InformationAccess hidden; hidden.task_deadline_observable = false;
    World hw; hw.tasks.front().due_at_total_minutes = 1; Observation ho = refresh_observation({}, hw, {}, hidden);
    apply_world_events(ho, {{"deadline", "deadline", "calendar", 1}}, hw, hidden, "09:00");
    CharacterState hs; Personality hp; if (has(ho, "task.deadline_passed") || has_tag(appraise(ho, hs, hp), "deadline_passed")) return 11;
    return 0;
}
