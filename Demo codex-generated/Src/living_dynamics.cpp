#include "living_dynamics.h"
#include "runtime_scheduler.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace LivingDynamics {
static double clamp(double x){return std::clamp(x,0.0,1.0);}
static ActivationZone five_zone(double v,double a,double b,double c,double d){if(v<a)return ActivationZone::Low;if(v<b)return ActivationZone::Normal;if(v<c)return ActivationZone::Activated;if(v<d)return ActivationZone::High;return ActivationZone::Extreme;}
ActivationZone hunger_zone(double v){return five_zone(v,.25,.50,.70,.88);}
ActivationZone bathroom_zone(double v){return five_zone(v,.25,.50,.75,.90);}
ActivationZone fatigue_zone(double v){return five_zone(v,.25,.55,.80,.92);}
ActivationZone pressure_zone(double v){return five_zone(v,.25,.55,.80,.92);}
ActivationZone anxiety_zone(double v){return five_zone(v,.20,.45,.70,.88);}
ActivationZone boredom_zone(double v){return five_zone(v,.25,.55,.80,.92);}
ActivationZone satisfaction_zone(double v){return five_zone(v,.20,.50,.80,.92);}
ActivationZone screen_strain_zone(double v){return five_zone(v,.25,.55,.80,.92);}
ActivationZone purchase_urge_zone(double v){return five_zone(v,.25,.60,.85,.95);}
double task_absorption(const CharacterState& s){return clamp(0.65*s.satisfaction + 0.35*(1.0-s.boredom));}
double perceived_hunger(const CharacterState& s,const Personality& p){return clamp(s.hunger + 0.16*s.anxiety + 0.10*s.boredom - 0.14*task_absorption(s));}
double perceived_bathroom(const CharacterState& s,const Personality& p){return clamp(s.bathroom_urge + 0.10*s.anxiety - 0.05*task_absorption(s));}
double overload(const CharacterState& s,const Personality& p){return clamp(std::max(0.0,s.task_pressure-0.45)*0.9 + 0.55*s.anxiety*p.task_anxiety_sensitivity);}
double pressure_motivation(const CharacterState& s){return s.task_pressure < .70 ? s.task_pressure/.70 : 1.0;}
double anxiety_facilitation(const CharacterState& s){return clamp(1.0-std::abs(s.anxiety-.35)/.35);}
double anxiety_impairment(const CharacterState& s){return clamp((s.anxiety-.70)/.30);}
double overload_risk(const CharacterState& s,const Personality& p){return clamp(std::max(0.0,(s.task_pressure-.75)/.25)*std::max(0.0,(s.anxiety-.65)/.35)*(0.65+0.35*s.fatigue*p.task_anxiety_sensitivity));}
double circadian_sleep_factor(const Observation& o){const auto* f=find_fact(o,"clock.total_minutes"); if(!f)return -0.1; int t=0; try{t=std::stoi(f->value)%1440;}catch(...){return -0.1;} if(t<360||t>=1320)return .55; if(t>=1200)return .22; if(t>=1080)return 0.0; if(t<540)return -.12; return -.28;}
double sleep_readiness(const Observation& o,const CharacterState& s,const Personality& p){return clamp(.65*s.fatigue+.20*s.screen_strain+circadian_sleep_factor(o)-.22*s.anxiety-.18*perceived_hunger(s,p)-.22*perceived_bathroom(s,p));}
double rest_recovery_efficiency(const CharacterState& s){
    const double stress_penalty=clamp((s.anxiety-.70)/.30)*.22;
    return clamp(.62 - stress_penalty + (s.fatigue>=.55?.16:0.0));
}
double meal_hunger_relief(const CharacterState& s){
    const double hungry=clamp((s.hunger-.25)/.63);
    return clamp(.12 + .72*hungry*hungry*(3.0-2.0*hungry));
}
double meal_satisfaction_gain(const CharacterState& s,const Personality& p){return clamp((.015+.12*clamp((s.hunger-.25)/.63))*(1.0-.35*clamp((s.anxiety-.75)/.25)));}
double bathroom_relief(const CharacterState& s){
    const double pressing=clamp((s.bathroom_urge-.25)/.65);
    return clamp(.10 + .78*pressing*pressing*(3.0-2.0*pressing));
}
double metabolism_rate(const CharacterState& s,const RunningAction* a){
    double rate=.025*(1.0+.30*s.fatigue+.15*s.anxiety);
    if(a && (a->action==ActionType::RestAtBed || a->action==ActionType::SleepAtBed)) rate*=.72;
    if(a && (a->action==ActionType::StudyFocused || a->action==ActionType::StudyAtComputer)) rate*=1.12;
    return rate;
}
double bathroom_accumulation_rate(const CharacterState& s,const RunningAction* a){
    double rate=.020*(1.0+.18*s.hunger+.12*s.fatigue);
    if(a && (a->action==ActionType::RestAtBed || a->action==ActionType::SleepAtBed)) rate*=.82;
    return rate;
}
double need_discomfort(const CharacterState& s,const Personality& p){
    return clamp(.62*perceived_hunger(s,p)+.48*perceived_bathroom(s,p));
}
}
