#include "parameter_config.h"

#include <fstream>
#include <iomanip>
#include <regex>
#include <sstream>
#include <stdexcept>

ParameterConfig ParameterConfig::defaults() { return {}; }

ParameterConfig ParameterConfig::from_json_file(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open parameter config: " + path);
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    ParameterConfig config = defaults();
    const char* names[] = {"state_accumulation", "state_recovery_strength", "state_decay",
        "task_pressure_coupling", "study_fatigue_penalty", "task_drive_coefficient",
        "distraction_weight", "commitment_bonus", "recovery_drive_coefficient"};
    double* values[] = {&config.state_accumulation, &config.state_recovery_strength,
        &config.state_decay, &config.task_pressure_coupling, &config.study_fatigue_penalty,
        &config.task_drive_coefficient, &config.distraction_weight, &config.commitment_bonus,
        &config.recovery_drive_coefficient};
    for (int i = 0; i < 9; ++i) {
        std::regex pattern("\\\"" + std::string(names[i]) + "\\\"\\s*:\\s*([-+0-9.eE]+)");
        std::smatch match;
        if (std::regex_search(text, match, pattern)) *values[i] = std::stod(match[1].str());
    }
    return config;
}

std::string ParameterConfig::canonical_json() const {
    std::ostringstream out; out << std::setprecision(17) << "{";
    out << "\"state_accumulation\":" << state_accumulation;
    out << ",\"state_recovery_strength\":" << state_recovery_strength;
    out << ",\"state_decay\":" << state_decay;
    out << ",\"task_pressure_coupling\":" << task_pressure_coupling;
    out << ",\"study_fatigue_penalty\":" << study_fatigue_penalty;
    out << ",\"task_drive_coefficient\":" << task_drive_coefficient;
    out << ",\"distraction_weight\":" << distraction_weight;
    out << ",\"commitment_bonus\":" << commitment_bonus;
    out << ",\"recovery_drive_coefficient\":" << recovery_drive_coefficient << "}";
    return out.str();
}

std::string ParameterConfig::hash() const {
    // Stable, dependency-free provenance token. This is deliberately not a
    // cryptographic claim; the canonical JSON is the auditable source.
    std::hash<std::string> h;
    std::ostringstream out; out << std::hex << h(canonical_json());
    return out.str();
}
