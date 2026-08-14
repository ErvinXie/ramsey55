#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr int order = 24;

int edge_count(const std::string& text) {
  if (text.empty() || static_cast<unsigned char>(text[0]) - 63 != order) {
    throw std::runtime_error("expected an order-24 short graph6 record");
  }
  int edges = 0;
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
      edges += (value >> shift) & 1;
      if (--shift < 0) {
        shift = 5;
        ++word;
      }
    }
  }
  return edges;
}

}  // namespace

int main(int argc, char** argv) try {
  if (argc < 2 || argc > 3) {
    std::cerr << "usage: summarize_r45_catalog r45_24.g6 [threshold]\n";
    return 2;
  }
  const int threshold = argc == 3 ? std::stoi(argv[2]) : 128;
  std::ifstream input(argv[1]);
  if (!input) throw std::runtime_error("cannot open catalog");
  std::map<int, std::uint64_t> histogram;
  std::vector<std::pair<std::size_t, int>> selected;
  std::string line;
  std::size_t index = 0;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == '#') continue;
    const int edges = edge_count(line);
    ++histogram[edges];
    if (edges >= threshold) selected.emplace_back(index, edges);
    ++index;
  }
  std::cout << "records\t" << index << '\n';
  for (const auto& [edges, count] : histogram) {
    std::cout << "edges_" << edges << '\t' << count << '\n';
  }
  std::cout << "selected\t" << selected.size() << '\n';
  for (const auto& [record, edges] : selected) {
    std::cout << "record\t" << record << '\t' << edges << '\n';
  }
  return index == 352366 ? 0 : 2;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 2;
}
