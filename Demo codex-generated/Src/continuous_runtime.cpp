#include "continuous_runtime.h"

ContinuousRuntime::ContinuousRuntime(RuntimeScheduler& scheduler, World& world, Observation& observation)
    : scheduler_(scheduler), world_runtime_(world, scheduler), observation_(observation) {}

bool ContinuousRuntime::schedule_next_world_boundary() {
    return world_runtime_.schedule_next_world_boundary(scheduler_);
}

ContinuousRuntimeStep ContinuousRuntime::advance_next_boundary() {
    const RuntimeBoundary boundary = scheduler_.advance_to_next_boundary();
    const std::vector<WorldEvent> events = world_runtime_.advance_to_boundary(boundary, scheduler_);
    apply_world_events(observation_, events, world_runtime_.time_summary());
    return {boundary, events};
}
