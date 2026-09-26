# Evidentia Demo Paper Example (Synthetic Fixture / Tier 1)

> **Validation Status:** `SYNTHETIC_VALIDATED` (`SIMULATED_FIXTURE`)  
> For the genuine recorded Host-Agent execution on reconstructed source paper, see [`examples/real-paper-demo/`](../real-paper-demo/).

This directory provides a lightweight deterministic synthetic fixture demonstrating the canonical artifact layout produced by Evidentia. All scientific assertions herein are simulated test fixtures.

## Layout

```text
demo-paper/
├── source/
│   └── paper.pdf
├── model/
│   ├── source_map.json
│   ├── figure_inventory.json
│   ├── open_reading_model.json
│   ├── open_reading_manifest.json
│   ├── lens_reconciliation.json
│   ├── paper_model.json
│   ├── evidence_graph.json
│   └── manifest.json                # FROZEN
├── lens/
│   ├── author.json
│   ├── reviewer.json
│   ├── mechanism.json
│   ├── builder.json
│   ├── anomaly.json
│   └── counterfactual.json
├── reader/
│   ├── reader.html                  # Evidence Atlas
│   └── render_ir.json
└── run_state.json
```

To run and verify this example:

```bash
python scripts/evidentia.py validate --out examples/demo-paper
python scripts/evidentia.py status --out examples/demo-paper
```
