# Evidentia Reader Reset v3: Final Release Audit Report

**Date:** 2026-10-06T02:00:00Z  
**Repository:** `tianshuo886/evidentia`  
**Pull Request:** #21 — *Reader Reset v3: strong-model-first reading pipeline*  
**PR State:** `DRAFT / OPEN` (Merge Blocked by Failing GitHub Checks)  
**Release Verdict:** `READER_V3_MASTER_RELEASE = BLOCKED`  

---

## 1. Canonical Release SHA Resolution & Discrepancy Audit

* **Repository Runtime State:**
  * `master HEAD`: `4efd17397fda195a2a0dd3bf9246c55d1aa4e8c1`
  * `origin/master`: `4efd17397fda195a2a0dd3bf9246c55d1aa4e8c1`
  * `reader-reset-v3 HEAD`: `2eb494aae4684d3fa62407264e17960ea1df9219`
  * `origin/reader-reset-v3`: `2eb494aae4684d3fa62407264e17960ea1df9219`
  * `PR #21 head SHA`: `2eb494aae4684d3fa62407264e17960ea1df9219`
  * `PR #21 base SHA`: `4efd17397fda195a2a0dd3bf9246c55d1aa4e8c1`
  * `Mergeability`: `MERGEABLE`
* **Discrepancy Analysis:**
  * Observed PR #21 HEAD: `2eb494aae4684d3fa62407264e17960ea1df9219`
  * Prior Audit Report Record: `2eb494a5e2f75b8ba26fb966950ee0b2b8109bf1`
  * Investigation of `.git/logs/HEAD`: Commit `2eb494aae4684d3fa62407264e17960ea1df9219` was created at timestamp `1791221820 +0800` via `git merge issue23-kami-boundary`. No subsequent rewrite or rebase occurred.
  * Discrepancy Classification: **`REPORT_TYPO`** (The prior turn report took the 7-character prefix `2eb494a` and hallucinated the remaining 33 hexadecimal characters instead of resolving `git rev-parse HEAD`).
  * Actual Canonical Candidate SHA:
    ```text
    PR21_FINAL_RELEASE_SHA = 2eb494aae4684d3fa62407264e17960ea1df9219
    ```

---

## 2. Reader Reset Issues Final Audit & Closure States

Every Reader Reset issue has been audited against its original acceptance criteria and durable implementation evidence:

| Issue # | Title | Core Acceptance Criteria | Verification Evidence | Final Status |
|---|---|---|---|---|
| **#16** | Multimodal Visual Evidence Reconstruction | Page-first multimodal localization; generic figure/table disambiguation; visual trust gate; fail-closed crop bindings. | `scripts/visual_localization_protocol.py`, `scripts/apply_visual_verification.py`. Verified on LoRA F01/F02/T04 disambiguation (PR #26) and 6/6 added-value figure wins in Issue #19 benchmark. | **`CLOSED`** |
| **#17** | Lead Reader + 4 Core / 2 Adaptive Lens Orchestration | `Lens != Agent != Model != Harness`; Lead Reader draft; 4 Core + 2 Adaptive Lenses; isolated execution boundaries; same-model default. | `tasks/v3/lead_reading.json`, `scripts/lens_registry.py`, `provenance/lens/<task_id>` snapshots, gateway receipts in `scripts/agent_submit.py`. Canonical model `antigravity/gemini-3.8-flash [magpie]` executed all 6 passes across 6 real papers without crosstalk. | **`CLOSED`** |
| **#18** | Revision Memo + Strong-Model Lead Writer | Editorial revision memo without majority voting; dynamic narrative plan; strong-model academic authoring; deprecation of deterministic composers. | `tasks/v3/revision_memo.json`, `tasks/v3/narrative_plan.json`, `tasks/v3/lead_writing.json`. Verified structural diversity (LoRA 6, AlphaFold2 8, Sycamore 12 sections) and 5.0/5.0 anti-template safety in Issue #19. | **`CLOSED`** |
| **#19** | Real-Paper Formal A/B Benchmark | Formal post-freeze Direct-AI vs. Evidentia A/B benchmark on 6 real papers; mirrored blind evaluation across 14 dimensions; mandatory unseen paper. | `ISSUE19_FORMAL_AB_BENCHMARK.json`, `ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md`, `ISSUE19_EVIDENCE_MANIFEST.json`. Outcome: 6/6 Evidentia wins, 0 core regressions, `ISSUE19_RELEASE_GATE = PASS`. | **`CLOSED`** |
| **#20** | Canonical Reader Cleanup & Legacy Retirement | Reader v3 established as exclusive default; legacy deterministic synthesis/composer quarantined under `--legacy`; architecture docs updated. | `scripts/evidentia.py` defaults to v3; `capability_matrix.json` (v3.0); `SKILL.md` and reference docs rewritten; `ISSUE20_CANONICALIZATION_REPORT.md`. | **`CLOSED`** |
| **#22** | Anti-Template Narrative Bias Elimination | Eliminate narrative-template bias; restore authentic visual assets for LoRA; verify structural diversity across real papers. | `tests/test_issue22_antitemplate.py` (9/9), `scripts/reader_structure_diversity.py`, `ISSUE22_REAL_PAPER_VALIDATION.md`. | **`CLOSED`** |
| **#23** | Kami Presentation-Only Boundary Reset | Kami owns typography, spacing, layout, vector PDF export; Kami cannot alter scientific semantics; 3-tier warning classification. | `scripts/kami_adapter.py`, `references/reader_presentation_contract.md`, `tests/test_kami_boundary.py` (6/6), `ISSUE23_KAMI_BOUNDARY_REPORT.md`. | **`CLOSED`** |
| **#15** | Reader Reset v3 Umbrella | Complete end-to-end integration across all child milestones; 5-10 real papers; unseen paper validation; parity with direct AI. | All child issues (#16, #17, #18, #19, #20, #22, #23) completed and verified. 6 real papers executed with zero regressions. | **`CLOSED`** |

Remaining open issues in repository: Issue #24 and Issue #25 (P2 Human-AI Research Workspace, explicitly deferred to Wave 2).

---

## 3. Formal Release Evidence Audit

All durable evidence manifests and benchmark reports were verified on disk with matching SHA-256 hashes:
- `WAVE1_READER_V3_FREEZE_AUDIT.md`: `7aa2e0dbb9c625535f949c3ac8edcb0cbcb9392f0b73ed013b8aef976195a1e9`
- `ISSUE19_EVALUATION_PROTOCOL.json`: `3f68d0b34d27c21914c113a901bf22c4377bb967ed0c51a1f4178948f984507c`
- `ISSUE19_FORMAL_AB_BENCHMARK.json`: `d1e412392b42f1b70128dde6da4a17f19b4b8b00afd4918177b1ba0672844472`
- `ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md`: `783f4a8ebb6b1df77eea511144de0b7ada14948042850262fb02d18f16cd03e2`
- `ISSUE19_EVIDENCE_MANIFEST.json`: `fdf87593d71cd242c0072e509781e4a3f42a5e6aff99975f7dca75b31048ef78`
- `ISSUE19_UNSEEN_SELECTION_RECEIPT.json`: `e852fa16e6e8567e20f797de064e5e54bd7fa454d09be421de59ee4c31899bb1`
- `ISSUE20_CANONICALIZATION_REPORT.md`: `56680b1ff6b7ff36f361c78334aded0a220bbb48e77d9144b6db713900cdcdc1`
- `ISSUE22_REAL_PAPER_VALIDATION.md`: `584bc9d4b4069cd843e9dd5b8fbb3144bf4c27f171eb0e557f256c5babcec746`
- `ISSUE22_EVIDENCE_MANIFEST.json`: `5f5635a3324fb490f1a3c9542e80d9a1cd545ff70710328c2b1703518c5c023c`
- `ISSUE23_KAMI_BOUNDARY_REPORT.md`: `83565146f41240fdd6df7e4dfc5d82a0afda94241c4480add7a022d0792fe732`

---

## 4. Final Architecture & Documentation Audit

* **Canonical Architecture Path:**
  `Source Reconstruction → Semantic Visual Verification → Lead Reader → 4 Core + 2 Adaptive Lenses → Revision Memo → Dynamic Narrative Plan → Lead Writer → Integrity Validation → Kami Presentation / Evidence Atlas`.
* **Invariants Confirmed:**
  - Zero fixed scientific story templates;
  - Zero fixed-six-personality canonical Lens paths;
  - Zero deterministic scientific composer fallback;
  - Zero sibling Lens crosstalk;
  - Zero Project Apply or Research Memory contamination during Honest Reading;
  - Legacy code quarantined for compatibility/historical replay only;
  - Kami presentation strictly decoupled from scientific manuscript truth.
* **Verdict:** `CANONICAL_ARCHITECTURE = PASS`
* **Docs Release Gate:** `DOCS_RELEASE_GATE = PASS`

---

## 5. Test Gates & Semantic Invariance

* **Deterministic Local Regression Suite:**
  - `python3 -m pytest tests/ -q`: **180 passed, 0 failed** (5 deprecation warnings from SwigPy).
  - `FINAL_TEST_GATE = PASS`.
* **Scientific Semantic Invariance:**
  - Physical SHA-256 hashes of all 6 benchmark paper manuscripts match `ISSUE19_EVIDENCE_MANIFEST.json` with zero byte mutations.
  - `SCIENTIFIC_SEMANTICS_CHANGED = NO`.

---

## 6. Release Blocker Audit (Why Master Merge Is Blocked)

Under Section 8 release rules, PR #21 may leave Draft status and merge into `master` only if **all release conditions are met, including `GitHub checks green` without force-merging around failing checks**.

### Current GitHub Checks Status on PR #21 (`gh pr checks 21`):
1. **Reader v3 Migration CI (`reader-v3.yml`):**
   - `reader-v3 (3.9)`: **PASS** (32s)
   - `reader-v3 (3.10)`: **PASS** (24s)
   - `reader-v3 (3.11)`: **PASS** (22s)
2. **Evidentia CI (`ci.yml` - Run ID `37350273539`):**
   - `test (3.9)`: **FAIL** (2m21s)
   - `test (3.10)`: **FAIL** (2m01s)
   - `test (3.11)`: **FAIL** (1m48s)

### Root Cause of Check Failure:
1. **`UnboundLocalError` in `scripts/kami_adapter.py:148`:** In commit `ad44735` (Issue #23), the loop `for args in checks:` was accidentally de-indented outside of `if root and (root / 'scripts/build.py').exists():`. When executed on headless Ubuntu GitHub Actions runners where Kami is not pre-installed, `checks` is undefined, throwing `UnboundLocalError` and crashing all 31 acceptance/rendering tests.
2. **Legacy CI / Headless Runner Dependencies in `ci.yml`:** The legacy `ci.yml` workflow on `master` has been red since September 28 because standard Ubuntu runners lack CJK fonts (`fonts-noto-cjk`) required for WeasyPrint Chinese text extraction in `reader_acceptance.py`, and `contract_audit.py` / `reader_audit.py` still assert on obsolete v1 demo artifacts.

### Enforcement Policy:
In accordance with Section 8 ("Do not force merge around failing checks") and Section 11 ("If BLOCKED: do not merge; identify exact blocker; preserve current state"):
- PR #21 remains in **DRAFT / OPEN** state;
- No force merge was performed;
- All completed issue milestones and evidence remain securely frozen on `reader-reset-v3`.

---

## 7. Retained Compatibility Debt & Next Steps

1. **Bugfix on Kami Adapter:** Indent `for args in checks:` inside `if root and ...:` in `scripts/kami_adapter.py`, and provide fallback LaTeX SVG wrapper when Kami MathJax is absent.
2. **Modernize `ci.yml`:** Harmonize `ci.yml` with `reader-v3.yml` or install CJK font packages in CI (`fonts-noto-cjk`) so headless Linux test runs achieve parity with macOS local test runs.
3. **Draft Release Transition:** Once GitHub checks turn fully green, PR #21 can be undrafted and cleanly fast-forward/merged into `master`.

---

## 8. CI Hotfix & Successful Master Merge

**Date:** 2026-10-06T04:45:00Z  
**Final Release Verdict:** **`READER_V3_MASTER_RELEASE = PASS`**  
**Pre-Hotfix SHA:** `2eb494aae4684d3fa62407264e17960ea1df9219`  
**CI Hotfix SHA:** `61df8340b3f2b6fb4702598ebb3e30b323ab0028`  
**PR #21 Merge Commit SHA:** `2d95ad2a2ce976fd04fca5503a8fd18b02a6e31b`  
**Master HEAD after Merge:** `2d95ad2a2ce976fd04fca5503a8fd18b02a6e31b`  

### 8.1 Remote Failure Investigation & Root Causes
- **Original Failed Workflow ID:** `37350273539` (Evidentia CI on PR #21)
- **Root Causes:**
  1. *Control-flow defect in `scripts/kami_adapter.py`:* `for args in checks:` at line 148 was de-indented outside of `if root and (root / 'scripts/build.py').exists():`. On clean Linux runners without Kami installed, `checks` was unbound, throwing `UnboundLocalError`.
  2. *Missing Kami MathJax presentation dependency in CI:* `render_math_html` raised `RuntimeError` when Kami MathJax renderer was absent.
  3. *Missing CJK fonts on Ubuntu GitHub runners:* WeasyPrint in headless Linux could not render Chinese text for PDF extraction without `fonts-noto-cjk`.
  4. *Stale `contract_audit.py` output:* Legacy script generated schema v2.0 instead of validating v3.0 capability matrix.

### 8.2 Hotfix Implementation
- **Hotfix Commits:**
  - `d57fdc85654070863103fc348a743f6887d1ae3d`: `fix(ci): repair Kami adapter control-flow, provision CI presentation runtime, and modernize contract audit`
  - `61df8340b3f2b6fb4702598ebb3e30b323ab0028`: `fix(ci): scope fixture acceptance env to legacy reader audit step`
- **Actions Taken:**
  1. Fixed control flow in `scripts/kami_adapter.py`: properly nested `for args in checks:` and attached `else:` to the Kami availability check.
  2. Enhanced `find_kami_root()` to support both `skills/kami/scripts/build.py` and `scripts/build.py` layouts, and respect explicit disabled paths.
  3. Added regression test `test_kami_audit_when_kami_unavailable_does_not_crash` in `tests/test_kami_boundary.py`.
  4. Updated `.github/workflows/ci.yml` to install `fonts-noto-cjk` and provision pinned Kami v1.16.0 with MathJax runtime in Ubuntu CI runners.
  5. Modernized `scripts/contract_audit.py` to validate v3.0 capability matrix without corrupting `capability_matrix.json`.
  6. Scoped `EVIDENTIA_FIXTURE_ACCEPTANCE: "1"` strictly to legacy demo fixture audit steps, preserving fail-closed semantics for unit tests.

### 8.3 Remote Verification & 100% Green Matrix
- **Reader v3 Migration CI (`reader-v3.yml` - Run `37364344114`):**
  - Python 3.9: **PASS** (34s)
  - Python 3.10: **PASS** (30s)
  - Python 3.11: **PASS** (24s)
- **Evidentia CI (`ci.yml` - Run `37364344039`):**
  - Python 3.9: **PASS** (9m33s)
  - Python 3.10: **PASS** (8m25s)
  - Python 3.11: **PASS** (7m27s)
- **Deterministic Test Gate:** 181/181 tests passed locally and in CI (0 failures).
- **Scientific Semantic Invariance:** `SCIENTIFIC_SEMANTICS_CHANGED = NO` (All 6 real benchmark paper manuscripts match byte-for-byte).

### 8.4 Master Merge Execution
- PR #21 marked Ready for Review (`isDraft: false`).
- Merge executed via GitHub API targeting `master`:
  `gh pr merge 21 --merge --match-head-commit 61df8340b3f2b6fb4702598ebb3e30b323ab0028`
- Merge commit `2d95ad2a2ce976fd04fca5503a8fd18b02a6e31b` recorded and verified on `master`.
- Reader v3 is now the canonical production implementation on `master`.
