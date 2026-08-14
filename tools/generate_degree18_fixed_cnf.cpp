#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int order = 42;
constexpr int aSize = 18;
constexpr int bSize = 24;

struct CatalogGraph {
  std::array<std::uint32_t, bSize> adjacency{};
};

CatalogGraph decode_graph6(const std::string& text) {
  if (text.empty() || static_cast<unsigned char>(text[0]) - 63 != bSize) {
    throw std::runtime_error("expected an order-24 short graph6 record");
  }
  CatalogGraph graph;
  int word = 1;
  int shift = 5;
  for (int v = 1; v < bSize; ++v) {
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

using Clause = std::vector<int>;

struct EdgeValue {
  bool fixed{};
  bool value{};
  int variable{};
};

void add_lex_order(std::vector<Clause>& clauses, int& variables,
                   const std::array<std::array<int, bSize>, aSize>& cross) {
  for (int row = 0; row + 1 < aSize; ++row) {
    int prefixEqual = 0;  // Zero denotes true for the empty prefix.
    for (int column = 0; column < bSize; ++column) {
      const int left = cross[row][column];
      const int right = cross[row + 1][column];
      Clause orderClause;
      if (prefixEqual) orderClause.push_back(-prefixEqual);
      orderClause.push_back(-left);
      orderClause.push_back(right);
      clauses.push_back(std::move(orderClause));

      if (column + 1 == bSize) continue;
      const int nextEqual = ++variables;
      if (prefixEqual) clauses.push_back({-nextEqual, prefixEqual});
      clauses.push_back({-nextEqual, -left, right});
      clauses.push_back({-nextEqual, left, -right});
      if (prefixEqual) {
        clauses.push_back({-prefixEqual, -left, -right, nextEqual});
        clauses.push_back({-prefixEqual, left, right, nextEqual});
      } else {
        clauses.push_back({-left, -right, nextEqual});
        clauses.push_back({left, right, nextEqual});
      }
      prefixEqual = nextEqual;
    }
  }
}

void add_cardinality_range(std::vector<Clause>& clauses, int& variables,
                           const std::vector<int>& inputs, int lower,
                           int upper) {
  const int size = static_cast<int>(inputs.size());
  if (lower < 0 || lower > upper || upper > size) {
    throw std::runtime_error("invalid cardinality range");
  }
  if (lower == 0 && upper == size) return;
  const int threshold = std::min(size, upper + 1);
  std::vector<std::vector<int>> atLeast(
      size + 1, std::vector<int>(threshold + 1));
  for (int i = 1; i <= size; ++i) {
    const int input = inputs[i - 1];
    for (int j = 1; j <= std::min(i, threshold); ++j) {
      const int current = atLeast[i][j] = ++variables;
      if (i == 1 && j == 1) {
        clauses.push_back({-current, input});
        clauses.push_back({-input, current});
      } else if (j == 1) {
        const int previous = atLeast[i - 1][1];
        clauses.push_back({-previous, current});
        clauses.push_back({-input, current});
        clauses.push_back({-current, previous, input});
      } else if (j == i) {
        const int lowerCounter = atLeast[i - 1][j - 1];
        clauses.push_back({-current, lowerCounter});
        clauses.push_back({-current, input});
        clauses.push_back({-lowerCounter, -input, current});
      } else {
        const int previous = atLeast[i - 1][j];
        const int lowerCounter = atLeast[i - 1][j - 1];
        clauses.push_back({-previous, current});
        clauses.push_back({-lowerCounter, -input, current});
        clauses.push_back({-current, previous, lowerCounter});
        clauses.push_back({-current, previous, input});
      }
    }
  }
  if (lower > 0) clauses.push_back({atLeast[size][lower]});
  if (upper < size) clauses.push_back({-atLeast[size][upper + 1]});
}

void self_test_cardinality_encoding() {
  // Exhaust all primary and auxiliary assignments on small instances.  This
  // checks both directions of the sequential-counter equivalences, rather
  // than merely checking the intended auxiliary assignment.
  for (int size = 1; size <= 4; ++size) {
    std::vector<int> inputs;
    for (int variable = 1; variable <= size; ++variable) {
      inputs.push_back(variable);
    }
    for (int lower = 0; lower <= size; ++lower) {
      for (int upper = lower; upper <= size; ++upper) {
        int variables = size;
        std::vector<Clause> clauses;
        add_cardinality_range(clauses, variables, inputs, lower, upper);
        const int auxiliaries = variables - size;
        if (auxiliaries >= 63) {
          throw std::runtime_error("self-test has too many auxiliaries");
        }
        for (std::uint64_t primary = 0;
             primary < (std::uint64_t{1} << size); ++primary) {
          bool satisfiable = false;
          for (std::uint64_t auxiliary = 0;
               auxiliary < (std::uint64_t{1} << auxiliaries); ++auxiliary) {
            const std::uint64_t assignment = primary | (auxiliary << size);
            bool allSatisfied = true;
            for (const Clause& clause : clauses) {
              bool clauseSatisfied = false;
              for (const int literal : clause) {
                const int variable = std::abs(literal) - 1;
                const bool value =
                    (assignment >> variable) & std::uint64_t{1};
                clauseSatisfied |= literal > 0 ? value : !value;
              }
              if (!clauseSatisfied) {
                allSatisfied = false;
                break;
              }
            }
            if (allSatisfied) {
              satisfiable = true;
              break;
            }
          }
          const int count = static_cast<int>(std::popcount(primary));
          const bool expected = lower <= count && count <= upper;
          if (satisfiable != expected) {
            throw std::runtime_error("cardinality self-test failed");
          }
        }
      }
    }
  }
  std::cout << "cardinality encoding self-test passed\n";
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc == 2 && std::string(argv[1]) == "--self-test-cardinality") {
    self_test_cardinality_encoding();
    return 0;
  }
  if (argc < 4 || argc > 8) {
    std::cerr << "usage: generate_degree18_fixed_cnf r45_24.g6 index output.cnf"
                 " [--no-symmetry] [--no-degree-bounds] [--cross-first]"
                 " [--min-a-edges=N]\n";
    return 2;
  }
  const auto records = read_records(argv[1]);
  const std::size_t index = std::stoull(argv[2]);
  bool symmetry = true;
  bool degreeBounds = true;
  bool crossFirst = false;
  int minimumAEdges = -1;
  for (int argument = 4; argument < argc; ++argument) {
    const std::string option = argv[argument];
    if (option == "--no-symmetry") {
      symmetry = false;
    } else if (option == "--no-degree-bounds") {
      degreeBounds = false;
    } else if (option == "--cross-first") {
      crossFirst = true;
    } else if (option.starts_with("--min-a-edges=")) {
      minimumAEdges = std::stoi(option.substr(14));
    } else {
      throw std::runtime_error("unknown option " + option);
    }
  }
  if (records.size() != 352366 || index >= records.size()) {
    throw std::runtime_error("invalid R(4,5,24) catalog or index");
  }
  if (minimumAEdges < -1 || minimumAEdges > 85) {
    throw std::runtime_error("invalid A-edge lower bound (E(4,5,18)=85)");
  }
  const CatalogGraph catalog = decode_graph6(records[index]);

  std::array<std::array<int, aSize>, aSize> withinA{};
  std::array<std::array<int, bSize>, aSize> cross{};
  int variables = 0;
  const auto allocateWithinA = [&] {
    for (int u = 0; u < aSize; ++u) {
      for (int v = u + 1; v < aSize; ++v) {
        withinA[u][v] = withinA[v][u] = ++variables;
      }
    }
  };
  const auto allocateCross = [&] {
    for (int u = 0; u < aSize; ++u) {
      for (int v = 0; v < bSize; ++v) cross[u][v] = ++variables;
    }
  };
  if (crossFirst) {
    allocateCross();
    allocateWithinA();
  } else {
    allocateWithinA();
    allocateCross();
  }
  if (variables != 585) throw std::runtime_error("bad free-edge indexing");

  auto edge_value = [&](int u, int v) -> EdgeValue {
    if (u > v) std::swap(u, v);
    if (v < aSize) return {false, false, withinA[u][v]};
    if (u < aSize) return {false, false, cross[u][v - aSize]};
    const int left = u - aSize;
    const int right = v - aSize;
    const bool catalogEdge =
        (catalog.adjacency[left] >> right) & std::uint32_t{1};
    return {true, !catalogEdge, 0};
  };

  std::vector<Clause> clauses;
  std::array<std::uint64_t, 6> cliqueByACount{};
  std::array<std::uint64_t, 6> independentByACount{};
  for (int a = 0; a < order; ++a) {
    for (int b = a + 1; b < order; ++b) {
      for (int c = b + 1; c < order; ++c) {
        for (int d = c + 1; d < order; ++d) {
          for (int e = d + 1; e < order; ++e) {
            const std::array<int, 5> vertices{a, b, c, d, e};
            const int aCount = static_cast<int>(
                std::count_if(vertices.begin(), vertices.end(),
                              [](const int vertex) { return vertex < aSize; }));
            Clause forbidClique;
            Clause forbidIndependent;
            bool cliqueSatisfied = false;
            bool independentSatisfied = false;
            for (int i = 0; i < 5; ++i) {
              for (int j = i + 1; j < 5; ++j) {
                const EdgeValue edge = edge_value(vertices[i], vertices[j]);
                if (edge.fixed) {
                  cliqueSatisfied |= !edge.value;
                  independentSatisfied |= edge.value;
                } else {
                  forbidClique.push_back(-edge.variable);
                  forbidIndependent.push_back(edge.variable);
                }
              }
            }
            if (!cliqueSatisfied) {
              if (forbidClique.empty()) {
                throw std::runtime_error("fixed B contains a K5");
              }
              clauses.push_back(std::move(forbidClique));
              ++cliqueByACount[aCount];
            }
            if (!independentSatisfied) {
              if (forbidIndependent.empty()) {
                throw std::runtime_error("fixed B contains an independent 5-set");
              }
              clauses.push_back(std::move(forbidIndependent));
              ++independentByACount[aCount];
            }
          }
        }
      }
    }
  }

  const std::size_t ramseyClauses = clauses.size();
  std::uint64_t fourSets = 0;
  for (int a = 0; a < aSize; ++a) {
    for (int b = a + 1; b < aSize; ++b) {
      for (int c = b + 1; c < aSize; ++c) {
        for (int d = c + 1; d < aSize; ++d) {
          clauses.push_back({-withinA[a][b], -withinA[a][c], -withinA[a][d],
                             -withinA[b][c], -withinA[b][d], -withinA[c][d]});
          ++fourSets;
        }
      }
    }
  }
  const std::size_t beforeSymmetry = clauses.size();
  if (symmetry) add_lex_order(clauses, variables, cross);
  const std::size_t beforeDegreeBounds = clauses.size();
  if (degreeBounds) {
    for (int vertex = 0; vertex < aSize; ++vertex) {
      std::vector<int> incident;
      incident.reserve(order - 1);
      for (int other = 0; other < aSize; ++other) {
        if (other != vertex) incident.push_back(withinA[vertex][other]);
      }
      for (int other = 0; other < bSize; ++other) {
        incident.push_back(cross[vertex][other]);
      }
      // The apex is adjacent to A, so the remaining degree lies in [17,23].
      add_cardinality_range(clauses, variables, incident, 17, 23);
    }
    for (int vertex = 0; vertex < bSize; ++vertex) {
      const int catalogDegree =
          static_cast<int>(std::popcount(catalog.adjacency[vertex]));
      const int fixedDegree = bSize - 1 - catalogDegree;
      std::vector<int> incident;
      incident.reserve(aSize);
      for (int other = 0; other < aSize; ++other) {
        incident.push_back(cross[other][vertex]);
      }
      add_cardinality_range(clauses, variables, incident,
                            std::max(0, 18 - fixedDegree),
                            std::min(aSize, 24 - fixedDegree));
    }
  }
  const std::size_t beforeAEdgeBound = clauses.size();
  if (minimumAEdges >= 0) {
    std::vector<int> edges;
    edges.reserve(aSize * (aSize - 1) / 2);
    for (int u = 0; u < aSize; ++u) {
      for (int v = u + 1; v < aSize; ++v) {
        edges.push_back(withinA[u][v]);
      }
    }
    // Every Ramsey(4,5,18)-graph has at most 85 edges.
    add_cardinality_range(clauses, variables, edges, minimumAEdges, 85);
  }

  std::ofstream output(argv[3]);
  if (!output) throw std::runtime_error("cannot create output CNF");
  output << "c degree-18 split, R(4,5,24) catalog index " << index << '\n';
  output << "c fixed B is the complement of the catalog record\n";
  output << "c variable order " << (crossFirst ? "cross-first" : "A-first")
         << '\n';
  output << "p cnf " << variables << ' ' << clauses.size() << '\n';
  for (const Clause& clause : clauses) {
    for (const int literal : clause) output << literal << ' ';
    output << "0\n";
  }
  std::cout << "representative\t" << index << '\n';
  std::cout << "variables\t" << variables << '\n';
  std::cout << "ramsey_clauses\t" << ramseyClauses << '\n';
  std::cout << "apex_k4_clauses\t" << fourSets << '\n';
  std::cout << "symmetry_clauses\t"
            << beforeDegreeBounds - beforeSymmetry << '\n';
  std::cout << "degree_bound_clauses\t"
            << beforeAEdgeBound - beforeDegreeBounds << '\n';
  std::cout << "A_edge_bound_clauses\t"
            << clauses.size() - beforeAEdgeBound << '\n';
  for (int count = 0; count <= 5; ++count) {
    std::cout << "clique_with_" << count << "_A\t" << cliqueByACount[count]
              << '\n';
    std::cout << "independent_with_" << count << "_A\t"
              << independentByACount[count] << '\n';
  }
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
