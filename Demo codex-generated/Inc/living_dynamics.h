#pragma once

#include "observation.h"
#include "personality.h"
#include "state.h"

namespace LivingDynamics {
enum class ActivationZone { Low, Normal, Activated, High, Extreme };
struct Config {
    double metabolism = 0.025;
    double bathroom_rate = 0.020;
    double overload_threshold = 0.72;
    double meal_base_relief = 0.18;
    double bathroom_base_relief = 0.22;
};

double task_absorption(const CharacterState& state);
double perceived_hunger(const CharacterState& state, const Personality& personality);
double perceived_bathroom(const CharacterState& state, const Personality& personality);
double overload(const CharacterState& state, const Personality& personality);
double circadian_sleep_factor(const Observation& observation);
double sleep_readiness(const Observation& observation, const CharacterState& state,
                       const Personality& personality);
double rest_recovery_efficiency(const CharacterState& state);
double meal_hunger_relief(const CharacterState& state);
double meal_satisfaction_gain(const CharacterState& state, const Personality& personality);
double bathroom_relief(const CharacterState& state);
double metabolism_rate(const CharacterState& state, const RunningAction* action);
double bathroom_accumulation_rate(const CharacterState& state, const RunningAction* action);
double need_discomfort(const CharacterState& state, const Personality& personality);
double hunger_drive(const CharacterState& state, const Personality& personality);
double bathroom_drive(const CharacterState& state, const Personality& personality);
double fatigue_recovery_drive(const CharacterState& state);
double boredom_stimulation_drive(const CharacterState& state);
double screen_aversion(const CharacterState& state);
double task_engagement_drive(const CharacterState& state, const Personality& personality);
double recovery_drive(const CharacterState& state, const Personality& personality);
double distraction_drive(const CharacterState& state, const Personality& personality);
double goal_reward_support(const CharacterState& state);
double cognitive_fatigue_penalty(const CharacterState& state);
double pressure_motivation(const CharacterState& state);
double task_pressure_target(const Observation& observation, const CharacterState& state);
double anxiety_facilitation(const CharacterState& state);
double anxiety_impairment(const CharacterState& state);
double overload_risk(const CharacterState& state, const Personality& personality);
ActivationZone hunger_zone(double value);
ActivationZone bathroom_zone(double value);
ActivationZone fatigue_zone(double value);
ActivationZone pressure_zone(double value);
ActivationZone anxiety_zone(double value);
ActivationZone boredom_zone(double value);
ActivationZone satisfaction_zone(double value);
ActivationZone screen_strain_zone(double value);
ActivationZone purchase_urge_zone(double value);
}
