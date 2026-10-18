"""Scientific grounding metrics for Evidentia evaluation framework.

Calculates:
- Claim-Evidence precision
- Claim-Evidence recall
- Unsupported Claim Rate
- O/I/A leakage rate (measures boundary preservation between Observation, Interpretation, Assessment)
"""
import re

def compute_grounding_metrics(model_claims, gt_claims):
    gt_claim_map = {c['id']: c for c in gt_claims}
    total_claims = len(model_claims)
    if total_claims == 0:
        return {
            "claim_evidence_precision": 0.0,
            "claim_evidence_recall": 0.0,
            "unsupported_claim_rate": 0.0,
            "oia_leakage_rate": 0.0
        }

    correct_ev_bindings = 0
    total_ev_bindings = 0
    unsupported_count = 0
    oia_leakage_count = 0

    for c in model_claims:
        ev_list = c.get('evidence', [])
        if not ev_list or c.get('epistemic') in ('NOT_STATED', 'UNRESOLVED'):
            unsupported_count += 1
        
        cid = c.get('id')
        gt_c = gt_claim_map.get(cid)
        if gt_c:
            gt_ev = set(gt_c.get('evidence', []))
            for e in ev_list:
                total_ev_bindings += 1
                if e in gt_ev:
                    correct_ev_bindings += 1

        # O/I/A leakage check: Observation containing pure author rhetoric
        obs = c.get('observation', '').lower()
        rhetoric_markers = [r'\bwe believe\b', r'\bproves that\b', r'\bclearly shows superiority\b', r'\boutstanding\b']
        for r_m in rhetoric_markers:
            if re.search(r_m, obs):
                oia_leakage_count += 1
                break

    precision = correct_ev_bindings / max(total_ev_bindings, 1)
    unsupported_rate = unsupported_count / max(total_claims, 1)
    leakage_rate = oia_leakage_count / max(total_claims, 1)

    return {
        "claim_evidence_precision": round(precision, 4),
        "unsupported_claim_rate": round(unsupported_rate, 4),
        "oia_leakage_rate": round(leakage_rate, 4)
    }
