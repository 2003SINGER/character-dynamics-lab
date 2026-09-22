#include "continuous_runtime.h"
#include "demo_living_dynamics_v1.h"
#include "demo_personality_profiles.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kDay=1440;
constexpr int kStart=480;

void quote(std::ostream& out,const std::string& value) {
    out<<'"';
    for (const char c:value) {
        if (c=='"' || c=='\\') out<<'\\';
        if (c=='\n') out<<"\\n";
        else out<<c;
    }
    out<<'"';
}

void personality_json(std::ostream& out,const Personality& p) {
    out<<"{\"procrastination\":"<<p.procrastination
       <<",\"self_control\":"<<p.self_control
       <<",\"rest_preference\":"<<p.rest_preference
       <<",\"stimulation_seeking\":"<<p.stimulation_seeking
       <<",\"task_anxiety_sensitivity\":"<<p.task_anxiety_sensitivity
       <<",\"screen_strain_sensitivity\":"<<p.screen_strain_sensitivity
       <<",\"need_response\":"<<p.need_response
       <<",\"action_noise\":"<<p.action_noise<<'}';
}

const char* commitment_name(const CharacterState& state) {
    switch (state.commitment.status) {
    case CommitmentStatus::Active: return "active";
    case CommitmentStatus::Suspended: return "suspended";
    case CommitmentStatus::None: return "none";
    }
    return "none";
}

void state_json(std::ostream& out,const CharacterState& s) {
    out<<"{\"boredom\":"<<s.boredom<<",\"fatigue\":"<<s.fatigue
       <<",\"task_pressure\":"<<s.task_pressure<<",\"satisfaction\":"<<s.satisfaction
       <<",\"hunger\":"<<s.hunger<<",\"bathroom_urge\":"<<s.bathroom_urge
       <<",\"anxiety\":"<<s.anxiety<<",\"screen_strain\":"<<s.screen_strain
       <<",\"commitment\":"; quote(out,commitment_name(s)); out<<'}';
}

struct Counts {
    int study=0, leisure=0, rest=0, sleep=0, idle=0, bodily=0;
    int decisions=0, completed=0, assigned=0, boundaries=0;
    void include(const RuntimeExecutionResult& step) {
        ++boundaries;
        if (step.policy_evaluated) ++decisions;
        const auto& action=step.running_action_before;
        if (action) {
            const int minutes=step.runtime.boundary.elapsed_minutes;
            switch (action->action) {
            case ActionType::StudyFocused: case ActionType::StudyHalfhearted:
            case ActionType::StudyAtComputer: study+=minutes; break;
            case ActionType::UsePhone: case ActionType::UseComputer:
            case ActionType::ShopOnPhone: leisure+=minutes; break;
            case ActionType::RestAtBed: rest+=minutes; break;
            case ActionType::SleepAtBed: sleep+=minutes; break;
            case ActionType::GetMeal: case ActionType::GoToBathroom: bodily+=minutes; break;
            default: idle+=minutes; break;
            }
        }
        if (step.pre_policy_outcome && step.pre_policy_outcome->task_completed) ++completed;
        for (const auto& event:step.runtime.world_events)
            if (event.id=="task-assigned") ++assigned;
    }
};

void counts_json(std::ostream& out,const Counts& c) {
    out<<"\"study_minutes\":"<<c.study<<",\"leisure_minutes\":"<<c.leisure
       <<",\"rest_minutes\":"<<c.rest<<",\"sleep_minutes\":"<<c.sleep
       <<",\"idle_minutes\":"<<c.idle<<",\"bodily_minutes\":"<<c.bodily
       <<",\"decision_count\":"<<c.decisions<<",\"task_completions\":"<<c.completed
       <<",\"task_assignments\":"<<c.assigned<<",\"boundary_count\":"<<c.boundaries;
}

struct Snapshot {
    World world;
    Observation observation;
    RuntimeScheduler scheduler;
    CharacterState state;
    std::mt19937 rng;
};

Snapshot snapshot(const World& world,const Observation& observation,
                  const RuntimeScheduler& scheduler,const CharacterState& state,
                  const ContinuousRuntime& runtime) {
    return {world,observation,scheduler,state,runtime.policy_rng_state()};
}

double js_divergence(const DecisionContext& a,const DecisionContext& b) {
    std::map<ActionType,double> left,right;
    for (const auto& item:a.candidates) left[item.action]=item.probability;
    for (const auto& item:b.candidates) right[item.action]=item.probability;
    double result=0.0;
    for (const auto& [action,p]:left) {
        const double q=right[action], m=(p+q)/2.0;
        if (p>0.0) result+=0.5*p*std::log(p/m);
        if (q>0.0) result+=0.5*q*std::log(q/m);
    }
    return result;
}

ActionType top_action(const DecisionContext& decision) {
    const auto it=std::max_element(decision.candidates.begin(),decision.candidates.end(),
        [](const CandidateAction& a,const CandidateAction& b){return a.probability<b.probability;});
    return it==decision.candidates.end()?ActionType::Idle:it->action;
}

void fork_history(std::ostream& out,const Snapshot& current,const Snapshot& previous,
                  int checkpoint_day,const Personality& personality,unsigned int scenario_seed,
                  unsigned int policy_seed,DemoLivingDynamicsV1& model) {
    const DecisionContext correct_policy=model.build_policy(current.observation,current.state,personality);
    const std::vector<std::pair<std::string,CharacterState>> branches={
        {"correct",current.state},{"reset",CharacterState{}},{"stale_24h",previous.state}};
    for (const auto& [branch,starting_state]:branches) {
        World world=current.world;
        Observation observation=current.observation;
        RuntimeScheduler scheduler=current.scheduler;
        CharacterState state=starting_state;
        ContinuousRuntime runtime(scheduler,world,observation,model,{},policy_seed);
        runtime.restore_policy_rng_state(current.rng);
        const DecisionContext counterfactual=model.build_policy(observation,state,personality);
        const double js=js_divergence(correct_policy,counterfactual);
        const bool top_changed=top_action(correct_policy)!=top_action(counterfactual);
        const int start=scheduler.now_total_minutes();
        for (const int horizon:{360,1440,4320})
            scheduler.schedule({"fork_window",start+horizon,false,std::nullopt,std::nullopt});
        Counts counts;
        std::vector<std::pair<int,std::string>> future_events;
        while (scheduler.now_total_minutes()<start+4320) {
            const RuntimeExecutionResult step=runtime.execute_next_boundary(state,personality);
            counts.include(step);
            for (const auto& event:step.runtime.world_events)
                future_events.emplace_back(event.occurred_at_total_minutes,event.id);
            const int elapsed=scheduler.now_total_minutes()-start;
            if (elapsed!=360 && elapsed!=1440 && elapsed!=4320) continue;
            out<<"{\"type\":\"fork\",\"profile_id\":";quote(out,personality.name);
            out<<",\"scenario_seed\":"<<scenario_seed<<",\"policy_seed\":"<<policy_seed
               <<",\"checkpoint_day\":"<<checkpoint_day<<",\"branch\":";quote(out,branch);
            out<<",\"horizon_minutes\":"<<elapsed<<",\"immediate_pi_js\":"<<js
               <<",\"immediate_top1_changed\":"<<(top_changed?"true":"false")<<',';
            counts_json(out,counts);
            out<<",\"future_world_events\":[";
            for (std::size_t i=0;i<future_events.size();++i) {
                if (i) out<<',';
                out<<'['<<future_events[i].first<<',';
                quote(out,future_events[i].second);
                out<<']';
            }
            out<<"],\"task_episode\":"<<world.life_tape_episode
               <<",\"task_effort\":"<<world.tasks.front().effort_done
               <<",\"state\":";state_json(out,state);out<<"}\n";
        }
    }
}

bool fork_day(int day,int total_days) {
    if (total_days>=180) return day==7 || day==30 || day==60 || day==120 || day==180;
    return day==7 || day==total_days;
}

void run(unsigned int scenario_seed,unsigned int policy_seed,int days,
         const Personality& personality,const std::filesystem::path& output,bool trace_boundaries) {
    if (days<1 || days>365) throw std::invalid_argument("days must be in [1,365]");
    std::filesystem::create_directories(output.parent_path());
    std::ofstream out(output);
    if (!out) throw std::runtime_error("cannot open long horizon output");
    out.precision(12);
    World world(scenario_seed);
    world.enable_life_tape();
    Observation observation=refresh_observation({},world,{});
    RuntimeScheduler scheduler(kStart);
    DemoLivingDynamicsV1 model;
    ContinuousRuntime runtime(scheduler,world,observation,model,{},policy_seed);
    CharacterState state;
    if (!runtime.submit_action_intent(ActionType::Idle,"",10).accepted)
        throw std::logic_error("initial idle intent rejected");
    for (int day=1;day<=days;++day)
        scheduler.schedule({"daily_checkpoint",kStart+day*kDay,false,std::nullopt,std::nullopt});
    out<<"{\"type\":\"run\",\"profile_id\":";quote(out,personality.name);
    out<<",\"personality\":";personality_json(out,personality);
    out<<",\"scenario_seed\":"<<scenario_seed<<",\"policy_seed\":"<<policy_seed
       <<",\"days\":"<<days<<",\"dynamics_model\":";quote(out,model.identity());
    out<<",\"life_tape_cycle_days\":3,\"initial_task_effort_target\":"
       <<world.tasks.front().effort_target<<",\"initial_task_deadline\":"
       <<world.tasks.front().due_at_total_minutes<<"}\n";
    Counts day_counts;
    std::optional<Snapshot> previous_day;
    const int end=kStart+days*kDay;
    while (scheduler.now_total_minutes()<end) {
        const RuntimeExecutionResult step=runtime.execute_next_boundary(state,personality);
        day_counts.include(step);
        if (trace_boundaries) {
            out<<"{\"type\":\"boundary\",\"profile_id\":";quote(out,personality.name);
            out<<",\"scenario_seed\":"<<scenario_seed
               <<",\"timestamp\":"<<scheduler.now_total_minutes()
               <<",\"elapsed_minutes\":"<<step.runtime.boundary.elapsed_minutes
               <<",\"running_action_before\":";
            if (step.running_action_before) quote(out,to_string(step.running_action_before->action));
            else out<<"null";
            out<<",\"selected_action\":";
            if (step.selected_action) quote(out,to_string(*step.selected_action));
            else out<<"null";
            out<<",\"selected_target\":";quote(out,step.selected_target_object_id);
            out<<",\"world_light_on\":"<<(world.current_room().light_on?"true":"false");
            out<<",\"runtime_rejections\":[";
            bool first_rejection=true;
            for (const auto& event:step.runtime.boundary.events) {
                if (!event.rejection) continue;
                if (!first_rejection) out<<',';
                first_rejection=false;
                out<<event.rejection->failure_reason;
            }
            out<<']';
            out<<",\"world_events\":[";
            for (std::size_t i=0;i<step.runtime.world_events.size();++i) {
                if (i) out<<',';
                quote(out,step.runtime.world_events[i].id);
            }
            out<<"],\"task_episode\":"<<world.life_tape_episode
               <<",\"task_effort\":"<<world.tasks.front().effort_done
               <<",\"observed_task_status\":";
            if (const ObservationFact* fact=find_fact(observation,"task.coursework.status")) quote(out,fact->value);
            else out<<"null";
            out<<",\"observed_room_light\":";
            if (const ObservationFact* fact=find_fact(observation,"room.light")) quote(out,fact->value);
            else out<<"null";
            double study_probability=0.0;
            for (const CandidateAction& item:step.decision.candidates)
                if (item.action==ActionType::StudyFocused || item.action==ActionType::StudyHalfhearted
                    || item.action==ActionType::StudyAtComputer) study_probability+=item.probability;
            out<<",\"policy_evaluated\":"<<(step.policy_evaluated?"true":"false")
               <<",\"study_probability\":"<<study_probability
               <<",\"gate_reasons\":[";
            for (std::size_t i=0;i<step.runtime.boundary.decision_gate.reasons.size();++i) {
                if (i) out<<',';
                quote(out,to_string(step.runtime.boundary.decision_gate.reasons[i]));
            }
            out<<"],\"replacement_validation_performed\":"
               <<(step.replacement_validation_performed?"true":"false")
               <<",\"replacement_validation_accepted\":"
               <<(step.replacement_validation_accepted?"true":"false")
               <<",\"task_completed\":"
               <<(step.pre_policy_outcome && step.pre_policy_outcome->task_completed ? "true":"false")
               <<",\"state\":";state_json(out,state);out<<"}\n";
        }
        const int now=scheduler.now_total_minutes();
        if (now<kStart+kDay || (now-kStart)%kDay!=0) continue;
        const int day=(now-kStart)/kDay;
        out<<"{\"type\":\"daily\",\"profile_id\":";quote(out,personality.name);
        out<<",\"scenario_seed\":"<<scenario_seed<<",\"policy_seed\":"<<policy_seed
           <<",\"day\":"<<day<<',';
        counts_json(out,day_counts);
        out<<",\"task_episode\":"<<world.life_tape_episode
           <<",\"task_effort\":"<<world.tasks.front().effort_done
           <<",\"task_effort_target\":"<<world.tasks.front().effort_target
           <<",\"state\":";state_json(out,state);out<<"}\n";
        const Snapshot current=snapshot(world,observation,scheduler,state,runtime);
        if (fork_day(day,days) && previous_day)
            fork_history(out,current,*previous_day,day,personality,scenario_seed,policy_seed,model);
        previous_day=current;
        day_counts={};
    }
}
} // namespace

int main(int argc,char** argv) {
    if (argc!=7 && argc!=9) return 2;
    try {
        const unsigned scenario_seed=static_cast<unsigned>(std::stoul(argv[1]));
        const unsigned policy_seed=static_cast<unsigned>(std::stoul(argv[2]));
        const int days=std::stoi(argv[3]);
        Personality personality=DemoPersonalityProfiles::named(argv[4]);
        const std::filesystem::path output=argv[5];
        const bool trace_boundaries=std::string(argv[6])=="boundaries";
        if (argc==9) DemoPersonalityProfiles::set_axis(personality,argv[7],std::stod(argv[8]));
        run(scenario_seed,policy_seed,days,personality,output,trace_boundaries);
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<"long_horizon: "<<error.what()<<'\n';
        return 1;
    }
}
