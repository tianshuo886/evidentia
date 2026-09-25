# paper-read · Paper Research OS v1

A single-paper research workflow that turns a PDF into a source-grounded, frozen Paper Model, Evidence Graph, independent Multi-Lens rereads, and a unified Paper/Project Reader.

## Commands

```bash
/paper-read <paper.pdf> --out <directory> [--supplement <supp.pdf>]
/paper-apply --paper <directory> --project <project-doc> [--focus <section>]
```

The executable pieces can be run directly:

```bash
python scripts/extract_figs.py --pdf paper.pdf --out out/assets/figures --inventory out/model/figure_inventory.json
python scripts/extract_structure.py --pdf paper.pdf --out out/model/source_map.json
python scripts/freeze_check.py --out out
python scripts/verify_frozen.py --out out
python scripts/render_reader.py --out out
```

The freeze gate requires JSON Schema-valid data, explicit Figure/Table inspection, real critical assets, a complete Evidence Graph, six independent Lens files, unresolved/coverage declarations, and reproducible SHA-256 hashes. `paper_model.json` is canonical; the Reader is a presentation adapter. Project Delta is stored separately and must reference the frozen model.

Run `pytest -q` for failure-oriented regression tests.
