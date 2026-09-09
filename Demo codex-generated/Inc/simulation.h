#pragma once

#include "observation.h"
#include "personality.h"
#include "appraisal.h"
#include "decision.h"
#include "state.h"
#include "world.h"

#include <iosfwd>
#include <string>
#include <vector>

struct ScenarioConfig {
    InformationAccess information_access;
};

struct TaskSnapshot {
    double effort = 0.0;
    double target = 0.0;
    std::string status = "missing";
};

// Canonical per-decision record shared by autonomous runs and future replay.
// Keeping all causal stages together prevents experiments from rebuilding a
// subtly different pipeline.
struct StepRecord {
    std::string decision_time;
    std::string world_before;
    Observation observation_at_decision;
    Appraisal appraisal;
    StateUpdate state_update;
    CharacterState state_at_decision;
    TaskSnapshot task_before;
    DecisionContext decision;
    ActionType chosen_action = ActionType::Idle;
    CharacterActionPlan action_plan;
    WorldOutcome outcome;
    CharacterState state_after_settlement;
    TaskSnapshot task_after;
    std::string sleep_observation_updates;
    std::string world_after;
};

class Simulation {
public:
    void run_all(std::ostream& output) const;
    void run_batch(std::ostream& output, const std::string& output_directory) const;
    void run_paired_phone_intervention(std::ostream& output, const std::string& output_path) const;
    bool run_e0(std::ostream& output) const;
    bool verify(std::ostream& output) const;

private:
    std::string run_profile(const Personality& personality,
                            unsigned int action_seed,
                            unsigned int world_seed,
                            bool include_header,
                            int steps_per_run = 12,
                            bool verbose_trace = true,
                            const ScenarioConfig& scenario = {}) const;
    static std::vector<Personality> generate_personalities(std::size_t count, unsigned int seed);
};
