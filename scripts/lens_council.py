#!/usr/bin/env python3
"""DEPRECATED: Legacy v1/v2 evidence-grounded Lens Council boundary.

Retained for historical replays only. Superseded by Reader v3 Revision Memo.
Prohibited in canonical Reader v3 scientific execution.
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256, all_ids
from task_protocol import create_reconciliation_task, create_cross_examination_task
from reconciliation_agent import run_reconciliation_agent
from agent_dispatch import is_fixture_enabled, dispatch_agent_task

LENSES = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')
PACKAGE_REL = 'model/frozen_evidence_package.json'
COUNCIL_REL = 'model/lens_council.json'
MAX_CROSS_EXAMINATIONS = 3
MAX_CROSS_EXAMINATION_ROUNDS = 1


def _source_sha(root):
    p = root / 'source/paper.pdf'
    return sha256(p) if p.exists() else 'UNKNOWN_SOURCE_SHA'


def _base(root):
    p = root / 'model/open_reading_model.json'
    if not p.exists():
        p = root / 'model/paper_model.json'
    return p, (sha256(p) if p.exists() else 'UNKNOWN_BASE_SHA')


def build_frozen_evidence_package(root, *, refuse_mutation=True):
    """Build or verify the immutable, shared council input package.

    The package contains source-derived records only.  It intentionally does
    not include lens reports, project context, memory, or prior synthesis.
    """
    root = Path(root)
    base_p, base_sha = _base(root)
    pm = load_json(base_p) if base_p.exists() else {}
    src_sha = _source_sha(root)
    sm = load_json(root / 'model/source_map.json') if (root / 'model/source_map.json').exists() else {}
    inv = load_json(root / 'model/figure_inventory.json') if (root / 'model/figure_inventory.json').exists() else {}
    evidence = []
    for page in sm.get('pages', []):
        n = page.get('number', 1)
        evidence.append({'id': f'p.{n}', 'kind': 'page', 'page': n,
                         'sections': page.get('sections', []),
                         'mentions': page.get('mentions', []),
                         'equations': page.get('equations', [])})
    for item in inv.get('items', []):
        if item.get('id'):
            evidence.append({'id': item['id'], 'kind': item.get('kind', 'source_entity'),
                             'page': item.get('page'), 'label': item.get('paper_label'),
                             'caption': item.get('caption_original'), 'file': item.get('file'),
                             'parsed_cells': item.get('parsed_cells')})
    # Claims and other source model entities are copied as evidence cards, not
    # interpreted by this deterministic layer.
    for key in ('claims', 'observations', 'author_interpretations', 'reader_assessments',
                'experiments', 'methods', 'limitations', 'assumptions', 'unresolved'):
        for item in pm.get(key, []) if isinstance(pm.get(key, []), list) else []:
            if isinstance(item, dict) and item.get('id'):
                evidence.append({'id': item['id'], 'kind': key[:-1] if key.endswith('s') else key,
                                 'record': item})
    # Stable ordering makes the package hash reproducible and audit-friendly.
    evidence.sort(key=lambda x: (str(x.get('id', '')), str(x.get('kind', ''))))
    payload = {
        'schema_version': '1.0',
        'package_id': 'FEP-' + (pm.get('paper_id') or root.name),
        'source_sha256': src_sha,
        'base_model_sha256': base_sha,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'frozen': True,
        'evidence': evidence,
        'allowed_inputs': ['model/frozen_evidence_package.json'],
        'prohibited_context': ['raw_lens_reports', 'project_context', 'apply', 'research_memory']
    }
    # created_at is metadata, not scientific content; preserve it on replay so
    # byte identity is not changed by an ordinary continuation.
    out = root / PACKAGE_REL
    if out.exists():
        old = load_json(out)
        if old.get('source_sha256') != src_sha or old.get('base_model_sha256') != base_sha:
            raise ValueError('frozen evidence package provenance changed; create a new run')
        if refuse_mutation:
            payload['created_at'] = old.get('created_at', payload['created_at'])
            candidate = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + '\n'
            if out.read_text(encoding='utf-8') != candidate:
                raise ValueError('frozen evidence package was modified or source evidence changed')
            return old
    errs = schema_validate(payload, 'frozen_evidence_package')
    if errs:
        raise ValueError(f'frozen evidence package schema validation failed: {errs}')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return payload


def package_sha(root):
    return sha256(Path(root) / PACKAGE_REL)


def snapshot_round1(root):
    """Record the six independent reports and their hashes after Round 1."""
    root = Path(root)
    package = load_json(root / PACKAGE_REL)
    records = []
    missing = []
    out_dir = root / 'council' / 'round1'
    out_dir.mkdir(parents=True, exist_ok=True)
    for lens in LENSES:
        src = root / 'lens' / f'{lens}.json'
        if not src.exists():
            missing.append(lens)
            continue
        data = load_json(src)
        if data.get('source_sha256') != package['source_sha256'] or data.get('base_sha256') != package['base_model_sha256']:
            raise ValueError(f'Round 1 {lens} report is not bound to the frozen evidence package')
        dst = out_dir / f'{lens}.json'
        content = src.read_text(encoding='utf-8')
        if dst.exists() and dst.read_text(encoding='utf-8') != content:
            raise ValueError(f'Round 1 report changed after council snapshot: {lens}')
        dst.write_text(content, encoding='utf-8')
        records.append({'lens': lens, 'artifact': f'council/round1/{lens}.json', 'sha256': sha256(dst)})
    if missing:
        raise ValueError('missing independent Round 1 reports: ' + ', '.join(missing))
    manifest = {'schema_version': '1.0', 'evidence_package_sha256': package_sha(root), 'round': 1,
                'lenses': records, 'independent': True, 'no_majority_voting': True}
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return records


def _legacy_council(root, rec_data):
    """Normalize the pre-#14 reconciliation shape for old workspaces/tests."""
    root = Path(root)
    package = build_frozen_evidence_package(root)
    records = []
    for lens in LENSES:
        p = root / 'lens' / f'{lens}.json'
        if p.exists():
            records.append({'lens': lens, 'artifact': f'lens/{lens}.json', 'sha256': sha256(p)})
    items = rec_data.get('items', []) if isinstance(rec_data, dict) else []
    # Compatibility only: when no Chair artifact exists, carry raw findings
    # into a transient council-shaped view. The synthesis boundary still reads
    # this council view rather than lens/*.json.
    represented = {lens for item in items for lens in item.get('supporting_lenses', [])}
    # Pre-#14 reconciliation fixtures often contain only a partial item list.
    # Add a council singleton for each omitted Round-1 perspective so the
    # compatibility view remains lossless; this branch is never used when a
    # canonical lens_council.json exists.
    for lens in LENSES:
        if lens in represented:
            continue
        p = root / 'lens' / f'{lens}.json'
        if not p.exists():
            continue
        for f in load_json(p).get('findings', []):
            items.append({
                'id': f.get('id', f'LEGACY-{lens}'), 'statement': f.get('statement', ''),
                'canonical_statement': f.get('statement', ''), 'status': 'MODEL_SINGLETON',
                'relation': 'ORTHOGONAL', 'supporting_lenses': [lens],
                'evidence': f.get('evidence', []), 'source': f.get('evidence', []),
                'members': [f.get('id', f'LEGACY-{lens}')],
                'epistemic_state': f.get('epistemic', 'UNRESOLVED')
            })
    return {
        'schema_version': '1.0', 'council_id': 'LC-' + (root.name or 'workspace'),
        'source_sha256': package['source_sha256'], 'base_model_sha256': package['base_model_sha256'],
        'evidence_package_sha256': package_sha(root), 'round1': records,
        'items': items, 'cross_examinations': [],
        'unresolved': [i for i in items if i.get('status') == 'UNRESOLVED' or i.get('epistemic_state') in ('UNRESOLVED', 'AMBIGUOUS', 'INSUFFICIENT_EVIDENCE')],
        'chair_decision': {'mode': 'compatibility_normalization', 'basis': 'evidence_grounded_item_relations'},
        'no_majority_voting': True
    }


def select_cross_examination_requests(chair_payload, *, max_requests=MAX_CROSS_EXAMINATIONS):
    """Return only explicit Chair requests, bounded to one deliberation round.

    A request is a question directed at a concrete council item.  No request
    is inferred from vote counts or from mere disagreement.
    """
    raw = chair_payload.get('cross_examination_requests', []) if isinstance(chair_payload, dict) else []
    if not isinstance(raw, list):
        return []
    selected = []
    seen = set()
    for req in raw:
        if not isinstance(req, dict):
            continue
        target = str(req.get('target_item_id', req.get('item_id', ''))).strip()
        question = str(req.get('question', '')).strip()
        if not target or not question or target in seen:
            continue
        seen.add(target)
        selected.append({
            'target_item_id': target,
            'question': question,
            'challenger_lens': req.get('challenger_lens'),
            'round': 1
        })
        if len(selected) >= max_requests:
            break
    return selected


def execute_bounded_cross_examinations(root, chair_payload, *, fixture=None, replay_dir=None, adapter=None, model=None):
    """Execute only explicit Chair requests, with a hard one-round/three-item bound."""
    root = Path(root)
    records = []
    for req in select_cross_examination_requests(chair_payload):
        task_path = create_cross_examination_task(root, req['target_item_id'], req['question'], req.get('challenger_lens'))
        envelope = dispatch_agent_task(task_path, fixture=fixture, replay_dir=replay_dir, adapter=adapter, model=model)
        if envelope is None:
            records.append({**req, 'status': 'PENDING', 'task_id': task_path.stem})
            continue
        payload = envelope.get('result', {})
        if schema_validate(payload, 'cross_examination'):
            records.append({**req, 'status': 'UNRESOLVED', 'task_id': task_path.stem})
        else:
            records.append(payload)
    return records


def write_council_artifact(root, rec_data, *, round1=None):
    root = Path(root)
    package = build_frozen_evidence_package(root)
    if round1 is None:
        try:
            round1 = snapshot_round1(root)
        except ValueError:
            round1 = []
    council = _legacy_council(root, rec_data)
    council['round1'] = round1 or council['round1']
    # Preserve explicit Chair requests, but never allow an unbounded debate.
    requests = select_cross_examination_requests(rec_data)
    council['cross_examinations'] = [{**r, 'status': 'PENDING'} for r in requests]
    council['chair_decision']['cross_examination_rounds'] = 1 if requests else 0
    council['chair_decision']['cross_examination_limit'] = MAX_CROSS_EXAMINATIONS
    # Keep unresolved states explicit. Never convert unresolved to agreement.
    council['unresolved'] = [i for i in council['items'] if i.get('status') == 'UNRESOLVED' or i.get('epistemic_state') in ('UNRESOLVED', 'AMBIGUOUS', 'INSUFFICIENT_EVIDENCE') or i.get('verifier_status') in ('PENDING', 'PENDING_VERIFICATION')]
    errs = schema_validate(council, 'lens_council')
    if errs:
        raise ValueError(f'lens council schema validation failed: {errs}')
    p = root / COUNCIL_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(council, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return council


def load_council(root, *, allow_compat=True):
    root = Path(root)
    p = root / COUNCIL_REL
    if p.exists():
        council = load_json(p)
        errs = schema_validate(council, 'lens_council')
        if errs:
            raise ValueError(f'invalid lens council artifact: {errs}')
        package = load_json(root / PACKAGE_REL)
        if council['evidence_package_sha256'] != package_sha(root):
            raise ValueError('lens council is not bound to the frozen evidence package')
        return council
    if allow_compat:
        rec_p = root / 'model/lens_reconciliation.json'
        rec = load_json(rec_p) if rec_p.exists() else {'items': []}
        council = _legacy_council(root, rec)
        # Do not write compatibility artifacts here; callers can explicitly
        # persist one. This keeps reads side-effect free.
        return council
    raise FileNotFoundError('model/lens_council.json is required')


def main():
    ap = argparse.ArgumentParser(description='Build/inspect the Evidence-grounded Lens Council boundary')
    ap.add_argument('--out', required=True)
    ap.add_argument('--snapshot', action='store_true')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    root = Path(args.out)
    build_frozen_evidence_package(root)
    records = snapshot_round1(root) if args.snapshot else None
    if args.write:
        rec_p = root / 'model/lens_reconciliation.json'
        rec = load_json(rec_p) if rec_p.exists() else {'items': []}
        write_council_artifact(root, rec, round1=records)
    print(f'OK: Evidence-grounded Lens Council boundary ready at {root / COUNCIL_REL}')

if __name__ == '__main__':
    main()
