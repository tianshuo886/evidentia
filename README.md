# Evidentia

[English](README.md) · [中文](README.zh-CN.md)

## Evidence-Grounded Paper Research OS

Evidentia is a single-paper scientific research operating system for turning a supplied research PDF into an auditable, durable, deeply reasoned research object. It reconstructs the paper's multi-modal evidence surface, reads it through 4 Core + 2 Adaptive Specialist Lenses, reconciles findings through an Editorial Revision Memo, structures the narrative with a dynamic paper-specific plan, authors a publication-grade Chinese Academic Reader via a strong model, and renders it through Kami's presentation backend alongside an interactive Evidence Atlas.

The repository contains the reusable agent skill and research harness. It is validated against real-world, peer-reviewed scientific papers.

---

## Why Evidentia Exists

Conventional AI paper reading suffers from fundamental failure modes that make summaries unreliable for research decisions:

- **Evidence Erasure:** Figures and tables are flattened into brief prose; their quantitative backing disappears.
- **Rhetorical Parroting:** Language models follow the author's narrative unquestioningly, missing unstated assumptions, weak controls, and alternative explanations.
- **Template Imposition:** Enforcing rigid IMRaD templates forces theory, metrology, survey, and empirical papers into identical cookie-cutter molds, destroying their unique argumentative logic.
- **Premature Project Bias:** Feeding project goals into the first reading biases the model to see what the researcher wants to see, confirming existing hypotheses rather than faithfully understanding the paper.
- **Epistemic Collapse:** Disagreements, anomalies, and uncertainties are averaged away into smooth but uncalibrated statements.

Evidentia solves these challenges with an architecture founded on three core tenets:

> **Paper decides the story. Evidentia enforces rigor. Kami presents the story.**

---

## Canonical Reader v3 Architecture

```text
paper.pdf
   ↓
Page-First Multimodal Source Reconstruction (Full Text + Rasterized Pages + Clean Crops, bound to source_sha256)
   ↓
Deterministic Source Lock & Semantic Visual Verification (apply_visual_verification.py)
   ↓
Lead Reader Pass (Strong Model: Paper Characterization, Open Argument Topology, Specialist Lens Plan)
   ↓
4 Universal Core + 2 Adaptive Specialist Lenses (Independent Context-Isolated Execution, Zero Crosstalk)
   ↓
Editorial Revision Memo (Structured Revisions: ADD, REWRITE, CORRECT, QUALIFY; Zero Majority Voting)
   ↓
Dynamic Narrative Plan (Custom Section Architecture & Structural Diversity, Strictly Anti-Template)
   ↓
Lead Writer (Strong Model: Publication-Grade Chinese Academic Manuscript conforming to narrative_manuscript schema)
   ↓
Integrity & Anti-Template Validation (Fail-Closed Asset Verification, Citation Grounding, Structure Diversity)
   ↓
Kami Presentation Transformation (Typography, Spacing, Visual Hierarchy, Vector PDF Export)
   ↓
Publication-Grade Paper Reader (HTML + Markdown + Print PDF) & Secondary Evidence Atlas (evidence_atlas.html)
   ↓
PAPER_COMPLETE (Canonical reading stops here)

[Explicit User Intent Only]
   ↓
Contextual Apply (/evidentia-apply) → Project-Specific Reader & Research Delta (apply/<project>/)
   ↓
Optional Frozen Research Memory (/evidentia-memory)
```

---

## Formal Issue #19 Benchmark Validation

Evidentia Reader v3 is frozen and proven on real scientific papers under **GitHub Issue #19**:

- **Frozen Commit:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`
- **Canonical Model:** `antigravity/gemini-3.8-flash [magpie]` (High Reasoning Profile)
- **Primary 6-Paper Corpus:**
  1. `BENCH-01`: *Attention Is All You Need* (Foundational ML Architecture)
  2. `BENCH-02`: *LoRA: Low-Rank Adaptation of Large Language Models* (PEFT / Systems)
  3. `BENCH-03`: *A high-resolution canopy height model of the Earth* (Remote Sensing & Geospatial)
  4. `BENCH-04`: *Highly accurate protein structure prediction with AlphaFold* (Biophysics & Geometric DL)
  5. `BENCH-05`: *Quantum supremacy using a programmable superconducting processor* (Quantum Metrology)
  6. `UNSEEN-01`: *Understanding deep learning requires rethinking generalization* (Mandatory Post-Freeze Unseen Paper)
- **Benchmark Outcome:** **`ISSUE19_RELEASE_GATE = PASS`**
  - **Zero Core Regressions:** 0 losses across 18 core evaluation trials against Direct Gemini.
  - **Unseen Paper Robustness:** Successfully discovered the theorem/falsification logic of UNSEEN-01 without template collapse.
  - **Proven Added Value:** 6/6 Wins on Figure/Table Correctness and 6/6 Wins on Provenance/Auditability.
  - Complete report: [`ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md`](ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md)

---

## Core Principles

1. **Faithful Reading First, Transfer Second:**
   The default intent is always `PAPER_READING`. Project context, application proposals, and codebases are strictly invisible during paper reading. Project transfer is invoked only via explicit `/evidentia-apply`.
2. **Universal Core + Adaptive Specialist Lenses:**
   Every paper receives the 4 Universal Core lenses:
   - **Argument & Narrative:** How the paper constructs its case and links claims to evidence.
   - **Method & Study Design:** Mathematical formulation, algorithm logic, and study architecture.
   - **Evidence & Results:** Quantitative benchmarks, baselines, and ablation margins.
   - **Validity & Boundary:** Underlying assumptions, counterfactual explanations, and epistemic limits.
   Two additional specialist lenses (e.g. Mechanism & Causality, Proof Integrity, Measurement Integrity, Reproducibility) are dynamically selected according to the paper's characterization.
3. **Context Isolation with Cryptographic Proofs:**
   Each lens runs in an isolated input boundary (`provenance/lens/<task_id>`) with its own execution receipt. Sibling lenses cannot see each other's outputs or vote.
4. **Editorial Revision Memo:**
   Replaces lossy voting with an editor who reconciles lens findings into clear directives (Keep, Expand, Correct, Qualify, Boundary Actions) while preserving genuine scientific tensions and anomalies.
5. **Anti-Template Dynamic Narrative Plan:**
   Different papers have fundamentally different argument topologies. The Lead Writer follows a custom section plan designed specifically for the paper.
6. **Kami Presentation-Only Boundary:**
   Kami handles visual styling, typography, page composition, and PDF vector rendering. Kami never invents claims, alters section order, or modifies scientific conclusions.

---

## Quick Start

### 1. Read a Paper

```bash
# Automated canonical reading with active host agent:
python scripts/evidentia.py run --pdf /path/to/paper.pdf --out workspace/

# Run via DOI or arXiv ID (auto-acquisition):
python scripts/evidentia.py run --doi 10.48550/arXiv.2106.09685 --out workspace/
```

### 2. Inspect Progress & Submit Tasks

```bash
# Check current Reader v3 status:
python scripts/evidentia.py status --out workspace/

# Identify next active task packet:
python scripts/evidentia.py next --out workspace/

# Submit agent execution result:
python scripts/evidentia.py submit --out workspace/ --task TASK-V3-LEAD-READING --result result.json
```

### 3. Apply to a Project (Explicit Request Only)

```bash
python scripts/pipeline.py apply --paper workspace/ --project my_project.md
python scripts/validate_delta.py --paper workspace/ --delta workspace/apply/my_project/research_delta.json
```

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
