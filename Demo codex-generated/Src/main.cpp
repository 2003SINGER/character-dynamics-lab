#include "simulation.h"

#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    Simulation simulation;

    if (argc > 1 && std::string(argv[1]) == "--verify") {
        return simulation.verify(std::cout) ? 0 : 1;
    }

    simulation.run_all(std::cout);
    return 0;
}
