#include "cadical.hpp"

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

class Deadline final : public CaDiCaL::Terminator {
 public:
  void reset(double seconds) {
    deadline_ = Clock::now() + std::chrono::duration_cast<Clock::duration>(
                                   std::chrono::duration<double>(seconds));
  }

  bool terminate() override { return Clock::now() >= deadline_; }

 private:
  Clock::time_point deadline_ = Clock::time_point::max();
};

struct Result {
  int status = -1;
  double seconds = 0;
  std::string model;
};

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

std::vector<std::vector<int>> read_cubes(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::vector<std::vector<int>> cubes;
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == 'c') continue;
    std::istringstream fields(line);
    char marker = 0;
    fields >> marker;
    if (marker != 'a') throw std::runtime_error("invalid cube line");
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
    if (!terminated) throw std::runtime_error("unterminated cube line");
    cubes.push_back(std::move(cube));
  }
  if (cubes.empty()) throw std::runtime_error("cube file is empty");
  return cubes;
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc != 6) {
    std::cerr << "usage: solve_cadical_cubes input.cnf cubes per-cube-seconds"
                 " jobs output.tsv\n";
    return 2;
  }
  const std::string cnfPath = argv[1];
  const auto cubes = read_cubes(argv[2]);
  const double timeLimit = std::stod(argv[3]);
  const int jobs = std::stoi(argv[4]);
  if (!(timeLimit > 0) || jobs < 1 || jobs > 256) {
    throw std::runtime_error("invalid time limit or job count");
  }
  const int randomSeed = environmentInteger(
      "RAMSEY55_CADICAL_SEED", 0, 0, 2'000'000'000);
  const int initialPhase =
      environmentInteger("RAMSEY55_CADICAL_PHASE", 1, 0, 1);
  std::cout << "cadical_seed\t" << randomSeed << '\n';
  std::cout << "cadical_phase\t" << initialPhase << '\n';

  CaDiCaL::Solver probe;
  probe.set("quiet", 1);
  int variables = 0;
  if (const char* error = probe.read_dimacs(cnfPath.c_str(), variables, 1)) {
    throw std::runtime_error(error);
  }
  std::vector<bool> frozen(variables + 1);
  for (const auto& cube : cubes) {
    for (const int literal : cube) {
      if (literal == 0 || std::abs(literal) > variables) {
        throw std::runtime_error("cube literal is outside the CNF range");
      }
      frozen[std::abs(literal)] = true;
    }
  }

  std::vector<Result> results(cubes.size());
  std::atomic<std::size_t> next{0};
  std::atomic<std::size_t> finished{0};
  std::atomic<bool> foundSat{false};
  std::atomic<bool> workerFailed{false};
  std::mutex outputMutex;
  std::vector<std::thread> workers;
  workers.reserve(jobs);

  for (int worker = 0; worker < jobs; ++worker) {
    workers.emplace_back([&, worker] {
      CaDiCaL::Solver solver;
      solver.set("quiet", 1);
      solver.set("seed", randomSeed);
      solver.set("phase", initialPhase);
      int workerVariables = 0;
      if (const char* error =
              solver.read_dimacs(cnfPath.c_str(), workerVariables, 1)) {
        std::lock_guard<std::mutex> lock(outputMutex);
        std::cerr << "worker " << worker << ": " << error << '\n';
        workerFailed.store(true, std::memory_order_relaxed);
        return;
      }
      if (workerVariables != variables) {
        workerFailed.store(true, std::memory_order_relaxed);
        return;
      }
      for (int variable = 1; variable <= variables; ++variable) {
        if (frozen[variable]) solver.freeze(variable);
      }
      Deadline deadline;
      solver.connect_terminator(&deadline);

      while (!foundSat.load(std::memory_order_relaxed) &&
             !workerFailed.load(std::memory_order_relaxed)) {
        const std::size_t index = next.fetch_add(1);
        if (index >= cubes.size()) break;
        for (const int literal : cubes[index]) solver.assume(literal);
        deadline.reset(timeLimit);
        const auto start = Clock::now();
        const int status = solver.solve();
        const double elapsed =
            std::chrono::duration<double>(Clock::now() - start).count();
        Result result;
        result.status = status;
        result.seconds = elapsed;
        if (status == 10) {
          result.model.reserve(variables);
          for (int variable = 1; variable <= variables; ++variable) {
            result.model.push_back(solver.val(variable) > 0 ? '1' : '0');
          }
          foundSat.store(true, std::memory_order_relaxed);
        }
        results[index] = std::move(result);
        const std::size_t count = finished.fetch_add(1) + 1;
        if (count == cubes.size() || count % 16 == 0 || status == 10) {
          std::lock_guard<std::mutex> lock(outputMutex);
          std::cout << "finished " << count << '/' << cubes.size()
                    << " worker=" << worker << " status=" << status << '\n';
        }
      }
      solver.disconnect_terminator();
    });
  }
  for (auto& worker : workers) worker.join();
  if (workerFailed.load()) throw std::runtime_error("a solver worker failed");

  std::ofstream output(argv[5]);
  if (!output) throw std::runtime_error("cannot create result output");
  output << "cube\tstatus\tseconds\tmodel\n";
  output << std::fixed << std::setprecision(6);
  for (std::size_t index = 0; index < results.size(); ++index) {
    output << index << '\t' << results[index].status << '\t'
           << results[index].seconds << '\t' << results[index].model << '\n';
  }
  std::cout << "completed\t" << finished.load() << '\n';
  std::cout << "sat\t" << (foundSat.load() ? 1 : 0) << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
