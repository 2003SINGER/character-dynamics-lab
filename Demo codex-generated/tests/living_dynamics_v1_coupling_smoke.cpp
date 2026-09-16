#include "living_dynamics.h"
#include "demo_living_dynamics_v0.h"
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
    DemoLivingDynamicsV0 model; s = CharacterState{}; s.hunger=0.0; s.bathroom_urge=0.0; const double sat=s.satisfaction; model.advance_continuous(s,p,nullptr,30); if(!(std::abs(s.satisfaction-sat)<0.01)) return 9;
    std::cout<<"living_dynamics_v1_coupling_smoke: PASS\n"; return 0;
}
