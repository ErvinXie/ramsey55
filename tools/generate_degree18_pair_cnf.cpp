#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr int aSize = 18;
constexpr int bSize = 24;
constexpr int order = aSize + bSize;
using Clause = std::vector<int>;

template <int Size>
struct Graph {
  std::array<std::uint32_t, Size> adjacency{};
};

template <int Size>
Graph<Size> decode_graph6(const std::string& text) {
  if (text.empty() || static_cast<unsigned char>(text[0]) - 63 != Size) {
    throw std::runtime_error("unexpected graph6 order");
  }
  Graph<Size> graph;
  int word = 1;
  int shift = 5;
  for (int v = 1; v < Size; ++v) {
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

std::string read_record(const std::string& path, std::size_t target) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open " + path);
  std::string line;
  std::size_t index = 0;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == '#') continue;
    if (index++ == target) return line;
  }
  throw std::runtime_error("catalog index is out of range");
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

template <int Size>
std::vector<std::array<int, Size>> find_automorphisms(
    const Graph<Size>& graph) {
  std::array<int, Size> degree{};
  std::array<std::array<int, Size>, Size> neighbourDegreeCounts{};
  for (int vertex = 0; vertex < Size; ++vertex) {
    degree[vertex] = std::popcount(graph.adjacency[vertex]);
  }
  for (int vertex = 0; vertex < Size; ++vertex) {
    for (int neighbour = 0; neighbour < Size; ++neighbour) {
      if ((graph.adjacency[vertex] >> neighbour) & std::uint32_t{1}) {
        ++neighbourDegreeCounts[vertex][degree[neighbour]];
      }
    }
  }

  std::array<int, Size> image{};
  image.fill(-1);
  std::array<bool, Size> used{};
  std::vector<std::array<int, Size>> result;

  const auto compatible = [&](int vertex, int candidate) {
    if (used[candidate] || degree[vertex] != degree[candidate] ||
        neighbourDegreeCounts[vertex] != neighbourDegreeCounts[candidate]) {
      return false;
    }
    for (int other = 0; other < Size; ++other) {
      if (image[other] < 0) continue;
      const bool sourceEdge =
          (graph.adjacency[vertex] >> other) & std::uint32_t{1};
      const bool imageEdge =
          (graph.adjacency[candidate] >> image[other]) & std::uint32_t{1};
      if (sourceEdge != imageEdge) return false;
    }
    return true;
  };

  std::function<void(int)> search = [&](int assigned) {
    if (assigned == Size) {
      result.push_back(image);
      return;
    }
    int vertex = -1;
    std::vector<int> candidates;
    for (int probe = 0; probe < Size; ++probe) {
      if (image[probe] >= 0) continue;
      std::vector<int> probeCandidates;
      for (int candidate = 0; candidate < Size; ++candidate) {
        if (compatible(probe, candidate)) probeCandidates.push_back(candidate);
      }
      if (probeCandidates.empty()) return;
      if (vertex < 0 || probeCandidates.size() < candidates.size()) {
        vertex = probe;
        candidates = std::move(probeCandidates);
      }
    }
    for (const int candidate : candidates) {
      image[vertex] = candidate;
      used[candidate] = true;
      search(assigned + 1);
      used[candidate] = false;
      image[vertex] = -1;
    }
  };
  search(0);
  return result;
}

void add_lex_leader(std::vector<Clause>& clauses, int& variables,
                    const std::vector<int>& left,
                    const std::vector<int>& right) {
  if (left.size() != right.size()) {
    throw std::runtime_error("lex vectors have different lengths");
  }
  std::vector<std::pair<int, int>> differences;
  for (std::size_t index = 0; index < left.size(); ++index) {
    if (left[index] != right[index]) {
      differences.emplace_back(left[index], right[index]);
    }
  }
  int equalPrefix = 0;  // Zero denotes the constant true prefix.
  for (std::size_t index = 0; index < differences.size(); ++index) {
    const auto [leftBit, rightBit] = differences[index];
    if (equalPrefix == 0) {
      clauses.push_back({-leftBit, rightBit});
    } else {
      clauses.push_back({-equalPrefix, -leftBit, rightBit});
    }
    if (index + 1 == differences.size()) continue;

    const int nextPrefix = ++variables;
    if (equalPrefix == 0) {
      clauses.push_back({-nextPrefix, -leftBit, rightBit});
      clauses.push_back({-nextPrefix, leftBit, -rightBit});
      clauses.push_back({leftBit, rightBit, nextPrefix});
      clauses.push_back({-leftBit, -rightBit, nextPrefix});
    } else {
      clauses.push_back({-nextPrefix, equalPrefix});
      clauses.push_back({-nextPrefix, -leftBit, rightBit});
      clauses.push_back({-nextPrefix, leftBit, -rightBit});
      clauses.push_back({-equalPrefix, leftBit, rightBit, nextPrefix});
      clauses.push_back({-equalPrefix, -leftBit, -rightBit, nextPrefix});
    }
    equalPrefix = nextPrefix;
  }
}

bool satisfies(const std::vector<Clause>& clauses,
               const std::vector<bool>& assignment) {
  for (const auto& clause : clauses) {
    bool clauseSatisfied = false;
    for (const int literal : clause) {
      const bool value = assignment[std::abs(literal)];
      clauseSatisfied |= literal > 0 ? value : !value;
    }
    if (!clauseSatisfied) return false;
  }
  return true;
}

template <int Size>
void self_test_lex_size() {
  std::array<int, Size> permutation{};
  std::iota(permutation.begin(), permutation.end(), 0);
  do {
    std::vector<int> left(Size);
    std::iota(left.begin(), left.end(), 1);
    std::vector<int> right;
    for (const int index : permutation) right.push_back(index + 1);
    int variables = Size;
    std::vector<Clause> clauses;
    add_lex_leader(clauses, variables, left, right);
    for (std::uint32_t primary = 0;
         primary < (std::uint32_t{1} << Size); ++primary) {
      bool expected = true;
      for (int index = 0; index < Size; ++index) {
        const bool leftValue = (primary >> index) & 1U;
        const bool rightValue = (primary >> permutation[index]) & 1U;
        if (leftValue != rightValue) {
          expected = !leftValue && rightValue;
          break;
        }
      }
      bool observed = false;
      const int auxiliaries = variables - Size;
      for (std::uint32_t auxiliary = 0;
           auxiliary < (std::uint32_t{1} << auxiliaries); ++auxiliary) {
        std::vector<bool> assignment(variables + 1);
        for (int variable = 0; variable < Size; ++variable) {
          assignment[variable + 1] = (primary >> variable) & 1U;
        }
        for (int variable = 0; variable < auxiliaries; ++variable) {
          assignment[Size + variable + 1] = (auxiliary >> variable) & 1U;
        }
        observed |= satisfies(clauses, assignment);
      }
      if (observed != expected) {
        throw std::runtime_error("lex-leader self-test failed");
      }
    }
  } while (std::next_permutation(permutation.begin(), permutation.end()));
}

template <int Size>
void self_test_automorphisms_size() {
  constexpr int edgeCount = Size * (Size - 1) / 2;
  for (std::uint32_t bits = 0; bits < (std::uint32_t{1} << edgeCount);
       ++bits) {
    Graph<Size> graph;
    int edge = 0;
    for (int right = 1; right < Size; ++right) {
      for (int left = 0; left < right; ++left, ++edge) {
        if ((bits >> edge) & 1U) {
          graph.adjacency[left] |= std::uint32_t{1} << right;
          graph.adjacency[right] |= std::uint32_t{1} << left;
        }
      }
    }
    const auto observed = find_automorphisms(graph);
    std::size_t expected = 0;
    std::array<int, Size> permutation{};
    std::iota(permutation.begin(), permutation.end(), 0);
    do {
      bool valid = true;
      for (int right = 1; right < Size; ++right) {
        for (int left = 0; left < right; ++left) {
          const bool source =
              (graph.adjacency[left] >> right) & std::uint32_t{1};
          const bool image = (graph.adjacency[permutation[left]] >>
                              permutation[right]) &
                             std::uint32_t{1};
          valid &= source == image;
        }
      }
      expected += valid;
    } while (std::next_permutation(permutation.begin(), permutation.end()));
    if (observed.size() != expected) {
      throw std::runtime_error("automorphism self-test failed");
    }
  }
}

void self_test_symmetry() {
  self_test_lex_size<1>();
  self_test_lex_size<2>();
  self_test_lex_size<3>();
  self_test_lex_size<4>();
  self_test_lex_size<5>();
  self_test_automorphisms_size<1>();
  self_test_automorphisms_size<2>();
  self_test_automorphisms_size<3>();
  self_test_automorphisms_size<4>();
  self_test_automorphisms_size<5>();
  std::cout << "symmetry encoding self-test passed\n";
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc == 2 && std::string(argv[1]) == "--self-test-symmetry") {
    self_test_symmetry();
    return 0;
  }
  if (argc < 6) {
    std::cerr << "usage: generate_degree18_pair_cnf r45_24.g6 H-index"
                 " r45_18.g6 A-index output.cnf [--no-degree-bounds]"
                 " [--no-symmetry]\n";
    return 2;
  }
  const std::size_t hIndex = std::stoull(argv[2]);
  const std::size_t aIndex = std::stoull(argv[4]);
  bool degreeBounds = true;
  bool symmetry = true;
  for (int argument = 6; argument < argc; ++argument) {
    const std::string option = argv[argument];
    if (option == "--no-degree-bounds") {
      degreeBounds = false;
    } else if (option == "--no-symmetry") {
      symmetry = false;
    } else {
      throw std::runtime_error("unknown option " + option);
    }
  }
  const auto h = decode_graph6<bSize>(read_record(argv[1], hIndex));
  const auto aGraph = decode_graph6<aSize>(read_record(argv[3], aIndex));

  std::array<std::array<int, bSize>, aSize> cross{};
  int variables = 0;
  for (int u = 0; u < aSize; ++u) {
    for (int v = 0; v < bSize; ++v) cross[u][v] = ++variables;
  }

  struct EdgeValue {
    bool fixed;
    bool value;
    int variable;
  };
  const auto edgeValue = [&](int u, int v) -> EdgeValue {
    if (u > v) std::swap(u, v);
    if (v < aSize) {
      return {true,
              bool((aGraph.adjacency[u] >> v) & std::uint32_t{1}), 0};
    }
    if (u < aSize) return {false, false, cross[u][v - aSize]};
    const int left = u - aSize;
    const int right = v - aSize;
    const bool hEdge = (h.adjacency[left] >> right) & std::uint32_t{1};
    return {true, !hEdge, 0};
  };

  std::vector<Clause> clauses;
  for (int v0 = 0; v0 < order; ++v0) {
    for (int v1 = v0 + 1; v1 < order; ++v1) {
      for (int v2 = v1 + 1; v2 < order; ++v2) {
        for (int v3 = v2 + 1; v3 < order; ++v3) {
          for (int v4 = v3 + 1; v4 < order; ++v4) {
            const std::array<int, 5> vertices{v0, v1, v2, v3, v4};
            Clause clique;
            Clause independent;
            bool cliqueSatisfied = false;
            bool independentSatisfied = false;
            for (int i = 0; i < 5; ++i) {
              for (int j = i + 1; j < 5; ++j) {
                const auto edge = edgeValue(vertices[i], vertices[j]);
                if (edge.fixed) {
                  cliqueSatisfied |= !edge.value;
                  independentSatisfied |= edge.value;
                } else {
                  clique.push_back(-edge.variable);
                  independent.push_back(edge.variable);
                }
              }
            }
            if (!cliqueSatisfied) {
              if (clique.empty()) throw std::runtime_error("fixed K5");
              clauses.push_back(std::move(clique));
            }
            if (!independentSatisfied) {
              if (independent.empty()) throw std::runtime_error("fixed I5");
              clauses.push_back(std::move(independent));
            }
          }
        }
      }
    }
  }

  for (int v0 = 0; v0 < aSize; ++v0) {
    for (int v1 = v0 + 1; v1 < aSize; ++v1) {
      for (int v2 = v1 + 1; v2 < aSize; ++v2) {
        for (int v3 = v2 + 1; v3 < aSize; ++v3) {
          const auto edge = [&](int u, int v) {
            return (aGraph.adjacency[u] >> v) & std::uint32_t{1};
          };
          if (edge(v0, v1) && edge(v0, v2) && edge(v0, v3) &&
              edge(v1, v2) && edge(v1, v3) && edge(v2, v3)) {
            throw std::runtime_error("fixed A contains a K4");
          }
        }
      }
    }
  }
  for (int v0 = 0; v0 < bSize; ++v0) {
    for (int v1 = v0 + 1; v1 < bSize; ++v1) {
      for (int v2 = v1 + 1; v2 < bSize; ++v2) {
        for (int v3 = v2 + 1; v3 < bSize; ++v3) {
          const auto edge = [&](int u, int v) {
            return (h.adjacency[u] >> v) & std::uint32_t{1};
          };
          if (edge(v0, v1) && edge(v0, v2) && edge(v0, v3) &&
              edge(v1, v2) && edge(v1, v3) && edge(v2, v3)) {
            throw std::runtime_error("fixed H contains a K4");
          }
        }
      }
    }
  }

  const std::size_t ramseyClauses = clauses.size();
  if (degreeBounds) {
    for (int vertex = 0; vertex < aSize; ++vertex) {
      const int fixedDegree = std::popcount(aGraph.adjacency[vertex]);
      std::vector<int> incident(cross[vertex].begin(), cross[vertex].end());
      add_cardinality_range(clauses, variables, incident,
                            std::max(0, 17 - fixedDegree),
                            std::min(bSize, 23 - fixedDegree));
    }
    for (int vertex = 0; vertex < bSize; ++vertex) {
      const int fixedDegree =
          bSize - 1 - std::popcount(h.adjacency[vertex]);
      std::vector<int> incident;
      for (int other = 0; other < aSize; ++other) {
        incident.push_back(cross[other][vertex]);
      }
      add_cardinality_range(clauses, variables, incident,
                            std::max(0, 18 - fixedDegree),
                            std::min(aSize, 24 - fixedDegree));
    }
  }
  const std::size_t degreeBoundClauses = clauses.size() - ramseyClauses;

  std::size_t aAutomorphisms = 1;
  std::size_t hAutomorphisms = 1;
  const std::size_t beforeSymmetry = clauses.size();
  if (symmetry) {
    const auto aGroup = find_automorphisms(aGraph);
    const auto hGroup = find_automorphisms(h);
    aAutomorphisms = aGroup.size();
    hAutomorphisms = hGroup.size();
    const std::array<int, aSize> aIdentity = [] {
      std::array<int, aSize> value{};
      std::iota(value.begin(), value.end(), 0);
      return value;
    }();
    const std::array<int, bSize> hIdentity = [] {
      std::array<int, bSize> value{};
      std::iota(value.begin(), value.end(), 0);
      return value;
    }();
    for (const auto& permutation : aGroup) {
      if (permutation == aIdentity) continue;
      std::vector<int> left;
      std::vector<int> right;
      left.reserve(aSize * bSize);
      right.reserve(aSize * bSize);
      for (int row = 0; row < aSize; ++row) {
        for (int column = 0; column < bSize; ++column) {
          left.push_back(cross[row][column]);
          right.push_back(cross[permutation[row]][column]);
        }
      }
      add_lex_leader(clauses, variables, left, right);
    }
    for (const auto& permutation : hGroup) {
      if (permutation == hIdentity) continue;
      std::vector<int> left;
      std::vector<int> right;
      left.reserve(aSize * bSize);
      right.reserve(aSize * bSize);
      for (int row = 0; row < aSize; ++row) {
        for (int column = 0; column < bSize; ++column) {
          left.push_back(cross[row][column]);
          right.push_back(cross[row][permutation[column]]);
        }
      }
      add_lex_leader(clauses, variables, left, right);
    }
  }
  const std::size_t symmetryClauses = clauses.size() - beforeSymmetry;

  std::ofstream output(argv[5]);
  if (!output) throw std::runtime_error("cannot create output CNF");
  output << "c degree-18 fixed pair H=" << hIndex << " A=" << aIndex << '\n';
  output << "p cnf " << variables << ' ' << clauses.size() << '\n';
  for (const auto& clause : clauses) {
    for (const int literal : clause) output << literal << ' ';
    output << "0\n";
  }
  std::cout << "H\t" << hIndex << '\n';
  std::cout << "A\t" << aIndex << '\n';
  std::cout << "variables\t" << variables << '\n';
  std::cout << "ramsey_clauses\t" << ramseyClauses << '\n';
  std::cout << "degree_bound_clauses\t" << degreeBoundClauses << '\n';
  std::cout << "A_automorphisms\t" << aAutomorphisms << '\n';
  std::cout << "H_automorphisms\t" << hAutomorphisms << '\n';
  std::cout << "symmetry_clauses\t" << symmetryClauses << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
