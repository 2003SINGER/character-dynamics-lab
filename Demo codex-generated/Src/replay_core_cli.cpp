#include "candidate_scoring.h"
#include "state.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
inline constexpr const char* kReplayCoreVersion = "replay-core-v0";

std::vector<std::string> split_tab(const std::string& line) {
    std::vector<std::string> fields;
    std::size_t start = 0;
    while (true) {
        const std::size_t pos = line.find('\t', start);
        fields.push_back(line.substr(start, pos == std::string::npos ? pos : pos - start));
        if (pos == std::string::npos) break;
        start = pos + 1;
    }
    return fields;
}

double number(const std::string& text) {
    std::size_t used = 0;
    const double value = std::stod(text, &used);
    if (used != text.size() || !std::isfinite(value)) {
        throw std::runtime_error("invalid numeric field: " + text);
    }
    return value;
}

void append_signal(Appraisal& appraisal,
                   AppraisalSignalKind kind,
                   double intensity,
                   bool goal_related) {
    if (intensity <= 0.0) return;
    appraisal.semantic_signals.push_back({
        kind,
        std::clamp(intensity, 0.0, 1.0),
        goal_related ? 1.0 : 0.0,
        goal_related ? 1.0 : 0.0,
        0.0,
        "teacher_forced_previous_action"
    });
}
} // namespace

int main(int argc, char* argv[]) {
    if (argc > 1 && std::string(argv[1]) == "--version") {
        std::cout << kReplayCoreVersion << "|" << kReplayCandidateScorerVersion << '\n';
        return 0;
    }

    Personality personality;
    CharacterState state;
    std::string active_trajectory;
    std::string line;

    try {
        while (std::getline(std::cin, line)) {
            if (line.empty()) continue;
            const auto f = split_tab(line);

            if (f[0] == "RESET") {
                if (f.size() != 2) throw std::runtime_error("RESET expects trajectory id");
                active_trajectory = f[1];
                personality = Personality{};
                state = CharacterState{};
                continue;
            }

            if (f[0] == "UPDATE") {
                if (f.size() != 7 || f[1] != active_trajectory) {
                    throw std::runtime_error("UPDATE expects trajectory plus 5 semantic values");
                }
                Appraisal update_x;
                append_signal(update_x, AppraisalSignalKind::GoalProgress, number(f[2]), true);
                append_signal(update_x, AppraisalSignalKind::Stimulation, number(f[3]), false);
                append_signal(update_x, AppraisalSignalKind::Recovery, number(f[4]), false);
                append_signal(update_x, AppraisalSignalKind::ShortTermReward, number(f[5]), false);
                append_signal(update_x, AppraisalSignalKind::EnvironmentControl, number(f[6]), false);
                update_state(state, update_x, personality, 0);
                continue;
            }
            if (f[0] != "PREDICT" || f.size() != 4) {
                throw std::runtime_error("PREDICT expects trajectory, t, candidate_count");
            }
            if (f[1] != active_trajectory) {
                throw std::runtime_error("PREDICT trajectory differs from active RESET");
            }

            const int t = std::stoi(f[2]);

            const int candidate_count = std::stoi(f[3]);
            if (candidate_count <= 0) {
                throw std::runtime_error("invalid candidate_count");
            }

            std::vector<ExternalCandidate> candidates;
            candidates.reserve(static_cast<std::size_t>(candidate_count));
            for (int i = 0; i < candidate_count; ++i) {
                if (!std::getline(std::cin, line)) {
                    throw std::runtime_error("unexpected EOF inside candidate block");
                }
                const auto c = split_tab(line);
                if (c.size() != 10 || c[0] != "C") {
                    throw std::runtime_error("C expects 9 arguments");
                }
                CandidateSemantics s;
                s.goal_progress = number(c[1]);
                s.stimulation = number(c[2]);
                s.recovery = number(c[3]);
                s.hunger_relief = number(c[4]);
                s.bathroom_relief = number(c[5]);
                s.short_term_reward = number(c[6]);
                s.environment_control = number(c[7]);
                s.context_relevance = number(c[8]);
                candidates.push_back({std::to_string(i), s, number(c[9])});
            }

            // Prediction is dataset-neutral: RoomDemo state is retained only
            // for the teacher-forced transition trace emitted below.
            const auto scores = score_replay_candidates(candidates);
            std::cout << "RESULT\t" << active_trajectory
                      << '\t' << t
                      << '\t' << std::setprecision(17)
                      << state.boredom << '\t' << state.fatigue
                      << '\t' << state.task_pressure << '\t' << state.satisfaction
                      << '\t' << state.hunger << '\t' << state.bathroom_urge
                      << '\t' << state.anxiety << '\t' << state.screen_strain
                      << '\t' << state.purchase_urge
                      << '\t';
            for (std::size_t i = 0; i < scores.size(); ++i) {
                if (i) std::cout << ',';
                std::cout << scores[i].probability;
            }
            std::cout << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "replay core failed: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
