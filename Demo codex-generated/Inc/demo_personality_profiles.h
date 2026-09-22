#pragma once

#include "personality.h"

#include <array>
#include <stdexcept>
#include <string>

namespace DemoPersonalityProfiles {
inline const std::array<std::string, 8>& names() {
    static const std::array<std::string, 8> values = {
        "balanced", "disciplined", "procrastinating", "rest_seeking",
        "stimulation_seeking", "anxious", "body_sensitive", "spontaneous"};
    return values;
}

inline Personality named(const std::string& name) {
    static const std::array<std::array<double, 8>, 8> values = {{
        {{.5,.5,.5,.5,.5,.5,.5,.5}},
        {{.2,.8,.4,.35,.4,.5,.6,.25}},
        {{.8,.3,.5,.7,.65,.5,.5,.55}},
        {{.5,.45,.8,.4,.45,.5,.65,.35}},
        {{.65,.4,.35,.85,.45,.5,.45,.65}},
        {{.55,.5,.55,.5,.85,.55,.65,.4}},
        {{.45,.55,.6,.4,.5,.65,.9,.35}},
        {{.5,.45,.5,.65,.5,.5,.5,.9}}
    }};
    for (std::size_t i=0; i<names().size(); ++i) {
        if (names()[i] != name) continue;
        const auto& v=values[i];
        Personality p;
        p.name=name;
        p.procrastination=v[0]; p.self_control=v[1];
        p.rest_preference=v[2]; p.stimulation_seeking=v[3];
        p.task_anxiety_sensitivity=v[4]; p.screen_strain_sensitivity=v[5];
        p.need_response=v[6]; p.action_noise=v[7];
        return p;
    }
    throw std::invalid_argument("unknown demo profile: " + name);
}

inline void set_axis(Personality& p, const std::string& axis, double value) {
    if (value<0.0 || value>1.0) throw std::invalid_argument("personality axis outside [0,1]");
    if (axis=="procrastination") p.procrastination=value;
    else if (axis=="self_control") p.self_control=value;
    else if (axis=="rest_preference") p.rest_preference=value;
    else if (axis=="stimulation_seeking") p.stimulation_seeking=value;
    else if (axis=="task_anxiety_sensitivity") p.task_anxiety_sensitivity=value;
    else if (axis=="screen_strain_sensitivity") p.screen_strain_sensitivity=value;
    else if (axis=="need_response") p.need_response=value;
    else if (axis=="action_noise") p.action_noise=value;
    else throw std::invalid_argument("unknown personality axis: " + axis);
    p.name="balanced:" + axis + "=" + std::to_string(value);
}
} // namespace DemoPersonalityProfiles
