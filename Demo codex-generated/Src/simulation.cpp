#include "simulation.h"

#include "appraisal.h"
#include "decision.h"
#include "observation.h"
#include "state.h"
#include "world.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <ostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace {
#ifndef CHARACTER_DYNAMICS_GIT_REVISION
#define CHARACTER_DYNAMICS_GIT_REVISION "unknown"
#endif

constexpr int kStepsPerRun = 12;
constexpr int kBatchPersonalityCount = 32;
constexpr int kBatchScenarioSeedCount = 8;
constexpr int kBatchStepsPerRun = 256;
constexpr unsigned int kBatchPersonalitySeed = 20260904U;
constexpr const char* kBatchConfigVersion = "task-commitment-v0";

Personality procrastinating_profile() {
    return {"procrastinating / low self-control", 0.85, 0.20, 0.55, 0.75, 0.70, 0.45, 0.55, 0.70};
}

Personality self_controlled_profile() {
    return {"self-controlled / task-oriented", 0.20, 0.85, 0.45, 0.35, 0.45, 0.60, 0.65, 0.35};
}

std::string personality_summary(const Personality& personality) {
    std::ostringstream output;
    output << "P{name=" << personality.name
           << ", procrastination=" << std::fixed << std::setprecision(2) << personality.procrastination
           << ", self_control=" << personality.self_control
           << ", rest_preference=" << personality.rest_preference
           << ", stimulation_seeking=" << personality.stimulation_seeking
           << ", task_anxiety_sensitivity=" << personality.task_anxiety_sensitivity
           << ", screen_strain_sensitivity=" << personality.screen_strain_sensitivity
           << ", need_response=" << personality.need_response
           << ", action_noise=" << personality.action_noise << '}';
    return output.str();
}

std::string action_space_summary(const std::vector<ActionType>& world_actions) {
    std::ostringstream output;
    output << "A^W=";
    for (ActionType action : world_actions) {
        output << to_string(action) << ' ';
    }
    return output.str();
}

constexpr std::size_t kActionCount = static_cast<std::size_t>(ActionType::Count);
using ActionProbabilityVector = std::array<double, kActionCount>;
using ActionSupportVector = std::array<unsigned char, kActionCount>;

ActionSupportVector support_by_action(const DecisionContext& decision) {
    ActionSupportVector support{};
    for (ActionType action : decision.known_actions) {
        if (action == ActionType::Count) {
            throw std::logic_error("A^O cannot contain ActionType::Count");
        }
        support.at(static_cast<std::size_t>(action)) = 1U;
    }
    return support;
}

ActionProbabilityVector probability_by_action(const DecisionContext& decision) {
    ActionProbabilityVector probabilities{};
    for (const CandidateAction& candidate : decision.candidates) {
        probabilities.at(static_cast<std::size_t>(candidate.action)) = candidate.probability;
    }
    return probabilities;
}

void write_action_probability_columns(std::ostream& output, const DecisionContext& decision) {
    const ActionProbabilityVector probabilities = probability_by_action(decision);
    for (double probability : probabilities) {
        output << ',' << probability;
    }
}

void write_action_support_columns(std::ostream& output, const DecisionContext& decision) {
    const ActionSupportVector support = support_by_action(decision);
    for (unsigned char known : support) {
        output << ',' << static_cast<int>(known);
    }
}

void write_csv_field(std::ostream& output, const std::string& value) {
    output << '"';
    for (char character : value) {
        if (character == '"') output << '"';
        output << character;
    }
    output << '"';
}

std::filesystem::path create_batch_run_directory(const std::string& requested_root) {
    namespace fs = std::filesystem;
    const fs::path base(requested_root);
    fs::create_directories(base);
    const auto timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    for (int suffix = 0; suffix < 1000; ++suffix) {
        const fs::path candidate = base / ("run_" + std::to_string(timestamp) + "_" + std::to_string(suffix));
        if (!fs::exists(candidate)) {
            fs::create_directory(candidate);
            return candidate;
        }
    }
    throw std::runtime_error("Could not allocate a non-overwriting batch run directory under: " + requested_root);
}

unsigned int action_seed_for(std::size_t personality_index, unsigned int world_seed) {
    return 0xCD000000U + static_cast<unsigned int>(personality_index * 1009U) + world_seed * 7919U;
}

const char* commitment_status_name(CommitmentStatus status) {
    switch (status) {
    case CommitmentStatus::None: return "none";
    case CommitmentStatus::Active: return "active";
    case CommitmentStatus::Suspended: return "suspended";
    }
    return "unknown";
}

const char* task_status_name(TaskStatus status) {
    switch (status) {
    case TaskStatus::Active: return "active";
    case TaskStatus::Completed: return "completed";
    }
    return "unknown";
}

TaskSnapshot coursework_snapshot(const World& world) {
    if (const WorldTask* task = world.task_by_id("coursework")) {
        return {task->effort_done, task->effort_target, task_status_name(task->status)};
    }
    return {};
}

struct DecisionSnapshot {
    Observation observation;
    Appraisal appraisal;
    StateUpdate state_update;
    CharacterState state_at_decision;
    DecisionContext decision;
};

DecisionSnapshot prepare_decision(World& world,
                                  CharacterState& state,
                                  Observation& observation,
                                  const WorldOutcome& previous_outcome,
                                  const Personality& personality,
                                  const InformationAccess& information_access = {}) {
    observation = refresh_observation(std::move(observation), world, previous_outcome, information_access);
    DecisionSnapshot snapshot;
    snapshot.observation = observation;
    snapshot.appraisal = appraise(observation, state, personality);
    clear_pending_appraisal_updates(observation);
    snapshot.state_update = update_state(state, snapshot.appraisal, personality, previous_outcome.elapsed_minutes);
    snapshot.state_at_decision = state;
    snapshot.decision = decide(observation, state, personality);
    return snapshot;
}

WorldOutcome settle_action(World& world,
                           CharacterState& state,
                           Observation& observation,
                           ActionType action,
                           const std::string& target_object_id,
                           const InformationAccess& information_access) {
    const WorldOutcome outcome = world.settle(action, target_object_id);
    apply_self_action_feedback(observation, outcome, world.time_summary(),
                               information_access.self_task_completion_observable);
    update_commitment(state, observation, total_minutes(world.time));
    return outcome;
}

StepRecord advance_one_decision(World& world,
                               CharacterState& state,
                               Observation& observation,
                               WorldOutcome& previous_outcome,
                               std::mt19937& action_rng,
                               const Personality& personality,
                               const InformationAccess& information_access = {}) {
    StepRecord trace;
    const DecisionSnapshot snapshot = prepare_decision(world, state, observation, previous_outcome,
                                                       personality, information_access);
    trace.observation_at_decision = snapshot.observation;
    trace.decision_time = world.time_summary();
    trace.world_before = world.summary();
    trace.appraisal = snapshot.appraisal;
    trace.state_update = snapshot.state_update;
    trace.state_at_decision = snapshot.state_at_decision;
    trace.task_before = coursework_snapshot(world);
    trace.decision = snapshot.decision;
    trace.chosen_action = sample_action(trace.decision, action_rng);
    std::string target_object_id;
    for (const CandidateAction& candidate : trace.decision.candidates) {
        if (candidate.action == trace.chosen_action) {
            target_object_id = candidate.target_object_id;
            break;
        }
    }
    trace.action_plan = world.expand_action(trace.chosen_action);
    trace.outcome = settle_action(world, state, observation, trace.chosen_action,
                                  target_object_id, information_access);
    trace.state_after_settlement = state;
    trace.task_after = coursework_snapshot(world);
    if (!trace.outcome.sleeping_sensory_events.empty()) {
        observation = apply_sleep_sensory_update(std::move(observation), trace.outcome, world);
        trace.sleep_observation_updates = observation_updates_summary(observation);
    }
    trace.world_after = world.summary();
    previous_outcome = trace.outcome;
    return trace;
}

const char* rejection_reason_name(RejectionReason reason) {
    switch (reason) {
    case RejectionReason::None: return "none";
    case RejectionReason::TargetAbsent: return "target_absent";
    case RejectionReason::TargetUnusable: return "target_unusable";
    case RejectionReason::PreconditionFailed: return "precondition_failed";
    case RejectionReason::ResourceInsufficient: return "resource_insufficient";
    }
    return "unknown";
}

double policy_distance(const DecisionContext& left, const DecisionContext& right) {
    double distance = 0.0;
    for (std::size_t index = 0; index < kActionCount; ++index) {
        const ActionType action = static_cast<ActionType>(index);
        const auto probability = [action](const DecisionContext& context) {
            for (const CandidateAction& candidate : context.candidates) {
                if (candidate.action == action) return candidate.probability;
            }
            return 0.0;
        };
        distance += std::abs(probability(left) - probability(right));
    }
    return distance / 2.0;
}

double state_distance(const CharacterState& left, const CharacterState& right) {
    const std::array<double, 9> a{left.boredom, left.fatigue, left.task_pressure,
        left.satisfaction, left.hunger, left.bathroom_urge, left.anxiety,
        left.screen_strain, left.purchase_urge};
    const std::array<double, 9> b{right.boredom, right.fatigue, right.task_pressure,
        right.satisfaction, right.hunger, right.bathroom_urge, right.anxiety,
        right.screen_strain, right.purchase_urge};
    double sum = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) sum += std::abs(a[i] - b[i]);
    return sum / static_cast<double>(a.size());
}

bool observation_equal(const Observation& left, const Observation& right) {
    return observation_summary(left) == observation_summary(right);
}
} // namespace

void Simulation::run_all(std::ostream& output) const {
    output << "Character Dynamics Reference\n"
           << "A deterministic, rule-based reading aid. It is not an LLM or a validated psychological model.\n\n";
    output << run_profile(procrastinating_profile(), 20260904U, 0U, true) << '\n';
    output << run_profile(self_controlled_profile(), 20260904U, 0U, true);
}

std::vector<Personality> Simulation::generate_personalities(std::size_t count, unsigned int seed) {
    std::mt19937 generator(seed);
    std::uniform_real_distribution<double> unit_interval(0.0, 1.0);
    std::vector<Personality> personalities;
    personalities.reserve(count);
    for (std::size_t index = 0; index < count; ++index) {
        std::ostringstream name;
        name << "generated_personality_" << std::setw(2) << std::setfill('0') << (index + 1);
        personalities.push_back({name.str(),
            unit_interval(generator),
            unit_interval(generator),
            unit_interval(generator),
            unit_interval(generator),
            unit_interval(generator),
            unit_interval(generator),
            unit_interval(generator),
            unit_interval(generator)});
    }
    return personalities;
}

void Simulation::run_batch(std::ostream& output, const std::string& output_directory) const {
    namespace fs = std::filesystem;
    const fs::path root = create_batch_run_directory(output_directory);
    std::ofstream profiles_file(root / "personalities.csv");
    std::ofstream trajectories_file(root / "trajectories.csv");
    std::ofstream runs_file(root / "runs.csv");
    std::ofstream metadata_file(root / "metadata.txt");
    if (!profiles_file || !trajectories_file || !runs_file || !metadata_file) {
        throw std::runtime_error("Cannot open batch output files under: " + output_directory);
    }

    const std::vector<Personality> personalities = generate_personalities(kBatchPersonalityCount, kBatchPersonalitySeed);
    metadata_file << "Character Dynamics Reference batch experiment\n"
                  << "run_directory=" << root.string() << '\n'
                  << "config_version=" << kBatchConfigVersion << '\n'
                  << "git_revision=" << CHARACTER_DYNAMICS_GIT_REVISION << '\n'
                  << "personality_generation=deterministic_uniform_[0,1]\n"
                  << "personality_generation_seed=" << kBatchPersonalitySeed << '\n'
                  << "personality_count=" << kBatchPersonalityCount << '\n'
                  << "world_scenario_seed_count=" << kBatchScenarioSeedCount << '\n'
                  << "steps_per_run=" << kBatchStepsPerRun << '\n'
                  << "total_decision_points=" << (kBatchPersonalityCount * kBatchScenarioSeedCount * kBatchStepsPerRun) << '\n'
                  << "task_model=single_world_task_with_continuous_effort\n"
                  << "task_effort_target=seeded_[7.2,9.2]_or_8.0_for_legacy_seed\n"
                  << "task_effort_settlement=base_effort_x_duration_x_interruption_x_seeded_variation_[0.90,1.10]\n"
                  << "world_events=per-day deterministic schedule generated from each scenario seed\n"
                  << "note=This is a synthetic rule-based stress run, not an LLM result or a psychological validation.\n";

    profiles_file << "personality_index,name,procrastination,self_control,rest_preference,stimulation_seeking,task_anxiety_sensitivity,screen_strain_sensitivity,need_response,action_noise\n";
    profiles_file << std::fixed << std::setprecision(6);
    for (std::size_t index = 0; index < personalities.size(); ++index) {
        const Personality& personality = personalities[index];
        profiles_file << (index + 1) << ',';
        write_csv_field(profiles_file, personality.name);
        profiles_file << ',' << personality.procrastination
                      << ',' << personality.self_control
                      << ',' << personality.rest_preference
                      << ',' << personality.stimulation_seeking
                      << ',' << personality.task_anxiety_sensitivity
                      << ',' << personality.screen_strain_sensitivity
                      << ',' << personality.need_response
                      << ',' << personality.action_noise << '\n';
    }

    trajectories_file << "personality_index,scenario_seed,action_seed,step,decision_time,pre_commitment_status,pre_commitment_task_id,pre_task_effort,pre_task_effort_target,pre_task_status,pre_boredom,pre_fatigue,pre_task_pressure,pre_satisfaction,pre_hunger,pre_bathroom_urge,pre_anxiety,pre_screen_strain,pre_purchase_urge,known_action_count";
    for (std::size_t index = 0; index < kActionCount; ++index) {
        trajectories_file << ",known_" << to_string(static_cast<ActionType>(index));
    }
    for (std::size_t index = 0; index < kActionCount; ++index) {
        trajectories_file << ",p_" << to_string(static_cast<ActionType>(index));
    }
    trajectories_file << ",chosen_action,accepted,elapsed_minutes,event_ids,outcome_task_id,outcome_task_effort_gained,outcome_task_settlement_variation,outcome_task_session_interrupted,post_commitment_status,post_commitment_task_id,post_task_effort,post_task_effort_target,post_task_status,post_wallet,post_unread_messages,post_weather,post_temperature_celsius\n";
    trajectories_file << std::fixed << std::setprecision(6);
    runs_file << "personality_index,scenario_seed,action_seed,steps,final_time,coursework_effort_done,coursework_effort_target,coursework_status,coursework_completed_at,coursework_execution_count,final_commitment_status,final_commitment_task_id,wallet,unread_messages,weather,temperature_celsius,phone_uses,computer_uses,study_sessions,rest_sessions,bathroom_visits,meals_collected,online_orders,final_boredom,final_fatigue,final_task_pressure,final_satisfaction,final_hunger,final_bathroom_urge,final_anxiety,final_screen_strain,final_purchase_urge\n";
    runs_file << std::fixed << std::setprecision(6);

    for (std::size_t personality_index = 0; personality_index < personalities.size(); ++personality_index) {
        const Personality& personality = personalities[personality_index];
        for (unsigned int scenario_seed = 1; scenario_seed <= kBatchScenarioSeedCount; ++scenario_seed) {
            const unsigned int action_seed = action_seed_for(personality_index, scenario_seed);
            const ScenarioConfig scenario{};
            World world(scenario_seed);
            CharacterState state;
            Observation observation;
            WorldOutcome previous_outcome;
            std::mt19937 action_rng(action_seed);

            for (int step = 1; step <= kBatchStepsPerRun; ++step) {
                const StepRecord trace = advance_one_decision(world, state, observation, previous_outcome,
                                                             action_rng, personality, scenario.information_access);
                std::ostringstream event_ids;
                for (std::size_t event_index = 0; event_index < trace.outcome.events.size(); ++event_index) {
                    if (event_index != 0) event_ids << '|';
                    event_ids << trace.outcome.events[event_index].id;
                }
                trajectories_file << (personality_index + 1)
                                  << ',' << scenario_seed
                                  << ',' << action_seed
                                  << ',' << step << ',';
                write_csv_field(trajectories_file, trace.decision_time);
                trajectories_file << ',' << commitment_status_name(trace.state_at_decision.commitment.status) << ',';
                write_csv_field(trajectories_file, trace.state_at_decision.commitment.task_id);
                trajectories_file << ',' << trace.task_before.effort
                                  << ',' << trace.task_before.target << ',' << trace.task_before.status
                                  << ',' << trace.state_at_decision.boredom
                                  << ',' << trace.state_at_decision.fatigue
                                  << ',' << trace.state_at_decision.task_pressure
                                  << ',' << trace.state_at_decision.satisfaction
                                  << ',' << trace.state_at_decision.hunger
                                  << ',' << trace.state_at_decision.bathroom_urge
                                  << ',' << trace.state_at_decision.anxiety
                                  << ',' << trace.state_at_decision.screen_strain
                                  << ',' << trace.state_at_decision.purchase_urge
                                  << ',' << trace.decision.known_actions.size();
                write_action_support_columns(trajectories_file, trace.decision);
                write_action_probability_columns(trajectories_file, trace.decision);
                trajectories_file << ',';
                write_csv_field(trajectories_file, to_string(trace.chosen_action));
                trajectories_file << ',' << (trace.outcome.accepted ? 1 : 0)
                                  << ',' << trace.outcome.elapsed_minutes << ',';
                write_csv_field(trajectories_file, event_ids.str());
                trajectories_file << ',';
                write_csv_field(trajectories_file, trace.outcome.task_id);
                trajectories_file << ',' << trace.outcome.task_effort_gained
                                  << ',' << trace.outcome.task_settlement_variation
                                  << ',' << (trace.outcome.task_session_interrupted ? 1 : 0)
                                  << ',' << commitment_status_name(trace.state_after_settlement.commitment.status) << ',';
                write_csv_field(trajectories_file, trace.state_after_settlement.commitment.task_id);
                trajectories_file << ',' << trace.task_after.effort
                                  << ',' << trace.task_after.target << ',' << trace.task_after.status
                                  << ',' << world.wallet
                                  << ',' << world.unread_messages << ',';
                write_csv_field(trajectories_file, world.weather);
                trajectories_file << ',' << world.current_room().temperature_celsius << '\n';
            }

            const WorldTask* coursework = world.task_by_id("coursework");
            runs_file << (personality_index + 1)
                      << ',' << scenario_seed
                      << ',' << action_seed
                      << ',' << kBatchStepsPerRun << ',';
            write_csv_field(runs_file, world.time_summary());
            runs_file << ',' << (coursework != nullptr ? coursework->effort_done : 0.0)
                      << ',' << (coursework != nullptr ? coursework->effort_target : 0.0)
                      << ',' << (coursework != nullptr ? task_status_name(coursework->status) : "unknown")
                      << ',' << (coursework != nullptr ? coursework->completed_at_total_minutes : -1)
                      << ',' << (coursework != nullptr ? coursework->execution_count : 0)
                      << ',' << commitment_status_name(state.commitment.status) << ',';
            write_csv_field(runs_file, state.commitment.task_id);
            runs_file << ',' << world.wallet
                      << ',' << world.unread_messages << ',';
            write_csv_field(runs_file, world.weather);
            runs_file << ',' << world.current_room().temperature_celsius
                      << ',' << world.phone_uses
                      << ',' << world.computer_uses
                      << ',' << world.study_sessions
                      << ',' << world.rest_sessions
                      << ',' << world.bathroom_visits
                      << ',' << world.meals_collected
                      << ',' << world.online_orders
                      << ',' << state.boredom
                      << ',' << state.fatigue
                      << ',' << state.task_pressure
                      << ',' << state.satisfaction
                      << ',' << state.hunger
                      << ',' << state.bathroom_urge
                      << ',' << state.anxiety
                      << ',' << state.screen_strain
                      << ',' << state.purchase_urge << '\n';
        }
    }

    output << "batch complete: " << kBatchPersonalityCount << " personalities x "
           << kBatchScenarioSeedCount << " scenario seeds x " << kBatchStepsPerRun
           << " decision points = " << (kBatchPersonalityCount * kBatchScenarioSeedCount * kBatchStepsPerRun)
           << " rows saved under " << root.string() << '\n';
}

void Simulation::run_paired_phone_intervention(std::ostream& output, const std::string& output_path) const {
    namespace fs = std::filesystem;
    const fs::path path(output_path);
    if (path.has_parent_path()) fs::create_directories(path.parent_path());
    std::ofstream file(path);
    if (!file) throw std::runtime_error("Cannot open paired intervention output: " + output_path);
    file << "scenario_seed,branch,step,decision_time,chosen_action,accepted,phone_world_present,phone_known,phone_fact_status,known_action_count,observation_summary,policy_distance,state_distance,observation_equal,phone_uses,target_object_id,failure_reason,discovery_event\n";
    file << std::fixed << std::setprecision(6);
    const Personality personality = procrastinating_profile();
    constexpr unsigned int action_seed_base = 20260904U;
    for (unsigned int scenario_seed = 1; scenario_seed <= 8; ++scenario_seed) {
        World control_world(scenario_seed), hidden_world(scenario_seed), visible_world(scenario_seed);
        CharacterState control_state, hidden_state, visible_state;
        Observation control_observation, hidden_observation, visible_observation;
        WorldOutcome control_previous, hidden_previous, visible_previous;
        std::mt19937 control_rng(action_seed_base + scenario_seed), hidden_rng(action_seed_base + scenario_seed), visible_rng(action_seed_base + scenario_seed);
        ScenarioConfig hidden_config{}; hidden_config.information_access.phone_presence_observable = false;
        ScenarioConfig visible_config{}; visible_config.information_access.phone_presence_observable = true;
        for (int step = 1; step <= 12; ++step) {
            // Both branches observe the common initial phone. After the
            // intervention the hidden branch keeps the last phone fact.
            hidden_config.information_access.phone_presence_observable = (step == 1);
            const StepRecord control = advance_one_decision(control_world, control_state, control_observation,
                control_previous, control_rng, personality, {});
            const StepRecord hidden = advance_one_decision(hidden_world, hidden_state, hidden_observation,
                hidden_previous, hidden_rng, personality, hidden_config.information_access);
            const StepRecord visible = advance_one_decision(visible_world, visible_state, visible_observation,
                visible_previous, visible_rng, personality, visible_config.information_access);
            const double pd = policy_distance(hidden.decision, visible.decision);
            const double sd = state_distance(hidden.state_at_decision, visible.state_at_decision);
            const bool oe = observation_equal(hidden.observation_at_decision, visible.observation_at_decision);
            const auto emit = [&](const char* branch, const StepRecord& trace, const World& world) {
                const ObservationFact* phone = find_fact(trace.observation_at_decision, "object.phone");
                file << scenario_seed << ',' << branch << ',' << step << ',';
                write_csv_field(file, trace.decision_time);
                file << ','; write_csv_field(file, to_string(trace.chosen_action));
                file << ',' << (trace.outcome.accepted ? 1 : 0) << ','
                     << (world.object_for(ActionType::UsePhone) != nullptr ? 1 : 0) << ','
                     << (phone != nullptr && phone->status == KnowledgeStatus::Known ? 1 : 0) << ',';
                if (phone != nullptr) write_csv_field(file, phone->status == KnowledgeStatus::Known ? "known" : "stale");
                else write_csv_field(file, "absent");
                file << ',' << trace.decision.known_actions.size() << ',';
                write_csv_field(file, observation_summary(trace.observation_at_decision));
                file << ',' << pd << ',' << sd << ',' << (oe ? 1 : 0) << ',' << world.phone_uses << ',';
                write_csv_field(file, trace.outcome.target_object_id);
                file << ','; write_csv_field(file, rejection_reason_name(trace.outcome.failure_reason));
                file << ',' << ((!trace.outcome.accepted && trace.outcome.failure_reason == RejectionReason::TargetAbsent) ? 1 : 0) << '\n';
            };
            emit("hidden", hidden, hidden_world);
            emit("visible", visible, visible_world);
            emit("control", control, control_world);
            if (step == 1) {
                for (World* world : {&hidden_world, &visible_world}) {
                    Room& room = world->current_room();
                    room.objects.erase(std::remove_if(room.objects.begin(), room.objects.end(),
                        [](const Object& object) { return object.id == "phone"; }), room.objects.end());
                }
            }
        }
        // Deterministic mechanism probe: force the hidden-belief action so
        // discovery semantics are recorded even when sampled policy does not
        // choose UsePhone within the short trajectory.
        World probe_world(scenario_seed);
        Observation probe_observation = refresh_observation({}, probe_world, {});
        probe_world.current_room().objects.erase(std::remove_if(
            probe_world.current_room().objects.begin(), probe_world.current_room().objects.end(),
            [](const Object& object) { return object.id == "phone"; }), probe_world.current_room().objects.end());
        const WorldOutcome probe_failure = probe_world.settle(ActionType::UsePhone, "phone");
        apply_self_action_feedback(probe_observation, probe_failure, probe_world.time_summary());
        file << scenario_seed << ",mechanism_probe,2,\"" << probe_world.time_summary()
             << "\",use_phone," << (probe_failure.accepted ? 1 : 0)
             << ",0,0,absent,0,";
        write_csv_field(file, observation_summary(probe_observation));
        file << ",0,0,0,0,phone,";
        write_csv_field(file, probe_failure.target_object_id);
        file << ','; write_csv_field(file, rejection_reason_name(probe_failure.failure_reason));
        file << "," << ((!probe_failure.accepted && probe_failure.failure_reason == RejectionReason::TargetAbsent) ? 1 : 0) << '\n';
    }
    output << "paired phone intervention complete: 8 seeds x 12 steps x 3 branches saved to " << path.string() << '\n';
}

void Simulation::run_paired_deadline_intervention(std::ostream& output, const std::string& output_path) const {
    namespace fs = std::filesystem;
    const fs::path path(output_path);
    if (path.has_parent_path()) fs::create_directories(path.parent_path());
    std::ofstream file(path);
    if (!file) throw std::runtime_error("Cannot open paired deadline output: " + output_path);
    file << "scenario_seed,branch,step,deadline_fact,deadline_source,appraisal_pressure_delta,pre_task_pressure,post_task_pressure,chosen_action,policy_tv_vs_control,observation_summary,discovery_event\n";
    file << std::fixed << std::setprecision(6);
    const Personality personality = procrastinating_profile();
    constexpr unsigned int action_seed_base = 20260914U;
    for (unsigned int scenario_seed = 1; scenario_seed <= 8; ++scenario_seed) {
        World control_world(scenario_seed), hidden_world(scenario_seed), visible_world(scenario_seed);
        CharacterState control_state, hidden_state, visible_state;
        Observation control_observation, hidden_observation, visible_observation;
        WorldOutcome control_previous, hidden_previous, visible_previous;
        std::mt19937 control_rng(action_seed_base + scenario_seed), hidden_rng(action_seed_base + scenario_seed), visible_rng(action_seed_base + scenario_seed);
        ScenarioConfig control_config{}, hidden_config{}, visible_config{};
        hidden_config.information_access.task_deadline_observable = false;
        for (int step = 1; step <= 12; ++step) {
            hidden_config.information_access.task_deadline_observable = (step == 1 || step >= 4);
            const StepRecord control = advance_one_decision(control_world, control_state, control_observation,
                control_previous, control_rng, personality, control_config.information_access);
            const StepRecord hidden = advance_one_decision(hidden_world, hidden_state, hidden_observation,
                hidden_previous, hidden_rng, personality, hidden_config.information_access);
            const StepRecord visible = advance_one_decision(visible_world, visible_state, visible_observation,
                visible_previous, visible_rng, personality, visible_config.information_access);
            if (step == 1) {
                for (World* world : {&hidden_world, &visible_world}) {
                    if (WorldTask* task = world->task_by_id("coursework")) {
                        task->due_at_total_minutes = total_minutes(world->time) + 60;
                    }
                }
            }
            const auto emit = [&](const char* branch, const StepRecord& trace, const CharacterState& state,
                                  const World& world, const DecisionContext& baseline) {
                const ObservationFact* deadline = find_fact(trace.observation_at_decision, "task.coursework.deadline");
                const double policy_tv = policy_distance(trace.decision, baseline);
                file << scenario_seed << ',' << branch << ',' << step << ',';
                write_csv_field(file, deadline != nullptr ? deadline->value : "unknown");
                file << ','; write_csv_field(file, deadline != nullptr ? deadline->source : "none");
                file << ',' << trace.appraisal.task_pressure_delta
                     << ',' << trace.state_at_decision.task_pressure
                     << ',' << trace.state_after_settlement.task_pressure << ',';
                write_csv_field(file, to_string(trace.chosen_action));
                file << ',' << policy_tv << ',';
                write_csv_field(file, observation_summary(trace.observation_at_decision));
                file << ',' << (deadline != nullptr && deadline->value == "passed" ? 1 : 0) << '\n';
            };
            emit("control", control, control_state, control_world, control.decision);
            emit("hidden", hidden, hidden_state, hidden_world, control.decision);
            emit("visible", visible, visible_state, visible_world, control.decision);
        }
    }
    output << "paired deadline intervention complete: 8 seeds x 12 steps x 3 branches saved to " << path.string() << '\n';
}

bool Simulation::verify(std::ostream& output) const {
    const Personality first = procrastinating_profile();
    const Personality second = self_controlled_profile();

    const std::string first_run = run_profile(first, 20260904U, 0U, false);
    const std::string repeated_first_run = run_profile(first, 20260904U, 0U, false);
    const std::string second_run = run_profile(second, 20260904U, 0U, false);

    World unavailable_computer;
    for (Object& object : unavailable_computer.current_room().objects) {
        if (object.id == "computer") {
            object.usable = false;
        }
    }
    const WorldOutcome rejected = unavailable_computer.execute(ActionType::UseComputer);

    World primitive_world;
    const CharacterActionPlan study_plan = primitive_world.expand_action(ActionType::StudyFocused);
    const WorldOutcome settled_study = primitive_world.settle(ActionType::StudyFocused);

    World sleeping_world;
    sleeping_world.time.minute_of_day = 10 * 60 + 46;
    const WorldOutcome interrupted_sleep = sleeping_world.settle(ActionType::SleepAtBed);
    const bool sleep_primitive_shortened = std::any_of(interrupted_sleep.settled_primitives.begin(),
        interrupted_sleep.settled_primitives.end(), [](const WorldPrimitive& primitive) {
            const auto* advance = std::get_if<AdvanceSimulationTime>(&primitive.payload);
            return advance != nullptr && advance->minutes == 314;
        });

    const bool reproducible = first_run == repeated_first_run;
    const bool profile_sensitive = first_run != second_run;
    const bool validates_world = !rejected.accepted && !rejected.provenance.empty();
    const bool has_primitives = first_run.find("a^world") != std::string::npos;
    const WorldTask* primitive_task = primitive_world.task_by_id("coursework");
    const bool primitives_settle = settled_study.accepted && settled_study.task_effort_gained > 0.0
                                && primitive_task != nullptr && primitive_task->effort_done > 0.0
                                && settled_study.settled_primitives.size() == study_plan.world_primitives.size();
    World completed_task_world;
    WorldTask* completed_task = completed_task_world.task_by_id("coursework");
    completed_task->effort_done = completed_task->effort_target;
    completed_task->status = TaskStatus::Completed;
    completed_task_world.time.minute_of_day = 11 * 60 + 50;
    const WorldOutcome no_completed_task_reminder = completed_task_world.execute(ActionType::Idle);
    const bool completed_task_stays_quiet = std::none_of(no_completed_task_reminder.events.begin(),
        no_completed_task_reminder.events.end(), [](const WorldEvent& event) { return event.id == "task-reminder"; });
    World duplicate_affordance_world;
    duplicate_affordance_world.current_room().objects.push_back(
        {"backup-phone", "backup phone", true, {ActionType::UsePhone}});
    const auto duplicate_actions = duplicate_affordance_world.available_actions();
    const bool deduplicates_actions = std::count(duplicate_actions.begin(), duplicate_actions.end(), ActionType::UsePhone) == 1;
    Observation visible_observation = refresh_observation({}, unavailable_computer, {});
    const WorldOutcome rejected_attempt = unavailable_computer.execute(ActionType::UseComputer);
    const Observation rejected_observation = refresh_observation(visible_observation, unavailable_computer, rejected_attempt);
    const Appraisal rejected_appraisal = appraise(rejected_observation, CharacterState{}, first);
    const bool preserves_rejected_feedback = rejected_observation.last_self_action.has_action
        && !rejected_observation.last_self_action.accepted
        && std::find(rejected_appraisal.tags.begin(), rejected_appraisal.tags.end(), "action_rejected")
            != rejected_appraisal.tags.end();
    const bool keeps_broken_object_visible = observation_knows_action(visible_observation, ActionType::UseComputer)
        && std::find(visible_observation.known_object_ids.begin(), visible_observation.known_object_ids.end(), "computer")
            != visible_observation.known_object_ids.end();
    World insufficient_wallet_world;
    insufficient_wallet_world.wallet = 20;
    const Observation insufficient_wallet_observation = refresh_observation({}, insufficient_wallet_world, {});
    const WorldOutcome rejected_purchase = insufficient_wallet_world.execute(ActionType::ShopOnPhone);
    const bool does_not_leak_hidden_wallet = observation_knows_action(insufficient_wallet_observation, ActionType::ShopOnPhone)
        && !rejected_purchase.accepted;
    World stale_object_world;
    Observation object_observation = refresh_observation({}, stale_object_world, {});
    auto& stale_objects = stale_object_world.current_room().objects;
    stale_objects.erase(std::remove_if(stale_objects.begin(), stale_objects.end(), [](const Object& object) {
        return object.id == "phone";
    }), stale_objects.end());
    object_observation = refresh_observation(std::move(object_observation), stale_object_world, {});
    const ObservationFact* stale_phone = find_fact(object_observation, "object.phone");
    const bool marks_absent_object_stale = stale_phone != nullptr && stale_phone->status == KnowledgeStatus::Stale;
    CharacterState capped_state;
    capped_state.hunger = 0.10;
    Appraisal large_reduction;
    large_reduction.hunger_delta = -1.0;
    const StateUpdate capped_update = update_state(capped_state, large_reduction, first, 0);
    const bool reports_applied_delta = capped_update.requested.hunger < capped_update.applied.hunger
        && capped_update.applied.hunger == -0.10;
    const bool handles_interruption = interrupted_sleep.accepted && interrupted_sleep.woke_early
                                   && sleep_primitive_shortened;
    CharacterState commitment_state;
    World commitment_world;
    Observation commitment_observation;
    const WorldOutcome first_study = commitment_world.settle(ActionType::StudyFocused);
    apply_self_action_feedback(commitment_observation, first_study, commitment_world.time_summary());
    update_commitment(commitment_state, commitment_observation, total_minutes(commitment_world.time));
    const bool starts_task_commitment = commitment_state.commitment.status == CommitmentStatus::Active
                                     && commitment_state.commitment.task_id == "coursework";
    const WorldOutcome meal = commitment_world.settle(ActionType::GetMeal);
    apply_self_action_feedback(commitment_observation, meal, commitment_world.time_summary());
    update_commitment(commitment_state, commitment_observation, total_minutes(commitment_world.time));
    const bool suspends_for_bodily_need = commitment_state.commitment.status == CommitmentStatus::Suspended;
    const WorldOutcome resumed_study = commitment_world.settle(ActionType::StudyAtComputer);
    apply_self_action_feedback(commitment_observation, resumed_study, commitment_world.time_summary());
    update_commitment(commitment_state, commitment_observation, total_minutes(commitment_world.time));
    const bool resumes_task_commitment = commitment_state.commitment.status == CommitmentStatus::Active;
    World completion_world;
    WorldTask* completion_task = completion_world.task_by_id("coursework");
    completion_task->effort_target = 0.10;
    const WorldOutcome completing_study = completion_world.settle(ActionType::StudyFocused);
    apply_self_action_feedback(commitment_observation, completing_study, completion_world.time_summary());
    update_commitment(commitment_state, commitment_observation, total_minutes(completion_world.time));
    const bool completes_task_with_variable_effort = completing_study.task_completed
        && completing_study.task_effort_gained != 1.0 && commitment_state.commitment.status == CommitmentStatus::None;
    CharacterState unconfirmed_completion_state;
    Observation unconfirmed_completion_observation;
    apply_self_action_feedback(unconfirmed_completion_observation, completing_study,
                               completion_world.time_summary(), false);
    update_commitment(unconfirmed_completion_state, unconfirmed_completion_observation,
                      total_minutes(completion_world.time));
    const bool completion_requires_observable_feedback = completing_study.task_completed
        && !has_known_fact(unconfirmed_completion_observation, "task.coursework.status", "completed")
        && unconfirmed_completion_state.commitment.status == CommitmentStatus::Active;
    World deadline_world;
    deadline_world.time.minute_of_day = 8 * 60;
    WorldTask* deadline_task = deadline_world.task_by_id("coursework");
    deadline_task->due_at_total_minutes = total_minutes(deadline_world.time) + action_definition(ActionType::Idle).default_duration_minutes;
    const Observation before_deadline_observation = refresh_observation({}, deadline_world, {});
    const WorldOutcome deadline_outcome = deadline_world.settle(ActionType::Idle);
    const Observation after_deadline_observation = refresh_observation(before_deadline_observation, deadline_world, deadline_outcome);
    const Appraisal deadline_appraisal = appraise(after_deadline_observation, CharacterState{}, first);
    const bool deadline_is_observable = std::any_of(deadline_outcome.events.begin(), deadline_outcome.events.end(),
        [](const WorldEvent& event) { return event.id == "task-deadline"; })
        && std::find(deadline_appraisal.tags.begin(), deadline_appraisal.tags.end(), "deadline_passed")
            != deadline_appraisal.tags.end();
    World reconsideration_world;
    const Observation reconsideration_observation = refresh_observation({}, reconsideration_world, {});
    CharacterState suspended_commitment;
    suspended_commitment.commitment = {CommitmentStatus::Suspended, "coursework", "test suspended commitment", 0, 1};
    suspended_commitment.fatigue = 0.90;
    const DecisionContext deferred_return = decide(reconsideration_observation, suspended_commitment, first);
    suspended_commitment.fatigue = 0.20;
    const DecisionContext permitted_return = decide(reconsideration_observation, suspended_commitment, first);
    const bool gates_suspended_return = deferred_return.intention_status.find("defers return") != std::string::npos
        && permitted_return.intention_status.find("permits return") != std::string::npos;

    const auto same_policy = [](const DecisionContext& left, const DecisionContext& right) {
        if (left.candidates.size() != right.candidates.size()) return false;
        for (std::size_t index = 0; index < left.candidates.size(); ++index) {
            if (left.candidates[index].action != right.candidates[index].action
                || left.candidates[index].probability != right.candidates[index].probability) {
                return false;
            }
        }
        return true;
    };

    // Research invariants: hidden W changes cannot affect policy before O
    // changes; observed O changes may affect the candidate support; S must be
    // consumed by policy; completion relief requires observable feedback.
    World hidden_wallet_a;
    World hidden_wallet_b;
    hidden_wallet_a.wallet = 20;
    hidden_wallet_b.wallet = 120;
    const Observation hidden_wallet_o_a = refresh_observation({}, hidden_wallet_a, {});
    const Observation hidden_wallet_o_b = refresh_observation({}, hidden_wallet_b, {});
    const DecisionContext hidden_wallet_pi_a = decide(hidden_wallet_o_a, CharacterState{}, first);
    const DecisionContext hidden_wallet_pi_b = decide(hidden_wallet_o_b, CharacterState{}, first);
    const bool hidden_w_same_pi = same_policy(hidden_wallet_pi_a, hidden_wallet_pi_b)
        && hidden_wallet_o_a.known_actions == hidden_wallet_o_b.known_actions;

    World visible_light_off;
    World visible_light_on;
    visible_light_off.current_room().light_on = false;
    visible_light_on.current_room().light_on = true;
    const Observation visible_o_off = refresh_observation({}, visible_light_off, {});
    const Observation visible_o_on = refresh_observation({}, visible_light_on, {});
    const DecisionContext visible_pi_off = decide(visible_o_off, CharacterState{}, first);
    const DecisionContext visible_pi_on = decide(visible_o_on, CharacterState{}, first);
    const bool visible_o_can_change_pi = visible_o_off.known_actions != visible_o_on.known_actions
        && !same_policy(visible_pi_off, visible_pi_on);

    CharacterState state_low_signal;
    CharacterState state_high_signal;
    state_low_signal.boredom = 0.0;
    state_high_signal.boredom = 1.0;
    const DecisionContext shuffled_s_low = decide(visible_o_off, state_low_signal, first);
    const DecisionContext shuffled_s_high = decide(visible_o_off, state_high_signal, first);
    const bool state_input_affects_policy = !same_policy(shuffled_s_low, shuffled_s_high);

    World information_access_world;
    information_access_world.wallet = 20;
    const InformationAccess visible_wallet_access{true, true, false};
    const Observation visible_wallet_observation = refresh_observation(
        {}, information_access_world, {}, visible_wallet_access);
    const bool scenario_information_access_is_configurable =
        has_known_fact(visible_wallet_observation, "wallet.balance", "20");

    const bool light_precondition_filters_known_state =
        std::find(visible_o_on.known_actions.begin(), visible_o_on.known_actions.end(), ActionType::TurnLightOn)
            == visible_o_on.known_actions.end();
    World open_curtain_world;
    open_curtain_world.current_room().curtain_open = true;
    const Observation open_curtain_observation = refresh_observation({}, open_curtain_world, {});
    const bool curtain_precondition_filters_known_state =
        std::find(open_curtain_observation.known_actions.begin(), open_curtain_observation.known_actions.end(), ActionType::OpenCurtain)
            == open_curtain_observation.known_actions.end();
    World dark_room_world;
    dark_room_world.current_room().light_on = false;
    const Observation dark_room_observation = refresh_observation({}, dark_room_world, {});
    const bool study_requires_known_light =
        std::find(dark_room_observation.known_actions.begin(), dark_room_observation.known_actions.end(), ActionType::StudyFocused)
            == dark_room_observation.known_actions.end();
    const bool silent_alarm_filters_action =
        std::find(visible_o_off.known_actions.begin(), visible_o_off.known_actions.end(), ActionType::TurnOffAlarm)
            == visible_o_off.known_actions.end();
    const bool visible_wallet_filters_purchase =
        std::find(visible_wallet_observation.known_actions.begin(), visible_wallet_observation.known_actions.end(), ActionType::ShopOnPhone)
            == visible_wallet_observation.known_actions.end();
    World visibly_broken_world;
    for (Object& object : visibly_broken_world.current_room().objects) {
        if (object.id == "computer") object.usable = false;
    }
    const InformationAccess visible_object_access{true, false, true};
    const Observation visibly_broken_observation = refresh_observation({}, visibly_broken_world, {}, visible_object_access);
    const ObservationFact* visible_usability = find_fact(visibly_broken_observation, "object.computer.usable");
    const bool visible_usability_filters_action =
        visible_usability != nullptr && visible_usability->status == KnowledgeStatus::Known
        && visible_usability->value == "false"
        && std::find(visibly_broken_observation.known_actions.begin(), visibly_broken_observation.known_actions.end(), ActionType::UseComputer)
            == visibly_broken_observation.known_actions.end();
    World hidden_phone_world;
    Observation hidden_phone_observation = refresh_observation({}, hidden_phone_world, {});
    hidden_phone_world.current_room().objects.erase(
        std::remove_if(hidden_phone_world.current_room().objects.begin(), hidden_phone_world.current_room().objects.end(),
            [](const Object& object) { return object.id == "phone"; }),
        hidden_phone_world.current_room().objects.end());
    InformationAccess hidden_phone_access;
    hidden_phone_access.phone_presence_observable = false;
    const Observation hidden_phone_after_removal = refresh_observation(
        hidden_phone_observation, hidden_phone_world, {}, hidden_phone_access);
    InformationAccess visible_phone_access;
    visible_phone_access.phone_presence_observable = true;
    const Observation visible_phone_after_removal = refresh_observation(
        hidden_phone_observation, hidden_phone_world, {}, visible_phone_access);
    const bool hidden_belief_retains_phone_actions =
        has_known_fact(hidden_phone_after_removal, "object.phone", "present")
        && std::find(hidden_phone_after_removal.known_actions.begin(), hidden_phone_after_removal.known_actions.end(), ActionType::UsePhone)
            != hidden_phone_after_removal.known_actions.end()
        && std::find(hidden_phone_after_removal.known_actions.begin(), hidden_phone_after_removal.known_actions.end(), ActionType::ShopOnPhone)
            != hidden_phone_after_removal.known_actions.end();
    const bool visible_phone_removes_actions =
        std::find(visible_phone_after_removal.known_actions.begin(), visible_phone_after_removal.known_actions.end(), ActionType::UsePhone)
            == visible_phone_after_removal.known_actions.end()
        && std::find(visible_phone_after_removal.known_actions.begin(), visible_phone_after_removal.known_actions.end(), ActionType::ShopOnPhone)
            == visible_phone_after_removal.known_actions.end();
    World discovery_world;
    Observation discovery_observation = refresh_observation({}, discovery_world, {});
    discovery_world.current_room().objects.erase(
        std::remove_if(discovery_world.current_room().objects.begin(), discovery_world.current_room().objects.end(),
            [](const Object& object) { return object.id == "phone"; }),
        discovery_world.current_room().objects.end());
    const WorldOutcome discovery_failure = discovery_world.settle(ActionType::UsePhone, "phone");
    apply_self_action_feedback(discovery_observation, discovery_failure,
                               discovery_world.time_summary());
    const Observation discovery_next = refresh_observation(discovery_observation, discovery_world, discovery_failure);
    const ObservationFact* corrected_phone = find_fact(discovery_next, "object.phone");
    const bool typed_discovery_correction = discovery_failure.failure_reason == RejectionReason::TargetAbsent
        && discovery_failure.target_object_id == "phone"
        && corrected_phone != nullptr && corrected_phone->value == "absent"
        && corrected_phone->source == "failed_direct_interaction"
        && std::find(discovery_next.known_actions.begin(), discovery_next.known_actions.end(), ActionType::UsePhone)
            == discovery_next.known_actions.end();
    ScenarioConfig configured_scenario;
    configured_scenario.information_access.wallet_balance_observable = true;
    const std::string default_scenario_run = run_profile(first, 20260904U, 0U, false, 2, true);
    const std::string configured_scenario_run = run_profile(first, 20260904U, 0U, false, 2, true, configured_scenario);
    const bool scenario_config_reaches_trajectory = default_scenario_run != configured_scenario_run;

    output << "verify: reproducible=" << reproducible
           << ", profile_sensitive=" << profile_sensitive
           << ", rejects_illegal_action=" << validates_world
           << ", trace_has_primitives=" << has_primitives
           << ", primitives_settle=" << primitives_settle
           << ", interruption_rewrites_plan=" << handles_interruption
           << ", completed_task_stays_quiet=" << completed_task_stays_quiet
           << ", deduplicates_actions=" << deduplicates_actions
           << ", preserves_rejected_feedback=" << preserves_rejected_feedback
           << ", keeps_broken_object_visible=" << keeps_broken_object_visible
           << ", does_not_leak_hidden_wallet=" << does_not_leak_hidden_wallet
           << ", marks_absent_object_stale=" << marks_absent_object_stale
           << ", reports_applied_delta=" << reports_applied_delta
           << ", starts_task_commitment=" << starts_task_commitment
           << ", suspends_for_bodily_need=" << suspends_for_bodily_need
           << ", resumes_task_commitment=" << resumes_task_commitment
           << ", completes_task_with_variable_effort=" << completes_task_with_variable_effort
           << ", completion_requires_observable_feedback=" << completion_requires_observable_feedback
           << ", deadline_is_observable=" << deadline_is_observable
           << ", gates_suspended_return=" << gates_suspended_return
           << ", hidden_w_same_pi=" << hidden_w_same_pi
           << ", visible_o_can_change_pi=" << visible_o_can_change_pi
           << ", state_input_affects_policy=" << state_input_affects_policy
           << ", scenario_information_access_is_configurable=" << scenario_information_access_is_configurable
           << ", scenario_config_reaches_trajectory=" << scenario_config_reaches_trajectory
           << ", light_precondition_filters_known_state=" << light_precondition_filters_known_state
           << ", curtain_precondition_filters_known_state=" << curtain_precondition_filters_known_state
           << ", study_requires_known_light=" << study_requires_known_light
           << ", silent_alarm_filters_action=" << silent_alarm_filters_action
           << ", visible_wallet_filters_purchase=" << visible_wallet_filters_purchase
           << ", visible_usability_filters_action=" << visible_usability_filters_action
           << ", hidden_belief_retains_phone_actions=" << hidden_belief_retains_phone_actions
           << ", visible_phone_removes_actions=" << visible_phone_removes_actions
           << ", typed_discovery_correction=" << typed_discovery_correction << '\n';
    return reproducible && profile_sensitive && validates_world && has_primitives
        && primitives_settle && handles_interruption && completed_task_stays_quiet && deduplicates_actions
        && preserves_rejected_feedback && keeps_broken_object_visible && does_not_leak_hidden_wallet
        && marks_absent_object_stale && reports_applied_delta
        && starts_task_commitment && suspends_for_bodily_need && resumes_task_commitment
        && completes_task_with_variable_effort && completion_requires_observable_feedback
        && deadline_is_observable && gates_suspended_return
        && hidden_w_same_pi && visible_o_can_change_pi && state_input_affects_policy
        && scenario_information_access_is_configurable
        && scenario_config_reaches_trajectory
        && light_precondition_filters_known_state && curtain_precondition_filters_known_state
        && study_requires_known_light && silent_alarm_filters_action
        && visible_wallet_filters_purchase && visible_usability_filters_action
        && hidden_belief_retains_phone_actions && visible_phone_removes_actions
        && typed_discovery_correction;
}

bool Simulation::run_e0(std::ostream& output) const {
    const Personality personality = procrastinating_profile();
    const auto probability_for = [](const DecisionContext& policy, ActionType action) {
        for (const CandidateAction& candidate : policy.candidates) {
            if (candidate.action == action) return candidate.probability;
        }
        return 0.0;
    };
    const auto support_summary = [](const Observation& observation) {
        std::ostringstream result;
        for (std::size_t index = 0; index < observation.known_actions.size(); ++index) {
            if (index != 0) result << '|';
            result << to_string(observation.known_actions[index]);
        }
        return result.str();
    };
    const auto same_observation = [](const Observation& left, const Observation& right) {
        if (left.visible_object_labels != right.visible_object_labels
            || left.known_object_ids != right.known_object_ids
            || left.known_actions != right.known_actions
            || left.facts.size() != right.facts.size()
            || left.updates_this_refresh.size() != right.updates_this_refresh.size()
            || left.pending_appraisal_updates.size() != right.pending_appraisal_updates.size()) return false;
        const auto same_fact = [](const ObservationFact& a, const ObservationFact& b) {
            return a.key == b.key && a.value == b.value && a.status == b.status
                && a.source == b.source && a.observed_at == b.observed_at;
        };
        const auto same_facts = [&same_fact](const auto& a, const auto& b) {
            for (std::size_t index = 0; index < a.size(); ++index) {
                if (!same_fact(a[index], b[index])) return false;
            }
            return true;
        };
        if (!same_facts(left.facts, right.facts)
            || !same_facts(left.updates_this_refresh, right.updates_this_refresh)
            || !same_facts(left.pending_appraisal_updates, right.pending_appraisal_updates)) return false;
        const ObservedAction& a = left.last_self_action;
        const ObservedAction& b = right.last_self_action;
        if (a.has_action != b.has_action || a.action != b.action || a.accepted != b.accepted
            || a.task_id != b.task_id || a.task_completed != b.task_completed
            || a.outcome_reason != b.outcome_reason || a.source != b.source
            || a.observed_at != b.observed_at) return false;
        return true;
    };
    const auto emit_pair = [&](const char* fixture,
                               const Observation& low_observation,
                               const DecisionContext& low_policy,
                               const CharacterState& low_state,
                               const Observation& high_observation,
                               const DecisionContext& high_policy,
                               const CharacterState& high_state) {
        double max_abs_delta = 0.0;
        for (std::size_t index = 0; index < kActionCount; ++index) {
            const ActionType action = static_cast<ActionType>(index);
            max_abs_delta = std::max(max_abs_delta,
                std::abs(probability_for(low_policy, action) - probability_for(high_policy, action)));
        }
        output << "fixture=" << fixture
               << ",support_low=" << support_summary(low_observation)
               << ",support_high=" << support_summary(high_observation)
               << ",max_abs_delta_p=" << std::fixed << std::setprecision(6) << max_abs_delta
               << ",commitment_low=" << commitment_status_name(low_state.commitment.status)
               << ",commitment_high=" << commitment_status_name(high_state.commitment.status) << '\n';
        for (std::size_t index = 0; index < kActionCount; ++index) {
            const ActionType action = static_cast<ActionType>(index);
            const double low_probability = probability_for(low_policy, action);
            const double high_probability = probability_for(high_policy, action);
            output << "p_low_" << to_string(action) << '=' << low_probability
                   << ",p_high_" << to_string(action) << '=' << high_probability
                   << ",delta_" << to_string(action) << '=' << (low_probability - high_probability) << '\n';
        }
        return max_abs_delta;
    };

    const ScenarioConfig hidden_scenario{};
    World hidden_low(42U);
    World hidden_high(42U);
    hidden_low.wallet = 20;
    hidden_high.wallet = 120;
    const Observation hidden_low_o = refresh_observation({}, hidden_low, {}, hidden_scenario.information_access);
    const Observation hidden_high_o = refresh_observation({}, hidden_high, {}, hidden_scenario.information_access);
    const CharacterState empty_state;
    const auto evaluate_hidden_wallet = [&personality](Observation observation) {
        CharacterState state;
        const Appraisal x = appraise(observation, state, personality);
        clear_pending_appraisal_updates(observation);
        const StateUpdate update = update_state(state, x, personality, 0);
        const DecisionContext policy = decide(observation, state, personality);
        return std::tuple<Observation, Appraisal, StateUpdate, CharacterState, DecisionContext>{
            std::move(observation), x, update, state, policy};
    };
    auto hidden_low_eval = evaluate_hidden_wallet(hidden_low_o);
    auto hidden_high_eval = evaluate_hidden_wallet(hidden_high_o);
    const DecisionContext& hidden_low_pi = std::get<4>(hidden_low_eval);
    const DecisionContext& hidden_high_pi = std::get<4>(hidden_high_eval);
    const double hidden_delta = emit_pair("E0-1_hidden_wallet", std::get<0>(hidden_low_eval), hidden_low_pi,
                                          std::get<3>(hidden_low_eval), std::get<0>(hidden_high_eval), hidden_high_pi,
                                          std::get<3>(hidden_high_eval));

    const ScenarioConfig visible_scenario{{true, true, false}};
    const Observation visible_low_o = refresh_observation({}, hidden_low, {}, visible_scenario.information_access);
    const Observation visible_high_o = refresh_observation({}, hidden_high, {}, visible_scenario.information_access);
    const DecisionContext visible_low_pi = decide(visible_low_o, empty_state, personality);
    const DecisionContext visible_high_pi = decide(visible_high_o, empty_state, personality);
    const double visible_delta = emit_pair("E0-2_visible_wallet", visible_low_o, visible_low_pi, empty_state,
                                           visible_high_o, visible_high_pi, empty_state);

    World completion_visible_world(42U);
    World completion_hidden_world(42U);
    completion_visible_world.task_by_id("coursework")->effort_target = 0.10;
    completion_hidden_world.task_by_id("coursework")->effort_target = 0.10;
    const WorldOutcome visible_completion = completion_visible_world.settle(ActionType::StudyFocused);
    const WorldOutcome hidden_completion = completion_hidden_world.settle(ActionType::StudyFocused);
    Observation completion_visible_o;
    Observation completion_hidden_o;
    CharacterState completion_visible_state;
    CharacterState completion_hidden_state;
    completion_visible_state.commitment = {CommitmentStatus::Active, "coursework", "visible fixture", 0, 0};
    completion_hidden_state.commitment = completion_visible_state.commitment;
    apply_self_action_feedback(completion_visible_o, visible_completion, completion_visible_world.time_summary(), true);
    apply_self_action_feedback(completion_hidden_o, hidden_completion, completion_hidden_world.time_summary(), false);
    update_commitment(completion_visible_state, completion_visible_o, total_minutes(completion_visible_world.time));
    update_commitment(completion_hidden_state, completion_hidden_o, total_minutes(completion_hidden_world.time));
    completion_visible_o = refresh_observation(std::move(completion_visible_o), completion_visible_world, {},
                                               hidden_scenario.information_access);
    completion_hidden_o = refresh_observation(std::move(completion_hidden_o), completion_hidden_world, {},
                                              hidden_scenario.information_access);
    const Appraisal completion_visible_x = appraise(completion_visible_o, completion_visible_state, personality);
    const Appraisal completion_hidden_x = appraise(completion_hidden_o, completion_hidden_state, personality);
    const StateUpdate completion_visible_update = update_state(completion_visible_state, completion_visible_x, personality,
                                                               visible_completion.elapsed_minutes);
    const StateUpdate completion_hidden_update = update_state(completion_hidden_state, completion_hidden_x, personality,
                                                              hidden_completion.elapsed_minutes);
    const DecisionContext completion_visible_pi = decide(completion_visible_o, completion_visible_state, personality);
    const DecisionContext completion_hidden_pi = decide(completion_hidden_o, completion_hidden_state, personality);
    const double completion_delta = emit_pair("E0-3_completion_visibility", completion_visible_o, completion_visible_pi,
                                              completion_visible_state, completion_hidden_o, completion_hidden_pi,
                                              completion_hidden_state);
    output << "completion_visible_X=" << appraisal_summary(completion_visible_x)
           << ",completion_hidden_X=" << appraisal_summary(completion_hidden_x) << '\n'
           << "completion_visible_delta_S=" << state_delta_summary(completion_visible_update.applied)
           << ",completion_hidden_delta_S=" << state_delta_summary(completion_hidden_update.applied) << '\n'
           << "completion_visible_S=" << state_summary(completion_visible_state) << '\n'
           << "completion_hidden_S=" << state_summary(completion_hidden_state) << '\n';

    const bool hidden_observation_equal = same_observation(hidden_low_o, hidden_high_o);
    const bool hidden_appraisal_equal = appraisal_summary(std::get<1>(hidden_low_eval))
        == appraisal_summary(std::get<1>(hidden_high_eval));
    const bool hidden_state_equal = state_summary(std::get<3>(hidden_low_eval))
        == state_summary(std::get<3>(hidden_high_eval));
    const bool hidden_support_equal = support_summary(hidden_low_o) == support_summary(hidden_high_o);
    const bool visible_wallet_facts_correct = has_known_fact(visible_low_o, "wallet.balance", "20")
        && has_known_fact(visible_high_o, "wallet.balance", "120");
    const bool visible_wallet_support_correct =
        std::find(visible_low_o.known_actions.begin(), visible_low_o.known_actions.end(), ActionType::ShopOnPhone)
            == visible_low_o.known_actions.end()
        && std::find(visible_high_o.known_actions.begin(), visible_high_o.known_actions.end(), ActionType::ShopOnPhone)
            != visible_high_o.known_actions.end();
    output << "metadata=git_revision=" << CHARACTER_DYNAMICS_GIT_REVISION
           << ",world_seed=42,personality=procrastinating,action_sampling=none"
           << ",hidden_wallet_same_O=" << hidden_observation_equal
           << ",hidden_wallet_same_X=" << hidden_appraisal_equal
           << ",hidden_wallet_same_S=" << hidden_state_equal
           << ",hidden_wallet_same_support=" << hidden_support_equal
           << ",hidden_wallet_same_pi=" << (hidden_delta == 0.0)
           << ",visible_wallet_facts_correct=" << visible_wallet_facts_correct
           << ",visible_wallet_support_correct=" << visible_wallet_support_correct
           << ",visible_wallet_pi_changed=" << (visible_delta > 0.0)
           << ",completion_visibility_changes_state_or_pi=" << (completion_delta > 0.0
               || completion_visible_state.commitment.status != completion_hidden_state.commitment.status) << '\n';
    const auto has_tag = [](const Appraisal& appraisal, const std::string& tag) {
        return std::find(appraisal.tags.begin(), appraisal.tags.end(), tag) != appraisal.tags.end();
    };
    const bool completion_x_assertion = has_tag(completion_visible_x, "task_completed")
        && !has_tag(completion_hidden_x, "task_completed");
    const bool completion_state_assertion = completion_visible_update.applied.task_pressure
        != completion_hidden_update.applied.task_pressure
        && completion_visible_update.applied.satisfaction
            > completion_hidden_update.applied.satisfaction
        && completion_visible_state.task_pressure < completion_hidden_state.task_pressure
        && completion_visible_state.satisfaction > completion_hidden_state.satisfaction;
    output << "completion_X_assertion=" << completion_x_assertion
           << ",completion_state_assertion=" << completion_state_assertion << '\n';
    return hidden_observation_equal && hidden_delta == 0.0
        && hidden_appraisal_equal && hidden_state_equal && hidden_support_equal
        && visible_wallet_facts_correct && visible_wallet_support_correct && visible_delta > 0.0
        && completion_visible_state.commitment.status != completion_hidden_state.commitment.status
        && completion_x_assertion && completion_state_assertion;
}

std::string Simulation::run_profile(const Personality& personality,
                                    unsigned int action_seed,
                                    unsigned int world_seed,
                                    bool include_header,
                                    int steps_per_run,
                                    bool verbose_trace,
                                    const ScenarioConfig& scenario) const {
    World world(world_seed);
    CharacterState state;
    std::mt19937 rng(action_seed);
    std::ostringstream output;
    Observation observation;
    WorldOutcome previous_outcome; // No prior action at the initial decision point.

    if (include_header) {
        output << "============================================================\n"
               << personality_summary(personality) << "\n"
               << "============================================================\n";
    }

    for (int step = 1; step <= steps_per_run; ++step) {
        const std::vector<ActionType> world_actions = world.available_actions();
        const bool was_observation_frozen = previous_outcome.observation_frozen_during_action;
        const StepRecord trace = advance_one_decision(world, state, observation, previous_outcome,
                                                     rng, personality, scenario.information_access);

        if (verbose_trace) {
            output << "\n[Decision point " << step << " | " << trace.decision_time << "]\n"
                   << "  W before action: " << trace.world_before << '\n'
                   << "  X input: Delta-O / O + old S + P"
                   << " | self_action=" << (trace.observation_at_decision.last_self_action.has_action
                       ? to_string(trace.observation_at_decision.last_self_action.action) : "none") << '\n'
                   << (was_observation_frozen
                       ? "  O refresh boundary: W advanced during sleep while O was frozen; current room perception now reconciles O.\n"
                       : "")
                   << "  " << observation_summary(trace.observation_at_decision) << '\n'
                   << "  " << action_space_summary(world_actions) << '\n'
                   << "  " << appraisal_summary(trace.appraisal) << '\n'
                   << "  " << state_update_summary(trace.state_update) << '\n'
                   << "  " << state_summary(trace.state_at_decision) << '\n'
                   << "  " << decision_summary(trace.decision)
                   << "  chosen A^char: " << to_string(trace.chosen_action) << '\n'
                   << "  planned a^world: " << world_primitives_summary(trace.action_plan.world_primitives) << '\n'
                   << "  W settlement: " << (trace.outcome.accepted ? "accepted" : "rejected")
                   << " | provenance=" << trace.outcome.provenance;
            if (!trace.outcome.object_id.empty()) {
                output << " | object=" << trace.outcome.object_id;
            }
            output << '\n';
            output << "  settled a^world: " << world_primitives_summary(trace.outcome.settled_primitives) << '\n';
            output << "  commitment after settlement: " << state_summary(trace.state_after_settlement) << '\n';
            for (const std::string& effect : trace.outcome.effects) {
                output << "    effect: " << effect << '\n';
            }
            for (const WorldEvent& event : trace.outcome.events) {
                output << "    event: id=" << event.id << " | source=" << event.source
                   << " | " << event.description << '\n';
            }
        }
        if (!trace.sleep_observation_updates.empty() && verbose_trace) {
            output << "  O partial update while asleep: " << trace.sleep_observation_updates << '\n';
        }
        if (verbose_trace) output << "  W after action: " << trace.world_after << '\n';
    }
    return output.str();
}
