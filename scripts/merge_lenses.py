#!/usr/bin/env python3
"""Cross-Lens Reconciliation for Evidentia v1.1.1.

Implements Section 14 Two-Layer Separation & P0-1 Hardening:
- Layer 1 (Deterministic): Pre-clusters findings by evidence overlap, normalized strings,
  and exact matching -> model/candidate_clusters.json.
  Deterministic code NEVER modifies relation, status, or canonical_statement.
- Layer 2 (Semantic Reasoning): Dispatches to Semantic Reconciliation Agent
  (scripts/reconciliation_agent.py) to assign canonical statements and relations.
- Localized Evidence Verification:
  Only triggered when semantic agent assigns TENSION, CONTRADICTION, or requires_verification=True.
  Verifies actual candidate statements (not generated meta-descriptions).
  If verifier is absent or returns None: verifier_status becomes PENDING_VERIFICATION and workflow
  pauses at WAITING_FOR_VERIFIERS. Zero fail-open to SUPPORTED.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256
import task_protocol, verifier
from reconciliation_agent import run_reconciliation_agent
from agent_dispatch import is_fixture_enabled

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
            "statements": [m.get('statement', '') for m in cluster_members],
            "distinct_statement_strings": len({m.get('statement', '').strip().lower() for m in cluster_members}) > 1,
            "candidate_for_semantic_review": len(cluster_members) > 1
        })

    return candidate_clusters

def run_merge(out_dir, fixture=None, replay_dir=None, adapter=None, model=None, verifier_fixture=None):
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

    # Layer 1: Deterministic Pre-clustering (Diagnostic only, no semantic mutation)
    candidate_clusters = precluster_findings(all_findings)
    cand_p = root / 'model/candidate_clusters.json'
    cand_p.write_text(json.dumps(candidate_clusters, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Create reconciliation task packet
    t_path = task_protocol.create_reconciliation_task(root)

    # Layer 2: Semantic Reconciliation Agent
    use_fixture = is_fixture_enabled(fixture)

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

    # Filter items requiring verification based purely on Semantic Agent judgment
    items_needing_verif = [
        it for it in reconciled_items
        if it.get('requires_verification') is True or it.get('status') in ('TENSION', 'CONTRADICTION')
    ]

    conflicts = []
    inv_p = root / 'model/figure_inventory.json'
    inv_items = load_json(inv_p).get('items', []) if inv_p.exists() else []

    all_verifications_completed = True
    use_verifier_fixture = use_fixture if verifier_fixture is None else is_fixture_enabled(verifier_fixture)

    for idx, item in enumerate(items_needing_verif, 1):
        cid = f"LC-{idx:03d}"
        ev_ids = item.get('source', item.get('evidence', ['p.1']))
        primary_ev = ev_ids[0] if ev_ids else 'p.1'
        matched_inv = next((x for x in inv_items if x.get('id') == primary_ev), {})

        # P0-1 Hardening: Statement verified is the actual candidate scientific claim
        candidate_claim = item.get('canonical_statement', item.get('statement', ''))

        loc_ev = {
            'source_ids': ev_ids,
            'captions': [matched_inv.get('caption_original', '')] if matched_inv.get('caption_original') else [],
            'page': matched_inv.get('page', 1),
            'surrounding_text': matched_inv.get('caption_original', ''),
            'figure_asset': matched_inv.get('file'),
            'table_cells': matched_inv.get('parsed_cells')
        }
        v_task_p = task_protocol.create_verification_task(
            root,
            target_id=cid,
            claim_or_statement=candidate_claim,
            localized_evidence=loc_ev,
            trigger_reason="cross_lens_contradiction" if item.get('status') == 'CONTRADICTION' else "high_impact_finding"
        )
        v_res = verifier.run_verification(v_task_p, fixture=use_verifier_fixture, replay_dir=replay_dir, adapter=adapter, model=model)

        # P0-1 Hardening: Fail-closed verification verdict. NEVER default to SUPPORTED!
        if v_res is None or v_res.get('status') in (None, 'PENDING', 'PENDING_VERIFICATION', 'UNRESOLVED'):
            verdict = 'PENDING_VERIFICATION'
            all_verifications_completed = False
        else:
            verdict = v_res.get('status')

        item['verifier_status'] = verdict

        conflicts.append({
            "id": cid,
            "target": primary_ev,
            "findings": item.get('members', [item['id']]),
            "statement": candidate_claim,
            "resolution": f"{item.get('status')} on {primary_ev}: evaluation status {verdict}.",
            "critical": True,
            "requires_verification": True,
            "verifier_status": verdict
        })

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

    if not all_verifications_completed:
        rs_p = root / 'run_state.json'
        if rs_p.exists():
            rs = load_json(rs_p)
            rs['phase'] = 'WAITING_FOR_VERIFIERS'
            rs_p.write_text(json.dumps(rs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f"[WAITING_FOR_VERIFIERS] Verification required for {len(items_needing_verif)} items. Results pending.")
        return 0

    print(f"OK: Cross-lens reconciliation complete ({len(reconciled_items)} items, {len(conflicts)} conflicts verified).")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--fixture', action='store_true', default=None)
    ap.add_argument('--no-fixture', dest='fixture', action='store_false')
    ap.add_argument('--replay')
    ap.add_argument('--adapter')
    ap.add_argument('--model')
    a = ap.parse_args()
    run_merge(a.out, fixture=a.fixture, replay_dir=a.replay, adapter=a.adapter, model=a.model)

if __name__ == '__main__':
    main()
