#include "living_dynamics.h"
#include "runtime_scheduler.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace LivingDynamics {
static double clamp(double x){return std::clamp(x,0.0,1.0);}
static double smoothstep(double e0,double e1,double x){if(e1<=e0)return x>=e1?1.0:0.0; const double t=clamp((x-e0)/(e1-e0)); return t*t*(3.0-2.0*t);}
double overload_risk(const CharacterState&,const Personality&);
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
double perceived_hunger(const CharacterState& s,const Personality& p){const double anxiety_notice=clamp((s.anxiety-.20)/.80);const double boredom_notice=clamp((s.boredom-.25)/.75);return clamp(s.hunger + 0.16*anxiety_notice + 0.10*boredom_notice - 0.14*task_absorption(s));}
double perceived_bathroom(const CharacterState& s,const Personality& p){const double anxiety_notice=clamp((s.anxiety-.20)/.80);return clamp(s.bathroom_urge + 0.10*anxiety_notice - 0.05*task_absorption(s));}
double overload(const CharacterState& s,const Personality& p){return overload_risk(s,p);}
double pressure_motivation(const CharacterState& s){return s.task_pressure < .70 ? s.task_pressure/.70 : 1.0;}
double task_pressure_target_at(const Observation& o,const CharacterState& s,int now){
    if (!has_known_fact(o,"task.coursework.status","active")) return .04;
    double effort=0.0, effort_target=0.0;
    const bool has_effort=known_double(o,"task.coursework.effort",effort);
    const bool has_target=known_double(o,"task.coursework.effort_target",effort_target) && effort_target>0.0;
    const double remaining=(has_effort && has_target) ? clamp(1.0-effort/effort_target) : 1.0;
    int deadline=0;
    const bool has_deadline=now >= 0
        && known_int(o,"task.coursework.deadline_at_total_minutes",deadline);
    const double urgency=!has_deadline ? .15 : (now>=deadline ? 1.0
        : clamp(1.0-static_cast<double>(deadline-now)/720.0));
    int unread=0; known_int(o,"message.unread_count",unread);
    // With no deadline urgency, an unfinished task remains a normal-pressure
    // background concern. Near/past deadline, the same O facts can reach the
    // declared High/Extreme and overload ranges rather than capping at .81.
    const double commitment=s.commitment.status==CommitmentStatus::Active ? .08
        : (s.commitment.status==CommitmentStatus::Suspended ? .03 : 0.0);
    return clamp(.10+.30*remaining+.48*urgency+(unread>0?.04:0.0)+commitment);
}
double task_pressure_target(const Observation& o,const CharacterState& s){
    int now=-1;
    known_int(o,"clock.total_minutes",now);
    return task_pressure_target_at(o,s,now);
}
double anxiety_facilitation(const CharacterState& s){return clamp(1.0-std::abs(s.anxiety-.35)/.35);}
double anxiety_impairment(const CharacterState& s){return clamp((s.anxiety-.70)/.30);}
double overload_risk(const CharacterState& s,const Personality& p){return clamp(std::max(0.0,(s.task_pressure-.75)/.25)*std::max(0.0,(s.anxiety-.65)/.35)*(0.65+0.35*s.fatigue*p.task_anxiety_sensitivity));}
double circadian_sleep_factor(const Observation& o){const auto* f=find_fact(o,"clock.total_minutes"); if(!f)return -0.1; int t=0; try{t=std::stoi(f->value)%1440;}catch(...){return -0.1;} if(t<360||t>=1320)return .55; if(t>=1200)return .22; if(t>=1080)return 0.0; if(t<540)return -.12; return -.28;}
double sleep_readiness(const Observation& o,const CharacterState& s,const Personality& p){
    // Fatigue enters recovery_drive exactly once.  Sleep readiness is the
    // remaining context: time of day, accumulated screen exposure, and
    // countervailing anxiety/bodily needs.
    return clamp(.20*s.screen_strain+circadian_sleep_factor(o)-.22*s.anxiety
                 -.18*perceived_hunger(s,p)-.22*perceived_bathroom(s,p));
}
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
double urgent_bodily_need_threshold(const Personality& personality){
    // Reconsider before a bodily state is saturated. The profile changes
    // salience slightly, while the threshold remains V1 model law rather
    // than a hidden Runtime policy rule.
    return .85-.04*personality.need_response;
}
double hunger_drive(const CharacterState& s,const Personality& p){
    // High need-response shifts awareness earlier by moving the effective
    // input upward; this is consistent with the lower urgent threshold in
    // policy rather than reversing direction at the response layer.
    const double h=perceived_hunger(s,p)+.04*p.need_response;
    return clamp(.08*smoothstep(.25,.50,h)+.28*smoothstep(.50,.70,h)+.62*smoothstep(.70,.88,h)+.38*smoothstep(.88,1.0,h));
}
double bathroom_drive(const CharacterState& s,const Personality& p){
    const double u=perceived_bathroom(s,p)+.04*p.need_response;
    return clamp(.08*smoothstep(.25,.50,u)+.30*smoothstep(.50,.75,u)+.62*smoothstep(.75,.90,u)+.35*smoothstep(.90,1.0,u));
}
double fatigue_recovery_drive(const CharacterState& s){
    return clamp(.05*smoothstep(.25,.55,s.fatigue)+.35*smoothstep(.55,.80,s.fatigue)+.60*smoothstep(.80,.92,s.fatigue));
}
double boredom_stimulation_drive(const CharacterState& s){
    return clamp(.08*smoothstep(.25,.55,s.boredom)+.42*smoothstep(.55,.80,s.boredom)+.50*smoothstep(.80,.92,s.boredom));
}
double screen_aversion(const CharacterState& s){
    return clamp(.10*smoothstep(.55,.80,s.screen_strain)+.90*smoothstep(.80,.98,s.screen_strain));
}
double task_engagement_drive(const CharacterState& s,const Personality& p){
    const double urgency=pressure_motivation(s);
    const double facilitation=anxiety_facilitation(s);
    const double impairment=anxiety_impairment(s);
    return clamp(urgency*(.72+.28*p.self_control)*(.88+.18*facilitation)
                 *(1.0-.70*overload_risk(s,p)-.30*impairment));
}
double recovery_drive(const CharacterState& s,const Personality& p){
    return clamp(.04*pressure_motivation(s)+fatigue_recovery_drive(s)
                 +screen_aversion(s)
                 +.06*p.rest_preference*smoothstep(.35,.55,s.fatigue)
                 +.08*overload_risk(s,p));
}
double distraction_drive(const CharacterState& s,const Personality& p){
    return clamp(.65*boredom_stimulation_drive(s)
                 +.16*smoothstep(.35,.75,s.boredom)*p.procrastination
                 +.14*smoothstep(.35,.75,s.boredom)*p.stimulation_seeking);
}
double goal_reward_support(const CharacterState& s){ return smoothstep(.25,.75,s.satisfaction); }
double cognitive_fatigue_penalty(const CharacterState& s){ return .25*fatigue_recovery_drive(s); }
}
