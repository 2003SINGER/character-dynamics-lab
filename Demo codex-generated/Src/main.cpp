#include "simulation.h"

#include <exception>
#include <iostream>
#include <string>
#include <fstream>
#include <regex>
#include <vector>

namespace {
std::vector<unsigned int> read_seed_list(const std::string& path, const std::string& key) {
    std::ifstream input(path); if (!input) throw std::runtime_error("cannot open split manifest: " + path);
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    const std::size_t begin = text.find("\"" + key + "\"");
    if (begin == std::string::npos) throw std::runtime_error("missing split key: " + key);
    const std::size_t left = text.find('[', begin), right = text.find(']', left);
    if (left == std::string::npos || right == std::string::npos) throw std::runtime_error("invalid split list");
    std::vector<unsigned int> seeds; std::regex number("[0-9]+");
    const auto first = text.begin() + static_cast<std::ptrdiff_t>(left);
    const auto last = text.begin() + static_cast<std::ptrdiff_t>(right);
    for (std::sregex_iterator it(first, last, number), end; it != end; ++it) seeds.push_back(static_cast<unsigned int>(std::stoul(it->str())));
    return seeds;
}
}

int main(int argc, char* argv[]) {
    std::string config_path;
    for (int index = 1; index + 1 < argc; ++index) if (std::string(argv[index]) == "--config") config_path = argv[index + 1];
    Simulation simulation(config_path.empty() ? ParameterConfig::defaults() : ParameterConfig::from_json_file(config_path));

    if (argc > 1 && std::string(argv[1]) == "--verify") {
        return simulation.verify(std::cout) ? 0 : 1;
    }
    if (argc > 1 && std::string(argv[1]) == "--batch") {
        const std::string output_directory = argc > 2 ? argv[2] : "batch_output";
        try {
            std::vector<unsigned int> seeds;
            for (int index = 1; index + 1 < argc; ++index) {
                if (std::string(argv[index]) == "--split-manifest") {
                    const std::string split = index + 2 < argc && std::string(argv[index + 2]) == "--split" ? argv[index + 3] : "optimizer_train";
                    seeds = read_seed_list(argv[index + 1], split == "internal_holdout" ? "internal_holdout_world_seeds" : "optimizer_train_world_seeds");
                }
            }
            simulation.run_batch(std::cout, output_directory, seeds);
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
    if (argc > 1 && std::string(argv[1]) == "--paired-deadline") {
        const std::string output_path = argc > 2 ? argv[2] : "paired_deadline_intervention.csv";
        try {
            simulation.run_paired_deadline_intervention(std::cout, output_path);
            return 0;
        } catch (const std::exception& error) {
            std::cerr << "paired deadline intervention failed: " << error.what() << '\n';
            return 1;
        }
    }
    if (argc > 1 && std::string(argv[1]) == "--paired-commitment") {
        const std::string output_path = argc > 2 ? argv[2] : "paired_commitment_recovery.csv";
        try {
            simulation.run_paired_commitment_recovery(std::cout, output_path);
            return 0;
        } catch (const std::exception& error) {
            std::cerr << "paired commitment fixture failed: " << error.what() << '\n';
            return 1;
        }
    }

    simulation.run_all(std::cout);
    return 0;
}
