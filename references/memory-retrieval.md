# Frozen Research Memory Retrieval Pipeline

Evidentia provides a portable, local-first retrieval architecture without requiring external vector database dependencies.

## Multi-Stage Retrieval Architecture

```text
User / Project Query
        │
        ▼
Structured Filters (memory_type, paper_id, epistemic_state)
        │
        ▼
FTS5 Full-Text Search (SQLite FTS5 virtual table)
        │
        ▼
Candidate Matches
        │
        ▼
Provenance Validation (Verify commit hashes & source evidence IDs)
        │
        ▼
Ranked Provenance-Linked Results
```

## Retrieval Output Contract

Every retrieved item returns complete provenance:
- `memory_id`
- `memory_type`
- `text`
- `paper_id`
- `object_id`
- `source_ids`
- `epistemic_state`
- `paper_model_sha256`
- `source_sha256`
- `retrieval_method`

## Search Interface

```bash
# Query all memory types
evidentia memory search --query "Attention"

# Filter by memory type
evidentia memory search --query "minority subgroup" --type ANOMALY
```
