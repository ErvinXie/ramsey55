#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int order = 24;

std::array<std::uint32_t, order> decode_complement(const std::string& text) {
  if (text.empty() || static_cast<unsigned char>(text[0]) - 63 != order) {
    throw std::runtime_error("expected an order-24 short graph6 record");
  }
  std::array<std::uint32_t, order> adjacency{};
  int word = 1;
  int shift = 5;
  for (int v = 1; v < order; ++v) {
    for (int u = 0; u < v; ++u) {
      if (word >= static_cast<int>(text.size())) {
        throw std::runtime_error("truncated graph6 record");
      }
      const int value = static_cast<unsigned char>(text[word]) - 63;
      if (value < 0 || value > 63) {
        throw std::runtime_error("invalid graph6 character");
      }
      const bool catalogEdge = value & (1 << shift);
      if (!catalogEdge) {
        adjacency[u] |= std::uint32_t{1} << v;
        adjacency[v] |= std::uint32_t{1} << u;
      }
      if (--shift < 0) {
        shift = 5;
        ++word;
      }
    }
  }
  return adjacency;
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

}  // namespace

int main(int argc, char** argv) try {
  if (argc != 3) {
    std::cerr << "usage: count_degree18_cones r45_24.g6 index\n";
    return 2;
  }
  const auto adjacency = decode_complement(read_record(argv[1], std::stoull(argv[2])));
  const std::uint32_t subsets = std::uint32_t{1} << order;
  std::vector<std::uint8_t> hasEdge(subsets);
  std::vector<std::uint8_t> hasTriangle(subsets);
  std::vector<std::uint8_t> hasK4(subsets);
  std::array<std::uint64_t, order + 1> bySize{};
  for (std::uint32_t mask = 1; mask < subsets; ++mask) {
    const int vertex = std::countr_zero(mask);
    const std::uint32_t rest = mask & (mask - 1);
    const std::uint32_t neighbors = rest & adjacency[vertex];
    hasEdge[mask] = hasEdge[rest] || neighbors;
    hasTriangle[mask] = hasTriangle[rest] || hasEdge[neighbors];
    hasK4[mask] = hasK4[rest] || hasTriangle[neighbors];
    if (!hasK4[mask]) ++bySize[std::popcount(mask)];
  }
  ++bySize[0];
  std::uint64_t total = 0;
  for (int size = 0; size <= order; ++size) {
    total += bySize[size];
    if (bySize[size]) std::cout << "size_" << size << '\t' << bySize[size] << '\n';
  }
  std::cout << "total\t" << total << '\n';
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
