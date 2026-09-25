---
name: paper-read
description: Deep-read a must-read paper PDF into a frozen Paper Model, Evidence Graph, and unified Kami reader (reader.html/pdf + notes.md) with original figures and claim-to-evidence links. Use when the user runs /paper-read <pdf> --out <dir> or /paper-apply --paper <dir> --project <doc>. Project context stays invisible during reading and loads only in apply. Not for paper search/triage (use paper-acquire) or multi-paper surveys.
argument-hint: "<pdf> --out <directory> [--supplement ...] | apply --paper <dir> --project <doc> [--focus ...]"
---

# paper-read · Paper Research OS (single-paper)

You turn one must-read paper into a long-lived research object:
`PDF → Paper Model → Evidence Graph → Unified Reader → Research Delta → Memory`.

## Two entries, one skill

```bash
/paper-read <paper.pdf> --out <directory> [--supplement <supp.pdf>] [--lang zh]
/paper-apply --paper <paper-output-dir> --project <project-main-doc> [--focus <section>]
```

- `/paper-read` never loads project context. Violation = restart the read.
- `/paper-apply` loads the frozen model plus exactly one project doc. Never rewrites frozen facts silently.
- Triage ("is it worth reading") is out of scope. The input paper is mandatory.

## Output contract (`--out` required, no default)

`--out` is mandatory. If missing, stop and ask. Never invent a directory.

```text
<out>/
├── source/paper.pdf [+ supplement.pdf]
├── model/paper_model.json + evidence_graph.json + manifest.json
├── assets/figures/figNN.png
├── lens/*.json (one per lens, see below)
├── apply/<project-name>/research_delta.json (apply only)
├── reader/reader.html + reader.pdf + render_ir.json
└── notes.md
```

## Phase 0 — INGEST

1. Verify `paper.pdf` readable; record pages, metadata, text-layer status.
2. Inventory supplements; record what was supplied vs missing. Missing = mark, never guess.
3. Run the figure extractor before reading prose:
   `python <skill>/scripts/extract_figs.py --pdf <paper.pdf> --out <out>/assets/figures --inventory <out>/model/figure_inventory.json`
4. Keep large embedded figures as-is; re-crop排版 figures from 300 dpi renders.
   Scanned PDF fallback: full-page 200 dpi render + manual crop boxes; unextractable caption = `"caption_original": null, "caption_status": "NOT_EXTRACTED"`.

## Phase 1 — SOURCE RECONSTRUCTION

Build the evidence surface before interpreting: Page / Section / Figure / Table /
Caption / Equation / Experiment / in-text citation links. Every figure/table gets
`id (F01…), paper_label, page, caption_original, source_location, surrounding_sections`.
Original figures are the only primary visual evidence. AI-drawn schematics are
allowed only as labeled `explanation` figures, never as evidence replacements.

## Phase 2 — OPEN READING (project invisible)

Allowed inputs: paper, supplement, bibliographic metadata. Forbidden: project
README, plans, repos, chats, goals, memory. First answer: what is this paper's
own skeleton (`natural_structure`)? Then map to the canonical model. Type
(`method/empirical/theory/dataset/benchmark/review/hybrid`) changes emphasis
only, never coverage: every figure/table is still inspected.

Figure depth is tiered, not skipped: `critical→deep, supporting→normal,
context/diagnostic→light`. Record role + depth per figure.

## Claim discipline (non-negotiable)

- Separate `observation` (data says) / `author_interpretation` (authors claim) /
  `reader_assessment` (you judge the link). Never collapse them.
- Every important claim gets `Cnn`, experiments `Enn`, assumptions `Ann`,
  boundaries `Bnn`, open questions `Qnn`; link `supported_by/depends_on/
  challenged_by/limited_by`.
- Epistemic states allowed: VERIFIED, SUPPORTED, PARTIAL, NOT_STATED,
  AMBIGUOUS, INSUFFICIENT_EVIDENCE, MODEL_UNCERTAIN, NEEDS_SUPPLEMENT,
  NEEDS_CITATION_TRACE. `UNRESOLVED` is a legal final state.
- `IN_PAPER_EVIDENCE` vs `CITED_EVIDENCE` stay separate. Cited claims never
  become this paper's facts without a chase.

## Multi-Lens Pass — HARD RULE (independent passes)

One combined "multi-perspective summary" prompt is forbidden. Each of the six
lenses below is an independent re-read of the frozen base understanding against
the source PDF. Run them one at a time (or in parallel subagents), each writing
its own file. Then merge/dedup into the model.

```text
lens/author.json         Author lens:      what do the authors want believed? (narrative)
lens/reviewer.json       Reviewer lens:    where is the evidence weakest? (controls, confounds, ablations)
lens/mechanism.json      Mechanism lens:   correlation vs mechanistic vs causal — what truly explains it?
lens/builder.json        Builder lens:      detachable transferable components (loss, sampling, eval, diagnostic…)
lens/anomaly.json        Anomaly lens:      real but downplayed anomalies. Absent = empty list, never forced.
lens/counterfactual.json Counterfactual:   best alternative explanations if the authors are wrong.
```

Each `lens/<name>.json` holds `{"lens": "<name>", "findings": [{"id": "L-<lens>-01", "statement": "...", "evidence": ["F06", "E04", "p.9"], "epistemic": "SUPPORTED|…", "novel_vs_base": true/false}], "notes": "..."}`.
Merge step: dedup by evidence+statement, keep provenance (`from_lens`), resolve
conflicts explicitly, add only genuinely new items to `paper_model.json`.
If you cannot produce six files, the pass did not happen — say so and stop.

## Freeze + audit

Run `python <skill>/scripts/freeze_check.py --out <out>`; it verifies figure/
table coverage, claim grounding, unresolved list, and writes `manifest.json`
(sha256 of pdf/model/graph, counts, status FROZEN). Fix failures by fixing the
model, never by loosening the check. `/paper-apply` refuses unfrozen dirs.

## Render (Kami is presentation, not truth)

Adapt `paper_model.json` → Paper Reader Adapter → `render_ir.json`; use Kami only for typography, MathJax and print tooling. The Paper Reader information architecture is owned here and is never reshaped to fit Kami Long Doc tokens. Emit `reader/reader.html`, print
`reader/reader.pdf` (Part I Understanding, Part II Evidence Atlas, Part III
Delta if present), and `notes.md` (5-minute fallback: one-line model, Q/A,
argument chain, decisive findings, key figures, weakest link, boundary, open
questions, side findings). Verify: no `{{…}}` left, every referenced figure file
exists, IDs intact, unresolved visible, delta links resolve. Spot-check rendered
pages visually (figure clarity, caption binding, no clipping).

Reader shows PAPER and PROJECT DELTA in one file, visually distinct (ink-blue
vs olive accents), data-isolated. Every delta links back (`[C07][Fig.6b]` →
claim/figure anchors).

## /paper-apply — contextual re-read

1. Load frozen model + one project doc (+ optional `--focus`). Re-scan the
   paper for evidence the first read underweighted. New relevance/transfer
   notes allowed; frozen observations immutable (real errors → explicit
   `paper_model_revision`, never silent edits).
2. Split findings into Side Findings (off-mainline real phenomena) vs Portable
   Components; pack components into Transfer Units (mechanism, measurement,
   loss, eval, preprocessing, ablation, failure mode, negative result) with
   verdicts DIRECT/ADAPT/INSPIRATION_ONLY/REJECT + specific reason codes
   (different_data_regime, different_scale, insufficient_evidence,
   already_covered, cost_exceeds_value, … — never bare "data differs").
3. Research Delta types: New Evidence, Changed Belief, New Unknown, Portable
   Method, Invalidated/Deprioritized Plan (deleting a bad experiment counts as
   success), New Experiment. No forced novelty: `NO_NEW_ACTIONABLE_EXPERIMENT`
   is legal; repackaging existing plans as new is forbidden.
4. Each proposed experiment carries Source, Delta vs current plan, Hypothesis,
   Integration point, Cost, Risk, Decision Value (what success AND failure each
   change — mandatory).
5. Write `apply/<project>/research_delta.json`, update the unified reader,
   re-verify links.

## Invariants

A: facts independent of project. B: claims traceable to evidence. C: originals
never replaced by prose. D: observation/interpretation/assessment separate.
E: project reasoning never mutates frozen facts. F: HTML primary, PDF snapshot.
G: Kami presents, never decides. H: natural structure before canonical index.
I: uncertainty is legitimate output. J: machine-reusable IDs from v1.

## Forbidden

No abstract-only "deep reads"; no cherry-picked figures without an inventory;
no AI inference stated as paper fact; no cited-work results counted as this
paper's evidence; no project context in first read; no forced side findings,
anomalies, or experiments; no silent frozen-model edits; no science reshaped
for templates; no pretty PDF without structured data; no full-reader dumps in
chat — report counts, paths, and anomalies only.

## Complete executable workflow

Use `scripts/pipeline.py read` to initialize the source-only run. The state machine in `scripts/phase.py` prevents skipping Source Reconstruction, Open Reading, independent Lens outputs, Freeze, or Reader rendering. `scripts/lens_runner.py` creates six separate task packets; it must never be replaced by one multi-perspective prompt.

Use `scripts/pipeline.py apply` only after `scripts/verify_frozen.py` succeeds. It copies exactly one project document into `apply/<project>/`, creates a Project Gap Map and an empty Research Delta contract, and keeps the frozen Paper Model outside the mutable apply workspace. Fill the delta from a contextual reread, then run `scripts/validate_delta.py`.

The repository contains no paper-specific fixture. Any paper, including a regression paper, is an external input to the skill.
