#include "candidate_scoring.h"
#include "state.h"

#include <cmath>
#include <iostream>

int main() {
    Personality p;

    CharacterState completion_state;
    Appraisal completion;
    completion.semantic_signals.push_back({
        AppraisalSignalKind::GoalCompletion, 1.0, 1.0, 1.0, 1.0, "fixture"
    });
    const auto completion_update = update_state(completion_state, completion, p, 0);
    if (!(completion_update.semantic_contribution.task_pressure < 0.0
          && completion_state.task_pressure < 0.55)) {
        std::cerr << "GoalCompletion X-U-S failed\n";
        return 1;
    }

    CharacterState progress_state;
    Appraisal progress;
    progress.semantic_signals.push_back({
        AppraisalSignalKind::GoalProgress, 1.0, 1.0, 1.0, 0.0, "fixture"
    });
    const auto progress_update = update_state(progress_state, progress, p, 0);
    if (!(progress_update.semantic_contribution.task_pressure < 0.0)) {
        std::cerr << "GoalProgress X-U-S failed\n";
        return 1;
    }

    CharacterState noop_a, noop_b;
    Appraisal ca, cb;
    ca.semantic_signals.push_back({
        AppraisalSignalKind::EnvironmentControl, 0.5, 0.0, 0.0, 0.0, "fixture"
    });
    cb.semantic_signals.push_back({
        AppraisalSignalKind::EnvironmentControl, 0.5, 0.0, 0.0, 1.0, "fixture"
    });
    update_state(noop_a, ca, p, 0);
    update_state(noop_b, cb, p, 0);
    if (std::abs(noop_a.satisfaction - noop_b.satisfaction) > 1e-12) {
        std::cerr << "controllability should be an explicit no-op in v0\n";
        return 1;
    }

    auto scores = score_external_candidates({
        {"work", {1,0,0,0,0,0,0}, 0},
        {"scroll", {0,1,0,0,0,0,0}, 0}
    }, completion_state, p);
    double z = 0.0;
    for (const auto& x : scores) z += x.probability;
    if (scores.size() != 2 || std::abs(z - 1.0) > 1e-9) {
        std::cerr << "candidate scorer normalization failed\n";
        return 1;
    }

    std::cout << "core experiment smoke OK\n";
    return 0;
}
