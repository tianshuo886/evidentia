---
name: evidentia
description: Evidence-grounded Paper Research OS for one paper at a time. Build a source-reconstructed Paper Model and Evidence Graph, perform 4 Core + 2 Adaptive Specialist Lens rereads, reconcile via Editorial Revision Memo, generate a dynamic paper-specific narrative plan, author a publication-grade Chinese Academic Reader via strong-model Lead Writer, and render a presentation-only Kami Reader with interactive Evidence Atlas. Optionally produce a provenance-linked Research Delta for a project upon explicit user request. Use when the user asks to deeply read, audit, transfer, or build research memory from a supplied paper PDF. Not for paper search, triage, or multi-paper surveys.
license: Apache-2.0
compatibility: Python 3.9+, PyMuPDF, JSON Schema, and Evidentia source-reconstruction dependencies.
metadata:
  version: "1.2.0"
  argument-hint: "<paper.pdf | DOI | arXiv-ID> [--out <directory>] [--supplement ...] | apply --paper <directory> --project <document> [--focus ...] | memory ..."
---

# Evidentia · Evidence-Grounded Paper Research OS

Evidentia turns one supplied research paper into a durable, deeply reasoned, auditable research object:

```text
PDF Source Acquisition & Reconstruction (Full Text + Page-first Multimodal Localization)
  → Deterministic Source Lock & Evidence Verification
  → Lead Reader (Strong Model: Paper Characterization, Open Argument Topology, Specialist Lens Plan)
  → 4 Core + 2 Adaptive Specialist Lenses (Independent Context-Isolated Rereads, No Sibling Crosstalk)
  → Scientific Revision Memo (Editorial Reconciliation: Keep, Expand, Correct, Qualify, Boundary Actions)
  → Dynamic Narrative Plan (Paper-Specific Structural Architecture, Anti-Template Topology)
  → Lead Writer (Strong Model: Chinese Academic Narrative Manuscript, schemas/narrative_manuscript.json)
  → Integrity & Anti-Template Validation (Fail-closed citation, visual asset binding, structure diversity)
  → Presentation Transformation (Kami HTML / Vector PDF & Evidence Atlas)
  → Human-Quality Release Gate / PAPER_COMPLETE (STOP)

[Explicit User Request Only]
→ Contextual Apply (/evidentia-apply) → Separate Project Reader (apply/<project>/)
→ Optional Frozen Research Memory (/evidentia-memory)
```

## Primary Invariant

> **Paper decides the story. Evidentia enforces rigor. Kami presents the story.**

- **The Paper Decides:** Section titles, section count, and narrative flow follow the paper's intrinsic intellectual case (e.g. theorem-proof, empirical-benchmark, remote sensing inversion, quantum metrology), not a rigid IMRaD template.
- **Evidentia Enforces Rigor:** Context isolation, cryptographic SHA-256 evidence chain, fail-closed visual asset binding, and editorial tension preservation without majority voting.
- **Kami Presents the Story:** Presentation-only backend responsible for typography, layout hierarchy, page composition, and PDF vector export. Kami never invents, alters, or suppresses scientific content.

## Entries

```bash
/evidentia <paper.pdf | DOI | arXiv-ID> [--out <directory>] [--supplement <supp.pdf>]
/evidentia-workspace --workspace <directory> [open-reader|ask|open-evidence|open-source|note|propose-correction|apply]
/evidentia-apply --paper <paper-output-dir> --project <project-document> [--focus <section>]
/evidentia-memory [commit-paper|commit-project|relation|inspect|snapshot|export|import]
```

Supports local PDF files, DOIs (e.g. `10.1038/...`), arXiv IDs (e.g. `1706.03762`), and direct paper URLs. Automatically acquires paper metadata, overview markdown, and open-access source PDF via `pa` (Paper Acquire), CrossRef, and Unpaywall. If `--out` is omitted, a local PDF is processed in a dedicated workspace beside the source paper.

## Execution Boundary & Model Policy

- **Canonical Scientific Model:** The approved strong scientific reasoning model (`antigravity/gemini-3.8-flash [magpie]` with High Reasoning Profile).
- **Default Execution:** A single strong model executing isolated specialist tasks. Lens diversity stems from distinct scientific questions and strictly isolated input boundaries, not from ad-hoc multi-provider routing.
- **Paper Reading Default:** Paper reading terminates at `PAPER_COMPLETE` once the frozen paper understanding, Chinese-first Academic Reader (`paper_reader.html`, `paper_reader.md`, `paper_reader.pdf`), Evidence Atlas (`evidence_atlas.html`), and visual QA pass.
- **Project Apply Isolation:** Project Apply runs **only upon explicit user intent** and writes exclusively to `apply/<project>/`. The Paper Reader is immutable and project-free.

## Workspace Structure (Canonical Reader v3)

```text
<out>/
├── source/paper.pdf [+ supplements] # authentic source PDF (bound to source_sha256)
├── source_pages/                    # full-page rasterizations (page-001.png, ...)
├── tasks/v3/                        # schema-valid AgentTask packets
│   ├── lead_reading.json
│   ├── visual/                      # page-first multimodal localization tasks
│   ├── lens/                        # 4 Core + 2 Adaptive specialist lens tasks
│   ├── revision_memo.json
│   ├── narrative_plan.json
│   └── lead_writing.json
├── agent_runs/                      # immutable execution receipts & AgentResultEnvelopes
├── provenance/lens/                 # isolated input snapshots per lens (zero crosstalk)
├── assets/figures/                  # verified page-localized crops (bound to figure_inventory)
├── model/
│   ├── source_map.json              # text structure, page rects, equations
│   ├── figure_inventory.json        # semantic visual inventory & binding status
│   ├── equation_inventory.json      # extracted LaTeX formulas & display modes
│   ├── paper_understanding_draft.json # Lead Reader draft & open argument topology
│   ├── lens_v3_manifest.json        # selected 4 Core + 2 Adaptive lenses
│   ├── revision_memo.json           # editorial reconciliation & revision directives
│   ├── narrative_plan.json          # dynamic section architecture (anti-template)
│   └── manifest.json                # immutable freeze record & SHA hashes
├── lens_v3/                         # isolated specialist findings
│   ├── argument_narrative.json      # Core: narrative progression & claim structure
│   ├── method_study_design.json     # Core: algorithmic / experimental design
│   ├── evidence_results.json        # Core: quantitative data & ablation scrutiny
│   ├── validity_boundary.json       # Core: assumptions, failure modes, epistemic limits
│   └── <specialist_1,2>.json        # Adaptive: e.g. mechanism, proof, reproducibility
├── reader/                          # publication-grade Chinese Academic Reader
│   ├── narrative_manuscript.json    # Lead Writer primary narrative manuscript
│   ├── frozen_paper_object.json     # canonical Versioned Frozen Paper Object (FPO)
│   ├── paper_reader.html            # interactive Kami editorial reader (and reader.html)
│   ├── paper_reader.md              # complete Markdown deep-reading report (and reader.md)
│   ├── paper_reader.pdf             # vector PDF print snapshot (and reader.pdf)
│   ├── evidence_atlas.html          # secondary audit & provenance surface
│   └── kami_audit.json              # presentation-only visual QA audit
├── notes/                           # private user notes (isolated from scientific core)
├── corrections/                     # non-mutating correction proposals & version records
└── apply/<project>/                 # created ONLY after explicit Apply request
    ├── project_context.json
    ├── research_delta.json
    └── project_reader.html
```

## Non-Negotiable Rules

1. **Source before interpretation.** Reconstruct pages, sections, captions, figures, tables, equations, experiments and in-text mentions before generating claims.
2. **Paper reading is default; project isolation is absolute.** Default run executes `PAPER_READING` intent and terminates at `PAPER_COMPLETE`. Project documents, codebase context, and research memory are strictly forbidden during paper reading. Zero `apply/` artifacts created by default.
3. **Natural structure and argument topology.** The Lead Reader recovers the paper's own argument topology (`model/paper_understanding_draft.json`) before drafting. Author Argument is explicitly distinguished from Assessed Argument.
4. **4 Core + 2 Adaptive Specialist Lenses.** All papers receive the 4 Core lenses (Argument & Narrative, Method & Study Design, Evidence & Results, Validity & Boundary). Two adaptive lenses are selected dynamically (Mechanism & Causality, Reproducibility & Implementation, Proof Integrity, Assumption Sensitivity, Measurement Integrity, Statistical & Causal Inference, Taxonomy & Coverage).
5. **Context-isolated execution with proofs.** Each lens executes against a self-hashed isolated input boundary (`provenance/lens/<task_id>`). Sibling lenses never share output or vote.
6. **Editorial Revision Memo without majority voting.** An editor reconciles specialist rereads into structured revisions (`revisions[]`), preserving genuine tensions, anomalies, and unresolved issues.
7. **Dynamic Narrative Plan (Anti-Template).** Section titles, counts, and logic are custom-designed for each paper. Imposing a fixed IMRaD template is prohibited.
8. **Strong-model Lead Writer.** The publication-grade Chinese academic manuscript (`reader/narrative_manuscript.json`) is authored by the strong model, not deterministic composition rules.
9. **Kami presentation-only boundary.** Kami styles typography, layout, and PDF vectors. Kami never synthesizes claims, reorders sections, alters headings, or drops evidence.
10. **Evidence Atlas is secondary.** The primary Reader stands alone for fluent human comprehension. The Evidence Atlas serves as an audit surface linked from quiet anchors.
11. **Apply is explicit-request-only.** Contextual project transfer runs only upon explicit user request and operates on the frozen Paper Object without mutating original understanding.
12. **Uncertainty is first-class data.** NOT_STATED, AMBIGUOUS, INSUFFICIENT_EVIDENCE, MODEL_UNCERTAIN and UNRESOLVED remain visible and un-collapsed.

## Core Workflows

### 1. Canonical Paper Reading

```bash
# Automated end-to-end reading with active host agent:
python scripts/evidentia.py run --pdf paper.pdf --out workspace/

# Inspect step-by-step state:
python scripts/evidentia.py status --out workspace/
python scripts/evidentia.py next --out workspace/

# Submit agent task results through the trust boundary:
python scripts/evidentia.py submit --out workspace/ --task TASK-V3-LEAD-READING --result envelope.json
```

### 2. Contextual Project Apply (Explicit User Request)

```bash
python scripts/pipeline.py apply --paper workspace/ --project my_project.md
python scripts/validate_delta.py --paper workspace/ --delta workspace/apply/my_project/research_delta.json
```

### 3. Frozen Research Memory (Cross-Paper Intelligence)

```bash
python scripts/evidentia.py memory commit-paper --paper workspace/
python scripts/evidentia.py memory search --query "attention mechanism sparsity"
```
