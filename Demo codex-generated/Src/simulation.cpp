#include "simulation.h"

#include "appraisal.h"
#include "decision.h"
#include "observation.h"
#include "state.h"
#include "world.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <ostream>
#include <random>
#include <sstream>
#include <stdexcept>
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

struct TaskSnapshot {
    double effort = 0.0;
    double target = 0.0;
    std::string status = "missing";
};

TaskSnapshot coursework_snapshot(const World& world) {
    if (const WorldTask* task = world.task_by_id("coursework")) {
        return {task->effort_done, task->effort_target, task_status_name(task->status)};
    }
    return {};
}

struct StepTrace {
    std::string decision_time;
    std::string world_before;
    Observation observation_at_decision;
    Appraisal appraisal;
    StateUpdate state_update;
    CharacterState state_at_decision;
    TaskSnapshot task_before;
    DecisionContext decision;
    ActionType chosen_action = ActionType::Idle;
    CharacterActionPlan action_plan;
    WorldOutcome outcome;
    CharacterState state_after_settlement;
    TaskSnapshot task_after;
    std::string sleep_observation_updates;
    std::string world_after;
};

StepTrace advance_one_decision(World& world,
                               CharacterState& state,
                               Observation& observation,
                               WorldOutcome& previous_outcome,
                               std::mt19937& action_rng,
                               const Personality& personality) {
    StepTrace trace;
    observation = refresh_observation(std::move(observation), world, previous_outcome);
    trace.observation_at_decision = observation;
    trace.decision_time = world.time_summary();
    trace.world_before = world.summary();
    trace.appraisal = appraise(observation, state, personality);
    clear_pending_appraisal_updates(observation);
    trace.state_update = update_state(state, trace.appraisal, personality, previous_outcome.elapsed_minutes);
    trace.state_at_decision = state;
    trace.task_before = coursework_snapshot(world);
    trace.decision = decide(observation, state, personality);
    trace.chosen_action = sample_action(trace.decision, action_rng);
    trace.action_plan = world.expand_action(trace.chosen_action);
    trace.outcome = world.settle(trace.chosen_action);
    update_commitment(state, trace.outcome, total_minutes(world.time));
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
            World world(scenario_seed);
            CharacterState state;
            Observation observation;
            WorldOutcome previous_outcome;
            std::mt19937 action_rng(action_seed);

            for (int step = 1; step <= kBatchStepsPerRun; ++step) {
                const StepTrace trace = advance_one_decision(world, state, observation, previous_outcome, action_rng, personality);
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
    World stale_object_world;
    Observation object_observation = refresh_observation({}, stale_object_world, {});
    for (Object& object : stale_object_world.current_room().objects) {
        if (object.id == "phone") object.usable = false;
    }
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
    const WorldOutcome first_study = commitment_world.settle(ActionType::StudyFocused);
    update_commitment(commitment_state, first_study, total_minutes(commitment_world.time));
    const bool starts_task_commitment = commitment_state.commitment.status == CommitmentStatus::Active
                                     && commitment_state.commitment.task_id == "coursework";
    const WorldOutcome meal = commitment_world.settle(ActionType::GetMeal);
    update_commitment(commitment_state, meal, total_minutes(commitment_world.time));
    const bool suspends_for_bodily_need = commitment_state.commitment.status == CommitmentStatus::Suspended;
    const WorldOutcome resumed_study = commitment_world.settle(ActionType::StudyAtComputer);
    update_commitment(commitment_state, resumed_study, total_minutes(commitment_world.time));
    const bool resumes_task_commitment = commitment_state.commitment.status == CommitmentStatus::Active;
    World completion_world;
    WorldTask* completion_task = completion_world.task_by_id("coursework");
    completion_task->effort_target = 0.10;
    const WorldOutcome completing_study = completion_world.settle(ActionType::StudyFocused);
    update_commitment(commitment_state, completing_study, total_minutes(completion_world.time));
    const bool completes_task_with_variable_effort = completing_study.task_completed
        && completing_study.task_effort_gained != 1.0 && commitment_state.commitment.status == CommitmentStatus::None;
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

    output << "verify: reproducible=" << reproducible
           << ", profile_sensitive=" << profile_sensitive
           << ", rejects_illegal_action=" << validates_world
           << ", trace_has_primitives=" << has_primitives
           << ", primitives_settle=" << primitives_settle
           << ", interruption_rewrites_plan=" << handles_interruption
           << ", completed_task_stays_quiet=" << completed_task_stays_quiet
           << ", deduplicates_actions=" << deduplicates_actions
           << ", preserves_rejected_feedback=" << preserves_rejected_feedback
           << ", marks_absent_object_stale=" << marks_absent_object_stale
           << ", reports_applied_delta=" << reports_applied_delta
           << ", starts_task_commitment=" << starts_task_commitment
           << ", suspends_for_bodily_need=" << suspends_for_bodily_need
           << ", resumes_task_commitment=" << resumes_task_commitment
           << ", completes_task_with_variable_effort=" << completes_task_with_variable_effort
           << ", deadline_is_observable=" << deadline_is_observable
           << ", gates_suspended_return=" << gates_suspended_return << '\n';
    return reproducible && profile_sensitive && validates_world && has_primitives
        && primitives_settle && handles_interruption && completed_task_stays_quiet && deduplicates_actions
        && preserves_rejected_feedback && marks_absent_object_stale && reports_applied_delta
        && starts_task_commitment && suspends_for_bodily_need && resumes_task_commitment
        && completes_task_with_variable_effort && deadline_is_observable && gates_suspended_return;
}

std::string Simulation::run_profile(const Personality& personality,
                                    unsigned int action_seed,
                                    unsigned int world_seed,
                                    bool include_header,
                                    int steps_per_run,
                                    bool verbose_trace) const {
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
        const StepTrace trace = advance_one_decision(world, state, observation, previous_outcome, rng, personality);

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
