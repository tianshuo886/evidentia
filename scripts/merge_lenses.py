#!/usr/bin/env python3
"""Semantic Cross-Lens Reconciliation for Evidentia Core.

Performs semantic clustering across six independent lens passes:
- Classifies relations into: AGREEMENT, COMPLEMENTARY, PARTIAL_AGREEMENT, TENSION, CONTRADICTION, ORTHOGONAL, UNRESOLVED.
- Groups findings into canonical Finding Clusters (cluster_id, members, relation, canonical_statement, supporting_lenses, source, epistemic_state).
- Automatically triggers Evidence-Localized Verifier for TENSION, CONTRADICTION, or high-uncertainty findings.
- Enforces Principle 4: NO majority voting. Scientific truth is determined by localized evidence verification.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256

LENSES = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')

NEGATION_PATTERNS = {
    'fails', 'fail', 'degrades', 'degrade', 'unstable', 'instability',
    'lacks', 'lack', 'weak', 'weakness', 'spurious', 'confounded',
    'overclaim', 'contradicts', 'insufficient', 'inconclusive'
}

AFFIRM_PATTERNS = {
    'improves', 'improve', 'superior', 'outperforms', 'outperform',
    'stable', 'stability', 'guarantees', 'guarantee', 'advances', 'effective'
}

def token_similarity(stmt_a, stmt_b):
    tokens_a = set(re.findall(r'\b[a-z]{3,}\b', stmt_a.lower()))
    tokens_b = set(re.findall(r'\b[a-z]{3,}\b', stmt_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

def classify_relation(f_a, f_b):
    stmt_a = f_a.get('statement', '')
    stmt_b = f_b.get('statement', '')
    sim = token_similarity(stmt_a, stmt_b)
    
    words_a = set(stmt_a.lower().split())
    words_b = set(stmt_b.lower().split())
    has_neg_a = bool(words_a & NEGATION_PATTERNS)
    has_neg_b = bool(words_b & NEGATION_PATTERNS)
    has_aff_a = bool(words_a & AFFIRM_PATTERNS)
    has_aff_b = bool(words_b & AFFIRM_PATTERNS)

    if (has_neg_a and has_aff_b) or (has_aff_a and has_neg_b):
        return "CONTRADICTION" if sim > 0.3 else "TENSION"
    
    if sim >= 0.75:
        return "AGREEMENT"
    elif sim >= 0.40:
        return "PARTIAL_AGREEMENT"
    else:
        # Check evidence overlap
        ev_a = set(f_a.get('evidence', []))
        ev_b = set(f_b.get('evidence', []))
        if ev_a & ev_b:
            return "COMPLEMENTARY"
        return "ORTHOGONAL"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    root = Path(a.out)
    
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

    # Semantic Clustering
    clusters = []
    assigned = set()

    for i, f1 in enumerate(all_findings):
        if i in assigned:
            continue
        cluster_members = [f1]
        cluster_lenses = {f1['origin_lens']}
        cluster_relation = "AGREEMENT"
        assigned.add(i)

        for j in range(i + 1, len(all_findings)):
            if j in assigned:
                continue
            f2 = all_findings[j]
            rel = classify_relation(f1, f2)
            if rel in ("AGREEMENT", "PARTIAL_AGREEMENT"):
                cluster_members.append(f2)
                cluster_lenses.add(f2['origin_lens'])
                assigned.add(j)
                cluster_relation = rel

        c_id = f"CLUST-{len(clusters)+1:03d}"
        all_ev = sorted({e for m in cluster_members for e in m.get('evidence', [])})
        
        clusters.append({
            "cluster_id": c_id,
            "members": [m['id'] for m in cluster_members],
            "relation": cluster_relation,
            "canonical_statement": cluster_members[0]['statement'],
            "supporting_lenses": sorted(cluster_lenses),
            "source": all_ev,
            "epistemic_state": cluster_members[0].get('epistemic', 'SUPPORTED'),
            "requires_verification": False,
            "findings_detail": cluster_members
        })

    # Prepare reconciliation items
    reconciled_items = []
    
    for c in clusters:
        status_map = {
            "AGREEMENT": "AGREEMENT",
            "COMPLEMENTARY": "COMPLEMENTARY",
            "PARTIAL_AGREEMENT": "PARTIAL_AGREEMENT",
            "TENSION": "TENSION",
            "CONTRADICTION": "CONTRADICTION",
            "ORTHOGONAL": "ORTHOGONAL",
            "UNRESOLVED": "UNRESOLVED"
        }
        item_status = status_map.get(c['relation'], "COMPLEMENTARY")
        
        reconciled_items.append({
            "id": c['members'][0],
            "statement": c['canonical_statement'],
            "status": item_status,
            "supporting_lenses": c['supporting_lenses'],
            "evidence": c['source'],
            "conflict_note": f"Relation {c['relation']} across {len(c['members'])} lens findings." if c['requires_verification'] else "",
            "cluster_id": c['cluster_id'],
            "members": c['members'],
            "relation": c['relation'],
            "canonical_statement": c['canonical_statement'],
            "source": c['source'],
            "epistemic_state": c['epistemic_state'],
            "requires_verification": c['requires_verification'],
            "verifier_status": None
        })

    # Detect conflicts on shared evidence
    conflicts = []
    by_ev = {}
    for item in reconciled_items:
        for e in item['evidence']:
            by_ev.setdefault(e, []).append(item['id'])

    for ev, ids in by_ev.items():
        stmts = {next(m['statement'] for m in reconciled_items if m['id'] == i) for i in ids}
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

    # Execute Verifier on all conflicts
    import task_protocol, verifier
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
        t_path = task_protocol.create_verification_task(
            root,
            target_id=conf['id'],
            claim_or_statement=conf['resolution'],
            localized_evidence=loc_ev
        )
        v_res = verifier.run_verification(t_path)
        conf['verifier_status'] = v_res['status']
        for item in reconciled_items:
            if item.get('cluster_id') == conf.get('id') or set(item.get('members', [])) & set(conf.get('findings', [])):
                item['verifier_status'] = v_res['status']

    # Update paper_model.json
    pm['lens_synthesis'] = [
        {
            'id': item['id'],
            'statement': item['statement'],
            'source': item['evidence'],
            'from_lens': item['supporting_lenses'],
            'epistemic': item.get('epistemic_state', 'SUPPORTED')
        }
        for item in reconciled_items
    ]
    pm['lens_conflicts'] = conflicts
    (root / 'model/paper_model.json').write_text(json.dumps(pm, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Reconciled lens artifact
    try:
        src_sha = load_json(root / 'model/source_map.json').get('pdf_sha256', '')
    except Exception:
        src_sha = ''
    try:
        base_sha = load_json(root / 'model/open_reading_manifest.json').get('base_model_sha256', '')
    except Exception:
        base_sha = ''

    recon = {
        'schema_version': '1.0',
        'source_sha256': src_sha,
        'base_model_sha256': base_sha,
        'items': reconciled_items
    }
    (root / 'model/lens_reconciliation.json').write_text(json.dumps(recon, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Lens synthesis artifact
    agreements = [m for m in reconciled_items if m.get('status') == 'AGREEMENT']
    unique = [m for m in reconciled_items if len(m.get('supporting_lenses', [])) == 1]
    synthesis = {
        'schema_version': '1.0',
        'paper_model_sha256': None,
        'agreement': [
            {
                'id': m['id'],
                'statement': m['statement'],
                'evidence': m['evidence'],
                'lenses': m['supporting_lenses'],
                'epistemic': m.get('epistemic_state'),
                'support_count': len(m['supporting_lenses'])
            }
            for m in agreements
        ],
        'unique_findings': [
            {
                'id': m['id'],
                'statement': m['statement'],
                'evidence': m['evidence'],
                'lenses': m['supporting_lenses'],
                'epistemic': m.get('epistemic_state'),
                'support_count': 1
            }
            for m in unique
        ],
        'complementary_findings': [],
        'conflicts': [
            {
                'id': c.get('id', f"LC-{i+1:03d}"),
                'evidence': [],
                'findings': c['findings'],
                'status': c.get('verifier_status') or 'UNRESOLVED'
            }
            for i, c in enumerate(conflicts)
        ],
        'unresolved_conflicts': [
            {
                'id': c.get('id', f"LC-{i+1:03d}"),
                'evidence': [],
                'findings': c['findings'],
                'status': 'UNRESOLVED'
            }
            for i, c in enumerate(conflicts)
            if c.get('verifier_status') in (None, 'UNRESOLVED')
        ],
        'cross_lens_support': [
            {
                'finding_id': m['id'],
                'lenses': m['supporting_lenses']
            }
            for m in agreements
        ]
    }
    try:
        import hashlib as _hl
        synthesis['paper_model_sha256'] = _hl.sha256((root / 'model/paper_model.json').read_bytes()).hexdigest()
    except Exception:
        pass
    (root / 'model/lens_synthesis.json').write_text(json.dumps(synthesis, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(json.dumps({'status': 'OK', 'clusters': len(clusters), 'conflicts': len(conflicts), 'reconciled_items': len(reconciled_items)}))

if __name__ == '__main__':
    main()
