#include "simulation.h"

#include <exception>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    Simulation simulation;

    if (argc > 1 && std::string(argv[1]) == "--verify") {
        return simulation.verify(std::cout) ? 0 : 1;
    }
    if (argc > 1 && std::string(argv[1]) == "--batch") {
        const std::string output_directory = argc > 2 ? argv[2] : "batch_output";
        try {
            simulation.run_batch(std::cout, output_directory);
            return 0;
        } catch (const std::exception& error) {
            std::cerr << "batch failed: " << error.what() << '\n';
            return 1;
        }
    }
    if (argc > 1 && std::string(argv[1]) == "--e0") {
        return simulation.run_e0(std::cout) ? 0 : 1;
    }
    if (argc > 1 && std::string(argv[1]) == "--paired-phone") {
        const std::string output_path = argc > 2 ? argv[2] : "paired_phone_intervention.csv";
        try {
            simulation.run_paired_phone_intervention(std::cout, output_path);
            return 0;
        } catch (const std::exception& error) {
            std::cerr << "paired phone intervention failed: " << error.what() << '\n';
            return 1;
        }
    }

    simulation.run_all(std::cout);
    return 0;
}
