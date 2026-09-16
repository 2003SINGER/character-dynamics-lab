#include "continuous_runtime.h"
#include "decision.h"

#include <filesystem>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace fs = std::filesystem;

static std::string esc(const std::string& value) {
    std::string out = "\"";
    for (char c : value) { if (c == '\"' || c == '\\') out += '\\'; if (c == '\n') out += "\\n"; else out += c; }
    return out + "\"";
}
static std::string action_name(const std::optional<ActionType>& a) { return a ? esc(to_string(*a)) : "null"; }
static std::string status_name(RunningActionStatus s) {
    switch (s) { case RunningActionStatus::Running: return "running"; case RunningActionStatus::Completed: return "completed"; case RunningActionStatus::Interrupted: return "interrupted"; case RunningActionStatus::Rejected: return "rejected"; }
    return "unknown";
}
static std::string gate_reason_name(DecisionGateReason r) { return to_string(r); }
static void write_state(std::ostream& out, const CharacterState& s) {
    out << "{\"fatigue\":" << s.fatigue << ",\"hunger\":" << s.hunger << ",\"boredom\":" << s.boredom
        << ",\"task_pressure\":" << s.task_pressure << ",\"satisfaction\":" << s.satisfaction
        << ",\"anxiety\":" << s.anxiety << ",\"commitment_status\":" << esc(s.commitment.status == CommitmentStatus::Active ? "active" : s.commitment.status == CommitmentStatus::Suspended ? "suspended" : "none")
        << ",\"commitment_task\":" << esc(s.commitment.task_id) << "}";
}
static void write_delta(std::ostream& out, const StateDelta& d) {
    out << "{\"fatigue\":" << d.fatigue << ",\"hunger\":" << d.hunger << ",\"boredom\":" << d.boredom
        << ",\"task_pressure\":" << d.task_pressure << ",\"satisfaction\":" << d.satisfaction << ",\"anxiety\":" << d.anxiety << "}";
}
static void write_outcome(std::ostream& out, const std::optional<WorldOutcome>& x) {
    if (!x) { out << "null"; return; }
    out << "{\"accepted\":" << (x->accepted ? "true" : "false") << ",\"action\":" << esc(to_string(x->action))
        << ",\"task_id\":" << esc(x->task_id) << ",\"task_completed\":" << (x->task_completed ? "true" : "false")
        << ",\"plan_invalidated\":" << (x->plan_invalidated ? "true" : "false") << ",\"provenance\":" << esc(x->provenance) << "}";
}
static void write_action(std::ostream& out, const std::optional<RunningAction>& a) {
    if (!a) { out << "null"; return; }
    out << "{\"action\":" << esc(to_string(a->action)) << ",\"target\":" << esc(a->target_object_id)
        << ",\"elapsed\":" << a->elapsed_minutes << ",\"planned\":" << a->planned_duration_minutes
        << ",\"status\":" << esc(status_name(a->status)) << "}";
}
static void write_facts(std::ostream& out, const Observation& o) {
    out << "["; bool first = true;
    for (const auto& f : o.facts) {
        if (f.key != FactKey::TaskDeadlinePassed && f.key != FactKey::EveningPhase && f.key != "message.unread_count" && f.key != "object.phone") continue;
        if (!first) out << ","; first = false;
        out << "{\"key\":" << esc(f.key) << ",\"value\":" << esc(f.value) << ",\"status\":"
            << esc(f.status == KnowledgeStatus::Known ? "known" : f.status == KnowledgeStatus::Stale ? "stale" : "unknown") << "}";
    }
    out << "]";
}
static void write_decision(std::ostream& out, const DecisionContext& d, bool gate = false, bool evaluated = false,
                           const std::vector<DecisionGateReason>* reasons = nullptr) {
    out << "{\"gate\":" << (gate ? "true" : "false") << ",\"policy_evaluated\":" << (evaluated ? "true" : "false")
        << ",\"reasons\":[";
    if (reasons) for (std::size_t i = 0; i < reasons->size(); ++i) { if (i) out << ","; out << esc(gate_reason_name((*reasons)[i])); }
    out << "],\"dominant_need\":" << esc(d.dominant_need) << ",\"candidates\":[";
    for (std::size_t i = 0; i < d.candidates.size(); ++i) { if (i) out << ","; const auto& c = d.candidates[i]; out << "{\"action\":" << esc(to_string(c.action)) << ",\"target\":" << esc(c.target_object_id) << ",\"probability\":" << c.probability << ",\"eligible\":" << (c.eligible ? "true" : "false") << "}"; }
    out << "]}";
}
static void write_frame(std::ostream& out, const std::string& scenario, int time, int elapsed,
                        const World& w, const Observation& o, const CharacterState& s,
                        const RuntimeExecutionResult* result, const std::string& note = {},
                        const DecisionContext* decision_override = nullptr,
                        const std::string& decision_mode = "sampled",
                        const std::string& attempted_action = {}) {
    const bool boundary_rejected = result && std::any_of(result->runtime.boundary.events.begin(), result->runtime.boundary.events.end(),
        [](const ScheduledRuntimeEvent& e) { return e.rejection.has_value(); });
    const RuntimeRejection* rejection = nullptr;
    if (result) for (const auto& event : result->runtime.boundary.events) if (event.rejection) { rejection = &*event.rejection; break; }
    out << "{\"scenario\":" << esc(scenario) << ",\"timestamp\":" << time << ",\"elapsed_minutes\":" << elapsed
        << ",\"policy_seed\":" << (result ? result->policy_seed : RuntimeConfig::DefaultPolicySeed) << ",\"world\":{\"time\":" << time << ",\"room\":" << esc(w.location)
        << ",\"phone_usable\":" << (w.current_room().objects.front().usable ? "true" : "false")
        << ",\"task_status\":" << esc(w.tasks.front().status == TaskStatus::Completed ? "completed" : "active")
        << ",\"task_effort\":" << w.tasks.front().effort_done << "},\"observation\":{\"facts\":"; write_facts(out, o);
    out << ",\"use_phone_in_AO\":" << (observation_knows_action(o, ActionType::UsePhone) ? "true" : "false")
        << ",\"action_constraints\":[";
    for (std::size_t i = 0; i < o.action_constraints.size(); ++i) { if (i) out << ","; const auto& c = o.action_constraints[i]; out << "{\"action\":" << esc(to_string(c.action)) << ",\"target\":" << esc(c.target_object_id) << ",\"satisfied\":" << (c.satisfied ? "true" : "false") << "}"; }
    out << "]"
        << "},\"state\":"; write_state(out, s); out << ",\"running_action_before\":";
    if (result) write_action(out, result->running_action_before); else out << "null";
    out << ",\"running_action_after\":"; if (result) write_action(out, result->running_action_after); else out << "null";
    out << ",\"decision_mode\":" << esc(decision_mode) << ",\"attempted_action\":" << (attempted_action.empty() ? "null" : esc(attempted_action))
        << ",\"decision\":"; if (result) write_decision(out, result->decision, result->runtime.boundary.decision_gate.open, result->policy_evaluated, &result->runtime.boundary.decision_gate.reasons); else if (decision_override) write_decision(out, *decision_override); else out << "{\"gate\":false,\"policy_evaluated\":false,\"candidates\":[]}";
    out << ",\"world_events\":[";
    if (result) for (std::size_t i=0;i<result->runtime.world_events.size();++i) { if(i) out<<","; out<<"{\"id\":"<<esc(result->runtime.world_events[i].id)<<",\"description\":"<<esc(result->runtime.world_events[i].description)<<"}"; }
    out << "],\"observation_deltas\":[";
    if (result) for (std::size_t i=0;i<result->observation_deltas.size();++i) { if(i) out<<","; out<<"{\"key\":"<<esc(result->observation_deltas[i].key)<<",\"value\":"<<esc(result->observation_deltas[i].value)<<"}"; }
    out << "],\"continuous_state_delta\":"; if(result) write_delta(out,result->continuous_state.applied); else out<<"null";
    out << ",\"impulse_state_delta\":"; if(result) write_delta(out,result->impulse_state.applied); else out<<"null";
    out << ",\"pre_policy_outcome\":"; if(result) write_outcome(out,result->pre_policy_outcome); else out<<"null";
    out << ",\"post_policy_outcome\":"; if(result) write_outcome(out,result->post_policy_outcome); else out<<"null";
    out << ",\"selected_action\":" << (result ? action_name(result->selected_action) : "null")
        << ",\"validation\":{\"accepted\":" << ((!boundary_rejected && (!result || !result->pre_policy_outcome || result->pre_policy_outcome->accepted)) ? "true" : "false")
        << ",\"rejection_reason\":" << (rejection ? esc(rejection->failure_reason == static_cast<int>(RejectionReason::TargetUnusable) ? "target_unusable" : std::to_string(rejection->failure_reason)) : (result && result->pre_policy_outcome && !result->pre_policy_outcome->accepted ? esc(std::to_string(static_cast<int>(result->pre_policy_outcome->failure_reason))) : "null"))
        << ",\"provenance\":" << (rejection ? esc(rejection->provenance) : "null") << "}"
        << ",\"note\":" << esc(note) << "}\n";
}

static bool run_deadline(std::ostream& out) {
    World w; w.time.minute_of_day = 540; w.tasks.front().due_at_total_minutes = 565; w.tasks.front().effort_target = 1.0;
    RuntimeScheduler scheduler(540); Observation o = refresh_observation({}, w, {}); ContinuousRuntime runtime(scheduler, w, o);
    CharacterState state; Personality p;
    if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 60).accepted) return false;
    out << "[\n"; bool first_frame = true;
    for (int i = 0; i < 30; ++i) { auto step = runtime.execute_next_boundary(state, p); if (!first_frame) out << ",\n"; first_frame = false; write_frame(out, "deadline", scheduler.now_total_minutes(), step.runtime.boundary.elapsed_minutes, w, o, state, &step, "runtime boundary"); if (step.pre_policy_outcome && step.pre_policy_outcome->task_completed) break; }
    out << "]\n"; return true;
}
static bool run_phone(std::ostream& out) {
    World w; w.time.minute_of_day = 540; Observation o = refresh_observation({}, w, {}); InformationAccess hidden; hidden.phone_presence_observable = false;
    w.current_room().objects.front().usable = false; o = refresh_observation(o, w, {}, hidden);
    RuntimeScheduler scheduler(540); ContinuousRuntime runtime(scheduler, w, o, hidden); CharacterState state; Personality p;
    out << "[\n"; DecisionContext d = decide(o, state, p); write_frame(out, "phone", 540, 0, w, o, state, nullptr, "W phone unusable; O retains stale usable affordance; policy candidate surface prepared", &d);
    if (runtime.submit_action_intent(ActionType::UsePhone, "phone", 10).accepted) return false;
    auto tick = runtime.execute_next_boundary(state, p); out << ",\n"; write_frame(out, "phone", scheduler.now_total_minutes(), tick.runtime.boundary.elapsed_minutes, w, o, state, &tick, "W validation rejected UsePhone: TargetUnusable; typed feedback updates O", nullptr, "scripted", "use_phone"); out << "]\n"; (void)d; return true;
}
static bool run_commitment(std::ostream& out) {
    World w; w.time.minute_of_day = 540; w.tasks.front().effort_target = 2.0;
    Observation o = refresh_observation({}, w, {}); RuntimeScheduler scheduler(540); ContinuousRuntime runtime(scheduler, w, o);
    CharacterState state; Personality p; int phase = 0;
    runtime.set_test_action_selector([&phase](const DecisionContext&) {
        return phase == 0 ? ActionType::RestAtBed : ActionType::StudyFocused;
    });
    if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 1).accepted) return false;
    out << "[\n";
    bool comma = false;
    auto emit = [&](const RuntimeExecutionResult& r, const char* note) { if (comma) out << ",\n"; comma = true; write_frame(out, "commitment", scheduler.now_total_minutes(), r.runtime.boundary.elapsed_minutes, w, o, state, &r, note, nullptr, "scripted"); };
    auto a = runtime.execute_next_boundary(state, p); emit(a, "Study establishes commitment");
    while (state.commitment.status != CommitmentStatus::Suspended) { auto r = runtime.execute_next_boundary(state, p); emit(r, "Rest suspends commitment"); }
    phase = 1;
    while (state.commitment.status != CommitmentStatus::Active) { auto r = runtime.execute_next_boundary(state, p); emit(r, "Study resumes commitment"); }
    w.tasks.front().effort_target = w.tasks.front().effort_done;
    phase = 2;
    while (state.commitment.status != CommitmentStatus::None) { auto r = runtime.execute_next_boundary(state, p); emit(r, "Visible completion clears commitment"); }
    out << "]\n"; return true;
}

int main(int argc, char** argv) {
    std::string scenario = "deadline", output;
    for (int i = 1; i < argc; ++i) { std::string arg = argv[i]; if (arg == "--scenario" && i + 1 < argc) scenario = argv[++i]; else if (arg == "--output" && i + 1 < argc) output = argv[++i]; }
    if (output.empty()) { std::cerr << "--output is required\n"; return 2; }
    fs::create_directories(fs::path(output).parent_path()); std::ofstream file(output); if (!file) return 3;
    bool ok = scenario == "deadline" ? run_deadline(file) : scenario == "phone" ? run_phone(file) : scenario == "commitment" ? run_commitment(file) : false;
    return ok ? 0 : 1;
}
