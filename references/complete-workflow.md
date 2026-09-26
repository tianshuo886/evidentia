# Complete Paper Research OS workflow

The skill is a state machine, not a single summarization prompt:

```text
source-only INGEST
  → SOURCE_RECONSTRUCTION (source_map + figure_inventory, both bound to SOURCE_SHA256)
  → SOURCE LOCK (freeze_check SHA chain: actual source/paper.pdf == all references)
  → OPEN_READING draft (model/paper_model.json, project invisible)
  → BASELINE LOCK (snapshot_baseline.py → model/open_reading_model.json + open_reading_manifest.json)
  → six independent LENS task packets (lens_runner.py binds source_sha256/base_sha256/contract+prompt versions)
  → merge with provenance (merge_lenses.py → model/lens_reconciliation.json; supporting_lenses preserved, conflicts recorded)
  → FINAL MODEL + evidence_graph (build_graph.py binds source_sha256)
  → FREEZE + hash verification (freeze_check.py fail-closed; verify_frozen.py)
  → PAPER READER render + content/visual audit
  → optional PROJECT APPLY contextual reread
  → Research Delta + Gap Map + transfer/experiment decisions
  → optional cross-paper index
```

`pipeline.py`, `init_run.py`, `phase.py`, and `init_apply.py` make the boundary explicit. The scripts never invent paper facts or pretend to have run an LLM pass: each generated artifact is a required, schema-validated input. This preserves the distinction between an execution contract and the model that performs the reading.

Open Reading can see only `working/paper.pdf`, supplied supplements, source reconstruction and skill resources. Apply begins only after `verify_frozen.py` succeeds and copies one project document into a separate apply directory. Frozen Paper Model files are read-only during apply.
