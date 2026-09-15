#include "world.h"

#include <algorithm>
#include <random>
#include <sstream>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace {
constexpr int kMinutesPerDay = 24 * 60;

enum class ScheduledEventKind {
    Alarm,
    StudyMessage,
    Weather,
    Temperature,
    TaskReminder,
    Evening
};

struct ScheduledEvent {
    int minute_of_day = 0;
    ScheduledEventKind kind = ScheduledEventKind::Alarm;
    bool rainy = false;
    double temperature_celsius = 23.0;
};

Room& require_room(Scene& scene, const std::string& room_id) {
    if (Room* room = scene.room_by_id(room_id)) {
        return *room;
    }
    throw std::logic_error("World location does not resolve to a Room in its Scene");
}

const Room& require_room(const Scene& scene, const std::string& room_id) {
    if (const Room* room = scene.room_by_id(room_id)) {
        return *room;
    }
    throw std::logic_error("World location does not resolve to a Room in its Scene");
}

std::vector<ScheduledEvent> schedule_for_day(unsigned int scenario_seed, int day_index) {
    if (scenario_seed == 0U) {
        std::vector<ScheduledEvent> legacy = {
            {9 * 60, ScheduledEventKind::Alarm},
            {9 * 60 + 30, ScheduledEventKind::StudyMessage},
            {11 * 60, ScheduledEventKind::Weather, true},
            {12 * 60, ScheduledEventKind::TaskReminder},
            {16 * 60, ScheduledEventKind::Temperature, false, 17.0},
            {18 * 60, ScheduledEventKind::Evening},
        };
        if (day_index > 0) {
            legacy.erase(std::remove_if(legacy.begin(), legacy.end(), [](const ScheduledEvent& event) {
                return event.kind == ScheduledEventKind::Weather || event.kind == ScheduledEventKind::Temperature;
            }), legacy.end());
        }
        return legacy;
    }

    std::seed_seq sequence{
        scenario_seed,
        static_cast<unsigned int>(day_index),
        0x43445257U,
        0x20260904U,
    };
    std::mt19937 generator(sequence);
    const auto minute_between = [&generator](int first, int last) {
        return std::uniform_int_distribution<int>(first, last)(generator);
    };
    const bool rain = std::bernoulli_distribution(0.55)(generator);
    const bool cold = std::bernoulli_distribution(0.45)(generator);

    std::vector<ScheduledEvent> events = {
        {minute_between(7 * 60, 9 * 60 + 30), ScheduledEventKind::Alarm},
        {minute_between(9 * 60, 18 * 60), ScheduledEventKind::StudyMessage},
        {minute_between(10 * 60, 17 * 60), ScheduledEventKind::Weather, rain},
        {minute_between(12 * 60, 20 * 60), ScheduledEventKind::Temperature, false, cold ? 17.0 : 24.0},
        {minute_between(11 * 60, 19 * 60), ScheduledEventKind::TaskReminder},
        {minute_between(17 * 60 + 30, 20 * 60 + 30), ScheduledEventKind::Evening},
    };
    std::sort(events.begin(), events.end(), [](const ScheduledEvent& left, const ScheduledEvent& right) {
        if (left.minute_of_day != right.minute_of_day) return left.minute_of_day < right.minute_of_day;
        return static_cast<int>(left.kind) < static_cast<int>(right.kind);
    });
    return events;
}

int first_cold_event_between(unsigned int scenario_seed, int before, int after) {
    const int first_day = before / kMinutesPerDay;
    const int last_day = after / kMinutesPerDay;
    for (int day_index = first_day; day_index <= last_day; ++day_index) {
        for (const ScheduledEvent& event : schedule_for_day(scenario_seed, day_index)) {
            const int absolute_minute = day_index * kMinutesPerDay + event.minute_of_day;
            if (event.kind == ScheduledEventKind::Temperature && event.temperature_celsius <= 18.0
                && before < absolute_minute && absolute_minute <= after) {
                return absolute_minute;
            }
        }
    }
    return -1;
}

void append_event(WorldOutcome& outcome, WorldEvent event) {
    outcome.effects.push_back("external event: " + event.description);
    outcome.events.push_back(std::move(event));
}

std::string task_status_name(TaskStatus status) {
    switch (status) {
    case TaskStatus::Active: return "active";
    case TaskStatus::Completed: return "completed";
    }
    return "unknown";
}

double settlement_variation(unsigned int scenario_seed, const WorldTask& task) {
    std::seed_seq sequence{
        scenario_seed,
        static_cast<unsigned int>(task.execution_count),
        0x5441534BU,
        0x20260905U,
    };
    std::mt19937 generator(sequence);
    return std::uniform_real_distribution<double>(0.90, 1.10)(generator);
}

void apply_scheduled_events(World& world, int before, int after, bool was_sleeping, WorldOutcome& outcome) {
    const int first_day = before / kMinutesPerDay;
    const int last_day = after / kMinutesPerDay;
    Room& room = world.current_room();
    for (int day_index = first_day; day_index <= last_day; ++day_index) {
        for (const ScheduledEvent& scheduled : schedule_for_day(world.scenario_seed, day_index)) {
            const int absolute_minute = day_index * kMinutesPerDay + scheduled.minute_of_day;
            if (before >= absolute_minute || after < absolute_minute) continue;

            switch (scheduled.kind) {
            case ScheduledEventKind::Alarm:
                if (!room.alarm_ringing) {
                    room.alarm_ringing = true;
                    append_event(outcome, {"alarm-rings", "the alarm clock rings in the room", "room/alarm-clock", absolute_minute});
                }
                break;
            case ScheduledEventKind::StudyMessage:
                ++world.unread_messages;
                append_event(outcome, {"message-study-group", "a study-group message arrives", "phone notification", absolute_minute});
                break;
            case ScheduledEventKind::Weather:
                world.weather = scheduled.rainy ? "rain" : "clear";
                append_event(outcome, {scheduled.rainy ? "weather-rain" : "weather-clear",
                    scheduled.rainy ? "rain begins outside" : "clouds clear outside",
                    "world/weather", absolute_minute});
                break;
            case ScheduledEventKind::Temperature: {
                room.temperature_celsius = scheduled.temperature_celsius;
                std::ostringstream description;
                description << "room temperature changes to " << static_cast<int>(scheduled.temperature_celsius) << "C";
                WorldEvent event{"room-temperature-shift", description.str(), "room/temperature", absolute_minute};
                append_event(outcome, event);
                if (was_sleeping && scheduled.temperature_celsius <= 18.0) {
                    outcome.sleeping_sensory_events.push_back(event);
                    outcome.effects.push_back("sleeping sensory update: cold is felt despite other O fields being frozen");
                }
                break;
            }
            case ScheduledEventKind::TaskReminder:
                if (world.has_pending_task()) {
                    append_event(outcome, {"task-reminder", "calendar reminder: a task remains due today", "calendar", absolute_minute});
                }
                break;
            case ScheduledEventKind::Evening:
                append_event(outcome, {"evening", "evening begins; the room becomes quieter", "world clock", absolute_minute});
                break;
            }
        }
    }
    for (const WorldTask& task : world.tasks) {
        if (task.status == TaskStatus::Active && task.due_at_total_minutes >= 0
            && before < task.due_at_total_minutes && after >= task.due_at_total_minutes) {
            append_event(outcome, {"task-deadline", "deadline passes for task: " + task.id,
                "world/task-calendar", task.due_at_total_minutes});
        }
    }
}
} // namespace

World::World(unsigned int seed) : scenario_seed(seed) {
    std::seed_seq sequence{seed, 0x5441534BU, 0x20260905U};
    std::mt19937 generator(sequence);
    const double target = seed == 0U ? 8.0 : std::uniform_real_distribution<double>(7.2, 9.2)(generator);
    const double desk_effort = seed == 0U ? 0.45 : std::uniform_real_distribution<double>(0.38, 0.56)(generator);
    const double computer_effort = seed == 0U ? 0.85 : std::uniform_real_distribution<double>(0.68, 1.02)(generator);
    const int due_offset = seed == 0U ? 12 * 60 : std::uniform_int_distribution<int>(10 * 60, 30 * 60)(generator);
    tasks.push_back({"coursework", "coursework", 0.0, target, TaskStatus::Active,
                     {ActionType::StudyFocused, ActionType::StudyHalfhearted, ActionType::StudyAtComputer}, due_offset,
                     desk_effort, computer_effort});
}

const WorldTask* World::task_by_id(const std::string& task_id) const {
    const auto found = std::find_if(tasks.begin(), tasks.end(), [&task_id](const WorldTask& task) {
        return task.id == task_id;
    });
    return found == tasks.end() ? nullptr : &*found;
}

WorldTask* World::task_by_id(const std::string& task_id) {
    const auto found = std::find_if(tasks.begin(), tasks.end(), [&task_id](const WorldTask& task) {
        return task.id == task_id;
    });
    return found == tasks.end() ? nullptr : &*found;
}

const WorldTask* World::active_task_for(ActionType action) const {
    const auto found = std::find_if(tasks.begin(), tasks.end(), [action](const WorldTask& task) {
        return task.status == TaskStatus::Active
            && std::find(task.supporting_actions.begin(), task.supporting_actions.end(), action)
                != task.supporting_actions.end();
    });
    return found == tasks.end() ? nullptr : &*found;
}

WorldTask* World::active_task_for(ActionType action) {
    const auto found = std::find_if(tasks.begin(), tasks.end(), [action](const WorldTask& task) {
        return task.status == TaskStatus::Active
            && std::find(task.supporting_actions.begin(), task.supporting_actions.end(), action)
                != task.supporting_actions.end();
    });
    return found == tasks.end() ? nullptr : &*found;
}

bool World::has_pending_task() const {
    return std::any_of(tasks.begin(), tasks.end(), [](const WorldTask& task) {
        return task.status == TaskStatus::Active;
    });
}

Room& World::current_room() {
    return require_room(scene, location);
}

const Room& World::current_room() const {
    return require_room(scene, location);
}

bool World::can_execute(ActionType action) const {
    if (action == ActionType::Idle) {
        return true;
    }
    const Room& room = current_room();
    if (object_for(action) == nullptr) {
        return false;
    }
    switch (action) {
    case ActionType::ShopOnPhone:
        return wallet >= 30;
    case ActionType::StudyFocused:
    case ActionType::StudyHalfhearted:
    case ActionType::StudyAtComputer:
        return room.light_on && active_task_for(action) != nullptr;
    case ActionType::TurnLightOn:
        return !room.light_on;
    case ActionType::TurnLightOff:
        return room.light_on;
    case ActionType::TurnOffAlarm:
        return room.alarm_ringing;
    case ActionType::OpenCurtain:
        return !room.curtain_open;
    case ActionType::CloseCurtain:
        return room.curtain_open;
    default:
        return true;
    }
}

const Object* World::object_for(ActionType action) const {
    return current_room().object_for(action);
}

CharacterActionPlan World::expand_action(ActionType action) const {
    CharacterActionPlan plan;
    plan.action = action;
    if (const Object* object = object_for(action)) {
        plan.object_id = object->id;
    }
    const auto add = [&plan](std::string id, std::string description, WorldPrimitivePayload payload) {
        plan.world_primitives.push_back({std::move(id), std::move(description), std::move(payload)});
    };

    add("record-action", action == ActionType::Idle
            ? "character remains in the room without a focused activity"
            : "character begins " + to_string(action),
        SetCurrentActivity{action});
    switch (action) {
    case ActionType::UsePhone:
        add("count-phone-use", "phone browsing completed", IncrementWorldCounter{WorldCounter::PhoneUses});
        break;
    case ActionType::ShopOnPhone:
        add("spend-wallet", "online order placed; wallet decreased by 30", AdjustWorldValue{WorldValue::Wallet, -30});
        add("count-order", "online order recorded", IncrementWorldCounter{WorldCounter::OnlineOrders});
        break;
    case ActionType::UseComputer:
        add("count-computer-use", "computer browsing completed", IncrementWorldCounter{WorldCounter::ComputerUses});
        break;
    case ActionType::StudyAtComputer:
    case ActionType::StudyFocused:
    case ActionType::StudyHalfhearted:
        add("count-study-session", "study session completed", IncrementWorldCounter{WorldCounter::StudySessions});
        break;
    case ActionType::RestAtBed:
        add("count-rest-session", "rest session completed in bed", IncrementWorldCounter{WorldCounter::RestSessions});
        break;
    case ActionType::SleepAtBed:
        add("count-sleep-session", "sleep session begins; ordinary O refresh is frozen during the interval",
            IncrementWorldCounter{WorldCounter::RestSessions});
        break;
    case ActionType::GoToBathroom:
        add("count-bathroom-visit", "brief excursion through door: bathroom visit completed",
            IncrementWorldCounter{WorldCounter::BathroomVisits});
        break;
    case ActionType::GetMeal:
        add("count-meal", "brief excursion through door: meal collected and eaten",
            IncrementWorldCounter{WorldCounter::MealsCollected});
        break;
    case ActionType::TurnLightOn:
        add("light-on", "room light turned on", SetRoomFlag{RoomFlag::LightOn, true});
        break;
    case ActionType::TurnLightOff:
        add("light-off", "room light turned off", SetRoomFlag{RoomFlag::LightOn, false});
        break;
    case ActionType::TurnOffAlarm:
        add("alarm-off", "alarm clock silenced", SetRoomFlag{RoomFlag::AlarmRinging, false});
        break;
    case ActionType::OpenCurtain:
        add("curtain-open", "curtains opened; outside weather becomes visible from the room",
            SetRoomFlag{RoomFlag::CurtainOpen, true});
        break;
    case ActionType::CloseCurtain:
        add("curtain-close", "curtains closed; outside weather is no longer directly visible",
            SetRoomFlag{RoomFlag::CurtainOpen, false});
        break;
    case ActionType::Idle:
        break;
    case ActionType::Count:
        throw std::logic_error("ActionType::Count cannot be expanded");
    }
    add("advance-time", "advance simulated time", AdvanceSimulationTime{action_definition(action).default_duration_minutes});
    return plan;
}

std::vector<ActionType> World::available_actions() const {
    std::vector<ActionType> actions = {ActionType::Idle};
    const Room& room = current_room();
    for (const Object& object : room.objects) {
        for (ActionType action : object.affordances) {
            if (object.usable && can_execute(action)) {
                if (std::find(actions.begin(), actions.end(), action) == actions.end()) {
                    actions.push_back(action);
                }
            }
        }
    }
    return actions;
}

WorldOutcome World::settle(ActionType action) {
    const Object* object = object_for(action);
    return settle(action, object != nullptr ? object->id : std::string{});
}

WorldOutcome World::settle(ActionType action, const std::string& target_object_id) {
    return settle_impl(action, target_object_id, true);
}

WorldOutcome World::validate_runtime_start(ActionType action, const std::string& target_object_id) const {
    WorldOutcome outcome;
    outcome.action = action;
    outcome.target_object_id = target_object_id;
    outcome.provenance = "World::validate_runtime_start(" + to_string(action) + ")";
    const CharacterActionPlan plan = expand_action(action);
    if (!target_object_id.empty()) {
        const Object* target = nullptr;
        for (const Object& candidate : current_room().objects) {
            if (candidate.id == target_object_id) { target = &candidate; break; }
        }
        if (target == nullptr) { outcome.failure_reason = RejectionReason::TargetAbsent; return outcome; }
        if (!provides_action(*target, plan.action)) { outcome.failure_reason = RejectionReason::PreconditionFailed; return outcome; }
        if (!target->usable) { outcome.failure_reason = RejectionReason::TargetUnusable; return outcome; }
    }
    if (!can_execute(plan.action)) {
        outcome.failure_reason = (plan.action == ActionType::ShopOnPhone && wallet < 30)
            ? RejectionReason::ResourceInsufficient : RejectionReason::PreconditionFailed;
        return outcome;
    }
    outcome.accepted = true;
    return outcome;
}

WorldOutcome World::settle_runtime_completion(ActionType action, const std::string& target_object_id,
                                               int action_elapsed_minutes) {
    WorldOutcome outcome = settle_impl(action, target_object_id, false, action_elapsed_minutes);
    outcome.action_elapsed_minutes = action_elapsed_minutes;
    return outcome;
}

WorldOutcome World::settle_impl(ActionType action, const std::string& target_object_id, bool advance_clock,
                                int runtime_action_elapsed_minutes) {
    // Re-expand inside W immediately before settlement. This deliberately
    // makes CharacterActionPlan a trace/provenance object rather than a
    // capability that another module can forge to mutate W.
    CharacterActionPlan plan = expand_action(action);
    WorldOutcome outcome;
    outcome.action = plan.action;
    outcome.target_object_id = target_object_id;
    outcome.provenance = "World::settle(" + to_string(plan.action) + ")";

    if (!target_object_id.empty()) {
        const Object* target = nullptr;
        for (const Object& candidate : current_room().objects) {
            if (candidate.id == target_object_id) { target = &candidate; break; }
        }
        if (target == nullptr) {
            outcome.failure_reason = RejectionReason::TargetAbsent;
            outcome.effects.push_back("rejected: target object absent");
            return outcome;
        }
        if (!provides_action(*target, plan.action)) {
            outcome.failure_reason = RejectionReason::PreconditionFailed;
            outcome.effects.push_back("rejected: target does not afford action");
            return outcome;
        }
        if (!target->usable) {
            outcome.failure_reason = RejectionReason::TargetUnusable;
            outcome.effects.push_back("rejected: target object unusable");
            return outcome;
        }
    }
    if (!can_execute(plan.action)) {
        outcome.failure_reason = (plan.action == ActionType::ShopOnPhone && wallet < 30)
            ? RejectionReason::ResourceInsufficient : RejectionReason::PreconditionFailed;
        outcome.effects.push_back("rejected: action precondition failed");
        return outcome;
    }

    outcome.accepted = true;
    if (!plan.object_id.empty()) {
        outcome.object_id = plan.object_id;
        if (outcome.target_object_id.empty()) outcome.target_object_id = plan.object_id;
        outcome.provenance += " via object:" + plan.object_id;
    }

    outcome.planned_primitives = plan.world_primitives;
    outcome.settled_primitives = outcome.planned_primitives;
    const int before = total_minutes(time);
    auto time_primitive = std::find_if(outcome.settled_primitives.begin(), outcome.settled_primitives.end(),
        [](const WorldPrimitive& primitive) {
            return std::holds_alternative<AdvanceSimulationTime>(primitive.payload);
        });
    if (time_primitive == outcome.settled_primitives.end()) {
        throw std::logic_error("CharacterActionPlan has no AdvanceSimulationTime primitive");
    }
    int after = before;
    if (advance_clock) {
        auto& advance = std::get<AdvanceSimulationTime>(time_primitive->payload);
        after = before + advance.minutes;
        if (plan.action == ActionType::SleepAtBed) {
        const int cold_wake_minute = first_cold_event_between(scenario_seed, before, after);
        if (cold_wake_minute >= 0) {
            after = cold_wake_minute;
            advance.minutes = after - before;
            outcome.woke_early = true;
        }
        }
    } else {
        outcome.settled_primitives.erase(time_primitive);
    }

    Room& room = current_room();
    for (const WorldPrimitive& primitive : outcome.settled_primitives) {
        std::visit([&](const auto& payload) {
            using Payload = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<Payload, SetCurrentActivity>) {
                last_action = payload.action;
                current_activity = to_string(payload.action);
                outcome.activity = current_activity;
            } else if constexpr (std::is_same_v<Payload, IncrementWorldCounter>) {
                switch (payload.counter) {
                case WorldCounter::PhoneUses: phone_uses += payload.amount; break;
                case WorldCounter::ComputerUses: computer_uses += payload.amount; break;
                case WorldCounter::StudySessions: study_sessions += payload.amount; break;
                case WorldCounter::RestSessions: rest_sessions += payload.amount; break;
                case WorldCounter::BathroomVisits: bathroom_visits += payload.amount; break;
                case WorldCounter::MealsCollected: meals_collected += payload.amount; break;
                case WorldCounter::OnlineOrders: online_orders += payload.amount; break;
                }
            } else if constexpr (std::is_same_v<Payload, AdjustWorldValue>) {
                switch (payload.value) {
                case WorldValue::Wallet: wallet += payload.amount; break;
                case WorldValue::TaskProgress:
                    throw std::logic_error("Task effort must be settled through WorldTask, not an integer primitive");
                }
            } else if constexpr (std::is_same_v<Payload, SetRoomFlag>) {
                switch (payload.flag) {
                case RoomFlag::LightOn: room.light_on = payload.value; break;
                case RoomFlag::AlarmRinging: room.alarm_ringing = payload.value; break;
                case RoomFlag::CurtainOpen: room.curtain_open = payload.value; break;
                }
            } else if constexpr (std::is_same_v<Payload, AdvanceSimulationTime>) {
                outcome.elapsed_minutes = payload.minutes;
                advance_minutes(time, payload.minutes);
            }
        }, primitive.payload);
        outcome.effects.push_back(primitive.description);
    }

    if (advance_clock && plan.action == ActionType::SleepAtBed) {
        outcome.observation_frozen_during_action = true;
        outcome.effects.push_back(outcome.woke_early
            ? "character wakes early because a cold scenario event is sensed; the next decision point can refresh O from the room"
            : "character wakes; the next decision point can refresh O from the room");
    }

    if (advance_clock) apply_scheduled_events(*this, before, after, plan.action == ActionType::SleepAtBed, outcome);

    if (plan.action == ActionType::StudyFocused
        || plan.action == ActionType::StudyHalfhearted
        || plan.action == ActionType::StudyAtComputer) {
        WorldTask* task = active_task_for(plan.action);
        if (task == nullptr) {
            throw std::logic_error("Accepted study action has no active supporting task");
        }
        outcome.task_id = task->id;
        outcome.task_effort_before = task->effort_done;
        outcome.task_settlement_variation = settlement_variation(scenario_seed, *task);
        const double base_effort = plan.action == ActionType::StudyAtComputer
            ? task->computer_base_effort
            : (plan.action == ActionType::StudyFocused
                ? task->desk_base_effort
                : task->desk_base_effort * 0.60);
        const int action_elapsed = advance_clock
            ? outcome.elapsed_minutes
            : (runtime_action_elapsed_minutes >= 0 ? runtime_action_elapsed_minutes
                                                   : action_definition(plan.action).default_duration_minutes);
        const double duration_factor = static_cast<double>(action_elapsed)
            / static_cast<double>(action_definition(plan.action).default_duration_minutes);
        outcome.task_session_interrupted = action_elapsed
            < action_definition(plan.action).default_duration_minutes;
        const double interruption_factor = outcome.task_session_interrupted ? 0.55 : 1.0;
        outcome.task_effort_gained = base_effort * duration_factor
            * interruption_factor * outcome.task_settlement_variation;
        task->effort_done = std::min(task->effort_target, task->effort_done + outcome.task_effort_gained);
        ++task->execution_count;
        outcome.task_effort_after = task->effort_done;
        std::ostringstream effect;
        effect << "task effort settled: " << task->id << ' ' << outcome.task_effort_before
               << " + " << outcome.task_effort_gained << " -> " << outcome.task_effort_after
               << '/' << task->effort_target << " (variation=" << outcome.task_settlement_variation << ')';
        outcome.effects.push_back(effect.str());
        if (task->effort_done >= task->effort_target) {
            task->status = TaskStatus::Completed;
            task->completed_at_total_minutes = total_minutes(time);
            outcome.task_completed = true;
            append_event(outcome, {"task-completed", "coursework has been completed", "world/task", total_minutes(time)});
        }
    }
    outcome.action_elapsed_minutes = advance_clock ? outcome.elapsed_minutes
                                                   : (runtime_action_elapsed_minutes >= 0
                                                          ? runtime_action_elapsed_minutes
                                                          : action_definition(plan.action).default_duration_minutes);
    outcome.time_advanced_by_settlement = advance_clock ? outcome.elapsed_minutes : 0;
    return outcome;
}

WorldOutcome World::execute(ActionType action) {
    return settle(action);
}

std::vector<WorldEvent> World::advance_runtime_by(int elapsed_minutes) {
    if (elapsed_minutes < 0) throw std::invalid_argument("Runtime World advance cannot be negative");
    const int before = total_minutes(time);
    const int after = before + elapsed_minutes;
    WorldOutcome transition;
    advance_minutes(time, elapsed_minutes);
    // Reuse the exact deterministic event source used by Reference v0, but
    // emit events at their own runtime boundary rather than action completion.
    apply_scheduled_events(*this, before, after, false, transition);
    return transition.events;
}

std::optional<WorldEvent> World::next_runtime_event_after(int total_minutes) const {
    const int first_day = total_minutes / kMinutesPerDay;
    std::optional<WorldEvent> earliest;
    for (int day_index = first_day; day_index <= first_day + 2; ++day_index) {
        for (const ScheduledEvent& scheduled : schedule_for_day(scenario_seed, day_index)) {
            const int absolute_minute = day_index * kMinutesPerDay + scheduled.minute_of_day;
            if (absolute_minute <= total_minutes) continue;
            WorldEvent candidate;
            switch (scheduled.kind) {
            case ScheduledEventKind::Alarm: candidate = {"alarm-rings", "the alarm clock rings in the room", "room/alarm-clock", absolute_minute}; break;
            case ScheduledEventKind::StudyMessage: candidate = {"message-study-group", "a study-group message arrives", "phone notification", absolute_minute}; break;
            case ScheduledEventKind::Weather: candidate = {scheduled.rainy ? "weather-rain" : "weather-clear", "weather changes", "world/weather", absolute_minute}; break;
            case ScheduledEventKind::Temperature: candidate = {"room-temperature-shift", "room temperature changes", "world/temperature", absolute_minute}; break;
            case ScheduledEventKind::TaskReminder: candidate = {"task-reminder", "calendar reminder: a task remains due today", "calendar", absolute_minute}; break;
            case ScheduledEventKind::Evening: candidate = {"evening", "evening begins", "world clock", absolute_minute}; break;
            }
            if (!earliest || candidate.occurred_at_total_minutes < earliest->occurred_at_total_minutes) earliest = candidate;
        }
        for (const WorldTask& task : tasks) {
            if (task.status == TaskStatus::Active && task.due_at_total_minutes > total_minutes
                && task.due_at_total_minutes / kMinutesPerDay == day_index) {
                WorldEvent candidate{"task-deadline", "deadline passes for task: " + task.id,
                                     "world/task-calendar", task.due_at_total_minutes};
                if (!earliest || candidate.occurred_at_total_minutes < earliest->occurred_at_total_minutes) earliest = candidate;
            }
        }
    }
    return earliest;
}

std::string World::time_summary() const {
    return ::time_summary(time);
}

std::string World::summary() const {
    const Room& room = current_room();
    std::ostringstream output;
    output << "W{time=" << time_summary()
           << ", scenario_seed=" << scenario_seed
           << ", scene=" << scene.id
           << ", location=" << location
           << ", light=" << (room.light_on ? "on" : "off")
           << ", alarm=" << (room.alarm_ringing ? "ringing" : "silent")
           << ", curtain=" << (room.curtain_open ? "open" : "closed")
           << ", weather=" << weather
           << ", temperature=" << room.temperature_celsius << "C"
           << ", tasks=[";
    for (std::size_t index = 0; index < tasks.size(); ++index) {
        const WorldTask& task = tasks[index];
        output << task.id << ':' << task.effort_done << '/' << task.effort_target
               << '{' << task_status_name(task.status) << '}';
        if (index + 1 < tasks.size()) output << ", ";
    }
    output << ']'
           << ", wallet=" << wallet
           << ", unread_messages=" << unread_messages
           << ", objects=[";
    for (std::size_t index = 0; index < room.objects.size(); ++index) {
        const Object& object = room.objects[index];
        output << object.id << ':' << (object.usable ? "ready" : "unavailable");
        if (index + 1 < room.objects.size()) {
            output << ", ";
        }
    }
    output << "], activity=" << current_activity
           << ", counts=[phone:" << phone_uses
           << ", computer:" << computer_uses
           << ", study:" << study_sessions
           << ", rest:" << rest_sessions
           << ", bathroom:" << bathroom_visits
           << ", meal:" << meals_collected
           << ", orders:" << online_orders << "]}";
    return output.str();
}
