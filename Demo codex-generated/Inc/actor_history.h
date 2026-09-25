#pragma once

#include "action.h"
#include "observation.h"
#include "runtime_scheduler.h"

#include <deque>
#include <string>

// Actor-visible temporal facts. This ledger is separate from O and S and is
// populated only from the actor's own action feedback and observed O deltas.
struct ActorEpisode {
    ActionType action = ActionType::Idle;
    std::string target;
    int start_total_minutes = 0;
    int end_total_minutes = 0;
    int planned_minutes = 0;
    int actual_minutes = 0;
    bool accepted = true;
    bool interrupted = false;
    std::string outcome;
    std::string task_id;
};

struct ActorObservedEvent {
    int total_minutes = 0;
    std::string key;
    std::string value;
};

struct ActorHistory {
    std::deque<ActorEpisode> episodes;
    std::deque<ActorObservedEvent> events;
};
