#include "world_runtime_adapter.h"

#include <stdexcept>

WorldRuntimeAdapter::WorldRuntimeAdapter(World& world, const RuntimeScheduler& scheduler) : world_(world) {
    if (total_minutes(world_.time) != scheduler.now_total_minutes()) {
        throw std::invalid_argument("WorldRuntimeAdapter requires World time to equal the authoritative scheduler clock");
    }
}

bool WorldRuntimeAdapter::schedule_next_world_boundary(RuntimeScheduler& scheduler) const {
    const auto next = world_.next_runtime_event_after(scheduler.now_total_minutes());
    if (!next.has_value()) return false;
    scheduler.schedule({"world_event:" + next->id, next->occurred_at_total_minutes, false, false});
    return true;
}

std::vector<WorldEvent> WorldRuntimeAdapter::advance_to_boundary(const RuntimeBoundary& boundary,
                                                                  const RuntimeScheduler& scheduler) {
    if (boundary.at_total_minutes != scheduler.now_total_minutes()
        || boundary.from_total_minutes != total_minutes(world_.time)) {
        throw std::logic_error("Runtime boundary is not aligned with the authoritative World clock");
    }
    std::vector<WorldEvent> events = world_.advance_runtime_by(boundary.elapsed_minutes);
    if (total_minutes(world_.time) != scheduler.now_total_minutes()) {
        throw std::logic_error("World time drifted from the authoritative scheduler clock");
    }
    return events;
}
