#include "local_model_policy_v0.h"
#include "laya_semantic_client_v0.h"
#include "runtime_scheduler.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstring>
#include <map>
#include <sstream>
#include <stdexcept>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "Ws2_32.lib")
using Socket = SOCKET;
constexpr Socket kInvalidSocket = INVALID_SOCKET;
static void close_socket(Socket socket) { closesocket(socket); }
struct WinsockScope {
    WinsockScope() { WSADATA data{}; if (WSAStartup(MAKEWORD(2, 2), &data) != 0) throw std::runtime_error("Laya socket initialization failed"); }
    ~WinsockScope() { WSACleanup(); }
};
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using Socket = int;
constexpr Socket kInvalidSocket = -1;
static void close_socket(Socket socket) { close(socket); }
#endif

namespace {
std::string quote(const std::string& text) {
    std::string result="\"";
    for (const char c:text) {
        if (c=='\"' || c=='\\') result+='\\';
        if (c=='\n') result+="\\n";
        else result+=c;
    }
    return result+'\"';
}

std::string json_field(const std::string& payload,const std::string& key) {
    const std::string marker="\""+key+"\"";
    std::size_t position=payload.find(marker);
    if (position==std::string::npos) return {};
    position=payload.find(':',position+marker.size());
    if (position==std::string::npos) return {};
    position=payload.find('"',position+1);
    if (position==std::string::npos) return {};
    const std::size_t end=payload.find('"',position+1);
    return end==std::string::npos ? std::string{} : payload.substr(position+1,end-position-1);
}

ActionType parse_action(const std::string& name) {
    for (int index=0;index<static_cast<int>(ActionType::Count);++index) {
        const ActionType candidate=static_cast<ActionType>(index);
        if (to_string(candidate)==name) return candidate;
    }
    throw std::runtime_error("Laya returned an unknown action: "+name);
}

bool eligible(const DecisionContext& decision,ActionType action) {
    return std::any_of(decision.candidates.begin(),decision.candidates.end(),[action](const CandidateAction& item) {
        return item.action==action && item.probability>0.0 && item.eligible;
    });
}

std::string request_json(unsigned long long request_id,const DecisionContext& decision,
                         const Observation& observation,const CharacterState& state,
                         const Personality& personality) {
    std::ostringstream out;
    out.precision(12);
    out<<"{\"request_id\":"<<request_id<<",\"timestamp\":";
    if (const ObservationFact* clock=find_fact(observation,"clock.total_minutes")) out<<clock->value;
    else out<<"null";
    out<<",\"profile\":"<<quote(personality.name)<<",\"personality\":{";
    out<<"\"procrastination\":"<<personality.procrastination<<",\"self_control\":"<<personality.self_control
       <<",\"rest_preference\":"<<personality.rest_preference<<",\"stimulation_seeking\":"<<personality.stimulation_seeking
       <<",\"task_anxiety_sensitivity\":"<<personality.task_anxiety_sensitivity<<",\"screen_strain_sensitivity\":"<<personality.screen_strain_sensitivity
       <<",\"need_response\":"<<personality.need_response<<",\"action_noise\":"<<personality.action_noise<<"}";
    out<<",\"state\":{\"boredom\":"<<state.boredom<<",\"fatigue\":"<<state.fatigue
       <<",\"task_pressure\":"<<state.task_pressure<<",\"satisfaction\":"<<state.satisfaction
       <<",\"hunger\":"<<state.hunger<<",\"bathroom_urge\":"<<state.bathroom_urge
       <<",\"anxiety\":"<<state.anxiety<<",\"screen_strain\":"<<state.screen_strain
       <<",\"commitment\":"<<quote(state.commitment.status==CommitmentStatus::Active?"active":state.commitment.status==CommitmentStatus::Suspended?"suspended":"none")
       <<",\"commitment_task_id\":"<<quote(state.commitment.task_id)
       <<",\"commitment_reason\":"<<quote(state.commitment.reason)
       <<",\"commitment_suspended_decision_points\":"<<state.commitment.suspended_decision_points<<"}";
    out<<",\"observation\":[";
    bool first=true;
    for (const ObservationFact& fact:observation.facts) {
        if (fact.status!=KnowledgeStatus::Known && fact.status!=KnowledgeStatus::Stale) continue;
        if (!first) out<<',';
        first=false;
        out<<"{\"key\":"<<quote(fact.key)<<",\"value\":"<<quote(fact.value)
           <<",\"status\":"<<quote(fact.status==KnowledgeStatus::Known?"known":"stale")<<"}";
    }
    out<<"],\"candidates\":[";
    first=true;
    for (const CandidateAction& candidate:decision.candidates) {
        if (!candidate.eligible || candidate.probability<=0.0) continue;
        if (!first) out<<',';
        first=false;
        out<<"{\"action\":"<<quote(to_string(candidate.action))<<",\"target\":"<<quote(candidate.target_object_id)
           <<",\"reason\":"<<quote(candidate.reason)<<"}";
    }
    out<<"]}";
    return out.str();
}

std::string soft_gate_request_json(unsigned long long request_id,
                                   const Observation& observation,const CharacterState& state,
                                   const Personality& personality,const RunningAction& action) {
    const DecisionContext no_candidates;
    std::string payload=request_json(request_id,no_candidates,observation,state,personality);
    payload.pop_back();
    payload+=",\"operation\":\"soft_reconsideration\",\"running_action\":{\"action\":";
    payload+=quote(to_string(action.action));
    payload+=",\"target\":"+quote(action.target_object_id);
    payload+=",\"elapsed_minutes\":"+std::to_string(action.elapsed_minutes);
    payload+=",\"planned_minutes\":"+std::to_string(action.planned_duration_minutes)+"}}";
    return payload;
}

std::string semantic_request_json(unsigned long long request_id,const char* operation,
                                  const Observation& observation,const CharacterState& state,
                                  const Personality& personality,
                                  const std::vector<std::string>& options={}) {
    const DecisionContext no_candidates;
    std::string payload=request_json(request_id,no_candidates,observation,state,personality);
    payload.pop_back();
    payload+=",\"operation\":"+quote(operation)+",\"observation_deltas\":[";
    bool first=true;
    for (const ObservationFact& fact:observation.updates_this_refresh) {
        if (fact.status!=KnowledgeStatus::Known && fact.status!=KnowledgeStatus::Stale) continue;
        if (!first) payload+=',';
        first=false;
        payload+="{\"key\":"+quote(fact.key)+",\"value\":"+quote(fact.value)
            +",\"status\":"+quote(fact.status==KnowledgeStatus::Known?"known":"stale")+'}';
    }
    payload+="],\"last_self_action\":{\"has_action\":";
    payload+=observation.last_self_action.has_action?"true":"false";
    payload+=",\"action\":"+quote(to_string(observation.last_self_action.action));
    payload+=",\"accepted\":";
    payload+=observation.last_self_action.accepted?"true":"false";
    payload+=",\"task_id\":"+quote(observation.last_self_action.task_id);
    payload+=",\"task_completed\":";
    payload+=observation.last_self_action.task_completed?"true":"false";
    payload+=",\"outcome_reason\":"+quote(observation.last_self_action.outcome_reason)+"}";
    payload+=",\"options\":[";
    for (std::size_t i=0;i<options.size();++i) {
        if (i) payload+=',';
        payload+=quote(options[i]);
    }
    payload+="]}";
    return payload;
}

std::map<std::string,double> parse_named_numbers(const std::string& encoded,
                                                  const std::vector<std::string>& expected,
                                                  double max_value) {
    std::map<std::string,double> values;
    std::istringstream entries(encoded);
    std::string entry;
    while (std::getline(entries,entry,',')) {
        const auto separator=entry.find('=');
        if (separator==std::string::npos || entry.find('=',separator+1)!=std::string::npos)
            throw std::runtime_error("Laya returned malformed typed values");
        const std::string name=entry.substr(0,separator);
        if (std::find(expected.begin(),expected.end(),name)==expected.end() || values.count(name))
            throw std::runtime_error("Laya returned an unexpected or duplicate typed value");
        std::size_t consumed=0;
        double value=0.0;
        const std::string number=entry.substr(separator+1);
        try { value=std::stod(number,&consumed); }
        catch (const std::exception&) { throw std::runtime_error("Laya returned nonnumeric typed value"); }
        if (consumed!=number.size() || !std::isfinite(value) || value<0.0 || value>max_value)
            throw std::runtime_error("Laya returned invalid typed value");
        values.emplace(name,value);
    }
    if (values.size()!=expected.size()) throw std::runtime_error("Laya omitted a typed value");
    return values;
}

std::string laya_exchange(int port,const std::string& request) {
#ifdef _WIN32
    WinsockScope winsock;
#endif
    Socket socket=::socket(AF_INET,SOCK_STREAM,0);
    if (socket==kInvalidSocket) throw std::runtime_error("cannot open Laya loopback socket");
    sockaddr_in address{};
    address.sin_family=AF_INET;
    address.sin_port=htons(static_cast<unsigned short>(port));
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if (::connect(socket,reinterpret_cast<sockaddr*>(&address),sizeof(address))!=0) {
        close_socket(socket);
        throw std::runtime_error("cannot reach Laya policy proxy on 127.0.0.1:"+std::to_string(port));
    }
    const std::string line=request+"\n";
    std::size_t sent=0;
    while (sent<line.size()) {
        const int written=::send(socket,line.data()+sent,static_cast<int>(line.size()-sent),0);
        if (written<=0) { close_socket(socket); throw std::runtime_error("Laya policy request write failed"); }
        sent+=static_cast<std::size_t>(written);
    }
    std::array<char,4096> buffer{};
    std::string response;
    while (response.find('\n')==std::string::npos) {
        const int read=::recv(socket,buffer.data(),static_cast<int>(buffer.size()),0);
        if (read<=0) { close_socket(socket); throw std::runtime_error("Laya policy response missing"); }
        response.append(buffer.data(),static_cast<std::size_t>(read));
        if (response.size()>65536) { close_socket(socket); throw std::runtime_error("Laya policy response too large"); }
    }
    close_socket(socket);
    return response.substr(0,response.find('\n'));
}

std::map<ActionType,double> parse_typed_weights(const std::string& encoded,
                                                const DecisionContext& decision) {
    if (encoded.empty()) throw std::runtime_error("Laya returned no typed probabilities");
    std::map<ActionType,double> weights;
    std::istringstream entries(encoded);
    std::string entry;
    double sum=0.0;
    while (std::getline(entries,entry,',')) {
        const std::size_t separator=entry.find('=');
        if (separator==std::string::npos || entry.find('=',separator+1)!=std::string::npos)
            throw std::runtime_error("Laya returned malformed typed probabilities");
        const ActionType action=parse_action(entry.substr(0,separator));
        if (!eligible(decision,action) || weights.count(action))
            throw std::runtime_error("Laya returned duplicate or ineligible probability");
        const std::string encoded_number=entry.substr(separator+1);
        std::size_t consumed=0;
        double weight=0.0;
        try { weight=std::stod(encoded_number,&consumed); }
        catch (const std::exception&) { throw std::runtime_error("Laya returned nonnumeric probability"); }
        if (consumed!=encoded_number.size() || !std::isfinite(weight) || weight<0.0 || weight>1.0)
            throw std::runtime_error("Laya returned invalid probability");
        weights.emplace(action,weight);
        sum+=weight;
    }
    std::size_t expected=0;
    for (const CandidateAction& candidate:decision.candidates)
        if (candidate.eligible && candidate.probability>0.0) ++expected;
    if (weights.size()!=expected || !std::isfinite(sum) || sum<0.5 || sum>1.5)
        throw std::runtime_error("Laya probabilities do not cover eligible A^O");
    for (auto& [action,weight]:weights) weight/=sum;
    return weights;
}
} // namespace

PolicySelection QwenSocketPolicyV0::select(const DecisionContext& decision,const Observation& observation,
                                            const CharacterState& state,const Personality& personality,std::mt19937&) {
    const std::string response=laya_exchange(port_,request_json(++request_index_,decision,observation,state,personality));
    const std::string error=json_field(response,"error");
    if (!error.empty()) throw std::runtime_error("Laya policy proxy rejected request: "+error);
    const ActionType action=parse_action(json_field(response,"action"));
    if (!eligible(decision,action)) throw std::runtime_error("Laya chose an action outside eligible A^O: "+to_string(action));
    return {action,identity(),"qwen-proxy request="+std::to_string(request_index_)+" hash="+json_field(response,"request_hash"),{}};
}

PolicySelection LayaTypedPolicyV0::select(const DecisionContext& decision,const Observation& observation,
                                         const CharacterState& state,const Personality& personality,
                                         std::mt19937& rng) {
    const std::string response=laya_exchange(port_,request_json(++request_index_,decision,observation,state,personality));
    const std::string error=json_field(response,"error");
    if (!error.empty()) throw std::runtime_error("Laya typed proxy rejected request: "+error);
    if (json_field(response,"model")!="convaiinnovations/laya-typed-decisions")
        throw std::runtime_error("Laya typed proxy returned an unexpected checkpoint");
    const auto weights=parse_typed_weights(json_field(response,"weights"),decision);
    DecisionContext sampled=decision;
    for (CandidateAction& candidate:sampled.candidates)
        candidate.probability=weights.count(candidate.action) ? weights.at(candidate.action) : 0.0;
    const ActionType action=sample_action(sampled,rng);
    PolicySelection selection{action,identity(),
        "laya-typed-decisions request="+std::to_string(request_index_)+" hash="+json_field(response,"request_hash"),{}};
    for (const CandidateAction& candidate:sampled.candidates)
        if (candidate.eligible && weights.count(candidate.action))
            selection.probabilities.emplace_back(candidate.action,candidate.probability);
    return selection;
}

std::optional<SoftReconsideration> LayaTypedPolicyV0::soft_reconsider(
    const Observation& observation,const CharacterState& state,const Personality& personality,
    const RunningAction& action,std::mt19937& rng) {
    if (!soft_gate_enabled_) return std::nullopt;
    const std::string response=laya_exchange(port_,soft_gate_request_json(
        ++request_index_,observation,state,personality,action));
    const std::string error=json_field(response,"error");
    if (!error.empty()) throw std::runtime_error("Laya soft gate proxy rejected request: "+error);
    if (json_field(response,"model")!="convaiinnovations/laya-typed-decisions")
        throw std::runtime_error("Laya soft gate returned an unexpected checkpoint");
    const std::string encoded=json_field(response,"probability");
    std::size_t consumed=0;
    double probability=0.0;
    try { probability=std::stod(encoded,&consumed); }
    catch (const std::exception&) { throw std::runtime_error("Laya soft gate returned nonnumeric probability"); }
    if (consumed!=encoded.size() || !std::isfinite(probability) || probability<0.0 || probability>1.0)
        throw std::runtime_error("Laya soft gate returned invalid probability");
    const bool requested=std::bernoulli_distribution(probability)(rng);
    return SoftReconsideration{probability,requested,
        "laya-noul request="+std::to_string(request_index_)+" hash="+json_field(response,"request_hash")};
}

LayaTypedChoice LayaSemanticClientV0::choose_commitment(
    const Observation& observation,const CharacterState& state,const Personality& personality,
    const std::vector<std::string>& options,std::mt19937& rng) const {
    if (options.size()<2 || options.size()>4) throw std::invalid_argument("invalid commitment choice surface");
    const std::string response=laya_exchange(port_,semantic_request_json(
        ++request_index_,"commitment_choice",observation,state,personality,options));
    const std::string error=json_field(response,"error");
    if (!error.empty()) throw std::runtime_error("Laya commitment proxy rejected request: "+error);
    if (json_field(response,"model")!="convaiinnovations/laya-typed-decisions")
        throw std::runtime_error("unexpected Laya commitment checkpoint");
    auto probabilities=parse_named_numbers(json_field(response,"weights"),options,1.0);
    double sum=0.0;
    for (const auto& [_,value]:probabilities) sum+=value;
    if (sum<0.5 || sum>1.5) throw std::runtime_error("Laya commitment choice is not a distribution");
    std::vector<double> weights;
    for (const std::string& option:options) weights.push_back(probabilities.at(option)/sum);
    const std::string selected=options[std::discrete_distribution<std::size_t>(
        weights.begin(),weights.end())(rng)];
    LayaTypedChoice result{selected,{},"laya-choice request="+std::to_string(request_index_)
        +" hash="+json_field(response,"request_hash")};
    for (const std::string& option:options) result.probabilities.emplace_back(option,probabilities.at(option)/sum);
    return result;
}

LayaTypedScores LayaSemanticClientV0::score_appraisal(
    const Observation& observation,const CharacterState& state,const Personality& personality) const {
    static const std::vector<std::string> keys={"goal_progress","goal_obstruction","stimulation",
        "uncertainty","positive_outcome","negative_outcome","control_restored"};
    const std::string response=laya_exchange(port_,semantic_request_json(
        ++request_index_,"appraisal_scores",observation,state,personality));
    const std::string error=json_field(response,"error");
    if (!error.empty()) throw std::runtime_error("Laya appraisal proxy rejected request: "+error);
    if (json_field(response,"model")!="convaiinnovations/laya-typed-decisions")
        throw std::runtime_error("unexpected Laya appraisal checkpoint");
    return {parse_named_numbers(json_field(response,"scores"),keys,4.0),
        "laya-score request="+std::to_string(request_index_)+" hash="+json_field(response,"request_hash")};
}
