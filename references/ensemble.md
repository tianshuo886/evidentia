# Multi-Model Ensemble Mode

Ensemble Mode enhances Standard Mode with model diversity while preserving invariant scientific contracts.

## Architecture

```text
Host Task Packet (Identical Lens Contract)
      ├── Model Alpha ──► lens_runs/<lens>/run-001.json
      └── Model Beta  ──► lens_runs/<lens>/run-002.json
                                 │
                                 ▼
                     Within-Lens Reconciliation
                                 │
                                 ▼
                     Adaptive Model Escalation
                                 │
                                 ▼
                     Canonical `lens/<lens>.json`
```

## Within-Lens States

- **MODEL_SINGLETON**: A finding identified by only one model.
- **CROSS_MODEL_CONVERGENCE**: Multiple independent models converge on the same finding.
- **MODEL_PARTIAL_AGREEMENT**: Models agree on core premise with varying nuance.
- **MODEL_CONFLICT**: Models produce conflicting interpretations of the same evidence.

## Adaptive Escalation Triggers

Second model passes or localized verification are triggered when:
- High scientific impact
- Epistemic uncertainty (`AMBIGUOUS`, `INSUFFICIENT_EVIDENCE`)
- Unexpected anomalies (`novel_vs_base: true`)
- Weak or unattached evidence
- Critical transfer value for project application

## Host Adapter Boundary

Adapters (such as `adapters/pi/`) handle:
- Model routing
- Task dispatch
- Result collection
- Executor metadata injection

Adapters never own lens definitions, scientific schemas, truth arbitration, or freeze gates.
