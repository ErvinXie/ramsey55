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

struct Result {
  int status = -1;
  int split = 0;
  double seconds = 0;
  std::string model;
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

}  // namespace

int main(int argc, char** argv) try {
  if (argc != 6) {
    std::cerr << "usage: refine_cadical_cubes input.cnf cubes jobs"
                 " output.icnf results.tsv\n";
    return 2;
  }
  const std::string cnfPath = argv[1];
  const auto cubes = readCubes(argv[2]);
  const int jobs = std::stoi(argv[3]);
  if (jobs < 1 || jobs > 256) throw std::runtime_error("invalid job count");

  CaDiCaL::Solver probe;
  probe.set("quiet", 1);
  int variables = 0;
  if (const char* error = probe.read_dimacs(cnfPath.c_str(), variables, 1)) {
    throw std::runtime_error(error);
  }
  for (const auto& cube : cubes) {
    std::vector<bool> seen(variables + 1);
    for (const int literal : cube) {
      if (literal == 0 || std::abs(literal) > variables ||
          seen[std::abs(literal)]) {
        throw std::runtime_error("invalid or repeated cube literal");
      }
      seen[std::abs(literal)] = true;
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
        solver.freeze(variable);
      }

      while (!foundSat.load(std::memory_order_relaxed) &&
             !workerFailed.load(std::memory_order_relaxed)) {
        const std::size_t index = next.fetch_add(1);
        if (index >= cubes.size()) break;
        for (const int literal : cubes[index]) solver.assume(literal);
        const auto start = Clock::now();
        const int split = solver.lookahead();
        const double seconds =
            std::chrono::duration<double>(Clock::now() - start).count();
        const int status = solver.status();
        Result result;
        result.status = status;
        result.split = split;
        result.seconds = seconds;
        if (status == 10) {
          result.model.reserve(variables);
          for (int variable = 1; variable <= variables; ++variable) {
            result.model.push_back(solver.val(variable) > 0 ? '1' : '0');
          }
          foundSat.store(true, std::memory_order_relaxed);
        } else if (status == 20) {
          if (split != 0) workerFailed.store(true, std::memory_order_relaxed);
        } else if (split == 0 || std::abs(split) > variables) {
          workerFailed.store(true, std::memory_order_relaxed);
        } else {
          for (const int literal : cubes[index]) {
            if (std::abs(literal) == std::abs(split)) {
              workerFailed.store(true, std::memory_order_relaxed);
            }
          }
        }
        results[index] = std::move(result);
        const std::size_t count = finished.fetch_add(1) + 1;
        if (count == cubes.size() || count % 256 == 0 || status == 10) {
          std::lock_guard<std::mutex> lock(outputMutex);
          std::cout << "finished " << count << '/' << cubes.size()
                    << " worker=" << worker << " status=" << status << '\n';
        }
      }
    });
  }
  for (auto& worker : workers) worker.join();
  if (workerFailed.load()) throw std::runtime_error("a worker failed");

  std::ofstream output(argv[4]);
  if (!output) throw std::runtime_error("cannot create cube output");
  std::size_t children = 0;
  std::size_t closed = 0;
  for (std::size_t index = 0; index < cubes.size(); ++index) {
    const auto& result = results[index];
    if (result.status < 0) continue;
    if (result.status == 20) {
      ++closed;
      continue;
    }
    if (result.status == 10) continue;
    output << 'a';
    for (const int literal : cubes[index]) output << ' ' << literal;
    output << ' ' << result.split << " 0\n";
    output << 'a';
    for (const int literal : cubes[index]) output << ' ' << literal;
    output << ' ' << -result.split << " 0\n";
    children += 2;
  }

  std::ofstream report(argv[5]);
  if (!report) throw std::runtime_error("cannot create result output");
  report << "cube\tstatus\tsplit\tseconds\tmodel\n";
  report << std::fixed << std::setprecision(6);
  for (std::size_t index = 0; index < results.size(); ++index) {
    report << index << '\t' << results[index].status << '\t'
           << results[index].split << '\t' << results[index].seconds << '\t'
           << results[index].model << '\n';
  }
  std::cout << "completed\t" << finished.load() << '\n';
  std::cout << "closed\t" << closed << '\n';
  std::cout << "children\t" << children << '\n';
  std::cout << "sat\t" << (foundSat.load() ? 1 : 0) << '\n';
  return foundSat.load() ? 10 : 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
