#include "cadical.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int baseOrder = 42;
constexpr int splitSize = 18;
constexpr int catalogOrder = 24;
constexpr int pairCount = baseOrder * (baseOrder - 1) / 2;

struct CatalogGraph {
  std::array<std::uint32_t, catalogOrder> adjacency{};
};

CatalogGraph decode_graph6(const std::string& text) {
  if (text.empty() || static_cast<unsigned char>(text[0]) - 63 != catalogOrder) {
    throw std::runtime_error("expected an order-24 short graph6 record");
  }
  CatalogGraph graph;
  int word = 1;
  int shift = 5;
  for (int v = 1; v < catalogOrder; ++v) {
    for (int u = 0; u < v; ++u) {
      if (word >= static_cast<int>(text.size())) {
        throw std::runtime_error("truncated graph6 record");
      }
      const int value = static_cast<unsigned char>(text[word]) - 63;
      if (value < 0 || value > 63) {
        throw std::runtime_error("invalid graph6 character");
      }
      if (value & (1 << shift)) {
        graph.adjacency[u] |= std::uint32_t{1} << v;
        graph.adjacency[v] |= std::uint32_t{1} << u;
      }
      if (--shift < 0) {
        shift = 5;
        ++word;
      }
    }
  }
  return graph;
}

std::vector<std::string> read_records(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::vector<std::string> records;
  std::string line;
  while (std::getline(input, line)) {
    if (!line.empty() && line[0] != '#') records.push_back(line);
  }
  return records;
}

template <std::size_t Size>
void add_clause(CaDiCaL::Solver& solver, const std::array<int, Size>& literals) {
  for (const int literal : literals) solver.add(literal);
  solver.add(0);
}

std::string encode_graph6(
    const std::array<std::array<int, baseOrder>, baseOrder>& variable,
    CaDiCaL::Solver& solver) {
  constexpr int order = baseOrder + 1;
  std::vector<int> bits;
  bits.reserve(order * (order - 1) / 2);
  for (int v = 1; v < order; ++v) {
    for (int u = 0; u < v; ++u) {
      if (u == 0) {
        bits.push_back(v <= splitSize);
      } else {
        bits.push_back(solver.val(variable[u - 1][v - 1]) > 0);
      }
    }
  }
  bits.resize((bits.size() + 5) / 6 * 6);
  std::string result(1, static_cast<char>(order + 63));
  for (std::size_t offset = 0; offset < bits.size(); offset += 6) {
    int value = 0;
    for (int index = 0; index < 6; ++index) {
      value |= bits[offset + index] << (5 - index);
    }
    result.push_back(static_cast<char>(value + 63));
  }
  return result;
}

struct Core {
  std::size_t source{};
  std::vector<int> literals;
};

bool core_matches(const Core& core,
                  const std::array<int, pairCount + 1>& assignment) {
  return std::all_of(core.literals.begin(), core.literals.end(),
                     [&](const int literal) {
                       return assignment[std::abs(literal)] == literal;
                     });
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc < 2 || argc > 4) {
    std::cerr << "usage: scan_degree18_catalog r45_24.g6 [start [stop]]\n";
    return 2;
  }
  const auto records = read_records(argv[1]);
  if (records.size() != 352366) {
    throw std::runtime_error("expected 352366 catalog records");
  }
  const std::size_t start = argc >= 3 ? std::stoull(argv[2]) : 0;
  const std::size_t stop = argc >= 4 ? std::stoull(argv[3]) : records.size();
  if (start > stop || stop > records.size()) {
    throw std::runtime_error("invalid catalog range");
  }

  std::array<std::array<int, baseOrder>, baseOrder> variable{};
  int nextVariable = 0;
  for (int u = 0; u < baseOrder; ++u) {
    for (int v = u + 1; v < baseOrder; ++v) {
      variable[u][v] = variable[v][u] = ++nextVariable;
    }
  }
  if (nextVariable != pairCount) throw std::runtime_error("bad pair indexing");

  CaDiCaL::Solver solver;
  solver.set("quiet", 1);
  std::uint64_t fiveSets = 0;
  for (int a = 0; a < baseOrder; ++a) {
    for (int b = a + 1; b < baseOrder; ++b) {
      for (int c = b + 1; c < baseOrder; ++c) {
        for (int d = c + 1; d < baseOrder; ++d) {
          for (int e = d + 1; e < baseOrder; ++e) {
            const std::array<int, 5> vertices{a, b, c, d, e};
            std::array<int, 10> forbidClique{};
            std::array<int, 10> forbidIndependent{};
            int offset = 0;
            for (int i = 0; i < 5; ++i) {
              for (int j = i + 1; j < 5; ++j) {
                const int edge = variable[vertices[i]][vertices[j]];
                forbidClique[offset] = -edge;
                forbidIndependent[offset] = edge;
                ++offset;
              }
            }
            add_clause(solver, forbidClique);
            add_clause(solver, forbidIndependent);
            ++fiveSets;
          }
        }
      }
    }
  }
  std::uint64_t fourSets = 0;
  for (int a = 0; a < splitSize; ++a) {
    for (int b = a + 1; b < splitSize; ++b) {
      for (int c = b + 1; c < splitSize; ++c) {
        for (int d = c + 1; d < splitSize; ++d) {
          add_clause(solver,
                     std::array<int, 6>{-variable[a][b], -variable[a][c],
                                        -variable[a][d], -variable[b][c],
                                        -variable[b][d], -variable[c][d]});
          ++fourSets;
        }
      }
    }
  }
  std::cout << "formula\tvariables=" << pairCount << "\tfive_sets=" << fiveSets
            << "\tfour_sets=" << fourSets << '\n';
  std::cout.flush();

  std::vector<Core> cores;
  std::uint64_t covered = 0;
  std::uint64_t solved = 0;
  for (std::size_t index = start; index < stop; ++index) {
    const CatalogGraph graph = decode_graph6(records[index]);
    std::vector<int> assumptions;
    assumptions.reserve(catalogOrder * (catalogOrder - 1) / 2);
    std::array<int, pairCount + 1> assignment{};
    for (int u = 0; u < catalogOrder; ++u) {
      for (int v = u + 1; v < catalogOrder; ++v) {
        const int edge = variable[splitSize + u][splitSize + v];
        const bool catalogEdge =
            (graph.adjacency[u] >> v) & std::uint32_t{1};
        const int literal = catalogEdge ? -edge : edge;
        assumptions.push_back(literal);
        assignment[edge] = literal;
      }
    }
    auto match = std::find_if(cores.begin(), cores.end(), [&](const Core& core) {
      return core_matches(core, assignment);
    });
    if (match != cores.end()) {
      ++covered;
      std::cout << "covered\t" << index << '\t' << match->source << '\n';
      continue;
    }

    std::cout << "solve\t" << index << '\n';
    std::cout.flush();
    for (const int literal : assumptions) solver.assume(literal);
    const int result = solver.solve();
    ++solved;
    if (result == 10) {
      std::cout << "SAT\t" << index << '\t' << encode_graph6(variable, solver)
                << '\n';
      std::cout.flush();
      return 10;
    }
    if (result != 20) throw std::runtime_error("solver returned UNKNOWN");
    Core core{index, {}};
    for (const int literal : assumptions) {
      if (solver.failed(literal)) core.literals.push_back(literal);
    }
    if (core.literals.empty()) {
      throw std::runtime_error("UNSAT assumption solve returned an empty core");
    }
    std::cout << "core\t" << index;
    for (const int literal : core.literals) std::cout << '\t' << literal;
    std::cout << '\n';
    std::cout.flush();
    cores.push_back(std::move(core));
  }
  std::cout << "summary\trange=" << start << ':' << stop
            << "\tsolved=" << solved << "\tcovered=" << covered
            << "\tcores=" << cores.size() << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
