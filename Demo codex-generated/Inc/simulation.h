#pragma once

#include "personality.h"

#include <iosfwd>
#include <string>

class Simulation {
public:
    void run_all(std::ostream& output) const;
    bool verify(std::ostream& output) const;

private:
    std::string run_profile(const Personality& personality,
                            unsigned int seed,
                            bool include_header) const;
};
