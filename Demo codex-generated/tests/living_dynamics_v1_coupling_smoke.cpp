#include "living_dynamics.h"
#include "demo_living_dynamics_v1.h"
#include "runtime_scheduler.h"
#include <cmath>
#include <iostream>
int main(){
    Personality p; CharacterState s;
    s.task_pressure=.2; if(!(LivingDynamics::pressure_motivation(s)<1.0)) return 1;
    s.task_pressure=.6; const double mid=LivingDynamics::pressure_motivation(s); s.task_pressure=.95; if(!(mid>0.8 && LivingDynamics::pressure_motivation(s)==1.0)) return 2;
    s.task_pressure=.9; s.anxiety=.2; if(!(LivingDynamics::overload_risk(s,p)<.01)) return 3;
    s.anxiety=.9; if(!(LivingDynamics::overload_risk(s,p)>.1 && LivingDynamics::anxiety_impairment(s)>0.5)) return 4;
    s.hunger=.1; const double low=LivingDynamics::meal_hunger_relief(s); s.hunger=.8; if(!(LivingDynamics::meal_hunger_relief(s)>low)) return 5;
    s.bathroom_urge=.1; const double b=LivingDynamics::bathroom_relief(s); s.bathroom_urge=.85; if(!(LivingDynamics::bathroom_relief(s)>b)) return 6;
    s.task_pressure=.9; s.anxiety=.2; if(!(LivingDynamics::overload_risk(s,p)<.01)) return 7;
    s.task_pressure=.9; s.anxiety=.9; if(!(LivingDynamics::overload_risk(s,p)>.1)) return 8;
    s.task_pressure=.1; const double u_low=LivingDynamics::pressure_motivation(s); s.task_pressure=.5; const double u_mid=LivingDynamics::pressure_motivation(s); s.task_pressure=.9; const double u_high=LivingDynamics::pressure_motivation(s); if (!(u_low < u_mid && u_mid <= u_high)) return 9;
    s.task_pressure=.9; s.anxiety=.2; s.fatigue=.2; const double focused=LivingDynamics::overload_risk(s,p); s.anxiety=.95; s.fatigue=.9; const double overloaded=LivingDynamics::overload_risk(s,p); if (!(focused < .05 && overloaded > focused + .25)) return 10;
    DemoLivingDynamicsV1 model; s = CharacterState{}; s.hunger=0.0; s.bathroom_urge=0.0; const double sat=s.satisfaction; model.advance_continuous(s,p,nullptr,30); if(!(std::abs(s.satisfaction-sat)<0.01)) return 11;
    s.purchase_urge=.8; const double purchase=s.purchase_urge; RunningAction idle; idle.action=ActionType::Idle; model.advance_continuous(s,p,&idle,30); if(!(s.purchase_urge<purchase)) return 12;
    if (LivingDynamics::hunger_zone(.10)!=LivingDynamics::ActivationZone::Low
        || LivingDynamics::hunger_zone(.60)!=LivingDynamics::ActivationZone::Activated
        || LivingDynamics::hunger_zone(.95)!=LivingDynamics::ActivationZone::Extreme) return 11;
    if (LivingDynamics::fatigue_zone(.30)!=LivingDynamics::ActivationZone::Normal
        || LivingDynamics::anxiety_zone(.80)!=LivingDynamics::ActivationZone::High) return 12;
    if (LivingDynamics::boredom_zone(.70)!=LivingDynamics::ActivationZone::Activated
        || LivingDynamics::satisfaction_zone(.10)!=LivingDynamics::ActivationZone::Low
        || LivingDynamics::screen_strain_zone(.90)!=LivingDynamics::ActivationZone::High
        || LivingDynamics::purchase_urge_zone(.90)!=LivingDynamics::ActivationZone::High) return 13;
    Observation observation; s = CharacterState{}; s.boredom=.1; observation.last_self_action.has_action=true; observation.last_self_action.action=ActionType::UsePhone; observation.last_self_action.accepted=true; const double low_boredom=model.appraise(observation,s,p).boredom_delta; s.boredom=.9; const double high_boredom=model.appraise(observation,s,p).boredom_delta; if(!(high_boredom<low_boredom)) return 14;
    s = CharacterState{}; s.purchase_urge=.8; observation.last_self_action.action=ActionType::ShopOnPhone; if(!(model.appraise(observation,s,p).purchase_urge_delta<0.0)) return 15;
    std::cout<<"living_dynamics_v1_coupling_smoke: PASS\n"; return 0;
}
