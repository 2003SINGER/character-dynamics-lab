#include "living_dynamics.h"
#include "demo_living_dynamics_v1.h"
#include "runtime_scheduler.h"
#include "world.h"
#include "observation.h"
#include <algorithm>
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
    s.anxiety=.10; const double anxiety_low=LivingDynamics::anxiety_facilitation(s);
    s.anxiety=.40; const double anxiety_mid=LivingDynamics::anxiety_facilitation(s);
    s.anxiety=.95; const double anxiety_extreme=LivingDynamics::anxiety_facilitation(s);
    if (!(anxiety_mid > anxiety_low && anxiety_mid > anxiety_extreme
          && LivingDynamics::anxiety_impairment(s) > .7)) return 21;
    s.fatigue=.10; const double fresh_recovery=LivingDynamics::fatigue_recovery_drive(s);
    s.fatigue=.65; const double tired_recovery=LivingDynamics::fatigue_recovery_drive(s);
    s.fatigue=.95; const double exhausted_recovery=LivingDynamics::fatigue_recovery_drive(s);
    if (!(fresh_recovery < .05 && tired_recovery > fresh_recovery && exhausted_recovery > tired_recovery)) return 22;
    s.hunger=.05; if (!(LivingDynamics::hunger_drive(s,p) < .02)) return 23;
    s.hunger=.85; if (!(LivingDynamics::hunger_drive(s,p) > .5)) return 24;
    s.screen_strain=.05; const double screen_low=LivingDynamics::screen_aversion(s);
    s.screen_strain=.90; const double screen_high=LivingDynamics::screen_aversion(s);
    if (!(screen_low < .02 && screen_high > .4)) return 25;
    // Coupling matrix: pressure with calm/fresh state remains executable,
    // while the same pressure with anxiety and fatigue enters overload.
    s.task_pressure=.85; s.anxiety=.20; s.fatigue=.20;
    if (!(LivingDynamics::pressure_motivation(s) > .9 && LivingDynamics::overload_risk(s,p) < .05)) return 18;
    s.hunger=.92; s.task_pressure=.40; s.anxiety=.20; s.fatigue=.20;
    if (!(LivingDynamics::hunger_drive(s,p) > LivingDynamics::pressure_motivation(s))) return 19;
    s.fatigue=.90; s.screen_strain=.85; Observation clock;
    clock.facts.push_back({"clock.total_minutes", "600", KnowledgeStatus::Known, "test", ""});
    const double day_sleep=LivingDynamics::sleep_readiness(clock,s,p);
    clock.facts[0].value="1320";
    const double night_sleep=LivingDynamics::sleep_readiness(clock,s,p);
    if (!(night_sleep > day_sleep + .15)) return 20;
    // Sleep readiness supplies context rather than a second fatigue path:
    // with the same clock and screen exposure, fatigue alone cannot change it.
    s.fatigue=.20; const double low_fatigue_readiness=LivingDynamics::sleep_readiness(clock,s,p);
    s.fatigue=.90; const double high_fatigue_readiness=LivingDynamics::sleep_readiness(clock,s,p);
    if (std::abs(low_fatigue_readiness-high_fatigue_readiness) > 1e-12) return 33;
    s.task_pressure=.1; const double u_low=LivingDynamics::pressure_motivation(s); s.task_pressure=.5; const double u_mid=LivingDynamics::pressure_motivation(s); s.task_pressure=.9; const double u_high=LivingDynamics::pressure_motivation(s); if (!(u_low < u_mid && u_mid <= u_high)) return 9;
    s.task_pressure=.9; s.anxiety=.2; s.fatigue=.2; const double focused=LivingDynamics::overload_risk(s,p); s.anxiety=.95; s.fatigue=.9; const double overloaded=LivingDynamics::overload_risk(s,p); if (!(focused < .05 && overloaded > focused + .25)) return 10;
    DemoLivingDynamicsV1 model; s = CharacterState{}; s.hunger=0.0; s.bathroom_urge=0.0; s.fatigue=0.0; s.anxiety=0.0; const double sat=s.satisfaction; RunningAction baseline; baseline.action=ActionType::Idle; model.advance_continuous(s,clock,p,&baseline,30); if(!(std::abs(s.satisfaction-sat)<0.01)) return 11;
    // Physiological inventory has one continuous owner: baseline × modifier,
    // exactly once per 30-minute interval.
    if (!(s.hunger > .024 && s.hunger < .027
          && s.bathroom_urge > .019 && s.bathroom_urge < .022)) return 26;
    s.purchase_urge=.8; const double purchase=s.purchase_urge; RunningAction idle; idle.action=ActionType::Idle; model.advance_continuous(s,clock,p,&idle,30); if(!(s.purchase_urge<purchase)) return 12;
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
    // Calibration regressions: fatigue gains load under sustained work and a
    // short rest recovers it without collapsing the inventory to zero.
    s = CharacterState{}; s.fatigue=.40; RunningAction study; study.action=ActionType::StudyFocused;
    model.advance_continuous(s,clock,p,&study,120); const double loaded_fatigue=s.fatigue;
    if (!(loaded_fatigue > .40)) return 27;
    RunningAction rest; rest.action=ActionType::RestAtBed; model.advance_continuous(s,clock,p,&rest,30);
    if (!(s.fatigue < loaded_fatigue && s.fatigue > .05)) return 28;
    // Rest/Sleep discharge acute anxiety but cannot overshoot the contextual
    // target and create a low-saturation attractor.
    s = CharacterState{}; s.task_pressure=.0; s.anxiety=.045;
    model.advance_continuous(s,clock,p,&rest,30);
    if (s.anxiety < .04 - 1e-12) return 40;
    // Fatigue and screen exposure each have one action-continuous owner.
    // Settlement and a Recovery semantic signal cannot replay either effect.
    observation = {}; observation.last_self_action = {true, ActionType::SleepAtBed, true};
    s = CharacterState{}; s.fatigue=.75; s.screen_strain=.75;
    const Appraisal sleep_settlement=model.appraise(observation,s,p);
    if (sleep_settlement.fatigue_delta != 0.0 || sleep_settlement.screen_strain_delta != 0.0) return 34;
    Appraisal recovery; recovery.semantic_signals.push_back({AppraisalSignalKind::Recovery,1.0,1.0,1.0,0.0,"test"});
    const double fatigue_before_recovery=s.fatigue, screen_before_recovery=s.screen_strain;
    model.apply_impulse(s,recovery,p);
    if (std::abs(s.fatigue-fatigue_before_recovery)>1e-12 || std::abs(s.screen_strain-screen_before_recovery)>1e-12) return 35;
    observation.last_self_action.action=ActionType::UsePhone;
    if (model.appraise(observation,s,p).screen_strain_delta != 0.0) return 36;
    RunningAction phone; phone.action=ActionType::UsePhone; const double screen_before_phone=s.screen_strain;
    model.advance_continuous(s,clock,p,&phone,30);
    if (!(s.screen_strain > screen_before_phone)) return 37;
    // Fragmented device exposure must enter a behaviorally meaningful zone;
    // short rests cannot erase it on the same timescale.
    s = CharacterState{}; s.screen_strain=.05;
    model.advance_continuous(s,clock,p,&phone,360);
    if (!(s.screen_strain >= .55 && LivingDynamics::screen_aversion(s) > 0.0)) return 39;
    // A quiet interval returns satisfaction toward neutral and never creates
    // an upward-only affect drift.
    s = CharacterState{}; s.satisfaction=.80; RunningAction quiet; quiet.action=ActionType::Idle;
    model.advance_continuous(s,clock,p,&quiet,30); if (!(s.satisfaction < .80)) return 29;
    // Equal positive appraisal has less effect near the high headroom bound.
    Appraisal reward; reward.satisfaction_delta=.12;
    s = CharacterState{}; s.satisfaction=.30; const double low_before=s.satisfaction;
    model.apply_impulse(s,reward,p); const double low_gain=s.satisfaction-low_before;
    s = CharacterState{}; s.satisfaction=.90; const double high_before=s.satisfaction;
    model.apply_impulse(s,reward,p); const double high_gain=s.satisfaction-high_before;
    if (!(low_gain > high_gain && high_gain > 0.0)) return 30;
    // Pressure is a continuous O-derived discrepancy, not an event stock.
    Observation task_o;
    task_o.facts={{"task.coursework.status","active",KnowledgeStatus::Known,"test",""},
                  {"task.coursework.effort","0",KnowledgeStatus::Known,"test",""},
                  {"task.coursework.effort_target","8",KnowledgeStatus::Known,"test",""},
                  {"task.coursework.deadline_at_total_minutes","1200",KnowledgeStatus::Known,"test",""},
                  {"clock.total_minutes","1080",KnowledgeStatus::Known,"test",""}};
    s = CharacterState{}; s.task_pressure=.10; model.advance_continuous(s,task_o,p,&idle,60);
    if (!(s.task_pressure > .10)) return 31;
    Appraisal obsolete_impulse; obsolete_impulse.task_pressure_delta=.50;
    const double after_target_rise=s.task_pressure; model.apply_impulse(s,obsolete_impulse,p);
    if (std::abs(s.task_pressure-after_target_rise)>1e-12) return 32;
    // Appraisal can report the O-derived target for traceability, but it must
    // never advance the continuous pressure channel at a zero-duration
    // boundary.
    const Appraisal target_report=model.appraise(task_o,s,p);
    if (!target_report.has_task_pressure_target) return 43;
    const double before_target_report=s.task_pressure;
    model.apply_impulse(s,target_report,p);
    if (std::abs(s.task_pressure-before_target_report)>1e-12) return 44;
    task_o.facts[0].value="completed";
    model.advance_continuous(s,task_o,p,&idle,60);
    if (!(s.task_pressure < after_target_rise)) return 38;
    // The exact continuous deadline integration is invariant to irrelevant
    // boundary density. Both trajectories see identical O-side clock/target
    // evolution; only the number of no-op boundaries differs.
    const auto pressure_after_boundaries = [&](int parts) {
        Observation evolving;
        evolving.facts={{"task.coursework.status","active",KnowledgeStatus::Known,"test",""},
                        {"task.coursework.effort","0",KnowledgeStatus::Known,"test",""},
                        {"task.coursework.effort_target","8",KnowledgeStatus::Known,"test",""},
                        {"task.coursework.deadline_at_total_minutes","1200",KnowledgeStatus::Known,"test",""},
                        {"clock.total_minutes","600",KnowledgeStatus::Known,"test",""}};
        CharacterState split_state; split_state.task_pressure=.10;
        for (int part=1; part<=parts; ++part) {
            evolving.facts[4].value=std::to_string(600 + part * (300 / parts));
            model.advance_continuous(split_state,evolving,p,&idle,300 / parts);
            const Appraisal boundary_report=model.appraise(evolving,split_state,p);
            model.apply_impulse(split_state,boundary_report,p);
        }
        return split_state.task_pressure;
    };
    const double two_boundary_pressure=pressure_after_boundaries(2);
    const double twenty_boundary_pressure=pressure_after_boundaries(20);
    if (std::abs(two_boundary_pressure-twenty_boundary_pressure)>1e-10) return 45;
    // High/extreme pressure is reachable from the observed active-task and
    // deadline trajectory itself, not by injecting a high pressure state.
    Observation overdue;
    overdue.facts={{"task.coursework.status","active",KnowledgeStatus::Known,"test",""},
                   {"task.coursework.effort","0",KnowledgeStatus::Known,"test",""},
                   {"task.coursework.effort_target","8",KnowledgeStatus::Known,"test",""},
                   {"task.coursework.deadline_at_total_minutes","600",KnowledgeStatus::Known,"test",""},
                   {"message.unread_count","1",KnowledgeStatus::Known,"test",""},
                   {"clock.total_minutes","600",KnowledgeStatus::Known,"test",""}};
    CharacterState reachable_pressure;
    reachable_pressure.task_pressure=.10;
    reachable_pressure.commitment.status=CommitmentStatus::Active;
    reachable_pressure.commitment.task_id="coursework";
    for (int step=1; step<=12; ++step) {
        overdue.facts[5].value=std::to_string(600 + step * 60);
        model.advance_continuous(reachable_pressure,overdue,p,&idle,60);
    }
    if (!(reachable_pressure.task_pressure>=.92
          && LivingDynamics::pressure_zone(reachable_pressure.task_pressure)==LivingDynamics::ActivationZone::Extreme)) return 46;
    reachable_pressure.anxiety=.90;
    reachable_pressure.fatigue=.90;
    if (!(LivingDynamics::overload_risk(reachable_pressure,p)>.10)) return 47;
    // Extreme fatigue is a real feasibility boundary: work/device candidates
    // cannot repeatedly keep the state saturated, while recovery remains.
    World policy_world; Observation policy_o=refresh_observation({},policy_world,{});
    s = CharacterState{}; s.fatigue=.95;
    const DecisionContext fatigue_decision=model.build_policy(policy_o,s,p);
    bool recovery_available=false;
    for (const CandidateAction& item : fatigue_decision.candidates) {
        if (item.action==ActionType::RestAtBed || item.action==ActionType::SleepAtBed)
            recovery_available = recovery_available || item.eligible;
        if ((item.action==ActionType::StudyFocused || item.action==ActionType::StudyHalfhearted
             || item.action==ActionType::StudyAtComputer || item.action==ActionType::UsePhone
             || item.action==ActionType::UseComputer) && item.eligible) return 41;
    }
    if (!recovery_available) return 42;
    std::cout<<"living_dynamics_v1_coupling_smoke: PASS\n"; return 0;
}
