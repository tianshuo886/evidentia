# Changelog

All notable changes to Evidentia are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-26

### Added
- **True Host-Agent Execution Protocol**: Removed all hardcoded pseudo-agent scientific conclusions (no LENS_FINDINGS_TEMPLATES or manufactured benefits); added automated regression gate against pseudo-agent strings in production code.
- **Frozen Research Memory Subsystem**: Explicit, rebuildable long-term research memory with immutable JSON object storage under `objects/`, SQLite+FTS5 index, paper/project commits, and experiment outcome tracking.
- **Open Reading Memory Firewall**: Technical boundary enforcing zero memory/project leakage during Open Reading and Lens passes (Open Reading contamination rate = 0.0).
- **Two-Stage Apply Design**: Stage A Local Apply (strictly isolated to current frozen paper and project document) and Stage B Memory-Augmented Synthesis (cross-paper context integration).
- **Scientific Artifact Model v2**: Canonical entity model with `origin_type` (SOURCE_EXTRACTION, HOST_AGENT, HUMAN, DETERMINISTIC_DERIVATION) and migration script (`migrate_v1_to_v2.py`).
- **Structured Evidence Bundles**: Core generation of clean evidence surfaces (`evidence_bundles/page-*.json`, `figure-*.json`, `table-*.json`, `equation-*.json`) for Host Agent consumption.
- **Two-Dimensional Capability Status**: Capability tracking now evaluates both `implementation_status` and `validation_status`.

## [0.2.0] - 2026-09-26

### Added
- **Phase B0 Repository Truth**: Synchronized capability matrix with code facts; normalized SKILL.md frontmatter with version and license; migrated schema `$id` to `https://evidentia.dev/schemas/`.
- **Phase B1 Deterministic Core v2**: Upgraded 12-state sequence machine (INGEST through COMPLETE); artifact bundle hashing; per-phase dependency validation; resume/retry granularity with downstream invalidation; hardened freeze gates (uninspected assets, visual review required, unverified critical conflicts).
- **Phase B2 Source Reconstruction v2**: Dual-track extraction with text quality checks (empty extraction, abnormal density, scanned detection); visual track with caption-geometry binding; rich Figure & Table objects; Equation schema (`equation.schema.json`); structured supplement metadata; in-text Mention Linking (`link_mentions.py`).
- **Phase B3 Standard Mode Agent Execution**: Host-agnostic task protocol (`tasks/open_reading.json`, `tasks/lens/*.json`, etc.); unified CLI `evidentia.py` (`run`, `status`, `next`, `validate`, `resume`); standardized executor metadata injection.
- **Phase B4 Semantic Reconciliation & Verifier**: Deterministic pre-clustering into canonical Finding Clusters (`cluster_id`, `members`, `relation`); Evidence-Localized Verifier (`verifier.py`) with strict status vocabulary; strict refusal of majority voting.
- **Phase B5 Multi-Model Ensemble Mode**: Execution configuration (`execution_config.schema.json`); within-lens reconciliation (`within_lens_reconciliation.py`) detecting `CROSS_MODEL_CONVERGENCE`, `MODEL_SINGLETON`, `MODEL_CONFLICT`; Adaptive Model Escalation policy engine (`adaptive_escalation.py`); Pi adapter isolation (`adapters/pi/`).
- **Phase B6 Evidence Atlas & Apply**: Claim-Centric Evidence Atlas with O/I/A separation; bidirectional anchor navigation (Claim <-> Evidence); Reader audit v2 (broken anchor detection, round-trip links); Apply Agent (`apply_agent.py`) with Transfer Unit v2 contracts.
- **Phase B7 Evaluation & Engineering Release**: Benchmark evaluation framework (`evals/`) with metrics for source, grounding, critical reading, and ensemble; three-condition comparison harness (Condition A vs B vs C); Lens x Model Detection Fingerprint matrix; CI workflow configuration.

## [0.1.0] - 2026-09-25

### Added
- Phase A Correctness Foundation: source SHA-256 chain, Open Reading baseline snapshot, 6 independent lens contracts, basic reconciliation, fail-closed freeze check.
