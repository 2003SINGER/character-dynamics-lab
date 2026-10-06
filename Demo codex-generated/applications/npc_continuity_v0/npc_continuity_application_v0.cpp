#include "npc_continuity_application_v0.h"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <stdexcept>

StateUpdate NpcContinuityApplicationModelV0::advance_continuous(
    CharacterState& s, const Observation& o, const Personality& p,
    const RunningAction* action, int minutes) const {
    return reference_.advance_continuous(s, o, p, action, minutes);
}

Appraisal NpcContinuityApplicationModelV0::appraise(
    const Observation& o, const CharacterState& s, const Personality& p) const {
    return reference_.appraise(o, s, p);
}

StateUpdate NpcContinuityApplicationModelV0::apply_impulse(
    CharacterState& s, const Appraisal& a, const Personality& p) const {
    return reference_.apply_impulse(s, a, p);
}

void NpcContinuityApplicationModelV0::update_persistent_intention(
    CharacterState& s, const Observation& o, int t) const {
    reference_.update_persistent_intention(s, o, t);
}

DecisionContext NpcContinuityApplicationModelV0::build_policy(
    const Observation& o, const CharacterState&, const Personality&) const {
    DecisionContext decision;
    Observation current_o = o;
    rebuild_known_actions_from_observation(current_o);
    decision.known_actions = current_o.known_actions;
    for (ActionType action : current_o.known_actions) {
        CandidateAction candidate;
        candidate.action = action;
        const auto binding = std::find_if(current_o.action_target_bindings.begin(), current_o.action_target_bindings.end(),
            [action](const ActionTargetBinding& item) { return item.action == action; });
        if (binding != current_o.action_target_bindings.end()) candidate.target_object_id = binding->target_object_id;

        // A^O is the shared admissibility boundary. A known unsatisfied O-side
        // constraint removes an option; hidden W facts never enter this check.
        candidate.hard_admissible = std::none_of(current_o.action_constraints.begin(), current_o.action_constraints.end(),
            [action, &candidate](const ActionConstraintBelief& belief) {
                return belief.action == action && belief.target_object_id == candidate.target_object_id
                    && !belief.satisfied;
            });
        candidate.eligible = candidate.hard_admissible;
        candidate.rule_soft_eligible = false;
        candidate.probability = candidate.hard_admissible ? 1.0 : 0.0;
        candidate.reason = "shared O-known hard candidate; no utility score";
        decision.candidates.push_back(std::move(candidate));
    }
    const auto admissible_count = std::count_if(decision.candidates.begin(), decision.candidates.end(),
        [](const CandidateAction& candidate) { return candidate.hard_admissible; });
    const double uniform_placeholder = admissible_count == 0 ? 0.0 : 1.0 / admissible_count;
    for (CandidateAction& candidate : decision.candidates)
        candidate.probability = candidate.hard_admissible ? uniform_placeholder : 0.0;
    return decision;
}

DynamicsReconsideration NpcContinuityApplicationModelV0::reconsider_running_action(
    const Observation& o, const CharacterState&, const CharacterState&,
    const RunningAction& running, const Personality&) const {
    if (running.status != RunningActionStatus::Running) return {};
    const bool visible_alarm_delta = std::any_of(o.updates_this_refresh.begin(), o.updates_this_refresh.end(),
        [](const ObservationFact& fact) {
            return fact.key == "room.alarm" && fact.value == "ringing"
                && fact.status == KnowledgeStatus::Known;
        });
    if (visible_alarm_delta) return {true, "new actor-visible room.alarm delta"};
    return {};
}

double UtilityPolicyV0::score(const CandidateAction& c, const Observation& o,
                              const ActorHistory& history, const RunningAction* running) const {
    if (!c.hard_admissible) return -1.0;
    double value = 0.05; // common neutral floor; not inherited from Demo scores

    if (c.action == ActionType::StudyFocused || c.action == ActionType::StudyHalfhearted
        || c.action == ActionType::StudyAtComputer) {
        if (!has_known_fact(o, "task.coursework.status", "active")) return -1.0;
        double done = 0.0, target = 0.0;
        if (known_double(o, "task.coursework.effort", done)
            && known_double(o, "task.coursework.effort_target", target) && target > 0.0) {
            value += 0.60 * std::clamp(1.0 - done / target, 0.0, 1.0);
        } else {
            value += 0.60; // an active known task with no progress reading
        }
    }

    if (c.action == ActionType::TurnOffAlarm && has_known_fact(o, "room.alarm", "ringing")) {
        value += 0.90;
    }

    // Graham (2013), §9.7: favor the current action to reduce oscillation.
    // A recently interrupted accepted action retains a smaller goal inertia.
    if (running && running->status == RunningActionStatus::Running && running->action == c.action) {
        value += running_action_inertia_;
    }
    if (!history.episodes.empty()) {
        const ActorEpisode& last = history.episodes.back();
        if (last.accepted && last.action == c.action) value += recent_action_inertia_;
    }
    return value;
}

PolicySelection UtilityPolicyV0::select(const DecisionContext& decision, const Observation& observation,
                                       const CharacterState&, const Personality&, std::mt19937& rng) {
    static const ActorHistory empty;
    return select_with_history(decision, observation, CharacterState{}, Personality{}, empty, nullptr, rng);
}

PolicySelection UtilityPolicyV0::select_with_history(const DecisionContext& decision,
    const Observation& observation, const CharacterState&, const Personality&,
    const ActorHistory& history, const RunningAction* running, std::mt19937&) {
    const CandidateAction* best = nullptr;
    double best_score = -1.0;
    std::ostringstream provenance;
    provenance << "argmax_utility_v0 scores=[";
    bool first = true;
    for (const CandidateAction& c : decision.candidates) {
        const double candidate_score = score(c, observation, history, running);
        if (!first) provenance << ';';
        first = false;
        provenance << to_string(c.action) << ':' << c.target_object_id << '=' << candidate_score;
        if (candidate_score > best_score) {
            best = &c;
            best_score = candidate_score;
        }
    }
    if (!best || best_score < 0.0) throw std::logic_error("utility policy has no hard-admissible candidate");
    provenance << "] selected=" << to_string(best->action) << " score=" << best_score;
    return {best->action, identity(), provenance.str(),
            {{best->action, 1.0}}};
}

bool contains_candidate(const DecisionContext& decision, ActionType action, bool require_hard) {
    return std::any_of(decision.candidates.begin(), decision.candidates.end(),
        [action, require_hard](const CandidateAction& candidate) {
            return candidate.action == action && (!require_hard || candidate.hard_admissible);
        });
}

std::string candidate_signature(const DecisionContext& decision) {
    std::ostringstream out;
    bool first = true;
    for (const CandidateAction& candidate : decision.candidates) {
        if (!first) out << ',';
        first = false;
        out << to_string(candidate.action) << ':' << candidate.target_object_id << ':'
            << (candidate.hard_admissible ? '1' : '0');
    }
    return out.str();
}
