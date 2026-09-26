# Evidence-Localized Verifier

The Verifier evaluates disputed claims, anomalies, and cross-lens contradictions against localized source evidence.

## Core Principle: No Majority Voting

Neither model count nor lens count determines scientific validity:
\[
4 \text{ models agree with Author} \neq \text{Truth}
\]
Truth is determined solely by localized evidence verification.

## Localized Evidence Boundary

The Verifier is NOT fed the entire paper text. Its input is strictly localized to:
- Candidate statement & claim target
- Relevant source IDs
- Figure/Table captions
- Localized visual asset (image file, dimensions, channel validity)
- Parsed table cells / regions
- Surrounding paragraphs and mathematical derivations

## Status Vocabulary

- **SUPPORTED**: Localized evidence directly and strictly confirms the statement.
- **PARTIAL**: Evidence partially corroborates the claim, but key aspects lack local verification.
- **REJECTED**: Localized evidence explicitly refutes, disproves, or contradicts the statement.
- **AMBIGUOUS**: Localized evidence is inconclusive or exhibits conflicting local signals.
- **INSUFFICIENT_EVIDENCE**: The localized evidence snippet lacks the necessary data to evaluate the claim.
