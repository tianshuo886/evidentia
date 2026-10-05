# Wave 1 Reader v3 Architecture Freeze Audit Report

**Date:** 2026-10-05T21:15:00Z  
**Repository:** `tianshuo886/evidentia`  
**Canonical Branch:** `reader-reset-v3`  
**Candidate Freeze Commit SHA:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`  
**Issue #22 Status:** CLOSED  
**PR #26 Status:** MERGED  
**Canonical Model Policy:** `antigravity/gemini-3.8-flash [magpie]`  

---

## 1. Executive Freeze Decision

### **`ARCHITECTURE_FROZEN = YES`**
### **`READER_V3_FREEZE_SHA = 4139ca7b0b1ae72c0930801df5e50653b59a7e92`**

All architectural, provenance, visual-trust, rendering, structural-diversity, and deterministic test gates have passed without exception. The Evidentia Reader v3 scientific architecture is officially frozen for Wave 1. All subsequent benchmark evaluations under formal Issue #19 must be conducted against this frozen codebase commit.

---

## 2. Canonical Repository & Ancestry State

- **Active Checkout:** `/Users/shentianshuo/.agents/skills/evidentia`
- **Active Branch:** `reader-reset-v3` (tracking `origin/reader-reset-v3`)
- **HEAD Commit:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92` (`Merge pull request #26 from tianshuo886/reader-v3-antitemplate`)
- **Ancestry Verification:** Confirms candidate SHA `c2039ff687aa1034706e2a42299c4ec8024d47d5` and its visual/provenance repair predecessors (`355e31c`, `f4b378d`, `ee9ec8d`) are direct ancestors of HEAD.
- **Repository Cleanliness:** No unstaged diff or uncommitted modifications on tracked files. Evidence artifacts are cleanly persisted in immutable manifest records.

---

## 3. Scientific Architecture Verification

The active Reader v3 execution path conforms strictly to the frozen strong-model contract:
```text
Source Acquisition & Reconstruction
  → Multimodal Evidence Verification (extract_figs.py / source_map.json)
  → Open-Form Lead Reader (schemas/paper_argument_topology.schema.json)
  → 4 Core + 2 Adaptive Specialist Lenses (context-isolated execution boundary)
  → Editorial Council Revision Memo (schemas/revision_memo.schema.json)
  → Dynamic Narrative Plan (schemas/narrative_plan.schema.json)
  → Strong-Model Lead Writer (schemas/narrative_manuscript.schema.json v3.0)
  → Source-Grounded Integrity & Anti-Template Validation
  → Unified Paper Reader (HTML/MD/PDF) & Evidence Atlas v3
```

- **No Template Slots:** Universal `problem → gap → method → results → limitations` fixed chapter slots are eradicated. The paper's native argument topology determines the narrative flow.
- **Dynamic Narrative Plan:** Lead Writer strictly follows the dynamic section sequence defined in `model/narrative_plan.json`.
- **Downstream-Only Legacy Compatibility:** Legacy `paper_reader_ir.json` and fixed story-spine mappings are relegated to downstream compatibility projections only; they cannot dictate upstream scientific reading.
- **Strict Context Boundary:** `apply/`, `project/`, and `memory/project/` are explicitly listed in `forbidden_inputs` and validated by gateway checks, ensuring zero Project Apply or Research Memory contamination during Honest Reading.

---

## 4. Lens Execution & Provenance Trust Gate

### **`LENS_PROVENANCE_GATE = PASS`**

The runtime execution boundary (implemented in `scripts/lens_execution_manifest.py` and `scripts/agent_submit.py`) enforces strict, machine-checked physical isolation rather than prompt-level assertions:
- **Mandatory Manifest Fields:** Every Lens execution requires `source_sha256`, `base_sha256`, `contract_version`, `prompt_version`, `task_sha256`, `code_sha`, `material_inputs`, and `manifest_sha256`.
- **Single-Use Core Dispatches:** Dispatches are cryptographically bound to nonces, tasks, code hashes, and input manifests, and invalidated upon receipt submission.
- **Boundary Verification:** Filesystem snapshot roots are audited to confirm:
  1. `forbidden_paths_present == []`
  2. `sibling_lens_outputs_present == False`
  3. No post-hoc or aggregate cross-lens generation.
- **Automated Regression Suite:** `tests/test_lens_execution_manifest.py` (**9/9 PASSED**) verifies detection of:
  - Sibling Lens contamination rejection (`test_manifest_rejects_sibling_lens_context`);
  - Material input drift rejection (`test_manifest_rejects_input_drift`);
  - Manifest self-hash tampering rejection (`test_manifest_rejects_self_hash_mismatch`);
  - Receipt, envelope, and promoted output tampering rejection.

---

## 5. Visual Reconstruction & Evidence Trust Gate

### **`VISUAL_EVIDENCE_GATE = PASS`**

- **Generic Extraction Hardening (`extract_figs.py`):**
  - Pure white vector background rectangles (`fill=(1.0, 1.0, 1.0)` with no stroke) and out-of-bounds drawing rectangles are ignored, preventing diagram fragmentation.
  - Tables are explicitly forbidden from binding to vector drawing candidates (`kind == 'table' and xref is None`), preventing nearby table/figure collisions.
- **Fail-Closed Ambiguity Resolution (`render_paper_reader.py`):**
  - Two-pass asset resolution: collects candidate claims across all blocks; if an asset is claimed by multiple distinct evidence IDs, it is flagged as ambiguous and fails closed without order-dependent first-wins rebinding.
- **LoRA Defect Resolution:** Generic mechanisms prevent the historical `F02`/`T04` collisions and incomplete `F01` crops across all papers.
- **Automated Regression Suite:** `tests/test_visual_reconstruction.py` (**5/5 PASSED**) verifies:
  - Vector background mask filtering and non-premature geometry verification;
  - Nearby table and chart collision prevention;
  - Uncertain visual assets fail-closed handling without full-page asset fallback.

---

## 6. Kami & Reader Rendering Warning Classification Policy

### **`KAMI_BLOCKING_DEFECTS = 0`**

A formal release classification policy is established for Reader rendering diagnostics:

| Classification | Definition | Examples | Release Action |
|---|---|---|---|
| **`BLOCKING`** | Scientific corruption, illegibility, asset collision, or broken layout that conceals meaning | Missing fonts/glyphs causing unreadable text; broken LaTeX formula rendering; clipped figure/table crop; missing bound visual asset; table/figure collision; overlapping text blocks | **Blocks release; halts pipeline** |
| **`NON_BLOCKING`** | Cosmetic or layout adaptations that preserve full scientific meaning | Sparse trailing final page; intentionally image-heavy page layout; whitespace caused by protective page-breaks before large figures/tables; cosmetic density variance | **Logged; release permitted** |
| **`HUMAN_REVIEW_REQUIRED`** | Layout anomalies that cannot be mechanically verified but have no obvious defect | Unusually tall equation blocks; custom tabular wrapping; edge-of-margin callouts | **Flags reviewer attention in release report** |

- **Audit of Existing Three Readers:**
  - `BENCH-02-LORA-ADAPTATION`: 11 pages rendered, all visual assets bound, 0 blocking defects.
  - `BENCH-04-ALPHAFOLD2-STRUCTURE`: 9 pages rendered, clean typography, 0 blocking defects.
  - `BENCH-05-QUANTUM-SUPREMACY-ABLATION`: 12 pages rendered, full substitution chain displayed, 0 blocking defects.
- **Blocking Defect Count:** **0**.

---

## 7. Canonical Scientific Model Policy

### **`MODEL_POLICY = FROZEN`**

- **Canonical Model:** `antigravity/gemini-3.8-flash [magpie]`
- **Authority:** Approved by system owner as the primary model for scientific comprehension, specialist Lens analysis, revision synthesis, and Lead Writer manuscript drafting.
- **Architectural Neutrality:** Model identity is preserved in runtime provenance and executor metadata (`executor.provider`, `executor.model`) rather than hard-coded into JSON Schemas or scientific task contracts.
- **Validation Continuity:** Existing artifacts produced by Gemini are fully valid and preserved.

---

## 8. Issue #19 Benchmark Readiness

### **`ISSUE19_INFRASTRUCTURE_READY = YES`**

The benchmark framework is verified and ready for formal execution:
- **Condition A (Direct Strong-Model Read):** Task generator `scripts/reader_v3_benchmark.py` creates clean direct-reading tasks (`TASK-V3-DIRECT-<PID>`) providing only `source/paper.pdf` with strict exclusion of all Evidentia intermediate artifacts.
- **Condition B (Frozen Evidentia Reader v3):** Full end-to-end execution utilizing the frozen candidate architecture.
- **Preserved Benchmark Corpus:**
  - `BENCH-01-VASWANI-ATTENTION` (Attention Is All You Need)
  - `BENCH-02-LORA-ADAPTATION` (LoRA)
  - `BENCH-03-REMOTE-SENSING-FOREST` (RSE Forest Trait)
  - `BENCH-04-ALPHAFOLD2-STRUCTURE` (AlphaFold2)
  - `BENCH-05-QUANTUM-SUPREMACY-ABLATION` (Sycamore Quantum Supremacy)
- **Evaluation Surface:** Automated evaluation protocol covers all 12 target scientific dimensions (narrative clarity, scientific completeness, method explanation, experiment interpretation, visual grounding, conclusion calibration, boundaries, insight, hallucination absence, provenance utility, paper-specific narrative completeness, and anti-template compliance).

---

## 9. Unseen-Paper Protocol

### **`UNSEEN_PROTOCOL_READY = YES`**

- **Freeze Precondition:** Unseen paper selection is strictly gated on `ARCHITECTURE_FROZEN = YES` and this recorded freeze commit.
- **Invariance Rule:** The unseen evaluation paper must be executed against the frozen commit `4139ca7b0b1ae72c0930801df5e50653b59a7e92`. No scientific contract, schema, prompt, or architecture modification is permitted in response to the unseen paper.
- **Bug Fix Discipline:** Any runtime execution bug encountered during unseen evaluation must be documented as an operational defect rather than silent architecture tuning.
- **Status:** **No unseen paper has been selected.** Selection will occur in formal Issue #19.

---

## 10. Workspace Hygiene & State Control

### **`WORKSPACE_READY_FOR_FREEZE = YES`**

- **Active Worktree:** Single canonical worktree at `/Users/shentianshuo/.agents/skills/evidentia` on branch `reader-reset-v3`.
- **Auxiliary Worktrees Removed:** All 12 temporary and revalidation worktrees (`issue22-goal0`, `bench02/04/05-issue22`, `issue22-lora-visual-fix`, `issue22-provenance-hardening`, `issue22-summary-audit`, `evidentia-benchmark-prep`, `evidentia-reader-v3-antitemplate`, `issue22-reval-bench02/04/05`) were cleanly unmounted and deleted.
- **PTY/Terminal State:** All stale background agent sessions closed; 0 zombie processes.
- **Evidence Integrity:** Historical manifests and benchmark workspaces under `reader-v3-runs/workspaces/` remain completely intact.

---

## 11. Deterministic Release Checks

### **`DETERMINISTIC_RELEASE_GATE = PASS`**

Focused test suite execution results on `reader-reset-v3`:
1. `tests/test_issue22_antitemplate.py`: **9 passed**
2. `tests/test_lens_execution_manifest.py`: **9 passed**
3. `tests/test_visual_reconstruction.py`: **5 passed**
4. `tests/test_agent_submit_trust_boundary.py`: **9 passed**
5. `tests/test_reader_v3.py`: **6 passed**
6. `tests/test_reader_acceptance.py`: **10 passed**
- **Total Focused Gate:** **48/48 PASSED** in 1.15s.
- **Structural Diversity Gate (`reader_structure_diversity.py`):** **PASS** (`materially_different_architectures: true`).
- **Git Status:** Clean tracked working tree.

*(Note: Pre-existing legacy red baseline tests in `test_phase_b7.py`, `test_replay_validation.py`, and `test_system_integrity.py` represent deprecated v1/v2 pipelines and are explicitly documented as isolated from Reader v3).*

---

## 12. Final Architecture Freeze Declaration

```text
================================================================================
ARCHITECTURE_FROZEN = YES
READER_V3_FREEZE_SHA = 4139ca7b0b1ae72c0930801df5e50653b59a7e92
================================================================================
```

Evidentia Reader v3 Wave 1 is officially frozen. All architectural development for Wave 1 is concluded. The repository is primed for formal Issue #19 unseen-paper benchmarking.
