#include "laya_policy_v0.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cstring>
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
       <<",\"commitment\":"<<quote(state.commitment.status==CommitmentStatus::Active?"active":state.commitment.status==CommitmentStatus::Suspended?"suspended":"none")<<"}";
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
} // namespace

PolicySelection LayaSocketPolicyV0::select(const DecisionContext& decision,const Observation& observation,
                                            const CharacterState& state,const Personality& personality,std::mt19937&) {
    const std::string response=laya_exchange(port_,request_json(++request_index_,decision,observation,state,personality));
    const std::string error=json_field(response,"error");
    if (!error.empty()) throw std::runtime_error("Laya policy proxy rejected request: "+error);
    const ActionType action=parse_action(json_field(response,"action"));
    if (!eligible(decision,action)) throw std::runtime_error("Laya chose an action outside eligible A^O: "+to_string(action));
    return {action,identity(),"laya-proxy request="+std::to_string(request_index_)+" hash="+json_field(response,"request_hash")};
}
