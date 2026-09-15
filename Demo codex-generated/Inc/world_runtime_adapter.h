#pragma once

#include "runtime_scheduler.h"
#include "world.h"

#include <vector>

// The only scheduler-native bridge allowed to advance W time. It mirrors the
// authoritative scheduler clock and returns W's typed event deltas; it never
// chooses an action, appraises an event, or mutates S.
class WorldRuntimeAdapter {
public:
    WorldRuntimeAdapter(World& world, const RuntimeScheduler& scheduler);
    bool schedule_next_world_boundary(RuntimeScheduler& scheduler) const;
    std::vector<WorldEvent> advance_to_boundary(const RuntimeBoundary& boundary,
                                                const RuntimeScheduler& scheduler);

private:
    World& world_;
};
