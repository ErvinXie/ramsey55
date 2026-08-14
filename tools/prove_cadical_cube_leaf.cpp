#include "cadical.hpp"

#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

std::vector<int> readCube(const std::string& path, std::size_t target) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::string line;
  std::size_t index = 0;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == 'c') continue;
    std::istringstream fields(line);
    std::string marker;
    fields >> marker;
    if (marker != "a") {
      if (std::stoull(marker) != index) {
        throw std::runtime_error("nonconsecutive numeric cube id");
      }
    }
    std::vector<int> cube;
    int literal = 0;
    bool terminated = false;
    while (fields >> literal) {
      if (!literal) {
        terminated = true;
        break;
      }
      cube.push_back(literal);
    }
    if (!terminated || cube.empty()) {
      throw std::runtime_error("invalid cube line");
    }
    if (index++ == target) return cube;
  }
  throw std::runtime_error("cube index is out of range");
}

void appendBinaryEmptyClause(const std::string& path) {
  std::ofstream proof(path, std::ios::binary | std::ios::app);
  if (!proof) throw std::runtime_error("cannot append to proof trace");
  proof.put('a');
  proof.put('\0');
  if (!proof) throw std::runtime_error("cannot append empty proof clause");
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc != 6) {
    std::cerr << "usage: prove_cadical_cube_leaf input.cnf cubes cube-index"
                 " proof.drat result.tsv\n";
    return 2;
  }
  const std::size_t cubeIndex = std::stoull(argv[3]);
  const auto cube = readCube(argv[2], cubeIndex);

  CaDiCaL::Solver solver;
  solver.set("quiet", 1);
  if (!solver.trace_proof(argv[4])) {
    throw std::runtime_error("cannot open proof trace");
  }
  int variables = 0;
  if (const char* error = solver.read_dimacs(argv[1], variables, 1)) {
    throw std::runtime_error(error);
  }
  for (const int literal : cube) {
    if (!literal || std::abs(literal) > variables) {
      throw std::runtime_error("cube literal is outside the CNF range");
    }
    solver.assume(literal);
  }
  for (int variable = 1; variable <= variables; ++variable) {
    solver.freeze(variable);
  }

  const auto start = Clock::now();
  const int status = solver.solve();
  const double seconds =
      std::chrono::duration<double>(Clock::now() - start).count();
  int core = 0;
  if (status == 20) {
    for (const int literal : cube) core += solver.failed(literal);
    solver.conclude();
  } else if (status == 10) {
    std::cout << "model";
    for (int variable = 1; variable <= variables; ++variable) {
      std::cout << ' ' << solver.val(variable);
    }
    std::cout << " 0\n";
  } else {
    throw std::runtime_error("unbounded solve returned UNKNOWN");
  }
  solver.flush_proof_trace();
  solver.close_proof_trace();
  if (status == 20) appendBinaryEmptyClause(argv[4]);

  std::ofstream result(argv[5]);
  if (!result) throw std::runtime_error("cannot create result output");
  result << "cube\tstatus\tcore\tseconds\n";
  result << cubeIndex << '\t' << status << '\t' << core << '\t'
         << std::fixed << std::setprecision(6) << seconds << '\n';
  std::cout << "status\t" << status << '\n';
  std::cout << "cube\t" << cubeIndex << '\n';
  std::cout << "core\t" << core << '\n';
  return status;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
