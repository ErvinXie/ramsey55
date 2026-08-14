#include "cadical.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

std::vector<std::vector<int>> readCubes(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::vector<std::vector<int>> cubes;
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == 'c') continue;
    std::istringstream fields(line);
    std::string marker;
    fields >> marker;
    if (marker != "a") {
      const std::size_t expected = cubes.size();
      if (std::stoull(marker) != expected) {
        throw std::runtime_error("nonconsecutive numeric cube id");
      }
    }
    std::vector<int> cube;
    int literal = 0;
    bool terminated = false;
    while (fields >> literal) {
      if (literal == 0) {
        terminated = true;
        break;
      }
      cube.push_back(literal);
    }
    if (!terminated || cube.empty()) {
      throw std::runtime_error("invalid cube line");
    }
    cubes.push_back(std::move(cube));
  }
  if (cubes.empty()) throw std::runtime_error("cube file is empty");
  return cubes;
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc != 6) {
    std::cerr << "usage: prove_cadical_cubes input.cnf cubes proof.drat"
                 " results.tsv conflicts\n";
    return 2;
  }
  const auto cubes = readCubes(argv[2]);
  const int conflictLimit = std::stoi(argv[5]);
  if (conflictLimit <= 0) throw std::runtime_error("invalid conflict limit");
  CaDiCaL::Solver solver;
  solver.set("quiet", 1);
  if (!solver.trace_proof(argv[3])) {
    throw std::runtime_error("cannot open proof trace");
  }
  int variables = 0;
  if (const char* error = solver.read_dimacs(argv[1], variables, 1)) {
    throw std::runtime_error(error);
  }
  for (const auto& cube : cubes) {
    for (const int literal : cube) {
      if (literal == 0 || std::abs(literal) > variables) {
        throw std::runtime_error("cube literal is outside the CNF range");
      }
    }
  }
  for (int variable = 1; variable <= variables; ++variable) {
    solver.freeze(variable);
  }

  std::ofstream report(argv[4]);
  if (!report) throw std::runtime_error("cannot create result output");
  report << "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n";
  report << std::fixed << std::setprecision(6);
  bool globallyUnsat = false;
  std::size_t attempts = 0;
  std::size_t splits = 0;
  int maximumDepth = 0;

  const auto printModel = [&] {
    std::cout << "model";
    for (int variable = 1; variable <= variables; ++variable) {
      std::cout << ' ' << solver.val(variable);
    }
    std::cout << " 0\n";
  };

  std::function<int(std::size_t, std::vector<int>&, int)> proveCube;
  proveCube = [&](std::size_t root, std::vector<int>& cube, int depth) {
    if (depth > 1024) throw std::runtime_error("dynamic cube depth exceeded 1024");
    maximumDepth = std::max(maximumDepth, depth);
    const int shift =
        depth < 512 ? 0 : std::min(7 + (depth - 512) / 16, 10);
    const long long scaledLimit =
        static_cast<long long>(conflictLimit) << shift;
    const int effectiveLimit = static_cast<int>(
        std::min<long long>(scaledLimit, 1'000'000'000));
    for (const int literal : cube) solver.assume(literal);
    if (!solver.limit("conflicts", effectiveLimit)) {
      throw std::runtime_error("conflict limit rejected");
    }
    const auto start = Clock::now();
    const int status = solver.solve();
    const double seconds =
        std::chrono::duration<double>(Clock::now() - start).count();
    const std::size_t attempt = attempts++;
    if (status == 10) {
      report << root << '\t' << attempt << '\t' << depth << '\t'
             << effectiveLimit << "\t10\t0\t0\t" << seconds << '\n';
      solver.conclude();
      printModel();
      return 10;
    }
    if (status == 20) {
      int core = 0;
      for (const int literal : cube) core += solver.failed(literal);
      solver.conclude();
      report << root << '\t' << attempt << '\t' << depth << '\t'
             << effectiveLimit << "\t20\t" << core << "\t0\t" << seconds
             << '\n';
      globallyUnsat |= core == 0;
      return 20;
    }
    if (status != 0) throw std::runtime_error("invalid solve status");

    for (const int literal : cube) solver.assume(literal);
    const auto lookaheadStart = Clock::now();
    const int split = solver.lookahead();
    const double lookaheadSeconds = std::chrono::duration<double>(
        Clock::now() - lookaheadStart).count();
    const int lookaheadStatus = solver.status();
    if (lookaheadStatus == 10) {
      report << root << '\t' << attempt << '\t' << depth << '\t'
             << effectiveLimit << "\t10\t0\t0\t"
             << seconds + lookaheadSeconds << '\n';
      solver.conclude();
      printModel();
      return 10;
    }
    if (lookaheadStatus == 20) {
      int core = 0;
      for (const int literal : cube) core += solver.failed(literal);
      solver.conclude();
      report << root << '\t' << attempt << '\t' << depth << '\t'
             << effectiveLimit << "\t20\t" << core << "\t0\t"
             << seconds + lookaheadSeconds << '\n';
      globallyUnsat |= core == 0;
      return 20;
    }
    if (split == 0 || std::abs(split) > variables) {
      throw std::runtime_error("lookahead did not return a split literal");
    }
    for (const int literal : cube) {
      if (std::abs(literal) == std::abs(split)) {
        throw std::runtime_error("lookahead repeated a cube variable");
      }
    }
    report << root << '\t' << attempt << '\t' << depth << '\t'
           << effectiveLimit << "\t0\t0\t" << split << '\t'
           << seconds + lookaheadSeconds << '\n';
    ++splits;
    cube.push_back(split);
    if (proveCube(root, cube, depth + 1) != 20) return 10;
    cube.back() = -split;
    if (proveCube(root, cube, depth + 1) != 20) return 10;
    cube.pop_back();
    return 20;
  };

  for (std::size_t index = 0; index < cubes.size(); ++index) {
    auto cube = cubes[index];
    if (proveCube(index, cube, 0) == 10) {
      solver.flush_proof_trace();
      solver.close_proof_trace();
      return 10;
    }
    if (globallyUnsat) break;
    if ((index + 1) % 256 == 0 || index + 1 == cubes.size()) {
      std::cout << "finished\t" << index + 1 << '/' << cubes.size()
                << " attempts=" << attempts << " splits=" << splits
                << std::endl;
    }
  }
  if (!globallyUnsat) {
    const int status = solver.solve();
    if (status == 10) {
      solver.conclude();
      solver.close_proof_trace();
      std::cout << "uncovered_model\t1\n";
      return 10;
    }
    if (status != 20) throw std::runtime_error("final solve returned UNKNOWN");
    solver.conclude();
  }
  solver.flush_proof_trace();
  solver.close_proof_trace();
  std::cout << "status\t20\n";
  std::cout << "cubes\t" << cubes.size() << '\n';
  std::cout << "attempts\t" << attempts << '\n';
  std::cout << "splits\t" << splits << '\n';
  std::cout << "maximum_extra_depth\t" << maximumDepth << '\n';
  return 20;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
