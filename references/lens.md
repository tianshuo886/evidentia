# Lens pass — six independent re-reads (HARD RULE)

One combined "multi-perspective" prompt is forbidden. Each lens re-reads the
frozen base understanding against the source PDF and writes its own file:
`lens/author.json, lens/reviewer.json, lens/mechanism.json, lens/builder.json,
lens/anomaly.json, lens/counterfactual.json`.

Record shape per file:
`{"lens": "<name>", "findings": [{"id": "L-<lens>-01", "statement": "...",
"evidence": ["F06", "E04", "p.9"], "epistemic": "<state>",
"novel_vs_base": true}], "notes": "..."}`.

## Prompts (run separately)

- **author**: What do the authors want believed? Reconstruct their narrative arc
  (problem → hypothesis → design → evidence → conclusion). Flag rhetorical
  jumps: where does persuasion exceed evidence?
- **reviewer**: Where is the evidence weakest? Check controls, confounds, eval
  mismatch, external validation, causal overclaim, ablation sufficiency.
  Name the single weakest link with its evidence IDs.
- **mechanism**: What mechanism truly explains the results? Separate
  correlation / mechanistic / causal / plausible-interpretation. State the
  minimal A→B→C chain and what would falsify it.
- **builder**: What detachable components exist (loss, sampling, preprocessing,
  architecture, diagnostic, eval, visualization, uncertainty, ablation
  protocol)? For each: inputs, outputs, page. No project relevance yet.
- **anomaly**: Real but downplayed anomalies (subgroup flips, condition
  failures, odd trends, off-mainline data). Absent = `"findings": []`, never
  forced. Each needs figure/page proof.
- **counterfactual**: Best alternative explanations if the authors are wrong.
  At least one serious rival account with the evidence it reuses.

## Merge

Dedup by (statement, evidence); keep `from_lens` provenance; resolve conflicts
explicitly in `reader_assessments`; add only genuinely new items to the model.
Six files or the pass did not happen — stop and say so.
