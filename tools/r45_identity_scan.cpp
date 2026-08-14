#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace {

struct Graph {
  int order{};
  std::vector<std::uint32_t> adjacency;
};

Graph decode_graph6(std::string_view text) {
  if (!text.empty() && text.back() == '\r') text.remove_suffix(1);
  if (text.empty()) throw std::runtime_error("empty graph6 record");
  const int order = static_cast<unsigned char>(text[0]) - 63;
  if (order < 0 || order > 32 || order == 63) {
    throw std::runtime_error("scanner supports short graph6 records up to order 32");
  }
  Graph graph{order, std::vector<std::uint32_t>(order)};
  int word = 1;
  int shift = 5;
  auto next_bit = [&]() {
    if (word >= static_cast<int>(text.size())) {
      throw std::runtime_error("truncated graph6 record");
    }
    const int value = static_cast<unsigned char>(text[word]) - 63;
    if (value < 0 || value > 63) throw std::runtime_error("bad graph6 byte");
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
        graph.adjacency[u] |= std::uint32_t{1} << v;
        graph.adjacency[v] |= std::uint32_t{1} << u;
      }
    }
  }
  return graph;
}

struct Features {
  std::int64_t vertices{};
  std::int64_t edges{};
  std::int64_t triangles{};
  std::int64_t paths3{};
  std::int64_t cycles4{};
  std::int64_t stars{};
  std::int64_t paths4{};
  std::int64_t trianglePendant{};
  std::int64_t diamonds{};
};

enum class FourType { other, cycle, star, path, trianglePendant, diamond };

FourType classify_four(int pattern) {
  constexpr int endpoints[6][2] = {
      {0, 1}, {0, 2}, {0, 3}, {1, 2}, {1, 3}, {2, 3}};
  int degree[4]{};
  int edges = 0;
  for (int bit = 0; bit < 6; ++bit) {
    if (!(pattern & (1 << bit))) continue;
    ++edges;
    ++degree[endpoints[bit][0]];
    ++degree[endpoints[bit][1]];
  }
  std::sort(std::begin(degree), std::end(degree));
  if (edges == 4 && std::equal(std::begin(degree), std::end(degree),
                               std::begin(std::array{2, 2, 2, 2}))) {
    return FourType::cycle;
  }
  if (edges == 3 && std::equal(std::begin(degree), std::end(degree),
                               std::begin(std::array{1, 1, 1, 3}))) {
    return FourType::star;
  }
  if (edges == 3 && std::equal(std::begin(degree), std::end(degree),
                               std::begin(std::array{1, 1, 2, 2}))) {
    return FourType::path;
  }
  if (edges == 4 && std::equal(std::begin(degree), std::end(degree),
                               std::begin(std::array{1, 2, 2, 3}))) {
    return FourType::trianglePendant;
  }
  if (edges == 5 && std::equal(std::begin(degree), std::end(degree),
                               std::begin(std::array{2, 2, 3, 3}))) {
    return FourType::diamond;
  }
  return FourType::other;
}

const std::array<FourType, 64>& four_types() {
  static const auto types = [] {
    std::array<FourType, 64> result{};
    for (int pattern = 0; pattern < 64; ++pattern) {
      result[pattern] = classify_four(pattern);
    }
    return result;
  }();
  return types;
}

void add_four(Features& features, FourType type) {
  switch (type) {
    case FourType::cycle: ++features.cycles4; break;
    case FourType::star: ++features.stars; break;
    case FourType::path: ++features.paths4; break;
    case FourType::trianglePendant: ++features.trianglePendant; break;
    case FourType::diamond: ++features.diamonds; break;
    case FourType::other: break;
  }
}

std::pair<Features, Features> count_features(const Graph& graph) {
  const auto& types = four_types();
  Features original, complement;
  original.vertices = complement.vertices = graph.order;
  for (const auto row : graph.adjacency) original.edges += std::popcount(row);
  original.edges /= 2;
  complement.edges = std::int64_t{graph.order} * (graph.order - 1) / 2 - original.edges;

  for (int a = 0; a < graph.order; ++a) {
    for (int b = a + 1; b < graph.order; ++b) {
      for (int c = b + 1; c < graph.order; ++c) {
        const int edge_count =
            ((graph.adjacency[a] >> b) & 1U) +
            ((graph.adjacency[a] >> c) & 1U) +
            ((graph.adjacency[b] >> c) & 1U);
        if (edge_count == 3) ++original.triangles;
        if (edge_count == 2) ++original.paths3;
        if (edge_count == 0) ++complement.triangles;
        if (edge_count == 1) ++complement.paths3;

        for (int d = c + 1; d < graph.order; ++d) {
          const int pattern =
              (((graph.adjacency[a] >> b) & 1U) << 0) |
              (((graph.adjacency[a] >> c) & 1U) << 1) |
              (((graph.adjacency[a] >> d) & 1U) << 2) |
              (((graph.adjacency[b] >> c) & 1U) << 3) |
              (((graph.adjacency[b] >> d) & 1U) << 4) |
              (((graph.adjacency[c] >> d) & 1U) << 5);
          add_four(original, types[pattern]);
          add_four(complement, types[pattern ^ 63]);
        }
      }
    }
  }
  return {original, complement};
}

std::int64_t p1(const Features& x, std::int64_t n) {
  const auto v = x.vertices;
  const auto e = x.edges;
  return n * (n - 3) * v - (n * n + 2 * n - 6) * v * v +
         3 * n * v * v * v - 2 * v * v * v * v +
         2 * (n * n + n - 8) * e - 12 * e * e -
         12 * (n - 1) * v * e + 12 * v * v * e +
         72 * x.cycles4 + 12 * (n - 2) * x.triangles +
         24 * x.stars + 24 * x.paths4 + 24 * x.trianglePendant +
         12 * (n + 2) * x.paths3 - 24 * v * x.paths3 +
         32 * x.diamonds;
}

std::int64_t p2(const Features& y, std::int64_t n) {
  return 4 * y.edges * y.edges - 12 * y.stars - 8 * y.cycles4 -
         8 * y.trianglePendant - 24 * y.diamonds +
         2 * (n - 8) * y.paths3;
}

std::int64_t dual_part(const Features& y, std::int64_t n,
                       std::int64_t neighborhood_order) {
  const auto d = neighborhood_order;
  return p2(y, n) + 4 * d * y.paths3 - 2 * (n - 2) * d * y.edges +
         4 * d * d * y.edges;
}

struct Extremum {
  std::int64_t value{};
  std::string witness;
};

struct Result {
  std::uint64_t count{};
  Extremum aMin{std::numeric_limits<std::int64_t>::max(), {}};
  Extremum aMax{std::numeric_limits<std::int64_t>::min(), {}};
  Extremum bMin{std::numeric_limits<std::int64_t>::max(), {}};
  Extremum bMax{std::numeric_limits<std::int64_t>::min(), {}};

  void observe(std::int64_t a, std::int64_t b, std::string_view witness) {
    ++count;
    if (a < aMin.value) aMin = {a, std::string(witness)};
    if (a > aMax.value) aMax = {a, std::string(witness)};
    if (b < bMin.value) bMin = {b, std::string(witness)};
    if (b > bMax.value) bMax = {b, std::string(witness)};
  }

  void merge(const Result& other) {
    count += other.count;
    auto merge_min = [](Extremum& target, const Extremum& source) {
      if (source.value < target.value) target = source;
    };
    auto merge_max = [](Extremum& target, const Extremum& source) {
      if (source.value > target.value) target = source;
    };
    merge_min(aMin, other.aMin);
    merge_max(aMax, other.aMax);
    merge_min(bMin, other.bMin);
    merge_max(bMax, other.bMax);
  }
};

std::vector<std::string_view> read_records(const std::string& path,
                                           std::string& storage,
                                           std::uint64_t limit) {
  std::ifstream input(path, std::ios::binary);
  if (!input) throw std::runtime_error("cannot open " + path);
  storage.assign(std::istreambuf_iterator<char>(input), {});
  std::vector<std::string_view> records;
  std::size_t start = 0;
  while (start < storage.size() && records.size() < limit) {
    const auto end = storage.find('\n', start);
    const auto stop = end == std::string::npos ? storage.size() : end;
    if (stop > start) records.emplace_back(storage.data() + start, stop - start);
    if (end == std::string::npos) break;
    start = end + 1;
  }
  return records;
}

Result scan_file(const std::string& path, int ambient,
                 std::uint64_t limit, unsigned jobs, int& order) {
  std::string storage;
  const auto records = read_records(path, storage, limit);
  if (records.empty()) throw std::runtime_error("no graph6 records in " + path);
  order = decode_graph6(records.front()).order;
  std::atomic<std::size_t> next{};
  std::vector<Result> local(jobs);
  std::vector<std::thread> threads;
  for (unsigned thread = 0; thread < jobs; ++thread) {
    threads.emplace_back([&, thread] {
      while (true) {
        const auto index = next.fetch_add(1, std::memory_order_relaxed);
        if (index >= records.size()) break;
        const auto graph = decode_graph6(records[index]);
        if (graph.order != order) throw std::runtime_error("mixed graph orders");
        const auto [features, complement] = count_features(graph);
        const auto a = p1(features, ambient);
        const auto d = ambient - 1 - graph.order;
        const auto b = dual_part(complement, ambient, d);
        local[thread].observe(a, b, records[index]);
      }
    });
  }
  for (auto& thread : threads) thread.join();
  Result result;
  for (const auto& partial : local) result.merge(partial);
  return result;
}

}  // namespace

int main(int argc, char** argv) try {
  int ambient = 43;
  std::uint64_t limit = std::numeric_limits<std::uint64_t>::max();
  unsigned jobs = std::max(1U, std::thread::hardware_concurrency());
  std::vector<std::string> paths;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    if (argument == "--ambient" && i + 1 < argc) ambient = std::stoi(argv[++i]);
    else if (argument == "--limit" && i + 1 < argc) limit = std::stoull(argv[++i]);
    else if (argument == "--jobs" && i + 1 < argc) jobs = std::stoul(argv[++i]);
    else paths.push_back(argument);
  }
  if (paths.empty()) {
    std::cerr << "usage: r45_identity_scan [--ambient N] [--limit N] [--jobs N] file.g6 ...\n";
    return 2;
  }
  std::cout << "file\torder\tcount\tA_min\tA_max\tB_min\tB_max"
               "\tA_min_witness\tA_max_witness\tB_min_witness\tB_max_witness\n";
  for (const auto& path : paths) {
    int order = 0;
    const auto result = scan_file(path, ambient, limit, jobs, order);
    std::cout << path << '\t' << order << '\t' << result.count << '\t'
              << result.aMin.value << '\t' << result.aMax.value << '\t'
              << result.bMin.value << '\t' << result.bMax.value << '\t'
              << result.aMin.witness << '\t' << result.aMax.witness << '\t'
              << result.bMin.witness << '\t' << result.bMax.witness << '\n';
  }
  return 0;
} catch (const std::exception& error) {
  std::cerr << "error: " << error.what() << '\n';
  return 1;
}
