#include "appraisal.h"
#include "observation.h"
#include "state.h"
#include "personality.h"

#include <algorithm>

static bool has_fact(const Observation& o, const char* key) { return find_fact(o, key) != nullptr; }

int main() {
    World world;
    Observation visible = refresh_observation({}, world, {});
    const std::vector<WorldEvent> events = {
        {"message-study-group", "message", "phone", 1},
        {"alarm-rings", "alarm", "room", 2},
        {"weather-rain", "rain", "window", 3},
        {"room-temperature-shift", "temperature", "room", 4},
        {"task-reminder", "reminder", "calendar", 5},
        {"task-deadline", "deadline", "calendar", 6},
        {"evening", "evening", "clock", 7},
    };
    apply_world_events(visible, events, world, {}, "09:00");
    if (!has_fact(visible, "message.unread_count") || !has_fact(visible, "room.alarm")
        || !has_fact(visible, "outside.weather") || !has_fact(visible, "room.temperature_celsius")
        || !has_fact(visible, "task.reminder") || !has_fact(visible, "task.deadline_passed")
        || !has_fact(visible, "world.time_phase")) return 1;
    CharacterState state;
    Personality personality;
    const Appraisal visible_x = appraise(visible, state, personality);
    if (visible_x.tags.empty() && visible_x.semantic_signals.empty()) return 2;

    InformationAccess hidden;
    hidden.phone_presence_observable = false;
    hidden.task_deadline_observable = false;
    hidden.wallet_balance_observable = false;
    Observation hidden_o = refresh_observation({}, world, {}, hidden);
    apply_world_events(hidden_o, events, world, hidden, "09:00");
    if (has_fact(hidden_o, "message.unread_count") && find_fact(hidden_o, "message.unread_count")->source == "world_event:message-study-group") return 3;
    if (has_fact(hidden_o, "task.deadline_passed") || has_fact(hidden_o, "task.reminder")) return 4;
    return 0;
}
