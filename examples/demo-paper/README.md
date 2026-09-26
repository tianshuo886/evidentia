# Evidentia Demo Paper Example

This directory demonstrates the canonical artifact layout produced by Evidentia Standard Mode.

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
