#include "simulation_time.h"

#include <iomanip>
#include <sstream>

int total_minutes(const SimTime& time) {
    return (time.day - 1) * 24 * 60 + time.minute_of_day;
}

void advance_minutes(SimTime& time, int elapsed_minutes) {
    const int advanced = total_minutes(time) + elapsed_minutes;
    time.day = advanced / (24 * 60) + 1;
    time.minute_of_day = advanced % (24 * 60);
}

std::string time_summary(const SimTime& time) {
    std::ostringstream output;
    output << "Day " << time.day << ' ' << std::setw(2) << std::setfill('0') << time.minute_of_day / 60
           << ':' << std::setw(2) << std::setfill('0') << time.minute_of_day % 60;
    return output.str();
}
