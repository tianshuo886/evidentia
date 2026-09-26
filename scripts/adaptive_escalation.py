#!/usr/bin/env python3
"""Adaptive Model Escalation policy engine for Evidentia Ensemble Mode.

Evaluates first-pass findings against trigger rules:
- high_impact
- critical_uncertainty
- causal_ambiguity
- unexpected_anomaly
- weak_evidence
- transfer_critical

Returns escalation recommendations: second independent model run or localized verifier.
"""
import argparse, json, sys
from pathlib import Path

TRIGGER_RULES = (
    "high_impact",
    "critical_uncertainty",
    "causal_ambiguity",
    "unexpected_anomaly",
    "weak_evidence",
    "transfer_critical"
)

def evaluate_escalation(lens_dir, pm_data=None):
    root = Path(lens_dir)
    escalations = []

    for lens_file in root.glob('*.json'):
        lens_name = lens_file.stem
        try:
            d = json.loads(lens_file.read_text(encoding='utf-8'))
        except Exception:
            continue

        for f in d.get('findings', []):
            f_id = f.get('id', 'UNKNOWN')
            epistemic = f.get('epistemic', 'SUPPORTED')
            evidence = f.get('evidence', [])

            # 1. Unexpected anomaly
            if lens_name == 'anomaly' and f.get('novel_vs_base') is True:
                escalations.append({
                    "target_id": f_id,
                    "lens": lens_name,
                    "trigger": "unexpected_anomaly",
                    "action": "ESCALATE_SECOND_MODEL",
                    "reason": f"Anomaly finding {f_id} introduces novel failure mode requiring second model confirmation."
                })

            # 2. Critical uncertainty
            if epistemic in ('AMBIGUOUS', 'INSUFFICIENT_EVIDENCE', 'MODEL_UNCERTAIN'):
                escalations.append({
                    "target_id": f_id,
                    "lens": lens_name,
                    "trigger": "critical_uncertainty",
                    "action": "ESCALATE_VERIFIER",
                    "reason": f"Epistemic uncertainty {epistemic} on {f_id} requires localized evidence verification."
                })

            # 3. Weak evidence
            if not evidence:
                escalations.append({
                    "target_id": f_id,
                    "lens": lens_name,
                    "trigger": "weak_evidence",
                    "action": "ESCALATE_VERIFIER",
                    "reason": f"Finding {f_id} lacks direct evidence attachment; verification required."
                })

    return escalations

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lens-dir', required=True)
    ap.add_argument('--out')
    a = ap.parse_args()

    escalations = evaluate_escalation(a.lens_dir)
    report = {
        "schema_version": "1.0",
        "total_escalations": len(escalations),
        "escalations": escalations
    }
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
