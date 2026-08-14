#include "cadical.hpp"

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char** argv) try {
  if (argc < 3 || argc > 4) {
    std::cerr << "usage: enumerate_primary_sat_models input.cnf primary-vars"
                 " [model-limit]\n";
    return 2;
  }
  const int primary = std::stoi(argv[2]);
  const std::uint64_t limit = argc == 4 ? std::stoull(argv[3]) : 0;
  std::ifstream input(argv[1]);
  if (!input) throw std::runtime_error("cannot open input CNF");

  CaDiCaL::Solver solver;
  solver.set("quiet", 1);
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == 'c' || line[0] == 'p') continue;
    std::istringstream literals(line);
    int literal;
    while (literals >> literal) solver.add(literal);
  }

  std::uint64_t models = 0;
  while (!limit || models < limit) {
    const int result = solver.solve();
    if (result == 20) break;
    if (result != 10) throw std::runtime_error("incremental solver returned UNKNOWN");
    std::vector<int> selected;
    for (int variable = 1; variable <= primary; ++variable) {
      if (solver.val(variable) > 0) selected.push_back(variable);
    }
    std::cout << "model";
    for (const int variable : selected) std::cout << '\t' << variable - 1;
    std::cout << '\n';
    for (const int variable : selected) solver.add(-variable);
    solver.add(0);
    ++models;
  }
  std::cout << "models\t" << models << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
