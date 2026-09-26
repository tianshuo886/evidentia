# P0 Contract Audit

This document is the contract audit baseline for the repository. It compares what the public README/SKILL and design references claim with the schemas, executable scripts, and tests that actually exist.

Run it from a checked-out repository with:

```bash
python scripts/contract_audit.py --out .
```

For a paper run, write the machine-readable copy into its model directory:

```bash
python scripts/contract_audit.py --out paper-output --write
```

## Status vocabulary

- **IMPLEMENTED** — an executable path and contract exist, with a meaningful gate or test.
- **PARTIAL** — a schema or skeleton exists, but an important execution or verification step remains external/manual.
- **DECLARED_ONLY** — the concept is documented but has no usable contract implementation.
- **MISSING** — the concept is not implemented and should not be promised as available.
- **DEPRECATED** — retained only for compatibility and should not be extended.

## Baseline matrix (updated Phase B7 Release)

| Capability | Area | Status | Evidence / limitation |
|---|---|---:|---|
| `source_reconstruction` | Core | IMPLEMENTED | Dual-track text/visual extraction, caption-geometry binding, structured table/equation objects, supplement metadata, and mention linking implemented and validated. |
| `source_lock` | Core | IMPLEMENTED | SOURCE_SHA256 chain closed across source_map, inventory, paper_model, evidence_graph, lens runs, and manifest; freeze fails closed on mismatch. |
| `open_reading_base` | Core | IMPLEMENTED | `snapshot_baseline.py` freezes `open_reading_model.json` + `open_reading_manifest.json` with hashes and contract versions. |
| `baseline_lock` | Core | IMPLEMENTED | `check_lenses.py` and `freeze_check.py` refuse lenses with stale `base_sha256` or mutated baseline. |
| `standard_agent_execution` | Execution | IMPLEMENTED | `evidentia.py` unified CLI and `task_protocol.py` create structured tasks and orchestrate the host-neutral loop. |
| `independent_lens_execution` | Execution | IMPLEMENTED | `task_protocol` and `lens_runner` create six independent task packets with executor metadata and contract validation. |
| `deterministic_pre_reconciliation` | Core | IMPLEMENTED | `merge_lenses.py` converges identical findings, preserves all `supporting_lenses`, and records TENSION. |
| `semantic_cross_lens_reconciliation` | Core | IMPLEMENTED | Deterministic pre-clustering into Finding Clusters with canonical relations (AGREEMENT, TENSION, etc.) and verification triggers implemented. |
| `evidence_verifier` | Verification | IMPLEMENTED | `verifier.py` evaluates candidate claims/conflicts against localized evidence without majority voting, enforcing schemas and status vocabulary. |
| `canonical_paper_model` | Core | IMPLEMENTED | Schema and freeze gates enforce O/I/A separation, coverage audits, and immutable paper truth without mutation during Apply. |
| `evidence_graph` | Core | IMPLEMENTED | `build_graph.py` connects claims, evidence, figures, and tables, with source SHA locking. |
| `freeze_integrity` | Core | IMPLEMENTED | Freeze gates check source hash, baseline hash, complete 6-lens set, dangling IDs, and tamper rejection. |
| `reader_evidence_atlas` | Presentation | IMPLEMENTED | Claim-centric Evidence Atlas HTML reader with O/I/A grid, bidirectional return links, and broken anchor auditing implemented. |
| `reader_visual_qa` | Presentation | IMPLEMENTED | Kami adapter and reader audit v2 check presentation boundaries, image assets, and layout completeness. |
| `project_apply_execution` | Apply | IMPLEMENTED | `apply_agent.py` executes project gap mapping, contextual reread, and refuses unfrozen paper models. |
| `research_delta` | Apply | IMPLEMENTED | Research Delta schema with Transfer Unit v2 contracts (assumptions, constraints, contracts) generated and validated. |
| `ensemble_execution` | Ensemble | IMPLEMENTED | `execution_config.schema.json`, Pi adapter, and multi-model dispatch architecture implemented. |
| `within_lens_reconciliation` | Ensemble | IMPLEMENTED | `within_lens_reconciliation.py` resolves multiple runs into canonical lens outputs with convergence/singleton/conflict tags. |
| `adaptive_model_escalation` | Ensemble | IMPLEMENTED | `adaptive_escalation.py` evaluates findings against explicit trigger policies (novel anomalies, uncertainty, weak evidence). |
| `frozen_research_memory` | Memory | IMPLEMENTED | `memory_manager.py` implements immutable JSON storage under `objects/`, rebuildable SQLite+FTS5 index, paper/project commits, experiment outcomes, and Open Reading firewall. |
| `evaluation_framework` | Evaluation | IMPLEMENTED | `evals/` directory with 3-condition benchmark comparison (Single-pass vs Standard vs Ensemble), metrics, and detection fingerprints. |
| `ci_release_engineering` | Engineering | IMPLEMENTED | `.github/workflows/ci.yml`, `pyproject.toml`, `LICENSE`, `CHANGELOG.md`, and `CONTRIBUTING.md` created and verified. |

The machine-readable source of truth is `capability_matrix.json` (generated by `scripts/contract_audit.py`). This matrix is intentionally conservative: documentation is not counted as implementation.

## P0 exit criteria

P0 is complete when README, SKILL, references, schemas, scripts and tests use the same status vocabulary and no public document presents PARTIAL or MISSING capabilities as end-to-end functionality. P1 starts with a model-independent execution adapter protocol (the `open_reading_base` contract is now implemented).
