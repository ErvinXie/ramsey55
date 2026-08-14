#include <array>
#include <atomic>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
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
    throw std::runtime_error("expected a short graph6 record of order 42");
  }
  Graph graph;
  int word = 1;
  int shift = 5;
  auto next_bit = [&] {
    if (word >= static_cast<int>(text.size())) {
      throw std::runtime_error("truncated graph6 record");
    }
    const int value = static_cast<unsigned char>(text[word]) - 63;
    const bool bit = value & (1 << shift);
    if (--shift < 0) {
      shift = 5;
      ++word;
    }
    return bit;
  };
  for (int v = 1; v < order; ++v) {
    for (int u = 0; u < v; ++u) {
      if (next_bit()) {
        graph.adjacency[u] |= std::uint64_t{1} << v;
        graph.adjacency[v] |= std::uint64_t{1} << u;
      }
    }
  }
  return graph;
}

struct ScanResult {
  std::uint64_t nearOne{};
  std::uint64_t nearTwo{};
  std::uint64_t safeSingles{};
  std::uint64_t safePairs{};
  std::vector<std::pair<int, int>> disconnectedPairs;
};

ScanResult scan_graph(const Graph& graph) {
  std::array<std::array<int, order>, order> pairIndex{};
  std::array<std::pair<int, int>, pairCount> pairs{};
  int nextPair = 0;
  for (int u = 0; u < order; ++u) {
    for (int v = u + 1; v < order; ++v) {
      pairIndex[u][v] = pairIndex[v][u] = nextPair;
      pairs[nextPair++] = {u, v};
    }
  }

  std::array<std::array<std::uint64_t, words>, pairCount> forbidden{};
  std::array<bool, pairCount> unsafeSingle{};
  ScanResult result;

  auto add_obstruction = [&](const std::array<int, 10>& fiveEdges,
                             const std::array<int, 2>& mismatch,
                             int distance) {
    if (distance == 1) {
      ++result.nearOne;
      const int edge = mismatch[0];
      unsafeSingle[edge] = true;
      std::array<std::uint64_t, words> inside{};
      for (const int item : fiveEdges) {
        inside[item / 64] |= std::uint64_t{1} << (item % 64);
      }
      for (int word = 0; word < words; ++word) {
        forbidden[edge][word] |= ~inside[word];
      }
    } else if (distance == 2) {
      ++result.nearTwo;
      forbidden[mismatch[0]][mismatch[1] / 64] |=
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
            int edgeOffset = 0;
            int presentCount = 0;
            for (int i = 0; i < 5; ++i) {
              for (int j = i + 1; j < 5; ++j) {
                const int pair = pairIndex[vertices[i]][vertices[j]];
                fiveEdges[edgeOffset] = pair;
                present[edgeOffset] =
                    (graph.adjacency[vertices[i]] >> vertices[j]) & 1U;
                presentCount += present[edgeOffset++];
              }
            }

            if (10 - presentCount <= 2) {
              std::array<int, 2> mismatch{};
              int count = 0;
              for (int i = 0; i < 10; ++i) {
                if (!present[i]) mismatch[count++] = fiveEdges[i];
              }
              add_obstruction(fiveEdges, mismatch, count);
            }
            if (presentCount <= 2) {
              std::array<int, 2> mismatch{};
              int count = 0;
              for (int i = 0; i < 10; ++i) {
                if (present[i]) mismatch[count++] = fiveEdges[i];
              }
              add_obstruction(fiveEdges, mismatch, count);
            }
          }
        }
      }
    }
  }

  for (const bool unsafe : unsafeSingle) result.safeSingles += !unsafe;
  for (int first = 0; first < pairCount; ++first) {
    for (int second = first + 1; second < pairCount; ++second) {
      const bool blocked =
          ((forbidden[first][second / 64] >> (second % 64)) & 1U) ||
          ((forbidden[second][first / 64] >> (first % 64)) & 1U);
      if (blocked) continue;
      ++result.safePairs;
      if (unsafeSingle[first] && unsafeSingle[second]) {
        result.disconnectedPairs.emplace_back(first, second);
      }
    }
  }
  return result;
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

}  // namespace

int main(int argc, char** argv) try {
  if (argc < 2 || argc > 3) {
    std::cerr << "usage: catalog_two_flip_scan graphs.g6 [jobs]\n";
    return 2;
  }
  const auto records = read_records(argv[1]);
  if (records.size() != 328) {
    throw std::runtime_error("expected 328 graph6 records");
  }
  const unsigned jobs = argc == 3
      ? static_cast<unsigned>(std::stoul(argv[2]))
      : std::max(1U, std::thread::hardware_concurrency());
  std::vector<ScanResult> results(records.size());
  std::atomic<std::size_t> next{};
  std::vector<std::thread> threads;
  for (unsigned thread = 0; thread < jobs; ++thread) {
    threads.emplace_back([&] {
      while (true) {
        const auto index = next.fetch_add(1, std::memory_order_relaxed);
        if (index >= records.size()) break;
        results[index] = scan_graph(decode_graph6(records[index]));
      }
    });
  }
  for (auto& thread : threads) thread.join();

  std::uint64_t nearOne = 0, nearTwo = 0, singles = 0, pairs = 0;
  std::uint64_t disconnected = 0;
  for (std::size_t index = 0; index < results.size(); ++index) {
    const auto& result = results[index];
    nearOne += result.nearOne;
    nearTwo += result.nearTwo;
    singles += result.safeSingles;
    pairs += result.safePairs;
    disconnected += result.disconnectedPairs.size();
    for (const auto [first, second] : result.disconnectedPairs) {
      std::cout << "candidate\t" << index << '\t' << first << '\t'
                << second << '\n';
    }
  }
  std::cout << "representatives\t" << records.size() << '\n';
  std::cout << "near_one_five_sets\t" << nearOne << '\n';
  std::cout << "near_two_five_sets\t" << nearTwo << '\n';
  std::cout << "safe_single_flips\t" << singles << '\n';
  std::cout << "safe_two_flips\t" << pairs << '\n';
  std::cout << "safe_two_flips_without_safe_intermediate\t"
            << disconnected << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
