#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int order = 42;
constexpr int pairCount = order * (order - 1) / 2;
constexpr int words = (pairCount + 63) / 64;

struct Graph {
  std::array<std::uint64_t, order> adjacency{};
};

Graph decode_graph6(const std::string& text) {
  if (text.empty() || static_cast<unsigned char>(text[0]) - 63 != order) {
    throw std::runtime_error("expected order-42 short graph6 input");
  }
  Graph graph;
  int word = 1, shift = 5;
  for (int v = 1; v < order; ++v) {
    for (int u = 0; u < v; ++u) {
      if (word >= static_cast<int>(text.size())) {
        throw std::runtime_error("truncated graph6 record");
      }
      const int value = static_cast<unsigned char>(text[word]) - 63;
      if (value & (1 << shift)) {
        graph.adjacency[u] |= std::uint64_t{1} << v;
        graph.adjacency[v] |= std::uint64_t{1} << u;
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

void add_exact_cardinality(std::vector<Clause>& clauses, int& variables,
                           int target) {
  std::vector<std::vector<int>> atLeast(
      pairCount + 1, std::vector<int>(target + 2));
  for (int i = 1; i <= pairCount; ++i) {
    const int x = i;
    for (int j = 1; j <= std::min(i, target + 1); ++j) {
      const int s = atLeast[i][j] = ++variables;
      if (i == 1 && j == 1) {
        clauses.push_back({-s, x});
        clauses.push_back({-x, s});
      } else if (j == 1) {
        const int previous = atLeast[i - 1][1];
        clauses.push_back({-previous, s});
        clauses.push_back({-x, s});
        clauses.push_back({-s, previous, x});
      } else if (j == i) {
        const int lower = atLeast[i - 1][j - 1];
        clauses.push_back({-s, lower});
        clauses.push_back({-s, x});
        clauses.push_back({-lower, -x, s});
      } else {
        const int previous = atLeast[i - 1][j];
        const int lower = atLeast[i - 1][j - 1];
        clauses.push_back({-previous, s});
        clauses.push_back({-lower, -x, s});
        clauses.push_back({-s, previous, lower});
        clauses.push_back({-s, previous, x});
      }
    }
  }
  clauses.push_back({atLeast[pairCount][target]});
  clauses.push_back({-atLeast[pairCount][target + 1]});
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc < 4 || argc > 5) {
    std::cerr << "usage: generate_three_flip_cnf graphs.g6 index output.cnf"
                 " [flip-count]\n";
    return 2;
  }
  const auto records = read_records(argv[1]);
  const std::size_t graphIndex = std::stoul(argv[2]);
  const int targetFlips = argc == 5 ? std::stoi(argv[4]) : 3;
  if (records.size() != 328 || graphIndex >= records.size()) {
    throw std::runtime_error("invalid public-catalog graph index");
  }
  if (targetFlips < 2 || targetFlips > 9) {
    throw std::runtime_error("flip count must lie between 2 and 9");
  }
  const Graph graph = decode_graph6(records[graphIndex]);

  std::array<std::array<int, order>, order> pairIndex{};
  int nextPair = 0;
  for (int u = 0; u < order; ++u) {
    for (int v = u + 1; v < order; ++v) {
      pairIndex[u][v] = pairIndex[v][u] = nextPair++;
    }
  }

  std::vector<Clause> clauses;
  std::array<std::array<std::uint64_t, words>, pairCount> forbiddenPair{};
  std::array<bool, pairCount> unsafeSingle{};
  std::vector<std::uint64_t> near(targetFlips + 1);

  auto record_obstruction = [&](const std::array<int, 10>& fiveEdges,
                                const std::array<int, 10>& mismatch,
                                int distance) {
    Clause clause;
    for (int i = 0; i < distance; ++i) clause.push_back(-(mismatch[i] + 1));
    for (const int edge : fiveEdges) {
      bool isMismatch = false;
      for (int i = 0; i < distance; ++i) isMismatch |= edge == mismatch[i];
      if (!isMismatch) clause.push_back(edge + 1);
    }
    clauses.push_back(std::move(clause));
    ++near[distance];

    if (distance == 1) {
      const int edge = mismatch[0];
      unsafeSingle[edge] = true;
      std::array<std::uint64_t, words> inside{};
      for (const int item : fiveEdges) {
        inside[item / 64] |= std::uint64_t{1} << (item % 64);
      }
      for (int word = 0; word < words; ++word) {
        forbiddenPair[edge][word] |= ~inside[word];
      }
    } else if (distance == 2) {
      forbiddenPair[mismatch[0]][mismatch[1] / 64] |=
          std::uint64_t{1} << (mismatch[1] % 64);
    }
  };

  for (int a = 0; a < order; ++a) {
    for (int b = a + 1; b < order; ++b) {
      for (int c = b + 1; c < order; ++c) {
        for (int d = c + 1; d < order; ++d) {
          for (int e = d + 1; e < order; ++e) {
            const std::array<int, 5> vertices{a, b, c, d, e};
            std::array<int, 10> fiveEdges{};
            std::array<int, 10> present{};
            int offset = 0, presentCount = 0;
            for (int i = 0; i < 5; ++i) {
              for (int j = i + 1; j < 5; ++j) {
                const int edge = pairIndex[vertices[i]][vertices[j]];
                fiveEdges[offset] = edge;
                present[offset] =
                    (graph.adjacency[vertices[i]] >> vertices[j]) & 1U;
                presentCount += present[offset++];
              }
            }
            if (10 - presentCount <= targetFlips) {
              std::array<int, 10> mismatch{};
              int count = 0;
              for (int i = 0; i < 10; ++i) {
                if (!present[i]) mismatch[count++] = fiveEdges[i];
              }
              record_obstruction(fiveEdges, mismatch, count);
            }
            if (presentCount <= targetFlips) {
              std::array<int, 10> mismatch{};
              int count = 0;
              for (int i = 0; i < 10; ++i) {
                if (present[i]) mismatch[count++] = fiveEdges[i];
              }
              record_obstruction(fiveEdges, mismatch, count);
            }
          }
        }
      }
    }
  }

  for (int edge = 0; edge < pairCount; ++edge) {
    if (!unsafeSingle[edge]) clauses.push_back({-(edge + 1)});
  }
  std::uint64_t safePairs = 0;
  for (int first = 0; first < pairCount; ++first) {
    for (int second = first + 1; second < pairCount; ++second) {
      const bool blocked =
          ((forbiddenPair[first][second / 64] >> (second % 64)) & 1U) ||
          ((forbiddenPair[second][first / 64] >> (first % 64)) & 1U);
      if (!blocked) {
        ++safePairs;
        clauses.push_back({-(first + 1), -(second + 1)});
      }
    }
  }

  int variables = pairCount;
  add_exact_cardinality(clauses, variables, targetFlips);
  std::ofstream output(argv[3]);
  if (!output) throw std::runtime_error("cannot create output CNF");
  output << "c public representative " << graphIndex << '\n';
  output << "c target flips " << targetFlips << " near patterns";
  for (int distance = 1; distance <= targetFlips; ++distance) {
    output << ' ' << near[distance];
  }
  output << " safe pairs " << safePairs << '\n';
  output << "p cnf " << variables << ' ' << clauses.size() << '\n';
  for (const auto& clause : clauses) {
    for (const int literal : clause) output << literal << ' ';
    output << "0\n";
  }
  std::cout << "graph\t" << graphIndex << '\n';
  std::cout << "variables\t" << variables << '\n';
  std::cout << "clauses\t" << clauses.size() << '\n';
  std::cout << "target_flips\t" << targetFlips << '\n';
  for (int distance = 1; distance <= targetFlips; ++distance) {
    std::cout << "near_" << distance << '\t' << near[distance] << '\n';
  }
  std::cout << "safe_pairs_excluded\t" << safePairs << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
