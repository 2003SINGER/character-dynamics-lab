#pragma once

#include <string>

struct Personality {
    std::string name;
    double procrastination = 0.5;
    double self_control = 0.5;
    double rest_preference = 0.5;
    double stimulation_seeking = 0.5;
    double task_anxiety_sensitivity = 0.5;
    double screen_strain_sensitivity = 0.5;
    double need_response = 0.5;
    double action_noise = 0.5;
};
