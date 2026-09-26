# Evaluation Framework & Benchmark Architecture

Evidentia strictly separates engineering correctness from scientific validation through a multi-tier evaluation system.

## Evaluation Tiers

### Tier 0 — Deterministic Correctness (CI Gate)
- Validates schemas against Draft 2020-12
- Enforces SHA-256 content-address chain and fail-closed freeze gates
- Enforces artifact bundle tamper detection and resume safety
- Runs on every pull request

### Tier 1 — Synthetic Integration
- Tests workflow plumbing and state transitions from raw synthetic PDFs to frozen reader
- Validates CLI orchestration without live LLM calls

### Tier 2 — Recorded Real-Agent Replay
- Replays sanitized, recorded Host Agent results to verify contract compatibility and schema stability

### Tier 3 — Live Agent Integration
- Evaluates live host models on benchmark corpus papers

### Tier 4 — Human-Annotated Scientific Benchmark
- Compares Condition A (Single-pass reading), Condition B (Evidentia Standard), and Condition C (Evidentia Ensemble) against ground-truth human annotations

## Key Metric Formulations

### Scientific Grounding
- **Claim-Evidence Precision**: Fraction of claim evidence attachments verified in ground truth.
- **Unsupported Claim Rate**: Fraction of claims lacking direct evidence citations.
- **O/I/A Leakage Rate**: Fraction of Observation blocks containing author rhetoric or unverified reader assessment.

### Critical Reading
- **Weakness Recall**: Fraction of real paper weaknesses captured across Reviewer, Mechanism, and Builder passes.
- **Anomaly Recall**: Fraction of real anomalies identified by the Anomaly pass.
- **Causal Overclaim Detection**: Identification of unsupported causal language.

### Memory Integrity
- **Open Reading Contamination Rate**: Fraction of Open Reading passes exposed to memory context (**Critical Invariant: MUST BE 0.0**).
- **Provenance Completeness**: Percentage of memory items retaining full commit and source evidence chains.
