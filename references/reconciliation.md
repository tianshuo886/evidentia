# Scientific Reconciliation — Editorial Revision Memo

> Note: Supersedes legacy deterministic cluster merging (`merge_lenses.py` / `schemas/finding_cluster.schema.json`).

In Evidentia Reader v3, reconciliation is performed by the **Editorial Revision Memo** (`model/revision_memo.json`, conforming to `schemas/revision_memo.schema.json`).

## Principle: Editorial Synthesis without Voting

Reconciliation operates like a senior scientific editor:
1. Re-reads the Lead Reader draft alongside all 6 isolated specialist lens findings.
2. Identifies agreements, complementary observations, tensions, and contradictions.
3. Issues concrete, structured revision directives (`revisions[]`):
   - **ADD:** Insert a missing proof step, experimental margin, or ablation detail.
   - **REWRITE:** Reconstruct a section whose narrative flow obscures the actual evidence.
   - **CORRECT:** Fix an inaccurate formula, metric, or factual interpretation.
   - **QUALIFY:** Demote an author overclaim to a calibrated evidence-backed assessment.
   - **REMOVE:** Excise unsupported assertions.
   - **VERIFY:** Flag a critical factual ambiguity for localized verification.
4. Preserves genuine scientific tensions and anomalies as `unresolved[]` issues instead of erasing them via majority voting.
5. Approves and binds verified visual assets (`visual_evidence_bindings[]`) for inclusion in the final Reader manuscript.
