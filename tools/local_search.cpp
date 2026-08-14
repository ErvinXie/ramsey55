#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

namespace {

constexpr int order = 43;
constexpr int edge_count = order * (order - 1) / 2;
using FiveEdges = std::array<std::uint16_t, 10>;
using FiveVertices = std::array<std::uint8_t, 5>;

struct SearchState {
  std::array<std::array<int, order>, order> edge_index{};
  std::vector<std::uint8_t> edge;
  std::vector<FiveEdges> five_edges;
  std::vector<FiveVertices> five_vertices;
  std::vector<std::uint8_t> one_count;
  std::vector<std::vector<std::uint32_t>> incident;
  std::vector<int> delta;
  std::vector<std::uint32_t> bad;
  std::vector<int> bad_position;

  explicit SearchState(const std::vector<std::string>& matrix)
      : edge(edge_count), incident(edge_count), delta(edge_count) {
    int next = 0;
    for (int v = 1; v < order; ++v) {
      for (int u = 0; u < v; ++u) {
        edge_index[u][v] = edge_index[v][u] = next;
        edge[next] = matrix[u][v] == '1';
        ++next;
      }
    }
    assert(next == edge_count);

    for (auto& list : incident) {
      list.reserve(11000);
    }
    enumerate_five_sets();
    initialize_scores();
  }

  static bool is_bad(int count) { return count == 0 || count == 10; }
  static bool is_critical(int count) {
    return count == 0 || count == 1 || count == 9 || count == 10;
  }

  static int contribution(int count, bool bit) {
    if (bit) {
      if (count == 1) return 1;
      if (count == 10) return -1;
    } else {
      if (count == 0) return -1;
      if (count == 9) return 1;
    }
    return 0;
  }

  void enumerate_five_sets() {
    five_edges.reserve(962598);
    five_vertices.reserve(962598);
    one_count.reserve(962598);
    for (int a = 0; a < order; ++a)
      for (int b = a + 1; b < order; ++b)
        for (int c = b + 1; c < order; ++c)
          for (int d = c + 1; d < order; ++d)
            for (int e = d + 1; e < order; ++e) {
              const std::array<int, 5> vertices{a, b, c, d, e};
              const FiveVertices compact_vertices{
                  static_cast<std::uint8_t>(a),
                  static_cast<std::uint8_t>(b),
                  static_cast<std::uint8_t>(c),
                  static_cast<std::uint8_t>(d),
                  static_cast<std::uint8_t>(e)};
              FiveEdges edges{};
              int position = 0;
              int count = 0;
              for (int j = 1; j < 5; ++j) {
                for (int i = 0; i < j; ++i) {
                  const int index =
                      edge_index[vertices[i]][vertices[j]];
                  edges[position++] = static_cast<std::uint16_t>(index);
                  count += edge[index];
                }
              }
              const std::uint32_t set_index =
                  static_cast<std::uint32_t>(five_edges.size());
              five_edges.push_back(edges);
              five_vertices.push_back(compact_vertices);
              one_count.push_back(static_cast<std::uint8_t>(count));
              for (int index : edges) {
                incident[index].push_back(set_index);
              }
            }
    if (five_edges.size() != 962598) {
      throw std::runtime_error("wrong number of five-vertex sets");
    }
  }

  void add_bad(std::uint32_t set_index) {
    assert(bad_position[set_index] < 0);
    bad_position[set_index] = static_cast<int>(bad.size());
    bad.push_back(set_index);
  }

  void remove_bad(std::uint32_t set_index) {
    const int position = bad_position[set_index];
    assert(position >= 0);
    const std::uint32_t last = bad.back();
    bad[position] = last;
    bad_position[last] = position;
    bad.pop_back();
    bad_position[set_index] = -1;
  }

  void initialize_scores() {
    bad_position.assign(five_edges.size(), -1);
    for (std::uint32_t set_index = 0; set_index < five_edges.size();
         ++set_index) {
      const int count = one_count[set_index];
      if (is_bad(count)) add_bad(set_index);
      if (!is_critical(count)) continue;
      for (int index : five_edges[set_index]) {
        delta[index] += contribution(count, edge[index]);
      }
    }
  }

  void flip(int index) {
    const int predicted_delta = delta[index];
    const int old_objective = static_cast<int>(bad.size());

    for (std::uint32_t set_index : incident[index]) {
      const int count = one_count[set_index];
      if (is_bad(count)) remove_bad(set_index);
      if (!is_critical(count)) continue;
      for (int other : five_edges[set_index]) {
        delta[other] -= contribution(count, edge[other]);
      }
    }

    edge[index] ^= 1;

    for (std::uint32_t set_index : incident[index]) {
      int count = one_count[set_index];
      count += edge[index] ? 1 : -1;
      one_count[set_index] = static_cast<std::uint8_t>(count);
      if (is_bad(count)) add_bad(set_index);
      if (!is_critical(count)) continue;
      for (int other : five_edges[set_index]) {
        delta[other] += contribution(count, edge[other]);
      }
    }

    assert(static_cast<int>(bad.size()) == old_objective + predicted_delta);
  }

  std::vector<std::string> matrix() const {
    std::vector<std::string> result(order, std::string(order, '0'));
    for (int v = 1; v < order; ++v) {
      for (int u = 0; u < v; ++u) {
        if (edge[edge_index[u][v]]) {
          result[u][v] = result[v][u] = '1';
        }
      }
    }
    return result;
  }
};

std::vector<std::string> read_matrix(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open input matrix");
  std::vector<std::string> rows;
  for (std::string line; std::getline(input, line);) {
    if (line.empty() || line[0] == '#') continue;
    if (line.size() != order ||
        line.find_first_not_of("01") != std::string::npos) {
      throw std::runtime_error("invalid adjacency row");
    }
    rows.push_back(line);
  }
  if (rows.size() != order) throw std::runtime_error("matrix is not 43 by 43");
  for (int u = 0; u < order; ++u) {
    if (rows[u][u] != '0') throw std::runtime_error("matrix has a loop");
    for (int v = u + 1; v < order; ++v) {
      if (rows[u][v] != rows[v][u]) {
        throw std::runtime_error("matrix is asymmetric");
      }
    }
  }
  return rows;
}

void write_matrix(const std::string& path,
                  const std::vector<std::string>& matrix) {
  std::ofstream output(path);
  if (!output) throw std::runtime_error("cannot open output matrix");
  for (const auto& row : matrix) output << row << '\n';
}

std::string state_key(const std::vector<std::uint8_t>& edge) {
  std::string key((edge.size() + 7) / 8, '\0');
  for (std::size_t i = 0; i < edge.size(); ++i) {
    if (edge[i]) key[i / 8] |= static_cast<char>(1U << (i % 8));
  }
  return key;
}

std::string key_to_graph6(const std::string& key) {
  std::string encoded(1, static_cast<char>(order + 63));
  for (int offset = 0; offset < edge_count; offset += 6) {
    int value = 0;
    for (int bit = 0; bit < 6; ++bit) {
      const int index = offset + bit;
      if (index >= edge_count) break;
      const bool present =
          (static_cast<unsigned char>(key[index / 8]) >> (index % 8)) & 1U;
      value |= static_cast<int>(present) << (5 - bit);
    }
    encoded.push_back(static_cast<char>(value + 63));
  }
  return encoded;
}

struct PlateauResult {
  std::size_t states = 0;
  int minimum_delta = std::numeric_limits<int>::max();
  bool complete = true;
  std::array<std::size_t, 6> intersection_histogram{};
  std::array<std::size_t, 3> color_histogram{};
  std::map<int, std::size_t> zero_move_histogram;
  std::array<std::size_t, edge_count> zero_edge_frequency{};
  std::vector<std::string> state_keys;
};

PlateauResult explore_objective_two_plateau(SearchState& state,
                                            std::size_t state_limit) {
  if (state.bad.size() != 2) {
    throw std::runtime_error("plateau exploration requires objective 2");
  }

  struct Frame {
    std::vector<int> moves;
    std::size_t next = 0;
    int incoming_edge = -1;
  };

  auto make_frame = [&state](int incoming_edge) {
    Frame frame;
    frame.incoming_edge = incoming_edge;
    for (int index = 0; index < edge_count; ++index) {
      if (state.delta[index] == 0) frame.moves.push_back(index);
    }
    return frame;
  };

  PlateauResult result;
  std::unordered_set<std::string> visited;
  visited.reserve(std::min<std::size_t>(state_limit, 1000000));
  const std::string initial_key = state_key(state.edge);
  visited.insert(initial_key);
  result.state_keys.push_back(initial_key);
  std::vector<Frame> stack;
  stack.push_back(make_frame(-1));

  auto observe = [&state, &result]() {
    assert(state.bad.size() == 2);
    for (int value : state.delta) {
      result.minimum_delta = std::min(result.minimum_delta, value);
    }
    int zero_moves = 0;
    for (int index = 0; index < edge_count; ++index) {
      if (state.delta[index] == 0) {
        ++zero_moves;
        ++result.zero_edge_frequency[index];
      }
    }
    ++result.zero_move_histogram[zero_moves];

    const auto& first = state.five_vertices[state.bad[0]];
    const auto& second = state.five_vertices[state.bad[1]];
    int intersection = 0;
    for (int u : first) {
      intersection += std::find(second.begin(), second.end(), u) != second.end();
    }
    ++result.intersection_histogram[intersection];

    const bool first_one = state.one_count[state.bad[0]] == 10;
    const bool second_one = state.one_count[state.bad[1]] == 10;
    const int color_class =
        first_one == second_one ? (first_one ? 2 : 0) : 1;
    ++result.color_histogram[color_class];
  };

  observe();
  while (!stack.empty()) {
    Frame& frame = stack.back();
    if (frame.next == frame.moves.size()) {
      const int incoming = frame.incoming_edge;
      stack.pop_back();
      if (incoming >= 0) state.flip(incoming);
      continue;
    }

    const int index = frame.moves[frame.next++];
    state.flip(index);
    assert(state.bad.size() == 2);
    const std::string key = state_key(state.edge);
    if (visited.contains(key)) {
      state.flip(index);
      continue;
    }
    if (visited.size() >= state_limit) {
      result.complete = false;
      state.flip(index);
      continue;
    }
    visited.insert(key);
    result.state_keys.push_back(key);
    observe();
    stack.push_back(make_frame(index));
  }

  result.states = visited.size();
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 3 || argc > 6) {
      std::cerr << "usage: local_search INPUT OUTPUT [STEPS] [RESTARTS] [SEED]\n";
      return 2;
    }
    const std::uint64_t steps =
        argc >= 4 ? std::stoull(argv[3]) : 200000;
    const int restarts = argc >= 5 ? std::stoi(argv[4]) : 10;
    const std::uint64_t seed =
        argc >= 6 ? std::stoull(argv[5]) : 20260811;

    SearchState state(read_matrix(argv[1]));
    const auto initial_edge = state.edge;
    auto best_edge = state.edge;
    int best = static_cast<int>(state.bad.size());
    std::mt19937_64 random(seed);
    std::vector<std::uint64_t> tabu_until(edge_count, 0);
    std::unordered_set<std::string> objective_two_states;
    objective_two_states.reserve(100000);
    std::unordered_set<std::string> classified_plateau_states;
    classified_plateau_states.reserve(100000);
    int plateau_components = 0;

    std::cout << "initial monochromatic K5: " << best << '\n';
    if (best == 2) {
      const PlateauResult plateau = explore_objective_two_plateau(state, 1000000);
      ++plateau_components;
      classified_plateau_states.insert(
          plateau.state_keys.begin(), plateau.state_keys.end());
      {
        std::ofstream plateau_output(
            std::string(argv[2]) + ".initial_plateau.g6");
        if (!plateau_output) {
          throw std::runtime_error("cannot open plateau graph6 output");
        }
        for (const std::string& key : plateau.state_keys) {
          plateau_output << key_to_graph6(key) << '\n';
        }
      }
      std::cout << "initial objective-2 plateau: " << plateau.states
                << " states (" << (plateau.complete ? "complete" : "truncated")
                << "), minimum one-flip delta " << plateau.minimum_delta << '\n';
      std::cout << "  bad-K5 intersection histogram:";
      for (std::size_t i = 0; i < plateau.intersection_histogram.size(); ++i) {
        if (plateau.intersection_histogram[i]) {
          std::cout << ' ' << i << ':' << plateau.intersection_histogram[i];
        }
      }
      std::cout << '\n';
      std::cout << "  bad-K5 colors (00/mixed/11): "
                << plateau.color_histogram[0] << '/'
                << plateau.color_histogram[1] << '/'
                << plateau.color_histogram[2] << '\n';
      std::cout << "  zero-delta move histogram:";
      for (const auto& [moves, states] : plateau.zero_move_histogram) {
        std::cout << ' ' << moves << ':' << states;
      }
      std::cout << '\n';
      std::map<std::size_t, std::size_t> label_frequency_histogram;
      for (std::size_t frequency : plateau.zero_edge_frequency) {
        if (frequency) ++label_frequency_histogram[frequency];
      }
      std::cout << "  transition-label frequency histogram:";
      for (const auto& [frequency, labels] : label_frequency_histogram) {
        std::cout << ' ' << frequency << ':' << labels;
      }
      std::cout << '\n';
      std::array<int, order> support_degree{};
      std::array<std::vector<int>, order> support_adjacency;
      for (int v = 1; v < order; ++v) {
        for (int u = 0; u < v; ++u) {
          const int index = state.edge_index[u][v];
          if (!plateau.zero_edge_frequency[index]) continue;
          ++support_degree[u];
          ++support_degree[v];
          support_adjacency[u].push_back(v);
          support_adjacency[v].push_back(u);
        }
      }
      std::map<int, int> support_degree_histogram;
      for (int degree : support_degree) ++support_degree_histogram[degree];
      int support_components = 0;
      std::array<bool, order> seen{};
      for (int start = 0; start < order; ++start) {
        if (seen[start] || support_degree[start] == 0) continue;
        ++support_components;
        std::vector<int> pending{start};
        seen[start] = true;
        while (!pending.empty()) {
          const int u = pending.back();
          pending.pop_back();
          for (int v : support_adjacency[u]) {
            if (!seen[v]) {
              seen[v] = true;
              pending.push_back(v);
            }
          }
        }
      }
      std::cout << "  transition-label support degrees:";
      for (const auto& [degree, vertices] : support_degree_histogram) {
        std::cout << ' ' << degree << ':' << vertices;
      }
      std::cout << ", components " << support_components << '\n';
      if (support_components == 1 && support_degree_histogram.size() == 1 &&
          support_degree_histogram.begin()->first == 2) {
        std::vector<int> cycle;
        int previous = -1;
        int current = 0;
        do {
          cycle.push_back(current);
          const auto& neighbors = support_adjacency[current];
          const int next = neighbors[0] == previous ? neighbors[1] : neighbors[0];
          previous = current;
          current = next;
        } while (current != cycle.front() && cycle.size() <= order);
        std::cout << "  transition-label Hamiltonian cycle:";
        for (int vertex : cycle) std::cout << ' ' << vertex;
        std::cout << '\n';
      }
    }

    std::uint64_t global_step = 0;
    for (int restart = 0; restart < restarts && best > 0; ++restart) {
      for (int index = 0; index < edge_count; ++index) {
        if (state.edge[index] != initial_edge[index]) state.flip(index);
      }

      if (restart > 0) {
        const int perturbations = 8 + static_cast<int>(random() % 25);
        for (int i = 0; i < perturbations; ++i) {
          state.flip(static_cast<int>(random() % edge_count));
        }
      }
      std::fill(tabu_until.begin(), tabu_until.end(), 0);

      for (std::uint64_t step = 0; step < steps && !state.bad.empty();
           ++step, ++global_step) {
        if (state.bad.size() == 2) {
          const std::string key = state_key(state.edge);
          objective_two_states.insert(key);
          if (!classified_plateau_states.contains(key)) {
            const PlateauResult component =
                explore_objective_two_plateau(state, 100000);
            ++plateau_components;
            classified_plateau_states.insert(
                component.state_keys.begin(), component.state_keys.end());
            {
              std::ofstream component_output(
                  std::string(argv[2]) + ".plateau_" +
                  std::to_string(plateau_components) + ".g6");
              if (!component_output) {
                throw std::runtime_error(
                    "cannot open component graph6 output");
              }
              for (const std::string& component_key : component.state_keys) {
                component_output << key_to_graph6(component_key) << '\n';
              }
            }
            std::cout << "discovered objective-2 component "
                      << plateau_components << ": " << component.states
                      << " states ("
                      << (component.complete ? "complete" : "truncated")
                      << "), minimum delta " << component.minimum_delta
                      << ", intersections";
            for (std::size_t i = 0;
                 i < component.intersection_histogram.size(); ++i) {
              if (component.intersection_histogram[i]) {
                std::cout << ' ' << i << ':'
                          << component.intersection_histogram[i];
              }
            }
            std::cout << ", colors "
                      << component.color_histogram[0] << '/'
                      << component.color_histogram[1] << '/'
                      << component.color_histogram[2]
                      << ", zero moves";
            for (const auto& [moves, states] :
                 component.zero_move_histogram) {
              std::cout << ' ' << moves << ':' << states;
            }
            std::map<std::size_t, std::size_t> label_frequencies;
            std::array<int, order> support_degrees{};
            for (std::size_t frequency :
                 component.zero_edge_frequency) {
              if (frequency) ++label_frequencies[frequency];
            }
            for (int v = 1; v < order; ++v) {
              for (int u = 0; u < v; ++u) {
                const int index = state.edge_index[u][v];
                if (component.zero_edge_frequency[index]) {
                  ++support_degrees[u];
                  ++support_degrees[v];
                }
              }
            }
            std::map<int, int> support_degrees_histogram;
            for (int degree : support_degrees) {
              ++support_degrees_histogram[degree];
            }
            std::cout << ", labels";
            for (const auto& [frequency, labels] : label_frequencies) {
              std::cout << ' ' << frequency << ':' << labels;
            }
            std::cout << ", support degrees";
            for (const auto& [degree, vertices] :
                 support_degrees_histogram) {
              std::cout << ' ' << degree << ':' << vertices;
            }
            std::cout << '\n';
          }
        }

        const std::uint32_t bad_set =
            state.bad[random() % state.bad.size()];
        const auto& candidates = state.five_edges[bad_set];
        const bool noisy = random() % 100 < 8;
        int chosen = -1;
        int chosen_delta = std::numeric_limits<int>::max();
        std::uint64_t ties = 0;

        if (noisy) {
          chosen = candidates[random() % candidates.size()];
        } else {
          for (int index : candidates) {
            const int proposed =
                static_cast<int>(state.bad.size()) + state.delta[index];
            const bool tabu = tabu_until[index] > global_step;
            if (tabu && proposed >= best) continue;
            if (state.delta[index] < chosen_delta) {
              chosen = index;
              chosen_delta = state.delta[index];
              ties = 1;
            } else if (state.delta[index] == chosen_delta && ++ties > 0 &&
                       random() % ties == 0) {
              chosen = index;
            }
          }
        }
        if (chosen < 0) chosen = candidates[random() % candidates.size()];

        state.flip(chosen);
        tabu_until[chosen] = global_step + 5 + random() % 17;

        if (static_cast<int>(state.bad.size()) < best) {
          best = static_cast<int>(state.bad.size());
          best_edge = state.edge;
          std::cout << "best " << best << " at restart " << restart
                    << ", step " << step << '\n';
        }
      }
    }

    state.edge = best_edge;
    write_matrix(argv[2], state.matrix());
    std::cout << "best monochromatic K5: " << best << '\n';
    std::cout << "distinct objective-2 states visited: "
              << objective_two_states.size() << '\n';
    std::cout << "objective-2 components classified: "
              << plateau_components << '\n';
    std::cout << "wrote best matrix to " << argv[2] << '\n';
    return best == 0 ? 0 : 1;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 2;
  }
}
