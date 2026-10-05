# Issue #22 / PR #26 Comprehensive Revalidation & Final Audit Report

**Date:** 2026-10-05T20:45:00Z  
**Repository:** `tianshuo886/evidentia`  
**Candidate Code SHA:** `c2039ff687aa1034706e2a42299c4ec8024d47d5`  
**PR:** #26 (`feat(reader-v3): eliminate narrative-template bias (#22)`)  
**Base Branch:** `reader-reset-v3` (HEAD aligned at `cd3b6eed17ca49ae4adab01c2a76ffd7447d254c`)  
**Canonical Model Policy:** `antigravity/gemini-3.8-flash [magpie]` (Owner-approved canonical)  

---

## Executive Summary & Merge Verdict

### Verdict: `FAIL / NEEDS_REVISION`

PR #26 remains **OPEN**; Issue #22 remains **OPEN**. No premature merge or branch deletion into `reader-reset-v3` has been executed.

### Exact Blocker Rationale:
1. **Stage 1 Repaired-Input Closure Failure (BENCH-02 LoRA)**:
   - While **BENCH-04 (AlphaFold2)** and **BENCH-05 (Quantum Supremacy)** achieved **100% material input closure compatibility** (`REUSE_VALID`, 12/12 Lenses pass with 0 hash discrepancies), **BENCH-02 (LoRA)** cannot reuse its 6 existing Lens receipts.
   - The accepted BENCH-02 Lens receipts bound the pre-repair visual artifacts: `model/figure_inventory.json` (SHA `198add30...`) and uncorrected crops (`crop_F01_p1_151x153.png`, `crop_F02_p8_1068x338.png`, `crop_T04_p8_1068x338.png`). All 6 BENCH-02 Lenses actively cited `F01`, `F02`, or `T04` across 18 distinct scientific findings.
   - Under candidate SHA `c2039ff...`, the canonical repaired visual inventory is SHA `71607d07...` with corrected crops `crop_F01_p1_312x274.png`, `crop_F02_p8_536x331.png`, and `crop_T04_p8_688x366.png`. Because the 6 Lenses consumed the obsolete visual inputs, their execution receipts are classified as `RERUN_REQUIRED` to uphold Evidentia fail-closed scientific integrity.
2. **Passed Dimensions**:
   - **Structural Diversity**: **PASS** (LoRA: 8 sections; AlphaFold2: 8 sections; Sycamore: 12 sections; `materially_different_architectures: true`).
   - **Gemini Lead Writer**: **PASS** (All 3 papers successfully generated rich Chinese-first narrative manuscripts, valid under schema `3.0`, and cleanly rendered to 11-28 page academic PDFs).
   - **Focused Test Suites & Provenance Gates**: **PASS** (48/48 unit & integration tests passing on candidate codebase).
   - **BENCH-04 & BENCH-05 Provenance**: **PASS** (`REUSE_VALID` for all 12 Lenses, verified isolated manifests).

---

## 18-Lens Provenance & Material Closure Matrix

| Paper ID | Lens Task ID | Model | Manifest Inputs | Code SHA | Material Input Closure Status | Provenance & Isolation | Decision | Rationale |
|---|---|---|---|---|---|---|---|---|
| **BENCH-02** | `TASK-V3-LENS-ARGUMENT_NARRATIVE` | `step-5-preview` | 199 items | `c2039ff` | **STALE** (consumed pre-repair F01/F02/T04) | VALID (isolated filesystem snapshot) | `RERUN_REQUIRED` | Pre-repair visual inventory `198add30` consumed; citations in `FIND-AN-02`, `FIND-AN-04` |
| **BENCH-02** | `TASK-V3-LENS-EVIDENCE_RESULTS` | `step-5-preview` | 199 items | `c2039ff` | **STALE** (consumed pre-repair F01/F02/T04) | VALID (isolated filesystem snapshot) | `RERUN_REQUIRED` | Pre-repair visual inventory `198add30` consumed; citations in `ER-01`, `ER-04`, `ER-09` |
| **BENCH-02** | `TASK-V3-LENS-MECHANISM_CAUSALITY` | `step-5-preview` | 199 items | `c2039ff` | **STALE** (consumed pre-repair F01) | VALID (isolated filesystem snapshot) | `RERUN_REQUIRED` | Pre-repair F01 consumed; citations in `MC-MECH-01`, `MC-MECH-02` |
| **BENCH-02** | `TASK-V3-LENS-METHOD_STUDY_DESIGN` | `step-5-preview` | 199 items | `c2039ff` | **STALE** (consumed pre-repair F01/F02/T04) | VALID (isolated filesystem snapshot) | `RERUN_REQUIRED` | Pre-repair visual inventory consumed; citations in `MSD-01`, `MSD-06`, `MSD-09` |
| **BENCH-02** | `TASK-V3-LENS-REPRODUCIBILITY_IMPLEMENTATION` | `step-5-preview` | 199 items | `c2039ff` | **STALE** (consumed pre-repair F01/T04) | VALID (isolated filesystem snapshot) | `RERUN_REQUIRED` | Pre-repair visual inventory consumed; citations in `REPRO-03`, `REPRO-05`, `REPRO-08` |
| **BENCH-02** | `TASK-V3-LENS-VALIDITY_BOUNDARY` | `step-5-preview` | 199 items | `c2039ff` | **STALE** (consumed pre-repair F01/F02/T04) | VALID (isolated filesystem snapshot) | `RERUN_REQUIRED` | Pre-repair visual inventory consumed; citations in `VB-02`, `VB-04`, `VB-09` |
| **BENCH-04** | `TASK-V3-LENS-ARGUMENT_NARRATIVE` | `step-5-preview` | 131 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-04** | `TASK-V3-LENS-EVIDENCE_RESULTS` | `step-5-preview` | 131 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-04** | `TASK-V3-LENS-MECHANISM_CAUSALITY` | `step-5-preview` | 131 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-04** | `TASK-V3-LENS-METHOD_STUDY_DESIGN` | `step-5-preview` | 131 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-04** | `TASK-V3-LENS-REPRODUCIBILITY_IMPLEMENTATION` | `step-5-preview` | 131 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-04** | `TASK-V3-LENS-VALIDITY_BOUNDARY` | `step-5-preview` | 131 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-05** | `TASK-V3-LENS-ARGUMENT_NARRATIVE` | `step-5-preview` | 90 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-05** | `TASK-V3-LENS-EVIDENCE_RESULTS` | `step-5-preview` | 90 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-05** | `TASK-V3-LENS-MEASUREMENT_INTEGRITY` | `step-5-preview` | 90 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-05** | `TASK-V3-LENS-MECHANISM_CAUSALITY` | `step-5-preview` | 90 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-05** | `TASK-V3-LENS-METHOD_STUDY_DESIGN` | `step-5-preview` | 90 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |
| **BENCH-05** | `TASK-V3-LENS-VALIDITY_BOUNDARY` | `step-5-preview` | 90 items | `c2039ff` | **IDENTICAL** (0 mismatches) | VALID (isolated filesystem snapshot) | `REUSE_VALID` | Canonical input closure fully matches candidate SHA; unaffected by LoRA repair |

---

## LoRA Visual Asset Verification Trace

- **F01 Repaired**: `assets/figures/crop_F01_p1_312x274.png` (SHA `4d48ed984efa...`), dimensions (312, 274). Contains the complete reparameterization diagram (frozen $W_0$, parallel $BA$, scaling factor $lpha/r$, input $x$, output $h$). Verified complete and not truncated.
- **T04 Repaired**: `assets/figures/crop_T04_p8_688x366.png` (SHA `fb74bae66594...`), dimensions (688, 366). Accurately captures Table 4 at the top of page 8 with GPT-3 175B performance benchmarks across WikiSQL, MultiNLI, and SAMSum.
- **F02 Repaired**: `assets/figures/crop_F02_p8_536x331.png` (SHA `2d526143759a...`), dimensions (536, 331). Accurately captures Figure 2 validation accuracy curves below Table 4.
- **Collision Resolution**: `F02` and `T04` have completely distinct bounding boxes, distinct pixel dimensions, distinct hashes, and distinct semantic bindings in `figure_inventory.json`.
- **Render Trace**: In the rendered `paper_reader.html` and `paper_reader.pdf`, Table 4 and Figure 2 are rendered into Section 1 with exact visual assets and faithful Chinese scientific descriptions.

---

## Three Manuscript & Reader Integrity Audit (Gemini Canonical)

| Paper | Manuscript SHA-256 | Rendered PDF SHA-256 | Sections | Visual Blocks | Scientific Topology |
|---|---|---|---|---|---|
| **BENCH-02** | `03ff25ee743adce5be2f628045e7f2081f9640960d7045b854e414c77d46c87e` | `7531405e3fbb1c2c31e40a0c9ba25c60e4088a223ad0f707f1f9661413a9485b` | 8 | 17 visual/table/eq | Operational constraints → Reparameterization → Serving duality → Scale validation → Budget allocation → Grassmann mechanics → Epistemic boundaries |
| **BENCH-04** | `9ea63a0ec3e9508d4b3fc63b27b9a5840d58aa89b4b037e954c25fca783f9e9a` | `ea89b9d36e2d93e8e24c0d3ce30d9a65664db22f986427df61e2f750c18d9e77` | 8 | 0 (narrative core) | Blinded benchmark accuracy → Confidence calibration → Evoformer spatial graph → Residue gas & FAPE → Self-distillation trajectories → Ablation penalty ladder → Evolutionary/contact boundaries → Biophysical scope |
| **BENCH-05** | `13a79d01fb8183141ec85c1bf431db87b1c34a2e5564993181829e7c53d0e91f` | `4328fc8a0fcbf1e35fa8cfd795b8d00d5a3712b32274b341f2a36d2c4e207908` | 12 | 0 (narrative core) | Dual complexity challenge → RCS probe → Observable ($F_{XEB}$) → Sycamore substrate → Simultaneous error calibration → Multiplicative model → Tiling ablation → Fig. 4a negative control → Supremacy measurement → Classical extrapolation → Pauli model validation → Moving frontiers |

All three manuscripts conform strictly to `schemas/narrative_manuscript.schema.json` under schema_version `3.0`.

---

## Structural Anti-Template Validation

- **Report Status:** `PASS`
- **Output Artifact:** `ISSUE22_STRUCTURAL_DIVERSITY_REVALIDATION.json`
- **Checker Command:** `python3 scripts/reader_structure_diversity.py ...`
- **Section Distribution:** 8 sections (LoRA), 8 sections (AlphaFold2), 12 sections (Quantum Supremacy).
- **Material Diversity:** `materially_different_architectures = true`
- **Qualitative Audit:** Readers follow the organic, intrinsic intellectual deduction of the underlying papers rather than a uniform IMRaD outline.

---

## Scientific Regression Assessment (Gemini Evaluator)

| Assessment Dimension | Rating | Technical Audit Summary |
|---|---|---|
| **Scientific Completeness** | **PASS** | Critical theorems, mathematical formalisms, experimental margins, and hardware budgets are fully preserved. |
| **Method/Study Explanation** | **PASS** | Evoformer metric constraints, LoRA $W_0 + rac{lpha}{r}BA$ folding, and Sycamore RCS elided circuits are rigorously expounded. |
| **Experiment & Result Interpretation** | **PASS** | Distinguishes actual measurement from classical runtime extrapolation (~200s vs ~10,000 years); records non-monotonic rank anomalies on dialogue summarization. |
| **Evidence Correctness & Grounding** | **PASS** | All citations map directly to authenticated source inventory items. |
| **Visual Interpretation** | **PASS** | Semantic visual bindings verified with zero ambiguous collisions. |
| **Conclusion Calibration & Boundaries** | **PASS** | Preserves boundaries: non-fault-tolerant quantum status, AlphaFold2 static crystallization vs dynamic ensemble limits, LoRA attention-only scope. |
| **Chinese-First Readability** | **PASS** | Native, fluent, academic Chinese prose without robotic direct translation artifact. |

---

## Candidate Code Tests & GitHub CI

1. `tests/test_issue22_antitemplate.py`: **9/9 PASSED**
2. `tests/test_lens_execution_manifest.py`: **4/4 PASSED**
3. `tests/test_visual_reconstruction.py`: **10/10 PASSED**
4. `tests/test_agent_submit_trust_boundary.py`: **9/9 PASSED**
5. `tests/test_reader_v3.py`: **6/6 PASSED**
6. `tests/test_reader_acceptance.py`: **10/10 PASSED**
- **Total Focused Candidate Suite:** **48/48 PASSED** in 0.94s.
- **GitHub Migration CI:** Passing on PR #26.

---

## Next Step for Final Release

To convert this audit verdict from `FAIL / NEEDS_REVISION` to `PASS`:
- Execute a clean rerun of the **6 Lenses on BENCH-02 only** against the repaired canonical visual assets (`figure_inventory.json` SHA `71607d07...`), register their execution manifests through the gateway, and regenerate the final manifest freeze.
- Do **NOT** rerun BENCH-04 or BENCH-05, as their closures are proven clean and reusable.
