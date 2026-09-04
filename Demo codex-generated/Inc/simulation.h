#pragma once

#include "personality.h"

#include <iosfwd>
#include <string>
#include <vector>

class Simulation {
public:
    void run_all(std::ostream& output) const;
    void run_batch(std::ostream& output, const std::string& output_directory) const;
    bool verify(std::ostream& output) const;

private:
    std::string run_profile(const Personality& personality,
                            unsigned int action_seed,
                            unsigned int world_seed,
                            bool include_header,
                            int steps_per_run = 12,
                            bool verbose_trace = true) const;
    static std::vector<Personality> generate_personalities(std::size_t count, unsigned int seed);
};
