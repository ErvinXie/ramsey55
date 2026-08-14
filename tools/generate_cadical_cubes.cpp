#include "cadical.hpp"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) try {
  if (argc < 4 || argc > 6) {
    std::cerr << "usage: generate_cadical_cubes input.cnf depth output.cubes"
                 " [min-depth] [--allow-elimination]\n";
    return 2;
  }
  const int depth = std::stoi(argv[2]);
  int minDepth = 0;
  bool freezeVariables = true;
  for (int argument = 4; argument < argc; ++argument) {
    const std::string option = argv[argument];
    if (option == "--allow-elimination") {
      freezeVariables = false;
    } else {
      minDepth = std::stoi(option);
    }
  }
  if (depth < 0 || depth > 30 || minDepth < 0 || minDepth > depth) {
    throw std::runtime_error("invalid cube depth");
  }

  CaDiCaL::Solver solver;
  solver.set("quiet", 1);
  int variables = 0;
  if (const char* error = solver.read_dimacs(argv[1], variables, 1)) {
    throw std::runtime_error(error);
  }
  // Keep the public DIMACS numbering stable.  This also makes the emitted
  // assumptions directly reusable by independent command-line solvers.
  if (freezeVariables) {
    for (int variable = 1; variable <= variables; ++variable) {
      solver.freeze(variable);
    }
  }

  const auto result = solver.generate_cubes(depth, minDepth);
  std::ofstream output(argv[3]);
  if (!output) throw std::runtime_error("cannot create cube output");
  for (const auto& cube : result.cubes) {
    output << "a";
    for (const int literal : cube) {
      if (literal == 0 || std::abs(literal) > variables) {
        throw std::runtime_error("CaDiCaL returned an invalid cube literal");
      }
      output << ' ' << literal;
    }
    output << " 0\n";
  }
  std::cout << "status\t" << result.status << '\n';
  std::cout << "variables\t" << variables << '\n';
  std::cout << "cubes\t" << result.cubes.size() << '\n';
  return result.status == 10 ? 10 : result.status == 20 ? 20 : 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
