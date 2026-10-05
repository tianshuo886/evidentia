# Issue #23: Kami Boundary Reset & Presentation Contract Report

**Date:** 2026-10-06T01:45:00Z  
**Repository:** `tianshuo886/evidentia`  
**GitHub Issue:** #23 — [P1] Kami boundary reset — visual consistency without scientific or narrative templating  
**Reader v3 Freeze Commit SHA:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`  
**Benchmark Release Status:** Issue #19 PASS (`ISSUE19_RELEASE_GATE = PASS`)  

---

## 1. Executive Summary

Issue #23 establishes the **strict presentation-only boundary** for the Kami rendering engine. The core product principle is:

> **Visual consistency, narrative diversity.**  
> *Paper decides the story. Evidentia enforces rigor. Kami presents the story.*

Kami provides elegant typography, vertical spacing, responsive layout, and print PDF styling. Kami is completely stripped of authority over scientific section titles, chapter counts, section order, claim formulation, and evidence selection.

---

## 2. Explicit Responsibility Boundaries

### Kami Owns (Presentation Only):
- Typography (Chinese serif font family hierarchy, line height, tabular numerals).
- Spacing and rhythm (`--rhythm-module`, paragraph margins, block padding).
- Visual hierarchy (chapter title sizes, callout styling, border accents).
- Local figure, table, and equation placement mechanics.
- Captions and callout styling.
- Responsive HTML presentation and print page breaks.
- PDF vector export via WeasyPrint / headless Chrome.
- Automated layout defect auditing (`reader/kami_audit.json`).

### Kami Must NOT Own (Prohibited Scientific Authority):
- Scientific section titles and chapter count.
- Section ordering (strictly governed by the Lead Writer's `narrative_plan.json`).
- Which experiments or figures are decisive.
- Formulating mechanisms, limitations, or caveats.
- Silently dropping blocks or summarizing paragraphs to fit layout constraints.
- Injecting generic IMRaD boilerplate (Background, Methods, Results, Discussion).

---

## 3. Renderer-Facing Semantic Manuscript Contract

Renderers receive the completed semantic manuscript (`reader/narrative_manuscript.json`, conforming to `schemas/narrative_manuscript.schema.json`).

Blocks are strictly presentation semantics:
- `paragraph`: Body prose.
- `callout`: Notable commentary or emphasis.
- `takeaway`: Key takeaway block with brand accent.
- `figure`: Bound figure asset with caption and analysis.
- `table`: Data table with caption and optional asset crop.
- `equation`: Numbered formula with display LaTeX and source confidence.
- `list`: Compact structured itemization.

Block types are visual layout primitives, never mandatory scientific categories.

---

## 4. Formal Warning Classification Policy

All visual QA diagnostics in `scripts/kami_adapter.py` are classified into three explicit tiers:

1. **`BLOCKING` (Release-Blocking):**
   - Missing glyphs / tofu characters (`--check-fonts`).
   - Placeholder leakage or unpopulated tokens (`--check-placeholders`).
   - Visual figure clipping or unreadable crops (`--check-visual`).
   - Missing asset files or asset collisions across distinct evidence IDs.
   - *Impact:* The audit status becomes `FAIL`; release is blocked until resolved.
2. **`HUMAN_REVIEW_REQUIRED` (Review Flag):**
   - Widows/orphans on non-standard paragraph ends (`--check-orphans`).
   - Low density on trailing chapter pages (`--check-density`).
   - *Impact:* Preserved in the audit log for human sign-off; does not halt automated CI if retained page render is approved.
3. **`NON_BLOCKING` (Advisory):**
   - Benign style lint notices (e.g. anchor link color matches).
   - Minor whitespace adjustments.

---

## 5. Verification & Regression Results

A dedicated test suite `tests/test_kami_boundary.py` was created to verify all Issue #23 contracts:

1. **Structural Diversity Without Imposition:** Verified that two papers with different structures (e.g., 3-section theory paper vs. 5-section system paper) render cleanly with their custom section titles and counts preserved (`test_different_structures_render_without_forcing_identical_chapters`).
2. **Order Preservation:** Verified that section sequence in `narrative_manuscript.json` is preserved 1:1 in HTML and Markdown (`test_renderer_preserves_manuscript_section_order`).
3. **Evidence Citations Survival:** Verified that all `evidence_refs` survive rendering without loss (`test_evidence_citations_survive_rendering`).
4. **Prose Fidelity:** Verified that technical prose authored by the Lead Writer is rendered without rewriting or paraphrasing (`test_prose_not_rewritten_by_renderer`).
5. **Decoupling from Scientific State:** Verified that absence or failure of Kami does not mutate or alter the SHA-256 hash of `narrative_manuscript.json` (`test_absence_of_kami_does_not_mutate_scientific_manuscript`).
6. **Defect Classification:** Verified that broken assets and font defects are correctly classified as `BLOCKING` (`test_kami_audit_warning_classification`).

All 6 tests in `tests/test_kami_boundary.py` passed with 100% success.
