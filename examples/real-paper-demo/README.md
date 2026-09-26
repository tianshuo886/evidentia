# Evidentia Real Paper Demo (Tier 2 Recorded Replay Validated)

This workspace demonstrates the full autonomous end-to-end scientific lifecycle of Evidentia v1.1 using a genuine reconstructed research paper and recorded Host-Agent execution (`claude-3-7-sonnet` on Pi agent harness).

## Artifact Structure

```text
examples/real-paper-demo/
├── source/
│   └── paper.pdf                     # Source PDF locked by SHA-256
├── model/
│   ├── source_map.json               # Reconstructed dual-track structure & mentions
│   ├── figure_inventory.json         # Reconstructed figure & table items with bounding boxes
│   ├── open_reading_manifest.json    # Snapshotted baseline hash & contract versions
│   ├── open_reading_model.json       # Project-independent baseline paper model
│   ├── candidate_clusters.json       # Layer 1 deterministic pre-clustering
│   ├── lens_reconciliation.json      # Layer 2 semantic cross-lens reconciliation
│   ├── evidence_graph.json           # Deterministic DAG of claims, evidence, and relations
│   ├── paper_model.json              # Canonical synthesized paper model
│   └── manifest.json                 # FROZEN immutable manifest with SHA-256 chain
├── lens/
│   ├── author.json                   # Intended contribution & claims
│   ├── reviewer.json                 # Critical methodology & limitation audit
│   ├── mechanism.json                # Algorithmic & causal mechanism deconstruction
│   ├── builder.json                  # Re-implementation feasibility & hyperparameters
│   ├── anomaly.json                  # Outlier & variance audit
│   └── counterfactual.json           # Component necessity stress-testing
├── tasks/
│   ├── open_reading.json             # Schema-validated AgentTask
│   ├── reconciliation.json           # Reconciliation AgentTask
│   └── lens/*.json                   # Six independent Lens AgentTasks
├── agent_runs/                       # Immutable record of Host-Agent result envelopes
├── reader/
│   ├── reader.html                   # Interactive 3-depth Evidence Atlas
│   └── render_ir.json                # Reader intermediate representation
└── run_state.json                    # Full phase advancement history & artifact hashes
```

## Validation

Validate this workspace at any time:

```bash
python scripts/evidentia.py validate --out examples/real-paper-demo
python scripts/phase.py --status --out examples/real-paper-demo
python scripts/freeze_check.py --out examples/real-paper-demo
python scripts/reader_audit.py --out examples/real-paper-demo
```
