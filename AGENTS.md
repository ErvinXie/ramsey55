# Agent Guidelines

Read and follow the runtime guide in `.meta-agent/AGENT-RUNTIME.md`.

This is a host project that consumes `meta-agent`. Keep project session records in
`daily-notes/` and stable project knowledge in `doc/`; do not write Ramsey55
records into `meta-agent/meta-log/`.

Only open `meta-agent/doc/methodology.md` when extra rationale, examples, or
edge-case guidance is needed.

Periodically check for guideline updates:

```bash
git submodule update --remote meta-agent
bash meta-agent/scripts/sync-runtime.sh
```

Commit the submodule pointer and synchronized runtime guide when they change.
