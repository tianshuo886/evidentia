# Canonical normalization (Phase-A)

Single-source-of-truth rule — no fact is stored in two places:

- **Claim.*inline strings are REQUIRED short summaries** (`observation`,
  `author_interpretation`, `reader_assessment` on each claim): one-line
  human-readable recap so a claim card renders without a graph join.
- **Top-level arrays are the CANONICAL detail records**:
  `observations[]` (id/text/source/page), `author_interpretations[]`
  (claim/text/page), `reader_assessments[]` (claim/verdict/reason/epistemic).
  Any non-trivial content (page anchors, multi-evidence links, verdicts) MUST
  live here, keyed by claim id — never only inside the claim inline string.
- **Evidence Graph owns relations.** `supported_by / observed_in / tested_by /
  supports / interpreted_as / assessed_as / limited_by / challenged_by /
  contradicts / consistent_with / alternative_to / raises_question /
  derived_from` are expressed as graph edges, not by copying strings.
  `validate_model.py` fails `reconciliation provenance loss` (empty
  `from_lens`) and dangling references; `freeze_check.py` fails dangling
  graph edges.
- **Source Reconstruction vs Interpretation layers:**
  - Source layer owns: `source_map` (pages/sections/equations/mentions),
    `figure_inventory` (caption_original, page, bbox, extraction/binding
    method+confidence, file asset). It never asserts claims.
  - Interpretation layer owns: claims, observations, assessments,
    experiments, methods, assumptions, boundaries, lens findings,
    reconciliation. It may only reference source-layer IDs (+ `p.N` pages).
- **Inventory vs model figures/tables:** inventory is the extraction record
  (what the PDF yielded); `paper_model.figures[]/tables[]` is the
  interpretation record (role/depth/inspection/supports_claims). Freeze
  requires ID-set equality between the two — no silent omission either way.

Rationale (§8): `canonical object` holds content, `Evidence Graph` holds
relationships; string copying is not a relationship mechanism.
