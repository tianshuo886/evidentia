# Lens Architecture — 4 Universal Core + 2 Adaptive Specialist Lenses

> Note: Supersedes legacy fixed-six lenses (`author`, `reviewer`, `mechanism`, `builder`, `anomaly`, `counterfactual`). See [lens-v3.md](lens-v3.md) for the full specification.

## Principle

**Lens diversity comes from scientific questions and isolated contexts, not provider switching.**

In Reader v3, all lenses are executed by the canonical strong model with strictly isolated input snapshots under `provenance/lens/<task_id>`. Sibling lenses cannot see each other's outputs or vote.

## 4 Universal Core Lenses
Always executed for every paper:
1. **Argument & Narrative:** How the paper constructs its intellectual case, claims, and narrative structure.
2. **Method & Study Design:** Mathematical definitions, algorithmic choices, and experimental design.
3. **Evidence & Results:** Quantitative benchmarks, baseline comparisons, and ablation margins.
4. **Validity & Boundary:** Underlying assumptions, counterfactual explanations, and epistemic limits.

## 2 Adaptive Specialist Lenses
Dynamically selected by the Lead Reader based on paper characterization:
- **Mechanism & Causality:** Causal chains and physical mechanisms.
- **Reproducibility & Implementation:** Code, hyperparameters, hardware, and replication bounds.
- **Proof Integrity:** Mathematical derivation, theorem steps, and lemma validity.
- **Assumption Sensitivity:** Parameter fragility and distribution shifts.
- **Measurement Integrity:** Sensor physics, instrument calibration, and detection margins.
- **Statistical & Causal Inference:** Observational study designs, confounding, and causal graphs.
- **Taxonomy & Coverage:** Survey categorization and benchmark completeness.

## Cross-Cutting Reasoning Checks
Anomaly detection and counterfactual reasoning are cross-cutting checks embedded within the relevant core and specialist lenses, not permanent separate lens personas.
