#include "cadical.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char **argv) try {
  if (argc != 4) {
    std::cerr << "usage: cadical_assumption_scan formula.cnf cubes.txt conflicts\n";
    return 2;
  }
  const int limit = std::stoi(argv[3]);
  if (limit <= 0) throw std::runtime_error("conflict limit must be positive");
  CaDiCaL::Solver solver;
  solver.set("quiet", 1);
  int variables = 0;
  if (const char *error = solver.read_dimacs(argv[1], variables, 1))
    throw std::runtime_error(error);
  std::ifstream input(argv[2]);
  if (!input) throw std::runtime_error("cannot open cube file");
  std::cout << "cube\tstatus\tseconds\n";
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == 'c') continue;
    std::istringstream fields(line);
    int cube = -1, literal = 0;
    fields >> cube;
    if (cube < 0) throw std::runtime_error("invalid cube id");
    std::vector<int> assumptions;
    while (fields >> literal && literal) assumptions.push_back(literal);
    if (literal != 0 || assumptions.empty()) throw std::runtime_error("bad cube line");
    for (const int assumption : assumptions) solver.assume(assumption);
    if (!solver.limit("conflicts", limit)) throw std::runtime_error("limit rejected");
    const auto start = std::chrono::steady_clock::now();
    const int status = solver.solve();
    const double seconds = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
    std::cout << cube << '\t' << status << '\t' << seconds << '\n' << std::flush;
    if (status == 10) {
      std::cout << "model";
      for (int variable = 1; variable <= 990; ++variable)
        std::cout << ' ' << solver.val(variable);
      std::cout << " 0\n";
      return 10;
    }
  }
  return 0;
} catch (const std::exception &error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
