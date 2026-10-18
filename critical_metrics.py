"""Critical reading and weakness detection metrics for Evidentia evaluation framework.

Calculates:
- Weakness recall
- Anomaly precision
- Anomaly recall
- Causal overclaim detection rate
"""

def compute_critical_metrics(findings, gt_weaknesses):
    gt_anomaly_ids = {w['id'] for w in gt_weaknesses if w.get('kind') == 'anomaly'}
    gt_overclaim_ids = {w['id'] for w in gt_weaknesses if w.get('kind') == 'causal_overclaim'}
    total_gt = len(gt_weaknesses)

    detected_weaknesses = 0
    detected_anomalies = 0
    detected_overclaims = 0

    for f in findings:
        stmt = f.get('statement', '').lower()
        for w in gt_weaknesses:
            keywords = w.get('keywords', [])
            if any(k.lower() in stmt for k in keywords):
                detected_weaknesses += 1
                if w['id'] in gt_anomaly_ids:
                    detected_anomalies += 1
                if w['id'] in gt_overclaim_ids:
                    detected_overclaims += 1
                break

    weakness_recall = detected_weaknesses / max(total_gt, 1)
    anomaly_recall = detected_anomalies / max(len(gt_anomaly_ids), 1)
    overclaim_detection_rate = detected_overclaims / max(len(gt_overclaim_ids), 1)

    return {
        "weakness_recall": round(weakness_recall, 4),
        "anomaly_recall": round(anomaly_recall, 4),
        "causal_overclaim_detection_rate": round(overclaim_detection_rate, 4)
    }
