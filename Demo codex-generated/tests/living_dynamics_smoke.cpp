#include "living_dynamics.h"
#include "decision.h"
#include "runtime_scheduler.h"
#include "demo_living_dynamics_v0.h"
#include <cmath>
int main() {
    Personality p; CharacterState calm, stressed;
    calm.hunger = stressed.hunger = .5; calm.bathroom_urge = stressed.bathroom_urge = .5;
    stressed.anxiety = .8; stressed.boredom = .8; stressed.task_pressure = .85;
    if (!(LivingDynamics::perceived_hunger(stressed,p) > LivingDynamics::perceived_hunger(calm,p))) return 1;
    if (!(LivingDynamics::rest_recovery_efficiency(calm) > LivingDynamics::rest_recovery_efficiency(stressed))) return 2;
    CharacterState hungry=calm; hungry.hunger=.9;
    if (!(LivingDynamics::meal_hunger_relief(hungry)>LivingDynamics::meal_hunger_relief(calm))) return 3;
    CharacterState urgent = calm; urgent.bathroom_urge = .9;
    if (!(LivingDynamics::bathroom_relief(urgent) > LivingDynamics::bathroom_relief(calm))) return 4;
    Observation o; o.facts.push_back({"clock.total_minutes","1380",KnowledgeStatus::Known,"test","23:00"});
    Observation d; d.facts.push_back({"clock.total_minutes","780",KnowledgeStatus::Known,"test","13:00"});
    if (!(LivingDynamics::sleep_readiness(o,calm,p)>LivingDynamics::sleep_readiness(d,calm,p))) return 5;
    CharacterState rested = calm; rested.fatigue = .1;
    CharacterState taxed = calm; taxed.fatigue = .9; taxed.anxiety = .7;
    if (!(LivingDynamics::metabolism_rate(taxed, nullptr) > LivingDynamics::metabolism_rate(rested, nullptr))) return 6;
    if (!(LivingDynamics::need_discomfort(taxed, p) > LivingDynamics::need_discomfort(rested, p))) return 7;
    CharacterState need_low = calm; need_low.hunger = .1;
    CharacterState need_high = calm; need_high.hunger = .9;
    RunningAction idle; idle.action = ActionType::Idle;
    DemoLivingDynamicsV0 dynamics;
    dynamics.advance_continuous(need_low, o, p, &idle, 30);
    dynamics.advance_continuous(need_high, o, p, &idle, 30);
    if (!(need_high.satisfaction < need_low.satisfaction)) return 8;
    return 0;
}
