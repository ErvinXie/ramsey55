#!/usr/bin/env bash
set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tools_root="$repo_root/.tools"
source_root="$tools_root/src"
bin_root="$tools_root/bin"

cadical_commit=3ff42f04384489916f017acd6d5e7cbfa7257be7
drat_trim_commit=2e3b2dc0ecf938addbd779d42877b6ed69d9a985
kissat_commit=8af8e56f174b778aef3aa45af9f739b2a5f492c2
satsuma_commit=c6ad1b59f29fa32dae587ef369135735f40d498a
cnc_commit=705b60c6491ef2b61988b3ce6ac674be1b90571d

skip_apt=false
skip_lean=false
for argument in "$@"; do
  case "$argument" in
    --skip-apt) skip_apt=true ;;
    --skip-lean) skip_lean=true ;;
    *)
      echo "usage: $0 [--skip-apt] [--skip-lean]" >&2
      exit 2
      ;;
  esac
done

if ! $skip_apt; then
  if [[ $(id -u) -eq 0 ]]; then
    apt_prefix=()
  elif command -v sudo >/dev/null 2>&1; then
    apt_prefix=(sudo)
  else
    echo "error: root privileges or sudo are required for package setup" >&2
    exit 2
  fi
  "${apt_prefix[@]}" apt-get update
  DEBIAN_FRONTEND=noninteractive "${apt_prefix[@]}" apt-get install -y \
    build-essential ca-certificates cmake elan git nauty ninja-build python3
fi

mkdir -p "$source_root" "$bin_root" "$repo_root/build"

checkout_pinned() {
  local url=$1
  local destination=$2
  local commit=$3
  if [[ ! -d "$destination/.git" ]]; then
    git clone --filter=blob:none --no-checkout "$url" "$destination"
  fi
  git -C "$destination" fetch --depth=1 origin "$commit"
  git -C "$destination" checkout --detach "$commit"
}

checkout_pinned \
  https://github.com/arminbiere/cadical.git \
  "$source_root/cadical" \
  "$cadical_commit"
(
  cd "$source_root/cadical"
  ./configure -q
  make -j"$(nproc)"
)
ln -sfn "$source_root/cadical/build/cadical" "$bin_root/cadical"

checkout_pinned \
  https://github.com/marijnheule/drat-trim.git \
  "$source_root/drat-trim" \
  "$drat_trim_commit"
make -C "$source_root/drat-trim" -j"$(nproc)" drat-trim
ln -sfn "$source_root/drat-trim/drat-trim" "$bin_root/drat-trim"

checkout_pinned \
  https://github.com/arminbiere/kissat.git \
  "$source_root/kissat" \
  "$kissat_commit"
(
  cd "$source_root/kissat"
  ./configure
  make -j"$(nproc)"
)
ln -sfn "$source_root/kissat/build/kissat" "$bin_root/kissat"

checkout_pinned \
  https://github.com/markusa4/satsuma.git \
  "$source_root/satsuma" \
  "$satsuma_commit"
cmake -S "$source_root/satsuma" -B "$source_root/satsuma/build" \
  -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build "$source_root/satsuma/build" --target satsuma \
  --parallel "$(nproc)"
ln -sfn "$source_root/satsuma/build/satsuma" "$bin_root/satsuma"

checkout_pinned \
  https://github.com/marijnheule/CnC.git \
  "$source_root/CnC" \
  "$cnc_commit"
make -C "$source_root/CnC/march_cu" clean
make -C "$source_root/CnC/march_cu" -j"$(nproc)" \
  CFLAGS="-O3 -DNDEBUG -fcommon"
ln -sfn "$source_root/CnC/march_cu/march_cu" "$bin_root/march_cu"

if command -v labelg >/dev/null 2>&1; then
  labelg_path=$(command -v labelg)
elif command -v nauty-labelg >/dev/null 2>&1; then
  labelg_path=$(command -v nauty-labelg)
else
  echo "error: the nauty package did not provide labelg" >&2
  exit 2
fi
ln -sfn "$labelg_path" "$bin_root/labelg"

(
  cd "$repo_root"
  sh scripts/build_catalog_two_flip_scan.sh
  c++ -std=c++20 -O3 -DNDEBUG \
    -I"$source_root/cadical/src" \
    tools/enumerate_primary_sat_models.cpp \
    "$source_root/cadical/build/libcadical.a" \
    -pthread -o build/enumerate_primary_sat_models
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    -I"$source_root/cadical/src" \
    tools/generate_cadical_cubes.cpp \
    "$source_root/cadical/build/libcadical.a" \
    -pthread -o build/generate_cadical_cubes
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    -I"$source_root/cadical/src" \
    tools/solve_cadical_cubes.cpp \
    "$source_root/cadical/build/libcadical.a" \
    -pthread -o build/solve_cadical_cubes
  sh scripts/build_refine_cadical_cubes.sh
  sh scripts/build_prove_cadical_cubes.sh
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    -I"$source_root/cadical/src" \
    tools/scan_degree18_catalog.cpp \
    "$source_root/cadical/build/libcadical.a" \
    -pthread -o build/scan_degree18_catalog
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    tools/generate_degree18_fixed_cnf.cpp \
    -o build/generate_degree18_fixed_cnf
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    tools/generate_degree18_pair_cnf.cpp \
    -o build/generate_degree18_pair_cnf
  sh scripts/build_order45_fixed_pair_generator.sh
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    tools/count_degree18_cones.cpp \
    -o build/count_degree18_cones
  c++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
    tools/summarize_r45_catalog.cpp \
    -o build/summarize_r45_catalog
)

echo "compute node ready"
echo "  cadical:    $bin_root/cadical"
echo "  drat-trim:  $bin_root/drat-trim"
echo "  kissat:     $bin_root/kissat"
echo "  satsuma:    $bin_root/satsuma"
echo "  march_cu:   $bin_root/march_cu"
echo "  labelg:     $bin_root/labelg"
echo "  enumerator: $repo_root/build/enumerate_primary_sat_models"
echo "  cuber:      $repo_root/build/generate_cadical_cubes"
echo "  cube solver: $repo_root/build/solve_cadical_cubes"
if ! $skip_lean; then
  toolchain=$(tr -d '[:space:]' < "$repo_root/lean-toolchain")
  elan toolchain install "$toolchain"
  elan run "$toolchain" lean --version
else
  echo "  lean:        skipped"
fi
