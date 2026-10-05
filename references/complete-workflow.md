# Canonical Evidentia Reader v3 Workflow

The skill is an evidence-grounded research operating system that turns a supplied paper PDF into a durable, deeply reasoned, auditable research object:

```text
source-only INGEST
  → SOURCE_RECONSTRUCTION (page-first: source_pages/ + source_map + figure_inventory + equation_inventory, bound to source_sha256)
  → SOURCE LOCK (freeze_check SHA chain: actual source/paper.pdf == all references)
  → MULTIMODAL VISUAL LOCALIZATION (semantic full-page inspection, collision-free crops)
  → LEAD READER PASS (model/paper_understanding_draft.json, open argument topology, specialist lens selection)
  → 4 UNIVERSAL CORE + 2 ADAPTIVE SPECIALIST LENSES (isolated execution snapshots under provenance/lens/<task_id>, zero crosstalk)
  → EDITORIAL REVISION MEMO (model/revision_memo.json; structured Keep/Expand/Correct/Qualify/Verify directives without majority voting)
  → DYNAMIC NARRATIVE PLAN (model/narrative_plan.json; paper-specific anti-template section architecture)
  → STRONG-MODEL LEAD WRITER (reader/narrative_manuscript.json; publication-grade Chinese academic manuscript)
  → INTEGRITY & ANTI-TEMPLATE VALIDATION (fail-closed check on evidence refs, assets, and structural diversity)
  → KAMI PRESENTATION TRANSFORMATION (render_paper_reader.py; typography, layout, responsive HTML, and vector PDF export)
  → SECONDARY EVIDENCE ATLAS (render_evidence_atlas_v3.py; claim-to-evidence inspection graph)
  → PAPER_COMPLETE (Canonical reading stops here)

Explicit user request only:
  → CONTEXTUAL PROJECT APPLY (/evidentia-apply)
  → separate apply/<project>/project_reader.html + research_delta.json
  → optional cross-paper memory index (/evidentia-memory)
```

## Primary Axiom

> **Paper decides the story. Evidentia enforces rigor. Kami presents the story.**

The scripts never invent paper facts or pretend to have run an LLM pass: each generated artifact is a required, schema-validated input with cryptographic execution receipts. This preserves the distinction between an execution contract and the model that performs the reading.

Paper reading is strictly project-independent. Project Apply begins only upon explicit user request and operates on the frozen Paper Object without mutating original understanding.
