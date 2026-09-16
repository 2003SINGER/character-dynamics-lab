#include "state.h"

#include "runtime_scheduler.h"

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

StateDelta semantic_delta(const Appraisal& appraisal,
                          const Personality& personality) {
    StateDelta delta;
    for (const auto& signal : appraisal.semantic_signals) {
        const double strength = std::clamp(signal.intensity, 0.0, 1.0);
        const double relevance = std::clamp(signal.goal_relevance, 0.0, 1.0);
        switch (signal.kind) {
        case AppraisalSignalKind::GoalProgress:
            delta.task_pressure -= 0.12 * strength * std::max(0.25, relevance);
            delta.satisfaction += 0.04 * strength;
            delta.anxiety -= 0.03 * strength * personality.task_anxiety_sensitivity;
            break;
        case AppraisalSignalKind::GoalCompletion:
            delta.task_pressure -= 0.85 * strength;
            delta.anxiety -= 0.55 * strength;
            delta.satisfaction += 0.32 * strength;
            break;
        case AppraisalSignalKind::GoalObstruction:
            delta.task_pressure += 0.06 * strength * std::max(0.25, relevance);
            delta.anxiety += 0.04 * strength * personality.task_anxiety_sensitivity;
            delta.satisfaction -= 0.03 * strength;
            break;
        case AppraisalSignalKind::Stimulation:
            delta.boredom -= 0.18 * strength;
            delta.fatigue += 0.04 * strength;
            break;
        case AppraisalSignalKind::Recovery:
            delta.fatigue -= 0.28 * strength;
            delta.screen_strain -= 0.12 * strength;
            delta.satisfaction += 0.04 * strength;
            break;
        case AppraisalSignalKind::ShortTermReward:
            delta.satisfaction += 0.08 * strength;
            break;
        case AppraisalSignalKind::EnvironmentControl:
            delta.satisfaction += 0.02 * strength;
            break;
        }
        // signal.controllability is intentionally not consumed in v0.
    }
    return delta;
}
} // namespace

StateUpdate update_state(CharacterState& state,
                          const Appraisal& appraisal,
                          const Personality& personality,
                         int elapsed_minutes,
                         const ParameterConfig& config) {
    const CharacterState before = state;
    StateUpdate update;
    update.semantic_contribution = semantic_delta(appraisal, personality);
    StateDelta& delta = update.requested;
    delta.elapsed_minutes = elapsed_minutes;
    const double time_scale = static_cast<double>(elapsed_minutes) / 30.0;

    delta.boredom = appraisal.boredom_delta
                  + update.semantic_contribution.boredom
                  + 0.01 * time_scale;
    delta.fatigue = appraisal.fatigue_delta
                  + update.semantic_contribution.fatigue
                  + 0.012 * time_scale;
    delta.task_pressure = (appraisal.task_pressure_delta
                        + update.semantic_contribution.task_pressure)
                        * config.task_pressure_coupling;
    delta.satisfaction = appraisal.satisfaction_delta
                       + update.semantic_contribution.satisfaction
                       - 0.01 * time_scale;
    delta.hunger = appraisal.hunger_delta
                 + update.semantic_contribution.hunger
                 + 0.025 * time_scale;
    delta.bathroom_urge = appraisal.bathroom_urge_delta
                        + update.semantic_contribution.bathroom_urge
                        + 0.020 * time_scale;
    delta.screen_strain = appraisal.screen_strain_delta
                        + update.semantic_contribution.screen_strain
                        - 0.030 * time_scale;
    delta.purchase_urge = appraisal.purchase_urge_delta
                        + update.semantic_contribution.purchase_urge
                        - 0.018 * time_scale;
    delta.anxiety = appraisal.anxiety_delta
                  + update.semantic_contribution.anxiety
                  + std::max(0.0, state.task_pressure - 0.55)
                    * 0.08 * time_scale * personality.task_anxiety_sensitivity;

    const double raw_task_pressure_delta = delta.task_pressure;
    if (raw_task_pressure_delta > 0.0) {
        delta.task_pressure += 0.06 * personality.procrastination * config.state_accumulation;
        delta.anxiety += 0.05 * personality.task_anxiety_sensitivity;
    }
    if (raw_task_pressure_delta < 0.0) {
        delta.task_pressure *= (0.70 + 0.30 * personality.self_control) * config.state_decay;
    }
    delta.fatigue += std::max(0.0, delta.screen_strain)
                   * 0.10 * personality.screen_strain_sensitivity;
    if (delta.fatigue < 0.0) {
        delta.fatigue *= (0.70 + 0.30 * personality.rest_preference) * config.state_recovery_strength;
    }
    if (delta.hunger < 0.0 || delta.bathroom_urge < 0.0) {
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

    update.applied.elapsed_minutes = elapsed_minutes;
    update.applied.boredom = state.boredom - before.boredom;
    update.applied.fatigue = state.fatigue - before.fatigue;
    update.applied.task_pressure = state.task_pressure - before.task_pressure;
    update.applied.satisfaction = state.satisfaction - before.satisfaction;
    update.applied.hunger = state.hunger - before.hunger;
    update.applied.bathroom_urge = state.bathroom_urge - before.bathroom_urge;
    update.applied.anxiety = state.anxiety - before.anxiety;
    update.applied.screen_strain = state.screen_strain - before.screen_strain;
    update.applied.purchase_urge = state.purchase_urge - before.purchase_urge;
    return update;
}

StateUpdate advance_continuous_state(CharacterState& state,
                                     const Personality& personality,
                                     const RunningAction* running_action,
                                     int elapsed_minutes,
                                     const ParameterConfig& config) {
    // Keep baseline wall-clock drift in the established updater, but isolate
    // it from all event/appraisal deltas. Running-action rates are explicitly
    // a v1 engineering adapter, not a claim about psychological parameters.
    StateUpdate update = update_state(state, Appraisal{}, personality, elapsed_minutes, config);
    if (running_action == nullptr || elapsed_minutes == 0) return update;

    const CharacterState before = state;
    const double scale = static_cast<double>(elapsed_minutes) / 30.0;
    StateDelta action_delta;
    action_delta.elapsed_minutes = elapsed_minutes;
    switch (running_action->action) {
    case ActionType::StudyAtComputer:
    case ActionType::StudyFocused:
    case ActionType::StudyHalfhearted:
        action_delta.fatigue = 0.018 * scale;
        action_delta.screen_strain = running_action->action == ActionType::StudyAtComputer ? 0.020 * scale : 0.0;
        break;
    case ActionType::RestAtBed:
        action_delta.fatigue = -0.050 * scale;
        action_delta.screen_strain = -0.020 * scale;
        break;
    case ActionType::SleepAtBed:
        action_delta.fatigue = -0.110 * scale;
        action_delta.screen_strain = -0.060 * scale;
        break;
    case ActionType::UsePhone:
    case ActionType::ShopOnPhone:
    case ActionType::UseComputer:
        action_delta.fatigue = 0.006 * scale;
        action_delta.screen_strain = 0.030 * scale;
        break;
    default:
        break;
    }
    state.fatigue = clamp_unit(state.fatigue + action_delta.fatigue);
    state.screen_strain = clamp_unit(state.screen_strain + action_delta.screen_strain);
    action_delta.fatigue = state.fatigue - before.fatigue;
    action_delta.screen_strain = state.screen_strain - before.screen_strain;
    update.requested.fatigue += action_delta.fatigue;
    update.requested.screen_strain += action_delta.screen_strain;
    update.applied.fatigue += action_delta.fatigue;
    update.applied.screen_strain += action_delta.screen_strain;
    return update;
}

StateUpdate apply_appraisal_impulse(CharacterState& state,
                                    const Appraisal& appraisal,
                                    const Personality& personality,
                                    const ParameterConfig& config) {
    return update_state(state, appraisal, personality, 0, config);
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
    output << ", commitment=";
    switch (state.commitment.status) {
    case CommitmentStatus::None: output << "none"; break;
    case CommitmentStatus::Active: output << state.commitment.task_id << "(active)"; break;
    case CommitmentStatus::Suspended:
        output << state.commitment.task_id << "(suspended:"
               << state.commitment.suspended_decision_points << ')';
        break;
    }
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

std::string state_update_summary(const StateUpdate& update) {
    return "StateUpdate{semantic_U=" + state_delta_summary(update.semantic_contribution)
         + ", requested=" + state_delta_summary(update.requested)
         + ", applied=" + state_delta_summary(update.applied) + '}';
}

