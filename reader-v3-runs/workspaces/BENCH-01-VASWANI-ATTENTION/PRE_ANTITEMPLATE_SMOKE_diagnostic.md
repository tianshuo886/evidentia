# BENCH-01 — PRE_ANTITEMPLATE_SMOKE diagnostic

## Run identity and integrity

- Paper: *Attention Is All You Need*.
- Continuation code: `reader-reset-v3 @ 22dcbcb5c9d935f7518a61c9457aa68a25801ae5`.
- Run class: `PRE_ANTITEMPLATE_SMOKE`.
- Source SHA256: `bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697`.
- Historical cloud commit `ca313e8c40ce2fe7ffea9e4fb31d31234500c5dd`: unavailable from local/GitHub refs.
- Historical archive: unavailable.
- Historical BENCH-01 Lead Reader and Direct-AI artifacts: unavailable; this workspace was reconstructed from the full arXiv PDF. Historical PDF byte identity is unproven.
- Source-grounded Reader integrity: **PASS** (`reader/source_grounded_integrity.json`; zero v3 integrity errors and zero HTML/Markdown/PDF semantic-parity errors).
- Schema validation: **PASS**, 40 checked payload/envelope artifacts (`validation_summary.json`).

## Completed artifacts

- Full 15-page source PDF, source pages, source map and figure inventory.
- Nine semantic visual page payloads and envelopes for F01–F05/T01–T04; all material visual bindings are source-hash bound. The duplicate `T02-p8` candidate was rejected rather than published as a second table.
- Lead Reader payload and envelope: `model/paper_understanding_draft.json`, `agent_runs/TASK-V3-LEAD-READING/run-001.json`.
- Six Lens payloads and envelopes: four core plus `proof_integrity` and `assumption_sensitivity` specialists.
- Revision Memo and envelope.
- Lead Writer manuscript and envelope.
- Rendered Reader: HTML, Markdown and PDF; Evidence Atlas HTML/JSON.
- Kami audit: `reader/kami_audit.json`.
- Real Direct-AI continuation baseline and pair evaluation.
- Required command executed: `python scripts/reader_v3_benchmark.py evaluate --out reader-v3-runs/workspaces/BENCH-01-VASWANI-ATTENTION`.

### Execution caveat

The configured delegated worker profile rejected `openai-codex/gpt-6.1-sol`, and repeated delegated fan-outs failed with connection/timeouts. To finish the diagnostic chain, the active `openai-codex/gpt-6.1-sol` parent authored the six role-separated Lens passes sequentially. No Lens read another Lens output, but independent context isolation is **not independently verified**. This is recorded in `lens_outputs_direct_execution_note.json` and is a release limitation, not hidden.

## Where Reader v3 is better than Direct-AI

1. **Evidence grounding and auditability.** Reader v3 binds prose to F01–F05/T01–T04/page IDs, source SHA, visual task payloads, envelopes and the Evidence Atlas. Direct-AI has only a source-bound narrative.
2. **Figure/table interpretation.** Reader v3 explains what each visual answers, what it shows and what it cannot establish. It distinguishes Table 1's asymptotic comparison from Table 2's BLEU/FLOP results, and preserves Table 4's 93.3 comparator rather than flattening parsing into an unconditional win.
3. **Boundary analysis.** Reader v3 explicitly separates O(1) sequential operations from O(n²d) attention computation, identifies FLOPs as estimates, and limits appendix attention plots to qualitative examples.
4. **Scientific completeness.** The structured run retains architecture asymmetry, masking, ablations, parsing transfer, long-sequence limits and qualitative interpretability caveats that are compressed in Direct-AI.
5. **Visual provenance.** The full-page semantic pass rejected a duplicate table candidate and generated verified crops rather than trusting geometry alone.

## Where Reader v3 is worse

1. **Reading economy.** Direct-AI is shorter and can be a better first-pass briefing. Reader v3's repeated visual explanations and caveats increase cognitive load.
2. **Presentation density.** Kami flagged sparse pages 11–13 and 41% trailing whitespace on page 11. This is a real rendering defect, not a scientific defect.
3. **Typography.** Kami reports CJK body text falling back to Songti-SC rather than the Kami primary font. Placeholder/style/orphan/visual commands otherwise returned success, but the font warning remains.
4. **Provenance discontinuity.** The continuation Reader is more auditable than the unavailable historical run, but cannot honestly claim continuity with the original cloud output.
5. **Lens execution independence.** The outputs are valid and role-separated, but this continuation could not prove six separately isolated model contexts after the worker harness failed.

## Narrative losses

- The Reader's formal chapter progression is clear, but the direct report's compact “problem → mechanism → result → limits” rhythm is more efficient.
- The generated Reader may over-explain the same calibration point (quadratic attention cost, qualitative visualization limits) in both narrative and callout blocks.
- The historical Lead Reader content mentioned by the operator could not be recovered, so no byte-level or sentence-level preservation comparison is possible.

## Scientific omissions or residual gaps

- No repeated-seed uncertainty, confidence intervals, or statistical significance analysis is available in the source.
- No matched-budget modern baseline or controlled wall-clock benchmark beyond the paper's estimated FLOPs is added.
- Long-sequence behavior and restricted-attention alternatives remain future work in the source.
- The attention visualizations are not a systematic interpretability evaluation.
- The continuation report does not recover any historical cloud metadata or prior Direct-AI output.

## Figure/table interpretation quality

- **F01:** correctly binds the complete encoder/decoder architecture and explains decoder cross-attention and future-token masking.
- **F02:** correctly binds both panels and explains scaling and multi-head parallel projections.
- **T01:** correctly preserves the O(1) sequential/path result together with the O(n²d) cost caveat.
- **T02:** correctly preserves base/big and En-De/En-Fr distinctions and the estimated-FLOP status.
- **T03:** correctly interprets head/key dimension, capacity, dropout and positional-encoding sensitivity.
- **T04:** correctly reports 91.3/92.7 and notes that 93.3 remains in the listed comparison.
- **F03–F05:** correctly treats attention-head patterns as qualitative examples, preserving “apparently/seems” calibration.
- Visual provenance is strong for this continuation: 9 page tasks, 9 envelopes, 9 applied verified bindings, and one duplicate rejected.

## Template-bias symptoms

Observed in this pre-anti-template run:

- The narrative repeatedly uses a common “what it shows / supports / limits” rhythm even when a visual could be integrated more naturally into the paper's argument.
- Every specialist pass is forced into the same finding/action vocabulary, which risks making the scientific report resemble a workflow checklist.
- The manuscript uses standardized callout/takeaway blocks for calibration; these are useful here but could become boilerplate on papers whose argument is not table-centered.
- The six-role inventory is useful for coverage but can encourage adding critique sections even when a paper's own structure would not call for them.

## Useful Lens corrections

- Argument/Narrative: keep asymptotic motivation separate from empirical proof and move visualizations after the performance argument.
- Method/Study Design: explain decoder cross-attention and causal masking, not only the encoder stack.
- Evidence/Results: preserve exact base/big and En-De/En-Fr values; retain the non-winning parsing comparator.
- Validity/Boundary: qualify state-of-the-art language, FLOP estimates, quadratic cost and selected protocols.
- Proof Integrity: prevent asymptotic statements from becoming universal runtime claims; preserve cautious caption language.
- Assumption Sensitivity: surface sequence-length, model-capacity, dropout, positional-encoding and decoding dependencies.

## Unsupported or overconfident claims

No material unsupported claim was found by the source-grounded integrity pass. The main risks were actively qualified:

- “O(1)” is not presented as universal end-to-end speed.
- “State of the art” is bound to the paper's reported tasks/comparisons.
- Attention figures are not presented as proof of general interpretability.
- The continuation does not claim to have recovered historical model provenance.

## Provenance and integrity failures

- Historical cloud commit/archive unavailable.
- Historical Lead Reader and Direct-AI artifacts unavailable.
- Historical source byte identity cannot be established.
- Delegated context-isolation requirement was not independently satisfied because the worker harness repeatedly failed; parent-direct role passes are explicitly marked.
- These are diagnostic limitations and block release evidence; they are not silently repaired or relabeled.

## Rendering/Kami defects

- Kami placeholder/style/orphan checks: pass.
- Kami visual command: completed, with manual page-review checklist still required.
- CJK font fallback: Songti-SC warning.
- Density: page 11 warning (41% trailing whitespace); pages 12–13 sparse (78% and 71% trailing whitespace).
- No orphan headings were reported.
- These defects should be tracked separately from scientific correctness.

## Explicit Issue #22 targets

1. Make narrative structure genuinely paper-derived; do not impose repeated “supports/limits” cards or mandatory chapter rhythms.
2. Allow specialist findings to disappear into the prose when they do not change the scientific story; preserve them in the Atlas instead.
3. Make visual blocks adapt to the visual's argumentative role instead of always rendering the same explanatory fields.
4. Keep calibration and uncertainty statements, but avoid repeating identical caveat language across chapters.
5. Preserve the evidence/provenance gains while preventing the Lens/action vocabulary from leaking into human narrative.
6. Add a first-class provenance state for reconstructed continuation runs whose historical source/model artifacts are unavailable.
7. Add a release gate that distinguishes schema validity from verified independent-model execution and human visual QA.
8. Improve CJK typography and sparse-page layout before treating visual QA as release evidence.

## Overall verdict

**BENCH-01 is a completed diagnostic continuation artifact set, but not final Issue #19 release evidence.** Reader v3 shows concrete added value over the continuation Direct-AI baseline in evidence grounding, figure/table interpretation, boundary analysis and provenance. It is worse in brevity, typography/layout polish and verified execution independence. The run remains explicitly `PRE_ANTITEMPLATE_SMOKE` and stops here; no Issue #22, Issue #20, PR #21 or master work was performed.
