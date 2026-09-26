# Evidentia Epistemic States Vocabulary

In Evidentia, scientific uncertainty is treated as first-class empirical data, never flattened into binary true/false.

## Canonical Epistemic States

| State | Definition | Example / Trigger |
|---|---|---|
| **VERIFIED** | The assertion has been independently verified against localized source evidence by the Verifier. | Numeric accuracy in Table 1 matches claimed improvement. |
| **SUPPORTED** | The assertion is directly substantiated by in-paper evidence (figures, tables, derivations). | Observation is directly visible in Figure 2. |
| **PARTIAL** | The assertion is partially supported, but key conditions, ablations, or controls are omitted. | Trend holds on benchmark A, but was not evaluated on benchmark B. |
| **NOT_STATED** | The paper implies a conclusion but omits explicit empirical data or formal derivation. | Hyperparameter sensitivity is not documented in the text. |
| **AMBIGUOUS** | The evidence is contradictory, poorly specified, or susceptible to multiple conflicting interpretations. | Divergent loss curves under different initialization seeds. |
| **INSUFFICIENT_EVIDENCE** | The available data is insufficient to establish or refute the claim. | Insufficient sample size or unstated statistical test. |
| **MODEL_UNCERTAIN** | The Host Agent identifies multiple plausible hypotheses and cannot resolve certainty. | Ambiguous wording in experimental setup. |
| **NEEDS_SUPPLEMENT** | Verification requires inspecting supplementary materials or external appendices. | Full proof or dataset license deferred to supplement. |
| **NEEDS_CITATION_TRACE** | The claim relies on external literature citations rather than in-paper data. | Baseline accuracy numbers cited from previous publications. |
| **UNRESOLVED** | Cross-lens tension or contradiction remains unverified or unresolved. | Reviewer lens and Author lens disagree on failure mode. |
| **REJECTED** | The assertion is explicitly disproved or refuted by localized evidence. | Ablation demonstrates loss term has negligible effect. |
