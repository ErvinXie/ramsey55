# Ramsey55

An AI-assisted research repository for work on the diagonal Ramsey number
`R(5, 5)`.

Project history is recorded in `daily-notes/`, while stable results and research
summaries belong in `doc/`. Agent collaboration conventions are defined in
`AGENTS.md` and `.meta-agent/AGENT-RUNTIME.md`.

## Research baseline

- [R(5,5) research frontier, 2026-08-11](doc/r55-frontier-2026-08-11.md)
- [Formal proof status and trust boundary](doc/formal-proof-status.md)
- [One-vertex extension certificates](doc/extension-certificates.md)
- [Extension multiplicity landscape](doc/extension-multiplicity-landscape.md)
- [Catalog single-edge flip forest](doc/catalog-flip-forest.md)
- [K43 two-violation landscape](doc/near-miss-landscape.md)
- [Nonseparable-identity experiment](doc/nonseparable-identity-experiment.md)
- [Degree-18 extreme gluing experiment](doc/degree18-extreme-gluing.md)
- [Order-45 upper-bound program](doc/order45-upper-bound.md)

## Reproduce the checked baseline

The Python verifier has no third-party dependencies:

    sh scripts/fetch_reference_data.sh
    PYTHONPATH=src:tools python3 -m unittest discover -s tests -v
    PYTHONPATH=src python3 tools/verify_reference.py
    PYTHONPATH=src python3 tools/verify_catalog_flip_certificate.py
    PYTHONPATH=src python3 tools/verify_four_flip_certificate.py

The formal development is pinned to Lean 4.31.0:

    lake build

The principal theorems already checked by Lean are:

- `Ramsey55.not_forcesMonochromatic5_42`, the lower bound
  \(R(5,5)>42\);
- `Ramsey55.reference42CatalogWithComplements_all_noExtension`, proving that
  none of the 656 public 42-vertex graphs can gain one vertex while remaining
  Ramsey-free;
- `Ramsey55.reference42TwoViolationCatalogWithComplements_all_atLeastTwo`,
  strengthening this to at least two distinct monochromatic \(K_5\)s for
  every attachment to every public graph;
- `Ramsey55.ramsey55_is_43_of_all_42_nonextendable`, reducing the exact target
  to the explicit remaining obligation that every Ramsey-free 42-vertex
  colouring is nonextendable.

The historical claim that the 656 public graphs form a complete
classification remains unproved. Consequently the exact upper bound is still
open and this repository does not claim that \(R(5,5)=43\) has been solved.

Regenerate the compact extension certificates and the generated Lean source:

    PYTHONPATH=src python3 tools/generate_extension_certificates.py
    PYTHONPATH=src python3 tools/generate_lean_extension_certificates.py
    PYTHONPATH=src python3 \
      tools/generate_extension_multiplicity_certificates.py
    PYTHONPATH=src python3 \
      tools/generate_lean_extension_multiplicity_certificates.py
    lake build

Generate the two raw 43-vertex SAT benchmarks with:

    PYTHONPATH=src python3 tools/generate_cnf.py --order 43 \
      --fixed-star-degree 18 --output build/r55_n43_d18.cnf
    PYTHONPATH=src python3 tools/generate_cnf.py --order 43 \
      --fixed-star-degree 20 --output build/r55_n43_d20.cnf

Generate and independently verify the complete pair of normalized 45-vertex
benchmarks with:

    PYTHONPATH=src python3 tools/generate_order45_benchmarks.py
    PYTHONPATH=src python3 tools/verify_order45_benchmarks.py \
      data/order45-benchmark-manifest.json --cnf-dir build/order45

Generate the degree-window-strengthened pair and run its independent encoder:

    PYTHONPATH=src python3 tools/generate_order45_strengthened_benchmarks.py
    PYTHONPATH=src python3 tools/verify_order45_strengthened_benchmarks.py \
      data/order45-strengthened-benchmark-manifest.json \
      --cnf-dir build/order45-strengthened

Generate the safe cross-row lex-leader variants with:

    PYTHONPATH=src python3 tools/generate_order45_lex_benchmarks.py
    PYTHONPATH=src:tools python3 tools/verify_order45_lex_benchmarks.py \
      data/order45-lex-benchmark-manifest.json --cnf-dir build/order45-lex

Generate the complete nonpositive-excess witness cover with:

    PYTHONPATH=src:tools python3 tools/generate_order45_excess_benchmarks.py
    PYTHONPATH=src:tools python3 tools/verify_order45_excess_benchmarks.py \
      data/order45-excess-benchmark-manifest.json --cnf-dir build/order45-excess

Generate and independently verify the exact local-edge cube strata with:

    PYTHONPATH=src:tools python3 tools/generate_order45_edge_strata.py
    PYTHONPATH=src:tools python3 tools/verify_order45_edge_strata.py \
      build/order45-strata/manifest.json --cnf-dir build/order45-strata
    lake env lean --run tools/VerifyOrder45ExactMothers.lean \
      build/order45-strata
    sh scripts/build_cadical_assumption_scan.sh

Reproduce the unique-H100 reduction and the complete two-formula H100/J132
top stratum with:

    PYTHONPATH=src:tools python3 tools/generate_order45_fixed_h100.py
    PYTHONPATH=src:tools python3 tools/verify_order45_fixed_h100.py \
      data/order45-fixed-h100-manifest.json \
      --cnf build/order45-fixed-h100.cnf
    sh scripts/build_order45_fixed_pair_generator.sh
    PYTHONPATH=src:tools python3 \
      tools/generate_order45_fixed_pair_benchmarks.py
    PYTHONPATH=src:tools python3 \
      tools/verify_order45_fixed_pair_benchmarks.py \
      data/order45-fixed-pair-manifest.json \
      --cnf-dir build/order45-fixed-pairs

The optional symmetry-reduced comparison is generated and independently
reconstructed with:

    PYTHONPATH=src:tools python3 \
      tools/generate_order45_fixed_pair_benchmarks.py \
      --symmetry --output-dir build/order45-fixed-pairs/symmetry
    PYTHONPATH=src:tools python3 \
      tools/verify_order45_fixed_pair_benchmarks.py \
      data/order45-fixed-pair-symmetry-manifest.json \
      --cnf-dir build/order45-fixed-pairs/symmetry

An UNSAT result for these lex-leader formulas still requires the checked
finite-orbit bridge documented in `formal/Ramsey55/Symmetry.lean`; it is not
by itself a labelled fixed-pair proof.

These fixed-pair formulas cover only the exact local edge layer
`e(H)=100, e(J)=132`. They are a rigorously checked subproblem of the full
order-45 excess cover, not an upper-bound proof by themselves.
