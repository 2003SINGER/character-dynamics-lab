#pragma once

#include <string>

// Do not call this header "time.h": a project header with that name can
// shadow the C standard header that libstdc++ itself needs.
struct SimTime {
    int day = 1;
    int minute_of_day = 8 * 60;
};

int total_minutes(const SimTime& time);
void advance_minutes(SimTime& time, int elapsed_minutes);
std::string time_summary(const SimTime& time);
