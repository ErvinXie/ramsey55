# Degree-8 R(4,5,25) gluing certificate checkpoint

This directory retains the complete 54-formula input family and the compact
manifests for the degree-8 gluing computation.  Every formula has a checked
DRAT refutation, but the 510,872,280 proof bytes are not committed to Git.
They remain on `sglang-arm-builder` under
`/root/ramsey55/build/r45-gluing-d08-v1/proofs-v1/`; every proof and log is
bound by `proof-manifest.json`.

This is a conditional gluing result, not yet a standalone proof that the
direct degree-8 fixed-star CNF is UNSAT.  The local cover audit proves that
every valid completion of each listed generalized graph is represented up to
isomorphism.  Global exhaustiveness of the 179 `R(3,5;8)` and two
`R(4,4;16)` isomorphism classes still depends on the separately checked graph
enumeration/HOL4 layer.

## Fixed evidence

- upstream source: `barakeel/ramsey` commit
  `065c07054483e3132f12909103e6d0e35e912c28`;
- published `gen.tar.gz` SHA-256:
  `2b3865c813f1568b757b242c62130716f374d6c687c68b798c7b300f34755f30`;
- `covers/gen358` SHA-256:
  `e785c585979cb058460ecbc0dbb8fee2167f390600dec3bdbb4fbc89e9cddfc8`;
- `covers/gen4416` SHA-256:
  `d342d951433311239ba7ab5c0eef809a7588b41c0e8a472e8930bd77d5489c6c`;
- `branch-manifest.json` SHA-256:
  `868fbdcc094e14840c9589480cd134b6ae3a08fd2a8933e73bb09b98ef60e60b`;
- `proof-manifest.json` SHA-256:
  `dd3bb57079f53d5e153c1a6146174364716ea2e7b57d66b05f2a99c4ca23858f`;
- `independent-proof-audit.json` SHA-256:
  `8e070a197e5c2676f2b2c2e0e3ffe6382a35481cde83c5c4d7db713a5c26847d`;
- `gen358-local-cover-audit.json` SHA-256:
  `0d0eadb8f72ef643fe583438368bf0d36479169b3d7d57e2eb9644ce9fe15aab`;
- `gen4416-local-cover-audit.json` SHA-256:
  `c1e17267e8693115a547171521f575355a34e866d12136fe36e4e5266b69c7dd`.

The producer used CaDiCaL SHA-256
`c42ba87b1af1c11b564aa6754a4c55911c7c99834a69eb3d802b938dcefc587c`.
Both replay passes used `drat-trim` SHA-256
`8de9a77e5ddf754f10cce7980a7495810ce9f4328c2df4e55419970ae1858d42`.

## Recheck

The committed cover inputs and all 54 CNFs can be reconstructed without the
proof files:

```bash
python3 tools/verify_generalized_graph_cover.py \
  data/certificates/r45-gluing-d08/covers/gen358 \
  --order 8 --blue-clique 3 --red-clique 5 \
  --output build/gen358-local-audit.json
python3 tools/verify_generalized_graph_cover.py \
  data/certificates/r45-gluing-d08/covers/gen4416 \
  --order 16 --blue-clique 4 --red-clique 4 \
  --output build/gen4416-local-audit.json
python3 tools/verify_r45_gluing_branches.py \
  data/certificates/r45-gluing-d08/branch-manifest.json \
  --cover-dir data/certificates/r45-gluing-d08/covers \
  --cnf-dir data/certificates/r45-gluing-d08/cnf
```

After copying the proof directory from the ARM host, replay every certificate
and emit a fresh audit:

```bash
python3 tools/audit_r45_gluing_proofs.py \
  data/certificates/r45-gluing-d08/proof-manifest.json \
  data/certificates/r45-gluing-d08/branch-manifest.json \
  build/r45-gluing-d08-proofs \
  --cnf-dir data/certificates/r45-gluing-d08/cnf \
  --checker .tools/src/drat-trim/drat-trim \
  --audit-dir build/r45-gluing-d08-audit-logs \
  --output build/r45-gluing-d08-independent-audit.json --jobs 12
```
