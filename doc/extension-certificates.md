# One-vertex extension certificates

Updated: 2026-08-11

## Result

Every one of the 328 public \(R(5,5,42)\) representatives, and therefore each
of their 328 colour complements, has a Lean-kernel-checked proof that no choice
of the 42 new edge colours can attach a 43rd vertex without creating a
monochromatic \(K_5\).

A second, stronger certificate family proves that every attachment creates at
least **two distinct** monochromatic \(K_5\)s. Its aggregate theorem is

    Ramsey55.reference42TwoViolationCatalogWithComplements_all_atLeastTwo

and its axiom audit again reports only `propext` and `Quot.sound`.

The aggregate theorem is

    Ramsey55.reference42CatalogWithComplements_all_noExtension

and the catalog length theorem checks that it contains 656 entries. Its axiom
audit reports only Lean's standard `propext` and `Quot.sound`; it contains no
`sorryAx` and no axiom introduced by native execution.

Neither statement is a proof that \(R(5,5)=43\). The 656 graphs have never
been proved to be a complete classification of the Ramsey-free graphs on 42
vertices.
The certificates close the extension question for every public candidate and
isolate catalog completeness as the remaining mathematical gap in this
particular route.

## Certificate format

Fix a base graph \(G\) on 42 old vertices. An attachment is a 42-bit string;
bit \(v\) is the colour of the edge from a new apex to old vertex \(v\).

For every monochromatic \(K_4\) of colour \(c\) in \(G\), an attachment must
give at least one of those four vertices the opposite apex colour. Otherwise
the four old vertices and the apex form a monochromatic \(K_5\). Thus the
extension question is a small Boolean constraint problem whose clauses all
have width four.

The certificate is a complete binary decision tree:

- a branch chooses one apex bit and checks both values;
- a leaf names four increasing old vertices and a colour;
- the checker verifies that those vertices form a monochromatic \(K_4\) in
  the base graph and that the current branch path fixed all four apex bits to
  the same colour.

Every root-to-leaf assignment is therefore blocked. The generic soundness
theorem

    Ramsey55.checkExtensionCover_sound

proves that any tree accepted by the Boolean checker rules out all
attachments. Its proof is independent of the certificate generator.

For the stronger `ExtensionCover2`, every leaf contains two checked witnesses
with different old four-vertex sets. The theorem
`checkExtensionCover2_sound` turns a successful Boolean check into the
quantified assertion that every attachment produces two different
monochromatic five-sets through the apex.

## Artifact census

The deterministic compressed artifact is
`data/reference/r55_42_extension_covers.json.gz`:

| quantity | value |
|---|---:|
| representative graphs | 328 |
| complements covered by colour duality | 328 |
| branch nodes | 47,387 |
| leaf nodes | 47,715 |
| total nodes | 95,102 |
| largest tree | 429 nodes |
| compressed size | 395,847 bytes |
| SHA-256 | `2a6fc3f56195ca962a14c2e15c56278043b222a2a8d568dad3024f6ab09a0e64` |

On the project machine, generation plus an independent Python reread and
verification took about 18 seconds. The generated Lean declarations are split
into 21 batches to control elaboration memory. A clean certificate build took
about 13 seconds on a 10-core Apple Silicon machine; an incremental full build
takes about one second.

The two-violation artifact is
`data/reference/r55_42_extension_two_covers.json.gz`:

| quantity | value |
|---|---:|
| representative graphs | 328 |
| complements covered by colour duality | 328 |
| branch nodes | 145,196 |
| leaf nodes | 145,524 |
| largest tree | 1,133 nodes |
| compressed size | 1,677,909 bytes |
| SHA-256 | `f15a2f01d5eff68c4ddba713a0bfe92cfd3ce103140ced186fbc7bab9a4a6609` |

The generated Lean data occupy about 8 MB in 41 batches. A clean parallel
build took 52 wall-clock seconds, 421 CPU seconds, and about 1.38 GB maximum
resident memory on the project machine.

This lower bound is attained within the catalog. Deleting vertex 0 from the
public 43-vertex two-violation near miss gives a graph isomorphic to public
representative 255. An explicit 42-vertex permutation in the Python tests
checks the isomorphism, and the deleted vertex's attachment recreates exactly
the two published violations. Thus “at least two” is sharp for at least one
catalog member; it is not merely an artifact of a loose checker.

## Reproduction

Run:

    PYTHONPATH=src python3 tools/generate_extension_certificates.py
    PYTHONPATH=src python3 tools/generate_lean_extension_certificates.py
    PYTHONPATH=src python3 \
      tools/generate_extension_multiplicity_certificates.py
    PYTHONPATH=src python3 \
      tools/generate_lean_extension_multiplicity_certificates.py
    ELAN_HOME=/tmp/ramsey55-elan \
      PATH=/tmp/ramsey55-elan/bin:$PATH \
      lake build

The two certificate-generation commands write gzip files with fixed
timestamps, reread them, and verify every serialized tree without invoking
the search procedure. The two source generators emit Lean batches. The final
command checks the graph data, all branches and leaves, both complement
arguments, and both 656-entry aggregate theorems.

The core implementation is divided as follows:

- `src/ramsey55/extension.py`: generator, independent checker, and colour
  complement transformation;
- `formal/Ramsey55/Extension.lean`: definitions and generic soundness proof;
- `formal/Ramsey55/ExtensionCertificates/`: generated graph/tree data and
  per-graph checked theorems;
- `formal/Ramsey55/ExtensionMultiplicityCertificates/`: generated stronger
  two-violation trees;
- `formal/Ramsey55/Reduction.lean`: proof that nonextendability of every
  Ramsey-free 42-vertex colouring implies the 43-vertex upper bound.

## Exact remaining obligation

Lean now checks the general reduction

    Ramsey55.forcesMonochromatic5_43_of_all_42_nonextendable

and combines it with the formal lower bound in

    Ramsey55.ramsey55_is_43_of_all_42_nonextendable.

The hypothesis still required by the latter theorem says, literally, that
every simple Ramsey-free colouring on 42 vertices has no Ramsey-free
one-vertex extension. To discharge it using the public catalog would require:

1. a complete classification proof for all 42-vertex Ramsey graphs;
2. a checked bridge from classification up to relabeling and colour swap to
   the labelled certificate statements;
3. an audit tying every classified orbit to one of the embedded records.

No current publication supplies item 1, so none of these is silently assumed
in the formal development.
