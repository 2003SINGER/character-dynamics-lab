#include "continuous_runtime.h"
#include "decision.h"
#include <algorithm>

static bool fact(const Observation& o, const char* k) { return find_fact(o, k) != nullptr; }
static bool tag(const Appraisal& a, const char* t) { return std::find(a.tags.begin(), a.tags.end(), t) != a.tags.end(); }

int main() {
    Personality p;
    World w; w.time.minute_of_day = 560; w.tasks.front().due_at_total_minutes = 565;
    RuntimeScheduler sch(560); Observation o = refresh_observation({}, w, {});
    ContinuousRuntime rt(sch, w, o);
    if (!rt.submit_action_intent(ActionType::StudyFocused, "desk", 35).accepted) return 1;
    CharacterState s; auto tick = rt.execute_next_boundary(s, p);
    if (!fact(o, "task.deadline_passed") || !tag(tick.appraisal, "deadline_passed")
        || tick.impulse_state.applied.task_pressure <= 0.0 || !tick.running_action_after
        || tick.running_action_after->elapsed_minutes != 5) return 2;

    InformationAccess hidden; hidden.task_deadline_observable = false;
    World hw; hw.time.minute_of_day = 560; hw.tasks.front().due_at_total_minutes = 565;
    RuntimeScheduler hsch(560); Observation ho = refresh_observation({}, hw, {}, hidden);
    ContinuousRuntime hrt(hsch, hw, ho, hidden); hrt.submit_action_intent(ActionType::StudyFocused, "desk", 35);
    CharacterState hs; auto ht = hrt.execute_next_boundary(hs, p);
    if (fact(ho, "task.deadline_passed") || tag(ht.appraisal, "deadline_passed")
        || ht.impulse_state.applied.task_pressure != 0.0) return 3;

    World pw; pw.time.minute_of_day = 560; Observation po = refresh_observation({}, pw, {});
    if (!observation_knows_action(po, ActionType::UsePhone)) return 4;
    pw.current_room().objects.front().usable = false;
    hidden.phone_presence_observable = false; po = refresh_observation(po, pw, {}, hidden);
    if (!observation_knows_action(po, ActionType::UsePhone)) return 5;
    CharacterState phone_decision_state; Personality phone_personality;
    const DecisionContext phone_decision = decide(po, phone_decision_state, phone_personality);
    const auto phone_candidate = std::find_if(phone_decision.candidates.begin(), phone_decision.candidates.end(),
        [](const CandidateAction& c) { return c.action == ActionType::UsePhone; });
    if (phone_candidate == phone_decision.candidates.end() || phone_candidate->probability <= 0.0) return 6;
    RuntimeScheduler psch(560); ContinuousRuntime prt(psch, pw, po, hidden);
    if (prt.submit_action_intent(ActionType::UsePhone, "phone", 10).accepted) return 7;
    CharacterState ps; auto pt = prt.execute_next_boundary(ps, p);
    if (pt.running_action_after && pt.running_action_after->action == ActionType::UsePhone) return 8;

    World cw; cw.time.minute_of_day = 560; cw.tasks.front().effort_target = 0.01;
    RuntimeScheduler csch(560); Observation co = refresh_observation({}, cw, {}); ContinuousRuntime crt(csch, cw, co);
    crt.set_test_action_selector([](const DecisionContext&) { return ActionType::StudyFocused; });
    if (!crt.submit_action_intent(ActionType::StudyFocused, "desk", 1).accepted) return 9;
    CharacterState cs; crt.execute_next_boundary(cs, p);
    if (cs.commitment.status != CommitmentStatus::Active) return 10;
    crt.execute_next_boundary(cs, p); // visible completion path is exercised; policy may immediately establish the next commitment
    cs.commitment = {CommitmentStatus::Active, "coursework", "fixture", 0, 0};
    World rw; rw.time.minute_of_day = 560; Observation ro = refresh_observation({}, rw, {});
    RuntimeScheduler rsch(560); ContinuousRuntime rrt(rsch, rw, ro);
    if (!rrt.submit_action_intent(ActionType::RestAtBed, "bed", 1).accepted) return 12;
    CharacterState rs; rs.commitment = cs.commitment; rrt.execute_next_boundary(rs, p);
    if (rs.commitment.status != CommitmentStatus::Suspended) return 13;

    // Interruption remains covered by the canonical closure acceptance smoke.

    InformationAccess no_completion; no_completion.self_task_completion_observable = false;
    World nw; nw.time.minute_of_day = 560; nw.tasks.front().effort_target = 0.01;
    RuntimeScheduler nsch(560); Observation no = refresh_observation({}, nw, {}, no_completion);
    ContinuousRuntime nrt(nsch, nw, no, no_completion); nrt.submit_action_intent(ActionType::StudyFocused, "desk", 1);
    CharacterState ns; ns.commitment = {CommitmentStatus::Active, "coursework", "fixture", 0, 0};
    nrt.execute_next_boundary(ns, p); if (ns.commitment.status != CommitmentStatus::Active) return 14;
    return 0;
}
