#include "state.h"

#include <algorithm>
#include <iomanip>
#include <sstream>

namespace {
double clamp_unit(double value) {
    return std::clamp(value, 0.0, 1.0);
}

void append_value(std::ostringstream& output, const char* label, double value) {
    output << label << '=' << std::fixed << std::setprecision(2) << value;
}
} // namespace

StateDelta update_state(CharacterState& state,
                        const Appraisal& appraisal,
                        const Personality& personality) {
    StateDelta delta;
    delta.boredom = appraisal.boredom_delta;
    delta.fatigue = appraisal.fatigue_delta;
    delta.task_pressure = appraisal.task_pressure_delta;
    delta.satisfaction = appraisal.satisfaction_delta;

    // P changes the response curve, not the identity of the action itself.
    if (appraisal.task_pressure_delta > 0.0) {
        delta.task_pressure += 0.05 * personality.procrastination;
    }
    if (appraisal.task_pressure_delta < 0.0) {
        delta.task_pressure *= 0.75 + 0.25 * personality.self_control;
    }
    if (appraisal.fatigue_delta < 0.0) {
        delta.fatigue *= 0.75 + 0.25 * personality.rest_preference;
    }

    state.boredom = clamp_unit(state.boredom + delta.boredom);
    state.fatigue = clamp_unit(state.fatigue + delta.fatigue);
    state.task_pressure = clamp_unit(state.task_pressure + delta.task_pressure);
    state.satisfaction = clamp_unit(state.satisfaction + delta.satisfaction);
    return delta;
}

std::string state_summary(const CharacterState& state) {
    std::ostringstream output;
    output << "S{";
    append_value(output, "boredom", state.boredom);
    output << ", ";
    append_value(output, "fatigue", state.fatigue);
    output << ", ";
    append_value(output, "task_pressure", state.task_pressure);
    output << ", ";
    append_value(output, "satisfaction", state.satisfaction);
    output << '}';
    return output.str();
}

std::string state_delta_summary(const StateDelta& delta) {
    std::ostringstream output;
    output << "StateDelta{";
    append_value(output, "boredom", delta.boredom);
    output << ", ";
    append_value(output, "fatigue", delta.fatigue);
    output << ", ";
    append_value(output, "task_pressure", delta.task_pressure);
    output << ", ";
    append_value(output, "satisfaction", delta.satisfaction);
    output << '}';
    return output.str();
}
