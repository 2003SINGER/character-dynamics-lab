#include "state.h"

#include "runtime_scheduler.h"
#include "living_dynamics.h"

#include <cmath>
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
            delta.satisfaction += 0.04 * strength;
            delta.anxiety -= 0.03 * strength * personality.task_anxiety_sensitivity;
            break;
        case AppraisalSignalKind::GoalCompletion:
            delta.anxiety -= 0.55 * strength;
            delta.satisfaction += 0.32 * strength;
            break;
        case AppraisalSignalKind::GoalObstruction:
            delta.anxiety += 0.04 * strength * personality.task_anxiety_sensitivity;
            delta.satisfaction -= 0.03 * strength;
            break;
        case AppraisalSignalKind::Stimulation:
            delta.boredom -= 0.18 * strength;
            delta.fatigue += 0.04 * strength;
            break;
        case AppraisalSignalKind::Recovery:
            // Recovery is already integrated by the action's continuous
            // owner.  Keep this semantic channel for its non-fatigue meaning
            // instead of letting it write the same inventory a second time.
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

namespace DemoLivingV0 {
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

    delta.boredom = appraisal.boredom_delta + update.semantic_contribution.boredom;
    delta.fatigue = appraisal.fatigue_delta
                  + update.semantic_contribution.fatigue
                  ;
    // V1 pressure is not an event-impulse inventory.  Its continuously
    // derived target is consumed here only as a bounded correction; the same
    // target is approached during elapsed continuous time below.
    delta.task_pressure = appraisal.has_task_pressure_target
        ? (appraisal.task_pressure_target - state.task_pressure) * 0.12
        : 0.0;
    delta.satisfaction = appraisal.satisfaction_delta
                       + update.semantic_contribution.satisfaction
                       ;
    delta.hunger = appraisal.hunger_delta
                 + update.semantic_contribution.hunger
                 ;
    delta.bathroom_urge = appraisal.bathroom_urge_delta
                        + update.semantic_contribution.bathroom_urge
                        ;
    delta.screen_strain = appraisal.screen_strain_delta
                        + update.semantic_contribution.screen_strain
                       ;
    delta.purchase_urge = appraisal.purchase_urge_delta
                        + update.semantic_contribution.purchase_urge
                        ;
    const double anxiety_target=.04+.40*LivingDynamics::pressure_motivation(state)
        * personality.task_anxiety_sensitivity;
    delta.anxiety = appraisal.anxiety_delta + update.semantic_contribution.anxiety
                  + .18*(anxiety_target-state.anxiety)*time_scale;
    delta.fatigue += std::max(0.0, delta.screen_strain)
                   * 0.10 * personality.screen_strain_sensitivity;
    if (delta.fatigue < 0.0) {
        delta.fatigue *= (0.70 + 0.30 * personality.rest_preference) * config.state_recovery_strength;
    }
    // Satisfaction and anxiety have a weak homeostatic return toward the
    // current context. This prevents repeated ordinary boundaries from
    // pinning affect at 0/1 while preserving stronger appraisal impulses.
    // Homeostasis returns affect toward a neutral setpoint instead of
    // rewarding every comfortable boundary until satisfaction saturates.
    if (delta.satisfaction > 0.0) {
        // Positive outcomes retain semantic meaning but exhibit diminishing
        // headroom near the high zone; no action receives a special bonus.
        delta.satisfaction *= 0.35 + 0.65 * (1.0 - state.satisfaction);
    }
    delta.satisfaction += 0.014 * (0.50 - state.satisfaction) * time_scale;

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
                                     const Observation& observation,
                                     const Personality& personality,
                                     const RunningAction* running_action,
                                     int elapsed_minutes,
                                     const ParameterConfig& config) {
    // Keep baseline wall-clock drift in the established updater, but isolate
    // it from all event/appraisal deltas. Running-action rates are explicitly
    // a v1 engineering adapter, not a claim about psychological parameters.
    StateUpdate update = DemoLivingV0::update_state(state, Appraisal{}, personality, elapsed_minutes, config);
    // Target pressure is an O-derived discrepancy, not an appraisal impulse.
    // The response is time-based, so extra event boundaries cannot pump it.
    const double pressure_before=state.task_pressure;
    const double target=LivingDynamics::task_pressure_target(observation,state);
    const double response=elapsed_minutes<=0 ? 0.0 : 1.0-std::exp(-static_cast<double>(elapsed_minutes)/180.0);
    state.task_pressure=clamp_unit(state.task_pressure+(target-state.task_pressure)*response);
    update.requested.task_pressure += state.task_pressure-pressure_before;
    update.applied.task_pressure += state.task_pressure-pressure_before;
    if (running_action == nullptr || elapsed_minutes == 0) return update;

    const CharacterState before = state;
    const double scale = static_cast<double>(elapsed_minutes) / 30.0;
    const double anxiety_context_target = .04 + .40 * LivingDynamics::pressure_motivation(state)
        * personality.task_anxiety_sensitivity;
    const auto bounded_anxiety_recovery = [&](double rate) {
        // Recovery may discharge acute strain, but may not drive the channel
        // below the same contextual target used by the continuous law.
        return -std::min(rate * scale, std::max(0.0, state.anxiety - anxiety_context_target));
    };
    StateDelta action_delta;
    action_delta.elapsed_minutes = elapsed_minutes;
    switch (running_action->action) {
    case ActionType::StudyAtComputer:
    case ActionType::StudyFocused:
    case ActionType::StudyHalfhearted:
        action_delta.fatigue = 0.018 * scale;
        action_delta.screen_strain = running_action->action == ActionType::StudyAtComputer ? 0.035 * scale : 0.0;
        break;
    case ActionType::RestAtBed:
        action_delta.boredom = 0.01 * scale;
        action_delta.fatigue = -0.028 * scale;
        // A short rest reduces acute discomfort but cannot erase a day of
        // fragmented device exposure; sleep remains the stronger reset.
        action_delta.screen_strain = -0.010 * scale;
        action_delta.anxiety = bounded_anxiety_recovery(
            0.008 * (1.0 + LivingDynamics::overload_risk(state, personality)));
        break;
    case ActionType::SleepAtBed:
        action_delta.boredom = -0.015 * scale;
        action_delta.fatigue = -0.060 * scale;
        action_delta.screen_strain = -0.035 * scale;
        action_delta.anxiety = bounded_anxiety_recovery(
            0.012 * (1.0 + LivingDynamics::overload_risk(state, personality)));
        break;
    case ActionType::UsePhone:
    case ActionType::ShopOnPhone:
    case ActionType::UseComputer:
        action_delta.fatigue = 0.006 * scale;
        action_delta.screen_strain = 0.050 * scale;
        break;
    default:
        break;
    }
    if (running_action->action == ActionType::Idle) action_delta.boredom = 0.025 * scale;
    if (running_action->action == ActionType::UsePhone || running_action->action == ActionType::ShopOnPhone
        || running_action->action == ActionType::UseComputer) action_delta.boredom = -0.025 * scale;
    if (running_action->action != ActionType::UsePhone && running_action->action != ActionType::ShopOnPhone
        && LivingDynamics::purchase_urge_zone(state.purchase_urge) != LivingDynamics::ActivationZone::Low) {
        action_delta.purchase_urge = -0.012 * state.purchase_urge * scale;
    }
    state.fatigue = clamp_unit(state.fatigue + action_delta.fatigue);
    state.screen_strain = clamp_unit(state.screen_strain + action_delta.screen_strain);
    state.boredom = clamp_unit(state.boredom + action_delta.boredom);
    state.anxiety = clamp_unit(state.anxiety + action_delta.anxiety);
    state.purchase_urge = clamp_unit(state.purchase_urge + action_delta.purchase_urge);
    const double metabolism = LivingDynamics::metabolism_rate(state, running_action) * scale;
    const double bathroom = LivingDynamics::bathroom_accumulation_rate(state, running_action) * scale;
    const bool recovery = running_action->action == ActionType::RestAtBed || running_action->action == ActionType::SleepAtBed;
    state.hunger = clamp_unit(state.hunger + metabolism * (recovery ? 0.7 : 1.0));
    state.bathroom_urge = clamp_unit(state.bathroom_urge + bathroom);
    // Bodily needs feed back into affect continuously; the effect grows with
    // the current state and personality rather than acting as a fixed penalty.
    const double discomfort_now = LivingDynamics::need_discomfort(before, personality);
    const double activated_discomfort = std::max(0.0, (discomfort_now - 0.35) / 0.65);
    const double need_mood_cost = (0.018 * activated_discomfort) * scale;
    const double need_anxiety = (0.010 * activated_discomfort)
                              * personality.need_response * scale;
    state.satisfaction = clamp_unit(state.satisfaction - need_mood_cost);
    state.anxiety = clamp_unit(state.anxiety + need_anxiety);
    action_delta.satisfaction -= need_mood_cost;
    action_delta.anxiety += need_anxiety;
    action_delta.fatigue = state.fatigue - before.fatigue;
    action_delta.screen_strain = state.screen_strain - before.screen_strain;
    update.requested.fatigue += action_delta.fatigue;
    update.requested.boredom += action_delta.boredom;
    update.requested.purchase_urge += action_delta.purchase_urge;
    update.applied.boredom += action_delta.boredom;
    update.applied.purchase_urge += action_delta.purchase_urge;
    update.requested.screen_strain += action_delta.screen_strain;
    update.applied.fatigue += action_delta.fatigue;
    update.applied.screen_strain += action_delta.screen_strain;
    update.requested.satisfaction += action_delta.satisfaction;
    update.requested.anxiety += action_delta.anxiety;
    update.applied.satisfaction += action_delta.satisfaction;
    update.applied.anxiety += action_delta.anxiety;
    return update;
}

StateUpdate apply_appraisal_impulse(CharacterState& state,
                                    const Appraisal& appraisal,
                                    const Personality& personality,
                                    const ParameterConfig& config) {
    return DemoLivingV0::update_state(state, appraisal, personality, 0, config);
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
    return "StateUpdate{semantic_U=" + DemoLivingV0::state_delta_summary(update.semantic_contribution)
         + ", requested=" + DemoLivingV0::state_delta_summary(update.requested)
         + ", applied=" + DemoLivingV0::state_delta_summary(update.applied) + '}';
}

}
