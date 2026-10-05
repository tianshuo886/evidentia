# Evidentia Reader Presentation Contract (Issue #23)

## Core Principle

> **Paper decides the story. Evidentia enforces rigor. Kami presents the story.**

The machine model must optimize for correctness and traceability.  
The Lead Writer must author the scientific narrative.  
Kami must optimize exclusively for document presentation and layout typography.  
These are separate responsibilities and must remain distinct.

---

## 1. Explicit Kami Ownership & Non-Ownership Boundary

### Kami Owns (Presentation Only):
- Typography (CJK font family hierarchy, line height, font sizing, font weights).
- Spacing and vertical rhythm (`--rhythm-module`, paragraph margins, block padding).
- Visual hierarchy (chapter title sizes, callout backgrounds, border accents).
- Responsive layout (fluid width on screen, static print layout).
- Figure, table, and equation placement mechanics (inline visual wrapping, LaTeX SVG formatting).
- Captions and callout styling.
- Page break control for print PDF.
- PDF vector export via WeasyPrint / headless Chrome.
- Automated visual QA and layout defect auditing.

### Kami Must NOT Own (Prohibited Responsibilities):
- Which scientific sections exist or how many chapters are rendered.
- The order of scientific sections (section order is strictly determined by the Lead Writer's `narrative_plan.json`).
- Which experiments or figures are decisive.
- Author interpretation vs. reader assessment calibration.
- Formulating new limitations, caveats, or mechanisms.
- Silently dropping or summarizing blocks to fit a visual page budget.
- Injecting generic IMRaD headings (Background, Methods, Results, Discussion).

---

## 2. Dynamic Semantic Manuscript Contract

Renderers receive the already-decided semantic manuscript (`reader/narrative_manuscript.json`, conforming to `schemas/narrative_manuscript.schema.json`).

Blocks are typed purely for visual semantics:
- `paragraph`: Standard body prose.
- `callout`: Highlighted commentary or key takeaway.
- `takeaway`: Core focal point with label.
- `figure`: Bound visual figure with caption, analysis, and asset path.
- `table`: Formatted data table with caption and optional asset crop.
- `equation`: Numbered formula with display LaTeX and source confidence.
- `list`: Compact structured itemization.

Block types are presentation primitives, never mandatory scientific categories.

---

## 3. Warning Classification Policy

Kami automated visual QA (`scripts/kami_adapter.py`) classifies all layout and rendering diagnostics into three strict severity levels:

| Severity Level | Definition | Impact | Examples |
|---|---|---|---|
| **`BLOCKING`** | Scientific corruption, illegible mathematics, missing assets, or content truncation. | **Release-Blocking** (Status fails to `FAIL` / `NEEDS_REVIEW`) | Missing fonts/glyphs (tofu), broken formula syntax, unreadable clipped figures, missing visual crops, asset ID collisions. |
| **`HUMAN_REVIEW_REQUIRED`** | Boundary layout anomalies that require human verification in context. | **Requires Visual Sign-off** | Unusual paragraph widows/orphans, low density on final chapter page, non-standard image aspect ratios. |
| **`NON_BLOCKING`** | Harmless styling notices. | **Advisory Only** | Benign style lint notices (e.g. anchor link color matches), minor whitespace adjustments. |

---

## 4. Immutability & Decoupling Invariant

The absence or execution failure of Kami **never mutates or invalidates the frozen scientific paper object**.
If Kami vector rendering is unavailable in a local environment:
- `narrative_manuscript.json` remains the authoritative, untampered scientific truth.
- HTML and Markdown readers are still generated deterministically.
- PDF generation falls back gracefully to standard headless printing without altering manuscript hashes.
