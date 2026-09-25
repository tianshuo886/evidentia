# Complete Paper Research OS workflow

The skill is a state machine, not a single summarization prompt:

```text
source-only INGEST
  → SOURCE_RECONSTRUCTION
  → OPEN_READING (project invisible)
  → six independent LENS task packets
  → merge/dedup with provenance
  → FREEZE + hash verification
  → PAPER READER render + content/visual audit
  → optional PROJECT APPLY contextual reread
  → Research Delta + Gap Map + transfer/experiment decisions
  → optional cross-paper index
```

`pipeline.py`, `init_run.py`, `phase.py`, and `init_apply.py` make the boundary explicit. The scripts never invent paper facts or pretend to have run an LLM pass: each generated artifact is a required, schema-validated input. This preserves the distinction between an execution contract and the model that performs the reading.

Open Reading can see only `working/paper.pdf`, supplied supplements, source reconstruction and skill resources. Apply begins only after `verify_frozen.py` succeeds and copies one project document into a separate apply directory. Frozen Paper Model files are read-only during apply.
