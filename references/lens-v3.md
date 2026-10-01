# Reader v3 Lens Architecture

## Principle

**Lens diversity comes from questions, not models.**

A Lens is a scientific reading responsibility. An Agent is one isolated execution
of that responsibility. A Model is the underlying reasoning engine. A Harness is
the execution environment. These are deliberately separate concepts.

Default Reader v3 execution uses the active harness and the same strong model for
all Lens passes. Independence is created by isolated contexts and separate task
contracts, not by switching providers.

## Universal Core Lenses

1. **Argument & Narrative**
2. **Method & Study Design**
3. **Evidence & Results**
4. **Validity & Boundary**

These four are always present.

## Adaptive Specialist Lenses

Two specialist lenses are selected from paper type/content. Initial registry:

- Mechanism & Causality
- Reproducibility & Implementation
- Proof Integrity
- Assumption Sensitivity
- Measurement Integrity
- Statistical & Causal Inference
- Taxonomy & Coverage

## Cross-cutting reasoning checks

Anomaly detection and counterfactual reasoning are not permanent Lens identities.
Relevant lenses must use them as checks:

- Evidence & Results checks anomalous/off-trend observations.
- Validity & Boundary checks alternative explanations.
- Mechanism & Causality uses falsification and competing mechanisms.

## Multi-model policy

A second model is optional and targeted only when:
- a material scientific conflict remains unresolved;
- a high-risk fact, figure or equation needs independent verification;
- robustness is being benchmarked explicitly.

No majority voting is allowed.
