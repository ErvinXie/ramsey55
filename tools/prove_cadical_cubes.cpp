#include "cadical.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

class DeadlineTerminator : public CaDiCaL::Terminator {
 public:
  void start(double seconds) {
    deadline_ = Clock::now() +
                std::chrono::duration_cast<Clock::duration>(
                    std::chrono::duration<double>(seconds));
    enabled_ = true;
  }

  void stop() { enabled_ = false; }

  void setGlobal(double seconds) {
    if (seconds <= 0.0) return;
    globalDeadline_ = Clock::now() +
                      std::chrono::duration_cast<Clock::duration>(
                          std::chrono::duration<double>(seconds));
    globalEnabled_ = true;
  }

  bool globalExpired() const {
    return globalEnabled_ && Clock::now() >= globalDeadline_;
  }

  bool terminate() override {
    return globalExpired() || (enabled_ && Clock::now() >= deadline_);
  }

 private:
  bool enabled_ = false;
  Clock::time_point deadline_{};
  bool globalEnabled_ = false;
  Clock::time_point globalDeadline_{};
};

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

std::vector<int> rankPrimaryVariables(const std::string& path, int limit) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::vector<std::size_t> occurrences(limit + 1);
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == 'c' || line[0] == 'p') continue;
    std::istringstream fields(line);
    int literal = 0;
    while (fields >> literal && literal) {
      const int variable = std::abs(literal);
      if (variable <= limit) ++occurrences[variable];
    }
  }
  std::vector<int> variables(limit);
  std::iota(variables.begin(), variables.end(), 1);
  std::sort(variables.begin(), variables.end(), [&](int left, int right) {
    if (occurrences[left] != occurrences[right]) {
      return occurrences[left] > occurrences[right];
    }
    return left < right;
  });
  return variables;
}

void appendBinaryEmptyClause(const std::string& path) {
  std::ofstream proof(path, std::ios::binary | std::ios::app);
  if (!proof) throw std::runtime_error("cannot append to proof trace");
  proof.put('a');
  proof.put('\0');
  if (!proof) throw std::runtime_error("cannot append empty proof clause");
}

int environmentInteger(const char* name, int fallback, int minimum,
                       int maximum) {
  const char* raw = std::getenv(name);
  if (!raw || !*raw) return fallback;
  std::size_t consumed = 0;
  const long long value = std::stoll(raw, &consumed);
  if (raw[consumed] || value < minimum || value > maximum) {
    throw std::runtime_error(std::string("invalid ") + name);
  }
  return static_cast<int>(value);
}

double environmentSeconds(const char* name) {
  const char* raw = std::getenv(name);
  if (!raw || !*raw) return 0.0;
  std::size_t consumed = 0;
  const double value = std::stod(raw, &consumed);
  if (raw[consumed] || !std::isfinite(value) || value < 0.0) {
    throw std::runtime_error(std::string("invalid ") + name);
  }
  return value;
}

}  // namespace

int main(int argc, char** argv) try {
  const bool fragmentMode =
      argc > 1 && std::string(argv[argc - 1]) == "--fragment";
  const int argumentCount = argc - (fragmentMode ? 1 : 0);
  if (argumentCount < 6 || argumentCount > 11) {
    std::cerr << "usage: prove_cadical_cubes input.cnf cubes proof.drat"
                 " results.tsv conflicts [maximum-conflicts]"
                 " [maximum-lookahead-seconds]"
                 " [maximum-primary-split-variable]"
                 " [maximum-solve-seconds] [root-index] [--fragment]\n";
    return 2;
  }
  const auto cubes = readCubes(argv[2]);
  const int conflictLimit = std::stoi(argv[5]);
  if (conflictLimit <= 0) throw std::runtime_error("invalid conflict limit");
  const int maximumConflictLimit =
      argumentCount >= 7 ? std::stoi(argv[6]) : 1'000'000'000;
  if (maximumConflictLimit < conflictLimit) {
    throw std::runtime_error("maximum conflict limit is below base limit");
  }
  const double maximumLookaheadSeconds =
      argumentCount >= 8 ? std::stod(argv[7]) : 0.0;
  if (maximumLookaheadSeconds < 0.0) {
    throw std::runtime_error("negative maximum lookahead time");
  }
  const int maximumPrimarySplitVariable =
      argumentCount >= 9 ? std::stoi(argv[8]) : 0;
  if (maximumPrimarySplitVariable < 0) {
    throw std::runtime_error("negative maximum primary split variable");
  }
  const double maximumSolveSeconds =
      argumentCount >= 10 ? std::stod(argv[9]) : 0.0;
  if (maximumSolveSeconds < 0.0) {
    throw std::runtime_error("negative maximum solve time");
  }
  const bool rootOnly = argumentCount == 11;
  const std::size_t selectedRoot = rootOnly ? std::stoull(argv[10]) : 0;
  if (rootOnly && selectedRoot >= cubes.size()) {
    throw std::runtime_error("root index is out of range");
  }
  const int randomSeed = environmentInteger(
      "RAMSEY55_CADICAL_SEED", 0, 0, 2'000'000'000);
  const int initialPhase =
      environmentInteger("RAMSEY55_CADICAL_PHASE", 1, 0, 1);
  const double maximumWallSeconds =
      environmentSeconds("RAMSEY55_CADICAL_WALL_SECONDS");
  std::cout << "conflicts\t" << conflictLimit << '\n';
  std::cout << "maximum_conflicts\t" << maximumConflictLimit << '\n';
  std::cout << "maximum_lookahead_seconds\t" << maximumLookaheadSeconds
            << '\n';
  std::cout << "maximum_primary_split_variable\t"
            << maximumPrimarySplitVariable << '\n';
  std::cout << "maximum_solve_seconds\t" << maximumSolveSeconds << '\n';
  std::cout << "maximum_wall_seconds\t" << maximumWallSeconds << '\n';
  std::cout << "freeze_policy\tselective\n";
  std::cout << "cadical_seed\t" << randomSeed << '\n';
  std::cout << "cadical_phase\t" << initialPhase << '\n';
  std::cout << "proof_fragment\t" << fragmentMode << '\n';
  std::cout << "root_index\t";
  if (rootOnly) {
    std::cout << selectedRoot;
  } else {
    std::cout << "all";
  }
  std::cout << std::endl;
  DeadlineTerminator terminator;
  terminator.setGlobal(maximumWallSeconds);
  CaDiCaL::Solver solver;
  if (maximumLookaheadSeconds > 0.0 || maximumSolveSeconds > 0.0 ||
      maximumWallSeconds > 0.0) {
    solver.connect_terminator(&terminator);
  }
  solver.set("quiet", 1);
  solver.set("seed", randomSeed);
  solver.set("phase", initialPhase);
  if (!solver.trace_proof(argv[3])) {
    throw std::runtime_error("cannot open proof trace");
  }
  int variables = 0;
  if (const char* error = solver.read_dimacs(argv[1], variables, 1)) {
    throw std::runtime_error(error);
  }
  if (maximumPrimarySplitVariable > variables) {
    throw std::runtime_error("primary split variable is outside the CNF range");
  }
  const auto primaryVariables =
      rankPrimaryVariables(argv[1], maximumPrimarySplitVariable);
  for (const auto& cube : cubes) {
    for (const int literal : cube) {
      if (literal == 0 || std::abs(literal) > variables) {
        throw std::runtime_error("cube literal is outside the CNF range");
      }
    }
  }
  std::vector<bool> frozen(variables + 1);
  std::size_t frozenVariables = 0;
  const auto freezeVariable = [&](int variable) {
    if (!frozen[variable]) {
      solver.freeze(variable);
      frozen[variable] = true;
      ++frozenVariables;
    }
  };
  for (const auto& cube : cubes) {
    for (const int literal : cube) freezeVariable(std::abs(literal));
  }
  for (int variable = 1; variable <= maximumPrimarySplitVariable; ++variable) {
    freezeVariable(variable);
  }
  std::cout << "initial_frozen_variables\t" << frozenVariables << std::endl;

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

  struct PendingCube {
    std::vector<int> literals;
    int depth;
  };
  const auto proveRoot = [&](std::size_t root,
                             const std::vector<int>& initialCube) {
    std::vector<PendingCube> pending{{initialCube, 0}};
    while (!pending.empty()) {
      if (terminator.globalExpired()) return 0;
      PendingCube node = std::move(pending.back());
      pending.pop_back();
      auto& cube = node.literals;
      const int depth = node.depth;
      maximumDepth = std::max(maximumDepth, depth);
      const int shift =
          depth < 512 ? 0 : std::min(7 + (depth - 512) / 16, 10);
      const long long scaledLimit =
          static_cast<long long>(conflictLimit) << shift;
      const int effectiveLimit = static_cast<int>(
          std::min<long long>(scaledLimit, maximumConflictLimit));
      for (const int literal : cube) solver.assume(literal);
      if (!solver.limit("conflicts", effectiveLimit)) {
        throw std::runtime_error("conflict limit rejected");
      }
      if (maximumSolveSeconds > 0.0) terminator.start(maximumSolveSeconds);
      const auto start = Clock::now();
      const int status = solver.solve();
      terminator.stop();
      const double seconds =
          std::chrono::duration<double>(Clock::now() - start).count();
      const std::size_t attempt = attempts;
      if (status == 10) {
        ++attempts;
        report << root << '\t' << attempt << '\t' << depth << '\t'
               << effectiveLimit << "\t10\t0\t0\t" << seconds << '\n'
               << std::flush;
        solver.conclude();
        printModel();
        return 10;
      }
      if (status == 20) {
        ++attempts;
        int core = 0;
        for (const int literal : cube) core += solver.failed(literal);
        solver.conclude();
        report << root << '\t' << attempt << '\t' << depth << '\t'
               << effectiveLimit << "\t20\t" << core << "\t0\t" << seconds
               << '\n'
               << std::flush;
        globallyUnsat |= core == 0;
        continue;
      }
      if (status != 0) throw std::runtime_error("invalid solve status");
      if (terminator.globalExpired()) return 0;

      for (const int literal : cube) solver.assume(literal);
      if (maximumLookaheadSeconds > 0.0) {
        terminator.start(maximumLookaheadSeconds);
      }
      const auto lookaheadStart = Clock::now();
      int split = solver.lookahead();
      terminator.stop();
      const double lookaheadSeconds = std::chrono::duration<double>(
          Clock::now() - lookaheadStart).count();
      const int lookaheadStatus = solver.status();
      if (lookaheadStatus == 10) {
        ++attempts;
        report << root << '\t' << attempt << '\t' << depth << '\t'
               << effectiveLimit << "\t10\t0\t0\t"
               << seconds + lookaheadSeconds << '\n'
               << std::flush;
        solver.conclude();
        printModel();
        return 10;
      }
      if (lookaheadStatus == 20) {
        ++attempts;
        int core = 0;
        for (const int literal : cube) core += solver.failed(literal);
        solver.conclude();
        report << root << '\t' << attempt << '\t' << depth << '\t'
               << effectiveLimit << "\t20\t" << core << "\t0\t"
               << seconds + lookaheadSeconds << '\n'
               << std::flush;
        globallyUnsat |= core == 0;
        continue;
      }
      if (terminator.globalExpired()) return 0;
      if (maximumPrimarySplitVariable &&
          std::abs(split) > maximumPrimarySplitVariable) {
        const auto unused = std::find_if(
            primaryVariables.begin(), primaryVariables.end(), [&](int variable) {
              return std::none_of(cube.begin(), cube.end(), [&](int literal) {
                return std::abs(literal) == variable;
              });
            });
        if (unused != primaryVariables.end()) split = *unused;
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
             << seconds + lookaheadSeconds << '\n'
             << std::flush;
      ++attempts;
      ++splits;
      freezeVariable(std::abs(split));
      auto negativeCube = cube;
      negativeCube.push_back(-split);
      cube.push_back(split);
      // LIFO order preserves the recursive runner's positive-then-negative
      // preorder traversal while avoiding a host-language recursion limit.
      pending.push_back({std::move(negativeCube), depth + 1});
      pending.push_back({std::move(cube), depth + 1});
    }
    return 20;
  };

  const std::size_t firstRoot = selectedRoot;
  const std::size_t lastRoot = rootOnly ? firstRoot + 1 : cubes.size();
  for (std::size_t index = firstRoot; index < lastRoot; ++index) {
    const int rootStatus = proveRoot(index, cubes[index]);
    if (rootStatus == 10) {
      solver.flush_proof_trace();
      solver.close_proof_trace();
      return 10;
    }
    if (rootStatus == 0) {
      solver.flush_proof_trace();
      solver.close_proof_trace();
      std::cout << "checkpoint\t1\n";
      std::cout << "status\t0\n";
      std::cout << "attempts\t" << attempts << '\n';
      std::cout << "splits\t" << splits << '\n';
      std::cout << "maximum_extra_depth\t" << maximumDepth << '\n';
      return 0;
    }
    if (globallyUnsat) break;
    if ((index + 1) % 256 == 0 || index + 1 == cubes.size()) {
      std::cout << "finished\t" << index + 1 << '/' << cubes.size()
                << " attempts=" << attempts << " splits=" << splits
                << std::endl;
    }
  }
  if (fragmentMode) {
    solver.flush_proof_trace();
    solver.close_proof_trace();
    std::cout << "status\t20\n";
    std::cout << "cubes\t" << (lastRoot - firstRoot) << '\n';
    std::cout << "attempts\t" << attempts << '\n';
    std::cout << "splits\t" << splits << '\n';
    std::cout << "maximum_extra_depth\t" << maximumDepth << '\n';
    return 20;
  }
  if (rootOnly) {
    const auto& cube = cubes[selectedRoot];
    for (const int literal : cube) solver.assume(literal);
    const int status = solver.solve();
    if (status == 10) {
      solver.conclude();
      solver.close_proof_trace();
      std::cout << "uncovered_model\t1\n";
      return 10;
    }
    if (status != 20) {
      throw std::runtime_error("final root solve returned UNKNOWN");
    }
    int core = 0;
    for (const int literal : cube) core += solver.failed(literal);
    solver.conclude();
    solver.flush_proof_trace();
    solver.close_proof_trace();
    appendBinaryEmptyClause(argv[3]);
    std::cout << "status\t20\n";
    std::cout << "root\t" << selectedRoot << '\n';
    std::cout << "root_core\t" << core << '\n';
    std::cout << "attempts\t" << attempts << '\n';
    std::cout << "splits\t" << splits << '\n';
    std::cout << "maximum_extra_depth\t" << maximumDepth << '\n';
    return 20;
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
