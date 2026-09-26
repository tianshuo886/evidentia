# Semantic Cross-Lens Reconciliation

Reconciliation integrates findings from the six independent Lens rereads into coherent, structured knowledge without erasing scientific tension.

## Two-Phase Pipeline

### 1. Deterministic Pre-Clustering (`merge_lenses.py`)
Deterministic code groups candidate findings by:
- Exact duplicate statements and shared evidence
- Shared source objects (e.g. both commenting on Figure 2)
- Potential polarity opposition (one affirming, one critiquing)

Deterministic code does NOT decide final scientific truth.

### 2. Semantic Relation Classification
Findings are categorized into canonical relations:
- **AGREEMENT**: Independent lenses converge on identical or corroborating findings.
- **COMPLEMENTARY**: Lenses reveal distinct, non-overlapping facets of the same evidence.
- **PARTIAL_AGREEMENT**: Lenses agree on core mechanism but differ on scope or assumptions.
- **TENSION**: Lenses observe divergent trends on the same evidence.
- **CONTRADICTION**: Lenses state diametrically opposing conclusions.
- **ORTHOGONAL**: Findings address unrelated aspects.
- **UNRESOLVED**: Ambiguous or insufficient evidence prevents classification.

## Finding Cluster Model

Canonical `Finding Cluster` objects (`schemas/finding_cluster.schema.json`) capture:
- `cluster_id`
- `member_finding_ids`
- `relation`
- `canonical_statement` (Agent-formulated)
- `supporting_lenses`
- `evidence_ids`
- `epistemic_state`
- `verification_required`
