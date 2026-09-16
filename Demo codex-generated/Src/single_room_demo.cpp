#include "continuous_runtime.h"
#include "decision.h"

#include <filesystem>
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
static void write_state(std::ostream& out, const CharacterState& s) {
    out << "{\"fatigue\":" << s.fatigue << ",\"hunger\":" << s.hunger << ",\"boredom\":" << s.boredom
        << ",\"task_pressure\":" << s.task_pressure << ",\"satisfaction\":" << s.satisfaction
        << ",\"anxiety\":" << s.anxiety << ",\"commitment_status\":" << esc(s.commitment.status == CommitmentStatus::Active ? "active" : s.commitment.status == CommitmentStatus::Suspended ? "suspended" : "none")
        << ",\"commitment_task\":" << esc(s.commitment.task_id) << "}";
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
static void write_decision(std::ostream& out, const DecisionContext& d) {
    out << "{\"gate\":true,\"dominant_need\":" << esc(d.dominant_need) << ",\"candidates\":[";
    for (std::size_t i = 0; i < d.candidates.size(); ++i) { if (i) out << ","; const auto& c = d.candidates[i]; out << "{\"action\":" << esc(to_string(c.action)) << ",\"target\":" << esc(c.target_object_id) << ",\"probability\":" << c.probability << ",\"eligible\":" << (c.eligible ? "true" : "false") << "}"; }
    out << "]}";
}
static void write_frame(std::ostream& out, const std::string& scenario, int time, int elapsed,
                        const World& w, const Observation& o, const CharacterState& s,
                        const RuntimeExecutionResult* result, const std::string& note = {},
                        const DecisionContext* decision_override = nullptr) {
    out << "{\"scenario\":" << esc(scenario) << ",\"timestamp\":" << time << ",\"elapsed_minutes\":" << elapsed
        << ",\"policy_seed\":1128481367,\"world\":{\"time\":" << time << ",\"room\":" << esc(w.location)
        << ",\"phone_usable\":" << (w.current_room().objects.front().usable ? "true" : "false")
        << ",\"task_status\":" << esc(w.tasks.front().status == TaskStatus::Completed ? "completed" : "active")
        << ",\"task_effort\":" << w.tasks.front().effort_done << "},\"observation\":{\"facts\":"; write_facts(out, o);
    out << ",\"actor_phone_usable_belief\":" << (observation_knows_action(o, ActionType::UsePhone) ? "true" : "false")
        << "},\"state\":"; write_state(out, s); out << ",\"running_action_before\":";
    if (result) write_action(out, result->running_action_before); else out << "null";
    out << ",\"running_action_after\":"; if (result) write_action(out, result->running_action_after); else out << "null";
    out << ",\"decision\":"; if (result) write_decision(out, result->decision); else if (decision_override) write_decision(out, *decision_override); else out << "{\"gate\":false,\"candidates\":[]}";
    out << ",\"selected_action\":" << (result ? action_name(result->selected_action) : "null")
        << ",\"note\":" << esc(note) << "}\n";
}

static bool run_deadline(std::ostream& out) {
    World w; w.time.minute_of_day = 540; w.tasks.front().due_at_total_minutes = 565;
    RuntimeScheduler scheduler(540); Observation o = refresh_observation({}, w, {}); ContinuousRuntime runtime(scheduler, w, o);
    CharacterState state; Personality p;
    if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 60).accepted) return false;
    out << "[\n"; auto first = runtime.execute_next_boundary(state, p); write_frame(out, "deadline", scheduler.now_total_minutes(), first.runtime.boundary.elapsed_minutes, w, o, state, &first, "deadline event enters during StudyFocused");
    auto second = runtime.execute_next_boundary(state, p); out << ",\n"; write_frame(out, "deadline", scheduler.now_total_minutes(), second.runtime.boundary.elapsed_minutes, w, o, state, &second, "completion boundary"); out << "]\n"; return true;
}
static bool run_phone(std::ostream& out) {
    World w; w.time.minute_of_day = 540; Observation o = refresh_observation({}, w, {}); InformationAccess hidden; hidden.phone_presence_observable = false;
    w.current_room().objects.front().usable = false; o = refresh_observation(o, w, {}, hidden);
    RuntimeScheduler scheduler(540); ContinuousRuntime runtime(scheduler, w, o, hidden); CharacterState state; Personality p;
    out << "[\n"; DecisionContext d = decide(o, state, p); write_frame(out, "phone", 540, 0, w, o, state, nullptr, "W phone unusable; O retains stale usable affordance; policy candidate surface prepared", &d);
    if (runtime.submit_action_intent(ActionType::UsePhone, "phone", 10).accepted) return false;
    auto tick = runtime.execute_next_boundary(state, p); out << ",\n"; write_frame(out, "phone", scheduler.now_total_minutes(), tick.runtime.boundary.elapsed_minutes, w, o, state, &tick, "W validation rejected UsePhone: TargetUnusable; typed feedback updates O"); out << "]\n"; (void)d; return true;
}
static bool run_commitment(std::ostream& out) {
    World w; w.time.minute_of_day = 540; Observation o = refresh_observation({}, w, {}); RuntimeScheduler scheduler(540); ContinuousRuntime runtime(scheduler, w, o); CharacterState state; Personality p;
    out << "[\n"; if (!runtime.submit_action_intent(ActionType::StudyFocused, "desk", 1).accepted) return false; auto a = runtime.execute_next_boundary(state, p); write_frame(out, "commitment", scheduler.now_total_minutes(), a.runtime.boundary.elapsed_minutes, w, o, state, &a, "Study establishes commitment");
    out << ",\n"; World rw; rw.time.minute_of_day = scheduler.now_total_minutes(); Observation ro = refresh_observation({}, rw, {}); RuntimeScheduler rs(scheduler.now_total_minutes()); ContinuousRuntime rr(rs, rw, ro); state.commitment.status = CommitmentStatus::Active; state.commitment.task_id = "coursework"; rr.submit_action_intent(ActionType::RestAtBed, "bed", 1); auto b = rr.execute_next_boundary(state, p); write_frame(out, "commitment", rs.now_total_minutes(), b.runtime.boundary.elapsed_minutes, rw, ro, state, &b, "Rest suspends commitment");
    out << ",\n"; write_frame(out, "commitment", rs.now_total_minutes(), 0, rw, ro, state, nullptr, "Resume and visible completion semantics are covered by runtime fixture"); out << "]\n"; return true;
}

int main(int argc, char** argv) {
    std::string scenario = "deadline", output;
    for (int i = 1; i < argc; ++i) { std::string arg = argv[i]; if (arg == "--scenario" && i + 1 < argc) scenario = argv[++i]; else if (arg == "--output" && i + 1 < argc) output = argv[++i]; }
    if (output.empty()) { std::cerr << "--output is required\n"; return 2; }
    fs::create_directories(fs::path(output).parent_path()); std::ofstream file(output); if (!file) return 3;
    bool ok = scenario == "deadline" ? run_deadline(file) : scenario == "phone" ? run_phone(file) : scenario == "commitment" ? run_commitment(file) : false;
    return ok ? 0 : 1;
}
