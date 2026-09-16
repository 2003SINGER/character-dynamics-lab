#include "living_dynamics.h"
#include "decision.h"
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
    return 0;
}
