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
                        const Personality& personality,
                        int elapsed_minutes) {
    StateDelta delta;
    delta.elapsed_minutes = elapsed_minutes;
    const double time_scale = static_cast<double>(elapsed_minutes) / 30.0;

    // The fields intentionally have different simple time terms. These are
    // placeholders for later per-field dynamics, not psychological claims.
    delta.boredom = appraisal.boredom_delta + 0.01 * time_scale;
    delta.fatigue = appraisal.fatigue_delta + 0.012 * time_scale;
    delta.task_pressure = appraisal.task_pressure_delta;
    delta.satisfaction = appraisal.satisfaction_delta - 0.01 * time_scale;
    delta.hunger = appraisal.hunger_delta + 0.025 * time_scale;
    delta.bathroom_urge = appraisal.bathroom_urge_delta + 0.020 * time_scale;
    delta.screen_strain = appraisal.screen_strain_delta - 0.030 * time_scale;
    delta.purchase_urge = appraisal.purchase_urge_delta - 0.018 * time_scale;
    delta.anxiety = appraisal.anxiety_delta
                  + std::max(0.0, state.task_pressure - 0.55) * 0.08 * time_scale * personality.task_anxiety_sensitivity;

    // P modulates response curves; it does not force a particular action.
    if (appraisal.task_pressure_delta > 0.0) {
        delta.task_pressure += 0.06 * personality.procrastination;
        delta.anxiety += 0.05 * personality.task_anxiety_sensitivity;
    }
    if (appraisal.task_pressure_delta < 0.0) {
        delta.task_pressure *= 0.70 + 0.30 * personality.self_control;
    }
    delta.fatigue += std::max(0.0, appraisal.screen_strain_delta) * 0.10 * personality.screen_strain_sensitivity;
    if (appraisal.fatigue_delta < 0.0) {
        delta.fatigue *= 0.70 + 0.30 * personality.rest_preference;
    }
    if (appraisal.hunger_delta < 0.0 || appraisal.bathroom_urge_delta < 0.0) {
        delta.satisfaction += 0.04 * personality.need_response;
    }

    state.boredom = clamp_unit(state.boredom + delta.boredom);
    state.fatigue = clamp_unit(state.fatigue + delta.fatigue);
    state.task_pressure = clamp_unit(state.task_pressure + delta.task_pressure);
    state.satisfaction = clamp_unit(state.satisfaction + delta.satisfaction);
    state.hunger = clamp_unit(state.hunger + delta.hunger);
    state.bathroom_urge = clamp_unit(state.bathroom_urge + delta.bathroom_urge);
    state.anxiety = clamp_unit(state.anxiety + delta.anxiety);
    state.screen_strain = clamp_unit(state.screen_strain + delta.screen_strain);
    state.purchase_urge = clamp_unit(state.purchase_urge + delta.purchase_urge);
    return delta;
}

std::string state_summary(const CharacterState& state) {
    std::ostringstream output;
    output << "S{";
    append_value(output, "boredom", state.boredom); output << ", ";
    append_value(output, "fatigue", state.fatigue); output << ", ";
    append_value(output, "task_pressure", state.task_pressure); output << ", ";
    append_value(output, "satisfaction", state.satisfaction); output << ", ";
    append_value(output, "hunger", state.hunger); output << ", ";
    append_value(output, "bathroom_urge", state.bathroom_urge); output << ", ";
    append_value(output, "anxiety", state.anxiety); output << ", ";
    append_value(output, "screen_strain", state.screen_strain); output << ", ";
    append_value(output, "purchase_urge", state.purchase_urge);
    output << '}';
    return output.str();
}

std::string state_delta_summary(const StateDelta& delta) {
    std::ostringstream output;
    output << "StateDelta{elapsed_minutes=" << delta.elapsed_minutes << ", ";
    append_value(output, "boredom", delta.boredom); output << ", ";
    append_value(output, "fatigue", delta.fatigue); output << ", ";
    append_value(output, "task_pressure", delta.task_pressure); output << ", ";
    append_value(output, "satisfaction", delta.satisfaction); output << ", ";
    append_value(output, "hunger", delta.hunger); output << ", ";
    append_value(output, "bathroom_urge", delta.bathroom_urge); output << ", ";
    append_value(output, "anxiety", delta.anxiety); output << ", ";
    append_value(output, "screen_strain", delta.screen_strain); output << ", ";
    append_value(output, "purchase_urge", delta.purchase_urge);
    output << '}';
    return output.str();
}
