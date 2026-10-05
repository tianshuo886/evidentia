# Issue #20: Reader Reset v3.5 Canonicalization & Legacy Retirement Report

**Date:** 2026-10-06T01:30:00Z  
**Repository:** `tianshuo886/evidentia`  
**GitHub Issue:** #20 — Reader Reset v3.5 — retire legacy fixed-six-Lens / premature ensemble / deterministic Reader paths and rewrite architecture docs  
**Reader v3 Freeze Commit SHA:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`  
**Benchmark Release Status:** Issue #19 PASS on 6 real papers (`ISSUE19_RELEASE_GATE = PASS`)  
**Canonical Model Policy:** `antigravity/gemini-3.8-flash [magpie]` (High Reasoning Profile)  

---

## 1. Executive Summary

With Reader v3 officially passing the 6-paper real-world benchmark in Issue #19, Issue #20 establishes **Reader v3 as the single canonical paper-reading implementation**. All obsolete, contradictory, or legacy deterministic paths have been classified, retired, or safely quarantined into downstream-only compatibility modes.

### Core Principle Reaffirmed:
> **Paper decides the story. Evidentia enforces rigor. Kami presents the story.**

---

## 2. Inventory & Classification of Legacy vs. Canonical Components

Every component in the repository has been audited and classified into four categories:
1. `KEEP_CANONICAL`: Core production architecture.
2. `MIGRATE`: Updated to make v3 default and remove legacy assumptions.
3. `COMPATIBILITY_ONLY`: Quarantined with deprecation headers for historical replay/downstream compatibility.
4. `DELETE`: Dead tests asserting on superseded pre-v3 artifacts.

| Component / File | Classification | Category Description & Action Taken |
|---|---|---|
| `scripts/reader_v3.py` | `KEEP_CANONICAL` | Core stateful orchestrator for Reader v3. |
| `scripts/reader_v3_protocol.py` | `KEEP_CANONICAL` | Protocol definitions for Lead Reader, 4 Core + 2 Adaptive Lenses, Revision Memo, Narrative Plan, Lead Writer. |
| `scripts/render_paper_reader.py` | `KEEP_CANONICAL` | Kami Chinese editorial renderer; fail-closed check on `narrative_manuscript.json` enforced. |
| `scripts/render_evidence_atlas_v3.py` | `KEEP_CANONICAL` | Interactive Evidence Atlas v3 linking claims to verified source anchors. |
| `scripts/agent_submit.py` | `KEEP_CANONICAL` | Scientific trust boundary gateway enforcing cryptographic manifests and input isolation. |
| `scripts/prepare_lens_isolation.py` | `KEEP_CANONICAL` | File-system isolation snapshots for each specialist lens. |
| `scripts/visual_localization_protocol.py` | `KEEP_CANONICAL` | Page-first multimodal localization protocol. |
| `scripts/apply_visual_verification.py` | `KEEP_CANONICAL` | Deterministic application of verified visual crops to figure inventory. |
| `scripts/evidentia.py` | `MIGRATE` | Default `run` command now executes the canonical Reader v3 pipeline. `--legacy` flag quarantined for backward compatibility. |
| `scripts/pipeline.py` | `MIGRATE` | `pipeline read` invokes the canonical Reader v3 pipeline. |
| `scripts/render_reader.py` | `MIGRATE` | Preserves Lead Writer `narrative_manuscript.json` without overwriting; renders via `render_paper_reader.py`. |
| `scripts/scientific_synthesis_agent.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Quarantined for historical replay only; prohibited in v3. |
| `scripts/narrative_composer_agent.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Silent fallback removed from `render_paper_reader.py`. |
| `scripts/merge_lenses.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Superseded by Editorial Revision Memo. |
| `scripts/within_lens_reconciliation.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Premature ensemble polling retired. |
| `scripts/adaptive_escalation.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Superseded by targeted verification. |
| `scripts/lens_council.py` & `council.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Superseded by Revision Memo. |
| `scripts/check_lenses.py` & `lens_runner.py`| `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Superseded by `tasks/v3/lens/` isolation protocol. |
| `scripts/snapshot_baseline.py` | `COMPATIBILITY_ONLY` | Marked `DEPRECATED`. Superseded by Lead Reader draft hash binding. |
| `schemas/lens.schema.json` | `COMPATIBILITY_ONLY` | Annotated as deprecated historical schema. |
| `schemas/lens_reconciliation.schema.json` | `COMPATIBILITY_ONLY` | Annotated as deprecated historical schema. |
| `schemas/scientific_synthesis.schema.json` | `COMPATIBILITY_ONLY` | Annotated as deprecated historical schema. |
| `schemas/paper_reader_ir.schema.json` | `COMPATIBILITY_ONLY` | Annotated as deprecated historical schema. |
| `tests/test_reader_release_gate.py` | `DELETE` | Removed dead Issue #13 test asserting on deleted `evals/reader_regression`. |
| `tests/test_issue20_canonical.py` | `KEEP_CANONICAL` | Added regression test suite verifying v3 defaults and fail-closed gates. |

---

## 3. Canonical Scientific Path Specification

The single official Evidentia paper-reading path is:

```text
Source Reconstruction (Full Text + Page-first Multimodal Localization)
  ↓
Deterministic Source Lock & Evidence Verification
  ↓
Lead Reader Pass (Open Argument Topology, Characterization, Lens Plan)
  ↓
4 Universal Core + 2 Adaptive Specialist Lenses (Context-Isolated Snapshots, Zero Crosstalk)
  ↓
Editorial Revision Memo (Structured Directives: Keep/Expand/Correct/Qualify/Verify; No Voting)
  ↓
Dynamic Narrative Plan (Custom Anti-Template Section Architecture)
  ↓
Lead Writer (Strong-Model Academic Manuscript authoring)
  ↓
Integrity & Anti-Template Validation (Fail-Closed Asset & Reference Verification)
  ↓
Kami Presentation Transformation (Typography, Responsive Layout, Vector PDF Export)
  ↓
Publication-Grade Paper Reader & Secondary Evidence Atlas
```

---

## 4. Documentation Canonicalization Summary

All architecture documentation was synchronized to eliminate outdated descriptions:
- **`SKILL.md`:** Rewritten to reflect the 4 Core + 2 Adaptive Lens structure, Revision Memo, Dynamic Narrative Plan, Lead Writer, and Kami presentation boundary. Removed fixed six personalities and deterministic synthesis.
- **`README.md` & `README.zh-CN.md`:** Updated to describe the canonical Reader v3 architecture, highlighting the Issue #19 release benchmark results and the three core tenets.
- **`references/complete-workflow.md`:** Updated state machine to the canonical Reader v3 progression.
- **`references/reader.md`:** Standardized on `narrative_manuscript.schema.json` and Kami presentation boundaries.
- **`references/lens.md` & `references/reconciliation.md`:** Superseded legacy fixed personalities and deterministic clustering with 4 Core + 2 Adaptive lenses and Editorial Revision Memo.
- **`references/evaluation.md`:** Documented the formal Issue #19 A/B Benchmark on real papers as the empirical release gate.
- **`capability_matrix.json`:** Updated to schema version 3.0, distinguishing `REAL_PAPER_VALIDATED` (Core v3), `SYNTHETIC_ONLY` (Project Apply / Memory prototypes), and `DEPRECATED` (Legacy v1/v2 synthesis/composer).

---

## 5. Deterministic Regression & Test Suite Verification

- **Total Test Cases Executed:** **174**
- **Passed:** **174 (100%)**
- **Failed:** **0**
- **New Canonicalization Tests:** `tests/test_issue20_canonical.py` (5/5 passed):
  - Verified `evidentia.py run` defaults to Reader v3.
  - Verified `evidentia.py status` and `next` correctly report v3 state.
  - Verified `render_paper_reader.py` fails closed when manuscript is missing.
  - Verified `render_reader.py` preserves Lead Writer manuscripts without overwriting.
  - Verified `capability_matrix.json` status vocabulary.
- **Semantic Change Assessment:** **`SCIENTIFIC_SEMANTICS_CHANGED = NO`** (All changes are organizational, architectural cleanup, and deprecation quarantines).

---

## 6. Remaining Technical Debt

1. **Legacy Test Fixtures:** A small number of test files (`test_replay_validation.py`, `test_system_integrity.py`) retain legacy replay assertions. They run cleanly under compatibility mode (`EVIDENTIA_FIXTURE_ACCEPTANCE=1`), but should be transitioned to pure v3 replays in a future maintenance cycle.
2. **Apply Pipeline Transfer Benchmark:** Project Apply (`init_apply.py`, `apply_agent.py`) is verified using synthetic fixtures (`SYNTHETIC_ONLY`). A real-paper multi-project transfer benchmark is scheduled for Wave 2.
