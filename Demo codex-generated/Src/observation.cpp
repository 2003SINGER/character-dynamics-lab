#include "observation.h"

#include <algorithm>
#include <iomanip>
#include <sstream>
#include <string_view>
#include <cstdlib>

namespace {
const char* to_string(KnowledgeStatus status) {
    switch (status) {
    case KnowledgeStatus::Known: return "known";
    case KnowledgeStatus::Stale: return "stale";
    case KnowledgeStatus::Unknown: return "unknown";
    }
    return "unknown";
}

const char* to_string(ActionConstraintType constraint) {
    switch (constraint) {
    case ActionConstraintType::TargetAbsent: return "target_absent";
    case ActionConstraintType::TargetUnusable: return "target_unusable";
    case ActionConstraintType::ResourceRequirement: return "resource_requirement";
    case ActionConstraintType::Precondition: return "precondition";
    }
    return "unknown";
}

ActionConstraintType constraint_type(RejectionReason reason) {
    switch (reason) {
    case RejectionReason::TargetAbsent: return ActionConstraintType::TargetAbsent;
    case RejectionReason::TargetUnusable: return ActionConstraintType::TargetUnusable;
    case RejectionReason::ResourceInsufficient: return ActionConstraintType::ResourceRequirement;
    case RejectionReason::PreconditionFailed: return ActionConstraintType::Precondition;
    case RejectionReason::None: break;
    }
    return ActionConstraintType::Precondition;
}

bool is_blocked(const Observation& observation, ActionType action, const std::string& target_object_id) {
    return std::any_of(observation.action_constraints.begin(), observation.action_constraints.end(),
        [&](const ActionConstraintBelief& belief) {
            return !belief.satisfied && belief.action == action
                && (belief.target_object_id.empty() || belief.target_object_id == target_object_id);
        });
}

void resolve_constraints(Observation& observation,
                         ActionConstraintType type,
                         const std::string& target_object_id) {
    for (ActionConstraintBelief& belief : observation.action_constraints) {
        if (belief.constraint == type && !belief.satisfied
            && (target_object_id.empty() || belief.target_object_id == target_object_id)) {
            belief.satisfied = true;
        }
    }
}

void record_constraint(Observation& observation,
                       const WorldOutcome& outcome,
                       const std::string& observed_at) {
    if (outcome.accepted || outcome.failure_reason == RejectionReason::None) return;
    const ActionConstraintType type = constraint_type(outcome.failure_reason);
    const auto existing = std::find_if(observation.action_constraints.begin(), observation.action_constraints.end(),
        [&](const ActionConstraintBelief& belief) {
            return belief.action == outcome.action && belief.target_object_id == outcome.target_object_id
                && belief.constraint == type && !belief.satisfied;
        });
    if (existing == observation.action_constraints.end()) {
        const std::string source = outcome.failure_reason == RejectionReason::ResourceInsufficient
            ? "failed_resource_check" : "failed_direct_interaction";
        observation.action_constraints.push_back({outcome.action, outcome.target_object_id, type, false,
                                                  source, observed_at});
    }
}

void write_fact(Observation& observation,
                std::string key,
                std::string value,
                std::string source,
                std::string observed_at) {
    const auto existing = std::find_if(observation.facts.begin(), observation.facts.end(),
        [&key](const ObservationFact& fact) { return fact.key == key; });
    const ObservationFact next{std::move(key), std::move(value), KnowledgeStatus::Known,
                               std::move(source), std::move(observed_at)};
    if (existing == observation.facts.end()) {
        observation.facts.push_back(next);
        observation.updates_this_refresh.push_back(next);
    } else {
        // A different observation channel can refresh provenance without
        // creating a new semantic Delta-O for X to interpret again.
        const bool changed = existing->value != next.value || existing->status != next.status;
        *existing = next;
        if (changed) {
            observation.updates_this_refresh.push_back(next);
        }
    }
}

void mark_stale(Observation& observation, const std::string& key) {
    const auto existing = std::find_if(observation.facts.begin(), observation.facts.end(),
        [&key](const ObservationFact& fact) { return fact.key == key; });
    if (existing != observation.facts.end() && existing->status == KnowledgeStatus::Known) {
        existing->status = KnowledgeStatus::Stale;
        observation.updates_this_refresh.push_back(*existing);
    }
}

bool contains_id(const std::vector<std::string>& ids, const std::string& id) {
    return std::find(ids.begin(), ids.end(), id) != ids.end();
}

std::string format_temperature(double temperature) {
    std::ostringstream output;
    output << std::fixed << std::setprecision(1) << temperature << "C";
    return output.str();
}

std::string fact_value(const Observation& observation, const std::string& key) {
    if (const ObservationFact* fact = find_fact(observation, key)) {
        return fact->value;
    }
    return "unknown";
}

std::string object_id_from_fact_key(const std::string& key) {
    constexpr std::string_view prefix = "object.";
    if (key.rfind(prefix, 0) != 0) return {};
    const std::string remainder = key.substr(prefix.size());
    constexpr std::string_view usability_suffix = ".usable";
    if (remainder.size() > usability_suffix.size()
        && remainder.compare(remainder.size() - usability_suffix.size(), usability_suffix.size(), usability_suffix) == 0) {
        return remainder.substr(0, remainder.size() - usability_suffix.size());
    }
    return remainder.find('.') == std::string::npos ? remainder : std::string{};
}

bool known_fact_allows(const Observation& observation,
                       const std::string& key,
                       const std::string& allowed_value,
                       const std::string& forbidden_value = {}) {
    const ObservationFact* fact = find_fact(observation, key);
    if (fact == nullptr || fact->status != KnowledgeStatus::Known) return true;
    if (!forbidden_value.empty() && fact->value == forbidden_value) return false;
    return fact->value == allowed_value;
}

bool subjective_preconditions_allow(ActionType action,
                                    const Observation& observation,
                                    const Object& object) {
    const std::string object_usable_key = "object." + object.id + ".usable";
    if (!known_fact_allows(observation, object_usable_key, "true", "false")) return false;
    switch (action) {
    case ActionType::TurnLightOn:
        return known_fact_allows(observation, "room.light", "off", "on");
    case ActionType::TurnLightOff:
        return known_fact_allows(observation, "room.light", "on", "off");
    case ActionType::OpenCurtain:
        return known_fact_allows(observation, "room.curtain", "closed", "open");
    case ActionType::CloseCurtain:
        return known_fact_allows(observation, "room.curtain", "open", "closed");
    case ActionType::TurnOffAlarm:
        return known_fact_allows(observation, "room.alarm", "ringing", "silent");
    case ActionType::StudyAtComputer:
    case ActionType::StudyFocused:
    case ActionType::StudyHalfhearted:
        return known_fact_allows(observation, "room.light", "on", "off")
            && known_fact_allows(observation, "task.coursework.status", "active", "completed");
    case ActionType::ShopOnPhone: {
        int wallet_balance = 0;
        if (!known_int(observation, FactKey::WalletBalance, wallet_balance)) return true;
        return wallet_balance >= 30;
    }
    default:
        return true;
    }
}
} // namespace

void rebuild_known_actions_from_observation(Observation& observation) {
    observation.known_actions.clear();
    observation.action_target_bindings.clear();
    observation.known_actions.push_back(ActionType::Idle);
    for (const KnownObjectAffordance& known_object : observation.known_object_affordances) {
        Object believed_object;
        believed_object.id = known_object.id;
        believed_object.affordances = known_object.affordances;
        for (ActionType action : known_object.affordances) {
            if (subjective_preconditions_allow(action, observation, believed_object)
                && !is_blocked(observation, action, known_object.id)
                && !observation_knows_action(observation, action)) {
                observation.known_actions.push_back(action);
                observation.action_target_bindings.push_back({action, known_object.id});
            }
        }
    }
}

const ObservationFact* find_fact(const Observation& observation, const std::string& key) {
    const auto fact = std::find_if(observation.facts.begin(), observation.facts.end(),
        [&key](const ObservationFact& item) { return item.key == key; });
    return fact == observation.facts.end() ? nullptr : &*fact;
}

bool has_known_fact(const Observation& observation, const std::string& key, const std::string& value) {
    const ObservationFact* fact = find_fact(observation, key);
    return fact != nullptr && fact->status == KnowledgeStatus::Known && fact->value == value;
}

bool known_bool(const Observation& observation, const std::string& key, bool& value) {
    const ObservationFact* fact = find_fact(observation, key);
    if (fact == nullptr || fact->status != KnowledgeStatus::Known) return false;
    if (fact->value == "true") { value = true; return true; }
    if (fact->value == "false") { value = false; return true; }
    return false;
}

bool known_int(const Observation& observation, const std::string& key, int& value) {
    const ObservationFact* fact = find_fact(observation, key);
    if (fact == nullptr || fact->status != KnowledgeStatus::Known || fact->value.empty()) return false;
    char* end = nullptr;
    const long parsed = std::strtol(fact->value.c_str(), &end, 10);
    if (end == fact->value.c_str() || *end != '\0') return false;
    value = static_cast<int>(parsed);
    return true;
}

bool known_double(const Observation& observation, const std::string& key, double& value) {
    const ObservationFact* fact = find_fact(observation, key);
    if (fact == nullptr || fact->status != KnowledgeStatus::Known || fact->value.empty()) return false;
    char* end = nullptr;
    const double parsed = std::strtod(fact->value.c_str(), &end);
    if (end == fact->value.c_str() || *end != '\0') return false;
    value = parsed;
    return true;
}

Observation refresh_observation(Observation observation,
                                const World& world,
                                const WorldOutcome& previous_outcome,
                                const InformationAccess& access) {
    observation.updates_this_refresh.clear();
    observation.visible_object_labels.clear();
    observation.known_object_ids.clear();
    observation.known_actions.clear();
    observation.action_target_bindings.clear();
    const std::string now = world.time_summary();

    // Current room rule: every present room object is directly observable.
    // Whether it is actually usable remains a W fact until an observation or
    // rejected attempt supplies feedback; a broken object must not vanish.
    // Other scenes can later omit objects here while still retaining facts from
    // message, memory, sound, or stale prior observation.
    const Room& room = world.current_room();
    for (const Object& object : room.objects) {
        if (object.id == "phone" && !access.phone_presence_observable) {
            // The phone can remain in W while its presence is withheld from O.
            // Existing phone facts are intentionally retained until a permitted
            // discovery channel refreshes them.
            continue;
        }
        observation.known_object_ids.push_back(object.id);
        observation.visible_object_labels.push_back(object.label);
        const auto known_affordance = std::find_if(observation.known_object_affordances.begin(),
            observation.known_object_affordances.end(),
            [&object](const KnownObjectAffordance& item) { return item.id == object.id; });
        if (known_affordance == observation.known_object_affordances.end()) {
            observation.known_object_affordances.push_back({object.id, object.affordances});
        } else {
            known_affordance->affordances = object.affordances;
        }
        write_fact(observation, "object." + object.id, "present", "direct_room_visual", now);
        if (access.object_usability_observable) {
            write_fact(observation, "object." + object.id + ".usable",
                       object.usable ? "true" : "false", "direct_object_inspection", now);
            if (object.usable) {
                resolve_constraints(observation, ActionConstraintType::TargetUnusable, object.id);
            }
        }
        resolve_constraints(observation, ActionConstraintType::TargetAbsent, object.id);
    }
    // Objects absent from this refresh remain remembered, but no longer count
    // as current visual knowledge. This is the minimal stale/unknown hook for
    // later movement, occlusion, and dynamically removed objects.
    std::vector<std::string> absent_object_ids;
    for (const ObservationFact& fact : observation.facts) {
        const std::string object_id = object_id_from_fact_key(fact.key);
        if (!object_id.empty()) {
            if (object_id == "phone" && !access.phone_presence_observable) continue;
            if (!contains_id(observation.known_object_ids, object_id) && fact.value == "present") {
                mark_stale(observation, fact.key);
                absent_object_ids.push_back(object_id);
            }
        }
    }
    if (access.phone_presence_observable) {
        std::sort(absent_object_ids.begin(), absent_object_ids.end());
        absent_object_ids.erase(std::unique(absent_object_ids.begin(), absent_object_ids.end()), absent_object_ids.end());
        observation.known_object_affordances.erase(
            std::remove_if(observation.known_object_affordances.begin(), observation.known_object_affordances.end(),
                [&absent_object_ids](const KnownObjectAffordance& item) {
                    return contains_id(absent_object_ids, item.id);
                }), observation.known_object_affordances.end());
    }
    for (const KnownObjectAffordance& item : observation.known_object_affordances) {
        if (!contains_id(observation.known_object_ids, item.id)) {
            observation.known_object_ids.push_back(item.id);
        }
    }
    apply_self_action_feedback(observation, previous_outcome, now,
                               access.self_task_completion_observable);
    write_fact(observation, "room.light", room.light_on ? "on" : "off", "direct_room_visual", now);
    write_fact(observation, "room.curtain", room.curtain_open ? "open" : "closed", "direct_room_visual", now);
    if (access.wallet_balance_observable) {
        write_fact(observation, "wallet.balance", std::to_string(world.wallet),
                   "direct_wallet_observation", now);
        // The actor has observed a resource update, not W's value at the
        // moment of failure.  Reconsider the old failed requirement through
        // the ordinary O-side wallet precondition on this refresh.
        resolve_constraints(observation, ActionConstraintType::ResourceRequirement, {});
    }
    const bool alarm_rang = std::any_of(previous_outcome.events.begin(), previous_outcome.events.end(),
        [](const WorldEvent& event) { return event.id == "alarm-rings"; });
    write_fact(observation, "room.alarm", room.alarm_ringing ? "ringing" : "silent",
               alarm_rang ? "direct_room_auditory" : "direct_room_visual", now);
    for (const WorldTask& task : world.tasks) {
        // An initial task brief is scenario input. Later W state is not copied
        // into O: progress and completion must arrive through typed feedback.
        if (task.status == TaskStatus::Active
            && find_fact(observation, "task." + task.id + ".status") == nullptr) {
            write_fact(observation, "task." + task.id + ".status", "active", "initial_task_brief", now);
        }
        // Workload is initial task-brief information.  Later progress is
        // received through the actor's own typed settlement feedback below,
        // not copied from hidden W on an ordinary refresh.
        if (find_fact(observation, "task." + task.id + ".effort_target") == nullptr) {
            write_fact(observation, "task." + task.id + ".effort_target",
                       std::to_string(task.effort_target), "initial_task_brief", now);
        }
        if (find_fact(observation, "task." + task.id + ".effort") == nullptr) {
            write_fact(observation, "task." + task.id + ".effort",
                       std::to_string(task.effort_done), "initial_task_brief", now);
        }
        if (access.task_deadline_observable) {
            const std::string key = "task." + task.id + ".deadline_at_total_minutes";
            const std::string source = find_fact(observation, key) == nullptr ? "initial_calendar" : "internal_calendar";
            write_fact(observation, key, std::to_string(task.due_at_total_minutes), source, now);
        }
    }
    write_fact(observation, "message.unread_count", std::to_string(world.unread_messages), "phone_notification_state", now);
    write_fact(observation, "clock.time", now, "internal_clock", now);
    write_fact(observation, "clock.total_minutes", std::to_string(total_minutes(world.time)), "internal_clock", now);
    write_fact(observation, "room.temperature_celsius", std::to_string(room.temperature_celsius), "direct_room_thermal", now);
    if (room.curtain_open) {
        write_fact(observation, "outside.weather", world.weather, "direct_window_visual", now);
    } else {
        mark_stale(observation, "outside.weather");
    }

    // The alarm is a room-local event. Its auditory source wins over the
    // ordinary visual refresh when it rang during the preceding action.
    for (const WorldEvent& event : previous_outcome.events) {
        if (event.id == "task-reminder" && access.task_deadline_observable) {
            write_fact(observation, FactKey::TaskReminder, "today", "calendar_notification", now);
        }
    }

    // A^O is generated from known objects and their believed stable
    // affordances. It must not call W::available_actions(): W-only guards
    // (wallet, hidden task completion, object failure, room flags) are tested
    // only at settlement and can then become O through feedback.
    rebuild_known_actions_from_observation(observation);
    return observation;
}

void apply_self_action_feedback(Observation& observation,
                                const WorldOutcome& outcome,
                                const std::string& observed_at,
                                bool completion_is_observable,
                                bool defer_appraisal) {
    if (outcome.provenance.empty()) {
        observation.last_self_action = {};
        return;
    }
    observation.last_self_action = {true, outcome.action, outcome.accepted, outcome.task_id,
        outcome.task_completed && completion_is_observable,
        outcome.plan_invalidated ? "plan invalidated during runtime"
                                 : (outcome.accepted ? "accepted by W" : "rejected by W"),
        "self_action_feedback", observed_at};
    if (outcome.plan_invalidated) return;
    record_constraint(observation, outcome, observed_at);
    if (outcome.accepted) {
        // A successful room-control action is directly observable to its
        // actor. Project the typed settled primitive, not a hidden W read;
        // otherwise a switched-off light can remain "on" in O indefinitely
        // and cause repeated invalid study intents.
        for (const WorldPrimitive& primitive:outcome.settled_primitives) {
            const SetRoomFlag* change=std::get_if<SetRoomFlag>(&primitive.payload);
            if (!change) continue;
            switch (change->flag) {
            case RoomFlag::LightOn:
                write_fact(observation,"room.light",change->value?"on":"off",
                           "self_action_room_feedback",observed_at);
                break;
            case RoomFlag::AlarmRinging:
                write_fact(observation,"room.alarm",change->value?"ringing":"silent",
                           "self_action_room_feedback",observed_at);
                break;
            case RoomFlag::CurtainOpen:
                write_fact(observation,"room.curtain",change->value?"open":"closed",
                           "self_action_room_feedback",observed_at);
                break;
            }
        }
    }
    if (!outcome.accepted && outcome.failure_reason == RejectionReason::TargetAbsent
        && !outcome.target_object_id.empty()) {
        const std::string object_key = "object." + outcome.target_object_id;
        const std::size_t pending_start = observation.updates_this_refresh.size();
        std::vector<ActionType> revoked_actions;
        for (const KnownObjectAffordance& item : observation.known_object_affordances) {
            if (item.id == outcome.target_object_id) revoked_actions = item.affordances;
        }
        write_fact(observation, object_key, "absent", "failed_direct_interaction", observed_at);
        observation.known_object_ids.erase(
            std::remove(observation.known_object_ids.begin(), observation.known_object_ids.end(), outcome.target_object_id),
            observation.known_object_ids.end());
        observation.known_object_affordances.erase(
            std::remove_if(observation.known_object_affordances.begin(), observation.known_object_affordances.end(),
                [&outcome](const KnownObjectAffordance& item) { return item.id == outcome.target_object_id; }),
            observation.known_object_affordances.end());
        observation.known_actions.erase(
            std::remove_if(observation.known_actions.begin(), observation.known_actions.end(),
                [&revoked_actions](ActionType action) {
                    return std::find(revoked_actions.begin(), revoked_actions.end(), action)
                        != revoked_actions.end();
                }), observation.known_actions.end());
        if (defer_appraisal) {
            observation.pending_appraisal_updates.insert(observation.pending_appraisal_updates.end(),
                observation.updates_this_refresh.begin() + static_cast<std::ptrdiff_t>(pending_start),
                observation.updates_this_refresh.end());
        }
    }
    if (!outcome.accepted || outcome.task_id.empty()) return;

    const std::string status_key = "task." + outcome.task_id + ".status";
    const std::size_t pending_start = observation.updates_this_refresh.size();
    if (outcome.task_completed && completion_is_observable) {
        write_fact(observation, status_key, "completed", "self_action_completion_feedback", observed_at);
    } else {
        write_fact(observation, status_key, "active", "self_action_progress_feedback", observed_at);
    }
    write_fact(observation, "task." + outcome.task_id + ".effort",
               std::to_string(outcome.task_effort_after), "self_action_progress_feedback", observed_at);
    // Preserve only semantic feedback created by this call for the next X
    // evaluation. refresh_observation clears the per-refresh list, so without
    // this handoff a completion delta can be lost before appraisal consumes it.
    if (defer_appraisal) {
        observation.pending_appraisal_updates.insert(observation.pending_appraisal_updates.end(),
            observation.updates_this_refresh.begin() + static_cast<std::ptrdiff_t>(pending_start),
            observation.updates_this_refresh.end());
    }
}

void apply_observable_runtime_event(Observation& observation,
                                    std::string key,
                                    std::string value,
                                    std::string source,
                                    const std::string& observed_at) {
    write_fact(observation, std::move(key), std::move(value), std::move(source), observed_at);
}

void apply_world_events(Observation& observation, const std::vector<WorldEvent>& events,
                        const World& world, const InformationAccess& access,
                        const std::string& observed_at) {
    for (const WorldEvent& event : events) {
        if (event.id == "task-assigned") {
            const WorldTask* task=world.task_by_id("coursework");
            if (task==nullptr) continue;
            apply_observable_runtime_event(observation,"task.coursework.episode",
                std::to_string(world.life_tape_episode),"world_event:task-assigned",observed_at);
            apply_observable_runtime_event(observation,"task.coursework.status","active",
                "world_event:task-assigned",observed_at);
            apply_observable_runtime_event(observation,"task.coursework.effort","0.000000",
                "world_event:task-assigned",observed_at);
            apply_observable_runtime_event(observation,"task.coursework.effort_target",
                std::to_string(task->effort_target),"world_event:task-assigned",observed_at);
            if (access.task_deadline_observable) {
                apply_observable_runtime_event(observation,FactKey::TaskDeadlineAt,
                    std::to_string(task->due_at_total_minutes),"world_event:task-assigned",observed_at);
                apply_observable_runtime_event(observation,FactKey::TaskDeadlinePassed,"0",
                    "world_event:task-assigned",observed_at);
                apply_observable_runtime_event(observation,FactKey::TaskReminder,"0",
                    "world_event:task-assigned",observed_at);
            }
        } else if (event.id == "message-study-group") {
            if (!access.phone_presence_observable) continue;
            apply_observable_runtime_event(observation, FactKey::MessageUnreadCount, std::to_string(world.unread_messages),
                                           "world_event:message-study-group", observed_at);
        } else if (event.id == "task-reminder") {
            if (!access.task_deadline_observable) continue;
            apply_observable_runtime_event(observation, FactKey::TaskReminder, "1",
                                           "world_event:task-reminder", observed_at);
        } else if (event.id == "task-deadline") {
            if (!access.task_deadline_observable) continue;
            apply_observable_runtime_event(observation, FactKey::TaskDeadlinePassed, "1",
                                           "world_event:task-deadline", observed_at);
        } else if (event.id == "alarm-rings") {
            apply_observable_runtime_event(observation, "room.alarm", "ringing",
                                           "world_event:alarm-rings", observed_at);
        } else if (event.id == "room-temperature-shift") {
            apply_observable_runtime_event(observation, "room.temperature_celsius",
                                           std::to_string(world.current_room().temperature_celsius),
                                           "world_event:room-temperature-shift", observed_at);
        } else if (event.id == "evening") {
            apply_observable_runtime_event(observation, FactKey::EveningPhase, "evening",
                                           "world_event:evening", observed_at);
        } else if (event.id == "weather-rain" || event.id == "weather-clear") {
            if (!world.current_room().curtain_open) continue;
            apply_observable_runtime_event(observation, FactKey::OutsideWeather,
                                           event.id == "weather-rain" ? "rain" : "clear",
                                           "world_event:" + event.id, observed_at);
        }
    }
}

bool observation_knows_action(const Observation& observation, ActionType action) {
    return std::find(observation.known_actions.begin(), observation.known_actions.end(), action)
        != observation.known_actions.end();
}

Observation apply_sleep_sensory_update(Observation observation,
                                       const WorldOutcome& outcome,
                                       const World& world) {
    observation.updates_this_refresh.clear();
    for (const WorldEvent& event : outcome.sleeping_sensory_events) {
        if (event.id == "room-cold") {
            write_fact(observation, "room.temperature_celsius", std::to_string(world.current_room().temperature_celsius),
                       "direct_room_thermal_while_asleep", world.time_summary());
        }
    }
    observation.pending_appraisal_updates.insert(observation.pending_appraisal_updates.end(),
        observation.updates_this_refresh.begin(), observation.updates_this_refresh.end());
    return observation;
}

void clear_pending_appraisal_updates(Observation& observation) {
    observation.pending_appraisal_updates.clear();
}

void consume_appraisal_inputs(Observation& observation) {
    observation.updates_this_refresh.clear();
    observation.pending_appraisal_updates.clear();
    observation.last_self_action = {};
}

std::string observation_updates_summary(const Observation& observation) {
    std::ostringstream output;
    output << "updates=[";
    for (std::size_t index = 0; index < observation.updates_this_refresh.size(); ++index) {
        const ObservationFact& fact = observation.updates_this_refresh[index];
        output << fact.key << '=' << fact.value << "{" << to_string(fact.status)
               << ", " << fact.source << '}';
        if (index + 1 < observation.updates_this_refresh.size()) output << ", ";
    }
    output << ']';
    return output.str();
}

std::string observation_summary(const Observation& observation) {
    std::ostringstream output;
    output << "O{visible_objects=[";
    for (std::size_t index = 0; index < observation.visible_object_labels.size(); ++index) {
        output << observation.visible_object_labels[index];
        if (index + 1 < observation.visible_object_labels.size()) output << ", ";
    }
    output << "], A^O=[";
    for (std::size_t index = 0; index < observation.known_actions.size(); ++index) {
        output << to_string(observation.known_actions[index]);
        if (index + 1 < observation.known_actions.size()) output << ", ";
    }
    output << "], " << observation_updates_summary(observation)
           << ", action_constraints=[";
    for (std::size_t index = 0; index < observation.action_constraints.size(); ++index) {
        const ActionConstraintBelief& belief = observation.action_constraints[index];
        output << to_string(belief.action) << '@' << belief.target_object_id << ':'
               << to_string(belief.constraint) << '{' << (belief.satisfied ? "resolved" : "unsatisfied")
               << ", " << belief.source << '}';
        if (index + 1 < observation.action_constraints.size()) output << ", ";
    }
    output << ']'
           << ", temperature_celsius=" << fact_value(observation, "room.temperature_celsius")
           << ", time=" << fact_value(observation, "clock.time")
           << ", light=" << fact_value(observation, "room.light")
           << ", coursework_effort=" << fact_value(observation, "task.coursework.effort")
           << ", coursework_status=" << fact_value(observation, "task.coursework.status")
           << ", unread_messages=" << fact_value(observation, "message.unread_count")
           << ", self_action=";
    if (observation.last_self_action.has_action) {
        output << to_string(observation.last_self_action.action)
               << "{" << (observation.last_self_action.accepted ? "accepted" : "rejected")
               << ", " << observation.last_self_action.source << "}";
    } else {
        output << "none";
    }
    output << '}';
    return output.str();
}
