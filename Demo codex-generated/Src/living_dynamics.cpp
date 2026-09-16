#include "living_dynamics.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace LivingDynamics {
static double clamp(double x){return std::clamp(x,0.0,1.0);}
double task_absorption(const CharacterState& s){return clamp(0.65*s.satisfaction + 0.35*(1.0-s.boredom));}
double perceived_hunger(const CharacterState& s,const Personality& p){return clamp(s.hunger + 0.16*s.anxiety + 0.10*s.boredom - 0.14*task_absorption(s));}
double perceived_bathroom(const CharacterState& s,const Personality& p){return clamp(s.bathroom_urge + 0.10*s.anxiety - 0.05*task_absorption(s));}
double overload(const CharacterState& s,const Personality& p){return clamp(std::max(0.0,s.task_pressure-0.45)*0.9 + 0.55*s.anxiety*p.task_anxiety_sensitivity);}
double circadian_sleep_factor(const Observation& o){const auto* f=find_fact(o,"clock.total_minutes"); if(!f)return -0.1; int t=0; try{t=std::stoi(f->value)%1440;}catch(...){return -0.1;} if(t<360||t>=1320)return .55; if(t>=1200)return .22; if(t>=1080)return 0.0; if(t<540)return -.12; return -.28;}
double sleep_readiness(const Observation& o,const CharacterState& s,const Personality& p){return clamp(.65*s.fatigue+.20*s.screen_strain+circadian_sleep_factor(o)-.22*s.anxiety-.18*perceived_hunger(s,p)-.22*perceived_bathroom(s,p));}
double rest_recovery_efficiency(const CharacterState& s){return clamp(.45 + .45*(1.0-s.anxiety)*(1.0-s.task_pressure));}
double meal_hunger_relief(const CharacterState& s){return clamp(.18+.62*s.hunger);}
double meal_satisfaction_gain(const CharacterState& s,const Personality& p){return clamp((.02+.10*s.hunger)*(1.0-.50*s.anxiety));}
double bathroom_relief(const CharacterState& s){return clamp(.22+.62*s.bathroom_urge);}
}
