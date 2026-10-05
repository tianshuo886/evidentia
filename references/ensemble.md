# Model Architecture & Multi-Model Boundary

> Note: Supersedes legacy automatic within-lens ensemble polling. See [reader-v3.md](reader-v3.md) for the canonical specification.

## Principle: Single Strong Model with Context Isolation

Evidentia Reader v3 establishes that scientific diversity arises from:
1. Distinct, rigorous scientific questions (4 Core + 2 Adaptive Lenses).
2. Physically isolated input boundaries (`provenance/lens/<task_id>`).
3. Cryptographic execution manifests proving zero crosstalk.

Switching models across lenses by default introduces noise, stylistic inconsistency, and loss of shared context without increasing scientific validity. A single approved strong model (e.g. `antigravity/gemini-3.8-flash [magpie]` with High Reasoning Profile) is the canonical engine for all scientific reasoning stages.

## Targeted Second-Model Verification (Optional)

A second independent model is deployed **only when specifically triggered**:
- Material, unresolved scientific contradictions in the Revision Memo.
- High-risk physical measurements or mathematical proofs requiring external scrutiny.
- Formal robustness benchmarking across models.

Majority voting across models is strictly prohibited. When models disagree, the disagreement is recorded as an epistemic tension (`UNRESOLVED` / `AMBIGUOUS`), never averaged away.
