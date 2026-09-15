#pragma once

#include "action.h"
#include "scene.h"
#include "simulation_time.h"
#include "world_primitive.h"

#include <string>
#include <vector>

struct WorldEvent {
    std::string id;
    std::string description;
    std::string source;
    int occurred_at_total_minutes = -1;
};

enum class RejectionReason { None, TargetAbsent, TargetUnusable, PreconditionFailed, ResourceInsufficient };

enum class TaskStatus {
    Active,
    Completed
};

struct WorldTask {
    std::string id;
    std::string label;
    double effort_done = 0.0;
    double effort_target = 8.0;
    TaskStatus status = TaskStatus::Active;
    std::vector<ActionType> supporting_actions;
    int due_at_total_minutes = -1;
    double desk_base_effort = 0.45;
    double computer_base_effort = 0.85;
    int completed_at_total_minutes = -1;
    int execution_count = 0;
};

struct WorldOutcome {
    bool accepted = false;
    ActionType action = ActionType::Idle;
    std::string activity;
    std::string object_id;
    std::string target_object_id;
    RejectionReason failure_reason = RejectionReason::None;
    int elapsed_minutes = 0;
    int action_elapsed_minutes = 0;
    int time_advanced_by_settlement = 0;
    bool observation_frozen_during_action = false;
    bool woke_early = false;
    std::string task_id;
    double task_effort_before = 0.0;
    double task_effort_gained = 0.0;
    double task_effort_after = 0.0;
    double task_settlement_variation = 1.0;
    bool task_session_interrupted = false;
    bool task_completed = false;
    std::vector<WorldPrimitive> settled_primitives;
    std::vector<WorldPrimitive> planned_primitives;
    std::vector<WorldEvent> events;
    std::vector<WorldEvent> sleeping_sensory_events;
    std::vector<std::string> effects;
    std::string provenance;
};

struct World {
    explicit World(unsigned int seed = 0);

    SimTime time;
    Scene scene = make_default_scene();
    unsigned int scenario_seed = 0;
    std::vector<WorldTask> tasks;
    std::string weather = "clear";
    int wallet = 120;
    int unread_messages = 0;
    std::string location = "room";
    std::string current_activity = "idle";
    int phone_uses = 0;
    int computer_uses = 0;
    int study_sessions = 0;
    int rest_sessions = 0;
    int bathroom_visits = 0;
    int meals_collected = 0;
    int online_orders = 0;
    ActionType last_action = ActionType::Idle;

    const WorldTask* task_by_id(const std::string& task_id) const;
    WorldTask* task_by_id(const std::string& task_id);
    const WorldTask* active_task_for(ActionType action) const;
    WorldTask* active_task_for(ActionType action);
    bool has_pending_task() const;
    bool can_execute(ActionType action) const;
    std::vector<ActionType> available_actions() const;
    Room& current_room();
    const Room& current_room() const;
    const Object* object_for(ActionType action) const;
    CharacterActionPlan expand_action(ActionType action) const;
    // W owns primitive generation. A plan is useful for trace/provenance,
    // but callers cannot submit arbitrary primitives for execution.
    WorldOutcome settle(ActionType action);
    WorldOutcome settle(ActionType action, const std::string& target_object_id);
    WorldOutcome validate_runtime_start(ActionType action, const std::string& target_object_id) const;
    WorldOutcome settle_runtime_completion(ActionType action, const std::string& target_object_id,
                                           int action_elapsed_minutes);
    // Scheduler-native API: time is advanced only by the runtime clock. This
    // leaves Reference v0's whole-action `settle` semantics unchanged.
    std::vector<WorldEvent> advance_runtime_by(int elapsed_minutes);
    WorldOutcome execute(ActionType action);
    std::string time_summary() const;
    std::string summary() const;

private:
    WorldOutcome settle_impl(ActionType action, const std::string& target_object_id, bool advance_clock,
                             int runtime_action_elapsed_minutes = -1);
};
