## Meta Agent Guidelines

Read and follow the runtime guide in `.meta-agent/AGENT-RUNTIME.md`.

This is a host project that consumes `meta-agent`. Keep project session records
in `daily-notes/` and stable project knowledge in `doc/`; do not write Ramsey55
records into `meta-agent/meta-log/`.

Only open `meta-agent/doc/methodology.md` when you need extra rationale, examples, or edge-case guidance.

Periodically (e.g., daily or weekly) check if meta-agent has updates:
```bash
git submodule update --remote meta-agent
bash meta-agent/scripts/sync-runtime.sh
```
If there are changes, commit the update.
