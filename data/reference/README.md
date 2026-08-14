# Reference data

Files in this directory are immutable external inputs. Every source must have a
stable URL, checksum where applicable, and an independent semantic verifier.

## r55_42some.g6

- Source: Brendan McKay's
  [Ramsey data page](https://users.cecs.anu.edu.au/~bdm/data/ramsey.html)
- Direct URL:
  <https://users.cecs.anu.edu.au/~bdm/data/r55_42some.g6>
- Format: 328 graph6 records of order 42; their complements give the 656 known
  \(R(5,5,42)\) graphs.
- SHA-256:
  067902e853d87b49bcef0d1d4c0e3bbadd238ee18bc65341b079a3ca4780eccb
- Fetch: scripts/fetch_reference_data.sh
- Verify: PYTHONPATH=src python3 tools/verify_reference.py

The 328 records are treated as known witnesses, not as a proved-complete
classification.

## r55_42_extension_covers.json.gz

- Derived from: `r55_42some.g6` by
  `tools/generate_extension_certificates.py`.
- Format: `ramsey55-extension-cover-v1`; one postorder binary decision tree
  for each of the 328 representatives. A branch fixes the colour of one edge
  from a new apex. Every leaf identifies a monochromatic old \(K_4\) whose
  four apex edges have the same colour, hence a monochromatic \(K_5\).
- Coverage: 328 representatives directly and their 328 complements by colour
  duality.
- Size: 395,847 bytes compressed.
- Trees: 47,387 branches, 47,715 leaves; largest tree 429 nodes.
- SHA-256:
  2a6fc3f56195ca962a14c2e15c56278043b222a2a8d568dad3024f6ab09a0e64
- Regenerate and independently recheck:
  `PYTHONPATH=src python3 tools/generate_extension_certificates.py`.
- Generate Lean certificates:
  `PYTHONPATH=src python3 tools/generate_lean_extension_certificates.py`.

This is a deterministic derived certificate artifact rather than an external
source. The Python verifier does not call the search routine when validating
a serialized tree. Lean separately embeds the graph and tree data and checks
all branches using the generic theorem in `formal/Ramsey55/Extension.lean`.
The certificates prove nonextendability of the listed graphs; they do not
prove that the list contains every Ramsey-free graph of order 42.

## r55_42_extension_two_covers.json.gz

- Derived from: `r55_42some.g6` by
  `tools/generate_extension_multiplicity_certificates.py`.
- Meaning: every leaf carries two different monochromatic old \(K_4\)s, so
  every apex attachment creates at least two distinct monochromatic
  \(K_5\)s.
- Coverage: 328 representatives directly and 328 complements by colour
  duality.
- Trees: 145,196 branches, 145,524 leaves; largest tree 1,133 nodes.
- Size: 1,677,909 bytes compressed.
- SHA-256:
  f15a2f01d5eff68c4ddba713a0bfe92cfd3ce103140ced186fbc7bab9a4a6609
- Regenerate and independently recheck:
  `PYTHONPATH=src python3 tools/generate_extension_multiplicity_certificates.py`.
- Generate Lean certificates:
  `PYTHONPATH=src python3 tools/generate_lean_extension_multiplicity_certificates.py`.

The stronger artifact implies the one-violation cover result but is kept
separate because the smaller certificate is faster to inspect and sufficient
for nonextendability. As before, the result applies to the public catalog and
does not assert that the catalog is complete.

## r55_42_flip_forest.json.gz

- Derived from: `r55_42some.g6` by
  `tools/generate_catalog_flip_certificate.py`.
- Meaning: six roots and 322 forest transitions reconstruct all 328
  representatives. The artifact also lists all 2,040 of the 328×861 labelled
  edge toggles that remain Ramsey-free and maps each back into the catalog.
  A transition toggles one edge, optionally complements all colours, and
  applies an explicit 42-vertex permutation.
- Component roots/sizes: 0/48, 23/96, 25/128, 39/12, 172/40, 190/4.
- Size: 60,880 bytes compressed.
- SHA-256:
  86c047ac9e8b3efffa2da8704305bcd5395c49d3dc6acbf118e9170b996c4625
- Verify without nauty:
  `PYTHONPATH=src python3 tools/verify_catalog_flip_certificate.py`.

Nauty is used by the generator to discover candidate isomorphisms, but the
artifact stores full permutations. The verifier checks every pair under those
permutations, independently recomputes the 2,040 safe flips using the local
triangle criterion, and checks complete forest coverage, so nauty is not part
of the verification trust boundary. The forest compresses the known list and
proves one-edge closure; it does not prove that the list is complete.

## r55_42_minimal_four_flips.json.gz

- Derived from the complete fixed-cardinality searches in
  `build/minimal-4-flip-models` by
  `tools/generate_four_flip_certificate.py`.
- Meaning: all 160 labelled inclusion-minimal Ramsey-free four-edge moves
  from the 328 public representatives. Every model includes explicit checks
  that all proper subsets are unsafe and an explicit 42-vertex permutation
  mapping the result back into the public catalog, possibly after a colour
  complement.
- Distribution: 208 representatives have no such model, 80 have one, and 40
  have two. There are no new catalog types.
- Size: 10,493 bytes compressed.
- SHA-256:
  72826dc991368fd42ffab6b1e6fb894f75821d19725efb97b0e2eb673ce2dd7a
- Verify without a SAT solver or nauty:
  `PYTHONPATH=src python3 tools/verify_four_flip_certificate.py`.

The enumeration was independently closed by blocking every listed model,
proving the residual formula UNSAT with CaDiCaL, and checking all 328 DRAT
proofs with drat-trim. The compact committed artifact stores the models and
explicit isomorphisms; it is not a proof that the public catalog is globally
complete.

## r45_24.g6

- Source: Brendan McKay's
  [Ramsey data page](https://users.cecs.anu.edu.au/~bdm/data/ramsey.html).
- Direct URL: <https://users.cecs.anu.edu.au/~bdm/data/r45_24.g6>.
- Format: the complete 352,366-record catalog of Ramsey(4,5,24) graphs.
- Size: 16,913,568 bytes.
- SHA-256:
  83ca4028f206b2fa4315ef219b8c2c57c7835209673dd8183d8fb4353bd4fdd0
- Summarize edge counts and select an extreme tail:
  `build/summarize_r45_catalog data/reference/r45_24.g6 128`.

## r4518.83.g6, r4518.84.g6, r4518.85.g6

- Source: the `r45extreme.tar.gz` archive linked from McKay's Ramsey data
  page.
- Direct archive URL:
  <https://users.cecs.anu.edu.au/~bdm/data/r45extreme.tar.gz>.
- Meaning: complete catalogs of Ramsey(4,5,18) graphs with respectively 83,
  84, and 85 edges. Their record counts are 1,089,692, 12,374, and 74.
- SHA-256, in the same order:
  - `0020fa4193adcb985e821ea32a267b0631f1342b0159391640d00304aa066662`
  - `471e92087741febbe0fe8417c8f65230e4fa1012dbefb01f4823f5a333ca6134`
  - `46abaee2572d06bba1e594554809d784be60f8f60b9b0d3345b8bf3dd800810a`

These catalogs support the degree-18 excess/gluing experiments. In
particular, the known exact bound `E(4,5,18)=85` makes the 85-edge file the
complete A-side catalog when a 128-edge 24-vertex H-side has nonpositive
excess contribution.

## r4520.100.g6

- Source: the `r45extreme.tar.gz` archive linked above.
- Meaning: the unique unlabelled Ramsey(4,5,20) graph having 100 edges.
- Size: one graph6 record. This is the complete 100-edge layer, not a sample.
- SHA-256:
  `d1d1ff46bd5d153b51d7da094f6bf459bceaefda65eb4941ead0bb9b09c897cd`.
- Use: together with the two 132-edge records in the complete
  `r45_24.g6` catalog, it defines the top `d=20` excess stratum used by the
  order-45 fixed-pair generator and independent verifier.
- Verify the copied record against the fetched archive with
  `cmp data/reference/r4520.100.g6 build/r45extreme-data/r45extreme/r4520.100.g6`.

## k43_near_miss_1.matrix

- Source:
  [Two K-43 graphs with only two monochromatic K-5's](https://gist.github.com/etherwalker/8d64fa0a1cc1dd508f75bf651aaec873)
- Format: symmetric \(43\times43\) zero-diagonal adjacency matrix.
- Expected property: exactly two monochromatic \(K_5\) subgraphs in the
  two-colouring.
- Verify: PYTHONPATH=src python3 tools/verify_reference.py
