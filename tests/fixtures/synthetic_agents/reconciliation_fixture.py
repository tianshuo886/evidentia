#!/usr/bin/env python3
"""Synthetic Reconciliation Agent Fixture for Evidentia Tier 1 Testing.

Produces schema-valid lens_reconciliation documents wrapped in an
AgentResultEnvelope tagged with execution_kind="SIMULATED_FIXTURE".
"""
import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_common import load_json, schema_validate, sha256

def run_synthetic_reconciliation(task_path_or_root):
    p = Path(task_path_or_root)
    if p.is_file():
        task = load_json(p)
        root = p.parent.parent
    else:
        root = p
        task = {}

    src_pdf = root / 'source/paper.pdf'
    base_model_p = root / 'model/open_reading_model.json'
    src_sha = sha256(src_pdf) if src_pdf.exists() else "UNKNOWN"
    base_sha = sha256(base_model_p) if base_model_p.exists() else "UNKNOWN"

    lenses = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')
    all_findings = []
    for l in lenses:
        lp = root / 'lens' / f'{l}.json'
        if lp.exists():
            data = load_json(lp)
            for f in data.get('findings', []):
                all_findings.append((l, f))

    # Cluster identical or complementary findings
    clusters = []
    assigned = set()
    for i, (lens1, f1) in enumerate(all_findings):
        if i in assigned:
            continue
        members = [f1.get('id', f"L-{lens1}-01")]
        lenses_set = {lens1}
        stmt1 = f1.get('statement', '')
        ev1 = set(f1.get('evidence', []))
        assigned.add(i)

        for j in range(i + 1, len(all_findings)):
            if j in assigned:
                continue
            lens2, f2 = all_findings[j]
            stmt2 = f2.get('statement', '')
            ev2 = set(f2.get('evidence', []))
            # Merge identical statements
            if stmt1.strip().lower() == stmt2.strip().lower():
                members.append(f2.get('id', f"L-{lens2}-01"))
                lenses_set.add(lens2)
                assigned.add(j)

        clusters.append({
            "canonical_statement": stmt1,
            "members": members,
            "supporting_lenses": sorted(lenses_set),
            "evidence": f1.get('evidence', ['p.1']),
            "epistemic": f1.get('epistemic', 'SUPPORTED')
        })

    # Evaluate relations across clusters
    items = []
    for idx, c in enumerate(clusters, 1):
        cid = f"RFC-{idx:02d}"
        stmt = c['canonical_statement']
        rel = "AGREEMENT" if len(c['supporting_lenses']) > 1 else "COMPLEMENTARY"
        req_verif = False
        verif_status = None

        # Check for opposing cluster on shared evidence
        for other_c in clusters:
            if other_c != c and set(c['evidence']) & set(other_c['evidence']):
                other_stmt = other_c['canonical_statement']
                words_f = set(stmt.lower().split())
                has_neg_f = bool(words_f & {'fails', 'fail', 'degrades', 'degrade', 'unstable', 'instability', 'lacks', 'lack', 'weak'})
                has_aff_f = bool(words_f & {'improves', 'improve', 'superior', 'outperforms', 'stable', 'stability', 'guarantees', 'advances', 'effective'})

                words_other = set(other_stmt.lower().split())
                has_neg_other = bool(words_other & {'fails', 'fail', 'degrades', 'degrade', 'unstable', 'instability', 'lacks', 'lack', 'weak'})
                has_aff_other = bool(words_other & {'improves', 'improve', 'superior', 'outperforms', 'stable', 'stability', 'guarantees', 'advances', 'effective'})

                if (has_neg_f and has_aff_other) or (has_aff_f and has_neg_other):
                    rel = "TENSION"
                    req_verif = True
                    verif_status = "SUPPORTED"
                    break

        items.append({
            "id": f"RF{idx:02d}",
            "statement": stmt,
            "status": rel,
            "relation": rel,
            "canonical_statement": stmt,
            "cluster_id": cid,
            "members": c['members'],
            "supporting_lenses": c['supporting_lenses'],
            "evidence": c['evidence'],
            "source": c['evidence'],
            "epistemic_state": c['epistemic'],
            "requires_verification": req_verif,
            "verifier_status": verif_status
        })

    if not items:
        items.append({
            "id": "RF01",
            "statement": "[SIMULATED] Reconciled core methodology performance.",
            "status": "AGREEMENT",
            "relation": "AGREEMENT",
            "canonical_statement": "[SIMULATED] Reconciled core methodology performance.",
            "cluster_id": "RFC-01",
            "members": ["L-author-01"],
            "supporting_lenses": ["author"],
            "evidence": ["p.1"],
            "source": ["p.1"],
            "epistemic_state": "SUPPORTED",
            "requires_verification": False,
            "verifier_status": None
        })

    rec_doc = {
        "schema_version": "1.0",
        "source_sha256": src_sha,
        "base_model_sha256": base_sha,
        "items": items
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    envelope = {
        "task_id": task.get("task_id", "TASK-RECONCILIATION"),
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-fixture-runner",
            "provider": "evidentia-test-suite",
            "model": "synthetic-reconciliation-v1",
            "started_at": now_iso,
            "completed_at": now_iso
        },
        "started_at": now_iso,
        "completed_at": now_iso,
        "result": rec_doc
    }
    return envelope

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: reconciliation_fixture.py <task_path_or_root> [<out_path>]")
    res = run_synthetic_reconciliation(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
    else:
        print(json.dumps(res, indent=2))
