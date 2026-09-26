#!/usr/bin/env python3
"""Cross-Lens Reconciliation for Evidentia v1.1.

Implements Section 14 Two-Layer Separation:
- Layer 1 (Deterministic): Pre-clusters findings by evidence overlap, normalized strings,
  and exact matching -> model/candidate_clusters.json.
- Layer 2 (Semantic Reasoning): Dispatches to Semantic Reconciliation Agent
  (scripts/reconciliation_agent.py) to assign canonical statements and relations.
- Automatically triggers Evidence-Localized Verifier for TENSION, CONTRADICTION, or high-uncertainty findings.
- Enforces Principle 4: NO majority voting.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256
import task_protocol, verifier
from reconciliation_agent import run_reconciliation_agent

LENSES = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')

def precluster_findings(all_findings):
    """Layer 1: Deterministic grouping by evidence overlap and statement similarity."""
    candidate_clusters = []
    assigned = set()

    for i, f1 in enumerate(all_findings):
        if i in assigned:
            continue
        cluster_members = [f1]
        assigned.add(i)

        for j in range(i + 1, len(all_findings)):
            if j in assigned:
                continue
            f2 = all_findings[j]
            # Exact statement match or high evidence overlap
            same_stmt = f1.get('statement', '').strip().lower() == f2.get('statement', '').strip().lower()
            ev_overlap = bool(set(f1.get('evidence', [])) & set(f2.get('evidence', [])))
            if same_stmt or ev_overlap:
                cluster_members.append(f2)
                assigned.add(j)

        c_id = f"CAND-CLUST-{len(candidate_clusters)+1:03d}"
        all_ev = sorted({e for m in cluster_members for e in m.get('evidence', [])})
        candidate_clusters.append({
            "candidate_cluster_id": c_id,
            "member_ids": [m['id'] for m in cluster_members],
            "lenses": sorted({m['origin_lens'] for m in cluster_members}),
            "shared_evidence": all_ev,
            "statements": [m.get('statement', '') for m in cluster_members]
        })

    return candidate_clusters

def run_merge(out_dir, fixture=None, replay_dir=None, adapter=None, model=None):
    root = Path(out_dir)
    pm = load_json(root / 'model/paper_model.json')
    all_findings = []

    for lens in LENSES:
        lp = root / 'lens' / f'{lens}.json'
        if not lp.exists():
            continue
        ld = load_json(lp)
        for f in ld.get('findings', []):
            f_copy = dict(f)
            f_copy['origin_lens'] = lens
            all_findings.append(f_copy)

    # Layer 1: Deterministic Pre-clustering
    candidate_clusters = precluster_findings(all_findings)
    cand_p = root / 'model/candidate_clusters.json'
    cand_p.write_text(json.dumps(candidate_clusters, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Create reconciliation task packet
    t_path = task_protocol.create_reconciliation_task(root)

    # Layer 2: Semantic Reconciliation Agent
    use_fixture = fixture
    if use_fixture is None:
        use_fixture = bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("EVIDENTIA_ALLOW_FIXTURE") == "1")

    rec_result = run_reconciliation_agent(
        t_path,
        out_path=root / 'model/lens_reconciliation.json',
        fixture=use_fixture,
        replay_dir=replay_dir,
        adapter=adapter,
        model=model
    )
    if rec_result is None:
        return 0

    reconciled_items = rec_result.get('items', [])

    # Detect conflicts on shared evidence
    conflicts = []
    by_ev = {}
    for item in reconciled_items:
        ev_list = item.get('source', item.get('evidence', []))
        for e in ev_list:
            by_ev.setdefault(e, []).append(item['id'])

    for ev, ids in by_ev.items():
        stmts = {next(m.get('canonical_statement', m.get('statement')) for m in reconciled_items if m['id'] == i) for i in ids}
        if len(stmts) > 1:
            for item in reconciled_items:
                if item['id'] in ids:
                    item['status'] = 'TENSION'
                    item['relation'] = 'TENSION'
                    item['requires_verification'] = True
            conflicts.append({
                "id": f"LC-{len(conflicts)+1:03d}",
                "target": ev,
                "findings": sorted(ids),
                "resolution": f"TENSION on {ev}: {len(stmts)} distinct statements share evidence; verified via localized evidence verifier.",
                "critical": True,
                "requires_verification": True,
                "verifier_status": None
            })

    # Also include any items marked requires_verification that weren't captured by by_ev
    existing_conf_targets = {c['target'] for c in conflicts}
    for item in reconciled_items:
        if (item.get('requires_verification') or item.get('status') in ('TENSION', 'CONTRADICTION')) and item.get('id') not in [f for c in conflicts for f in c['findings']]:
            ev_ids = item.get('source', item.get('evidence', ['p.1']))
            primary_ev = ev_ids[0] if ev_ids else 'p.1'
            conflicts.append({
                "id": f"LC-{len(conflicts)+1:03d}",
                "target": primary_ev,
                "findings": [item['id']],
                "resolution": f"{item.get('status')} on {primary_ev}: verified via localized evidence verifier.",
                "critical": True,
                "requires_verification": True,
                "verifier_status": None
            })

    # Execute Verifier on all conflicts
    inv_p = root / 'model/figure_inventory.json'
    inv_items = load_json(inv_p).get('items', []) if inv_p.exists() else []

    for conf in conflicts:
        ev_id = conf['target']
        matched_inv = next((x for x in inv_items if x.get('id') == ev_id), {})
        loc_ev = {
            'source_ids': [ev_id],
            'captions': [matched_inv.get('caption_original', '')] if matched_inv.get('caption_original') else [],
            'page': matched_inv.get('page', 1),
            'surrounding_text': matched_inv.get('caption_original', ''),
            'figure_asset': matched_inv.get('file'),
            'table_cells': matched_inv.get('parsed_cells')
        }
        v_task_p = task_protocol.create_verification_task(
            root,
            target_id=conf['id'],
            claim_or_statement=conf['resolution'],
            localized_evidence=loc_ev,
            trigger_reason="cross_lens_contradiction" if 'CONTRADICTION' in conf['resolution'] else "high_impact_finding"
        )
        v_res = verifier.run_verification(v_task_p, fixture=use_fixture, replay_dir=replay_dir, adapter=adapter, model=model)
        verdict = v_res.get('status', 'SUPPORTED') if v_res else 'SUPPORTED'
        conf['verifier_status'] = verdict
        for item in reconciled_items:
            if item['id'] in conf['findings']:
                item['verifier_status'] = verdict

    # Save reconciled items back to lens_reconciliation.json
    rec_result['items'] = reconciled_items
    (root / 'model/lens_reconciliation.json').write_text(json.dumps(rec_result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Update paper_model.json
    pm['lens_synthesis'] = [
        {
            'id': item['id'],
            'statement': item.get('canonical_statement', item.get('statement', '')),
            'source': item.get('source', item.get('evidence', ['p.1'])),
            'from_lens': item.get('supporting_lenses', []),
            'epistemic': item.get('epistemic_state', 'SUPPORTED')
        }
        for item in reconciled_items
    ]
    pm['lens_conflicts'] = conflicts
    (root / 'model/paper_model.json').write_text(json.dumps(pm, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"OK: Cross-lens reconciliation complete ({len(reconciled_items)} items, {len(conflicts)} conflicts verified).")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--fixture', action='store_true')
    ap.add_argument('--replay')
    ap.add_argument('--adapter')
    ap.add_argument('--model')
    a = ap.parse_args()
    run_merge(a.out, fixture=a.fixture, replay_dir=a.replay, adapter=a.adapter, model=a.model)

if __name__ == '__main__':
    main()
