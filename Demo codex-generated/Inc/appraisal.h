#pragma once

#include "observation.h"

#include <string>
#include <vector>

// X: structured meaning of the observed world change. These values are
// illustrative rules, not claims about real psychology.
struct Appraisal {
    double boredom_delta = 0.0;
    double fatigue_delta = 0.0;
    double task_pressure_delta = 0.0;
    double satisfaction_delta = 0.0;
    std::vector<std::string> tags;
};

Appraisal appraise(const Observation& observation);
std::string appraisal_summary(const Appraisal& appraisal);
