#pragma once

#include <string>

// Development-only tunables. Fixture schedules, observability, split seeds,
// and evaluator thresholds intentionally do not belong here.
struct ParameterConfig {
    double state_accumulation = 1.0;
    double state_recovery_strength = 1.0;
    double state_decay = 1.0;
    double task_pressure_coupling = 1.0;
    double study_fatigue_penalty = 1.0;
    double task_drive_coefficient = 1.0;
    double distraction_weight = 1.0;
    double commitment_bonus = 1.0;
    double recovery_drive_coefficient = 1.0;

    static ParameterConfig defaults();
    static ParameterConfig from_json_file(const std::string& path);
    std::string canonical_json() const;
    std::string hash() const;
};
