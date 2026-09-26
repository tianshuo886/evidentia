# Frozen Research Memory Architecture

Frozen Research Memory is Evidentia's explicit, inspectable, long-term cross-paper memory system.

## Storage Layout

```text
<EVIDENTIA_MEMORY_ROOT>/
├── memory.sqlite           # Rebuildable index + FTS5 full-text search
├── objects/                # Immutable canonical JSON objects
│   ├── paper_commits/     # Commits from frozen paper models
│   ├── project_commits/   # Commits from validated research deltas
│   ├── relations/         # Evidence-grounded cross-paper relations
│   └── outcomes/          # Experiment results & decision traces
├── snapshots/              # Periodic memory snapshots
├── exports/                # Exported portable memory archives
└── memory_manifest.json    # Top-level memory audit trail
```

## Immutable Objects vs Rebuildable Index

Canonical truth resides in immutable JSON objects under `objects/`.
`memory.sqlite` is an ephemeral index:
\[
\text{Database corruption} \neq \text{Knowledge loss}
\]
The index can be completely recreated from disk objects at any time:
```bash
evidentia memory rebuild-index
```

## Commit Gates

- **Paper Commit**: Requires `verify_frozen.py` to pass with `FROZEN` status. Unfrozen paper models are rejected.
- **Project Commit**: Requires `validate_delta.py` to pass with valid provenance.
- **Outcome Commit**: Records real experiment outcomes (`SUCCESS`, `FAILURE`, `PARTIAL_SUCCESS`, `INCONCLUSIVE`).
