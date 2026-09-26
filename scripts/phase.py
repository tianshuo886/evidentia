#!/usr/bin/env python3
"""Advance the explicit Evidentia state machine with artifact bundle hashing, dependency graph, and resume/retry.

Phase promotion requires:
- Dependency graph satisfaction (source lock, baseline lock, lens execution, etc.)
- Artifact bundles exist and schemas validate
- Hash bundles recorded in run_state.json
- Tamper detection across all previously recorded bundles
- Resume / Retry and invalidation support

Formal sequence:
INGEST -> SOURCE_RECONSTRUCTION -> SOURCE_LOCK -> OPEN_READING -> BASELINE_LOCK
-> LENS_EXECUTION -> RECONCILIATION -> VERIFICATION -> FINAL_MODEL -> FREEZE
-> RENDER -> COMPLETE
"""
import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone

STANDARD_ORDER = {
    'INGEST': 'SOURCE_RECONSTRUCTION',
    'SOURCE_RECONSTRUCTION': 'SOURCE_LOCK',
    'SOURCE_LOCK': 'OPEN_READING',
    'OPEN_READING': 'BASELINE_LOCK',
    'BASELINE_LOCK': 'LENS_EXECUTION',
    'LENS_EXECUTION': 'RECONCILIATION',
    'RECONCILIATION': 'VERIFICATION',
    'VERIFICATION': 'FINAL_MODEL',
    'FINAL_MODEL': 'FREEZE',
    'FREEZE': 'RENDER',
    'RENDER': 'COMPLETE',
}

# Compatibility aliases
COMPAT_NEXT = {
    # If starting from baseline lock with legacy LENS target
    ('BASELINE_LOCK', 'LENS'): True,
    ('LENS', 'RECONCILIATION'): True,
    ('LENS', 'FREEZE'): True,
    ('LENS_EXECUTION', 'FREEZE'): True,
    ('FINAL_MODEL', 'FREEZE'): True,
}

APPLY_ORDER = {
    'APPLY_INIT': 'PROJECT_CONTEXT',
    'PROJECT_CONTEXT': 'CONTEXTUAL_REREAD',
    'CONTEXTUAL_REREAD': 'DELTA_VALIDATION',
    'DELTA_VALIDATION': 'APPLY_COMPLETE',
}

PHASE_BUNDLES = {
    'SOURCE_RECONSTRUCTION': [
        'model/source_map.json',
        'model/figure_inventory.json',
    ],
    'SOURCE_LOCK': [
        'model/source_map.json',
        'model/figure_inventory.json',
        'source/paper.pdf',
    ],
    'OPEN_READING': [
        'model/paper_model.json',
    ],
    'BASELINE_LOCK': [
        'model/open_reading_model.json',
        'model/open_reading_manifest.json',
    ],
    'LENS_EXECUTION': [
        'lens/author.json',
        'lens/reviewer.json',
        'lens/mechanism.json',
        'lens/builder.json',
        'lens/anomaly.json',
        'lens/counterfactual.json',
    ],
    'LENS': [
        'lens/author.json',
        'lens/reviewer.json',
        'lens/mechanism.json',
        'lens/builder.json',
        'lens/anomaly.json',
        'lens/counterfactual.json',
    ],
    'RECONCILIATION': [
        'model/lens_reconciliation.json',
    ],
    'VERIFICATION': [],
    'FINAL_MODEL': [
        'model/paper_model.json',
        'model/evidence_graph.json',
    ],
    'FREEZE': [
        'model/manifest.json',
    ],
    'RENDER': [
        'reader/reader.html',
    ],
}

LENSES = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')

def fail(msg):
    raise SystemExit(f'REFUSED: {msg}')

def get_bundle_hashes(root, phase):
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_common import sha256
    files = PHASE_BUNDLES.get(phase, [])
    bundle = {}
    for rel in files:
        fp = root / rel
        if fp.exists():
            bundle[rel] = sha256(fp)
    return bundle

def check_preexisting_bundles(root, s, next_phase=None):
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_common import sha256
    for phase, entry in (s.get('artifact_hashes') or {}).items():
        if isinstance(entry, dict):
            for rel, expected_h in entry.items():
                if phase == 'OPEN_READING' and rel == 'model/paper_model.json' and (
                    next_phase in ('RECONCILIATION', 'FINAL_MODEL', 'FREEZE', 'RENDER', 'COMPLETE')
                    or 'RECONCILIATION' in s.get('completed_phases', [])
                    or s.get('phase') in ('RECONCILIATION', 'FINAL_MODEL', 'FREEZE', 'RENDER', 'COMPLETE')
                ):
                    continue
                fp = root / rel
                if not fp.exists():
                    fail(f'previously completed artifact bundle missing since phase {phase} ({rel}); resume refused')
                actual_h = sha256(fp)
                if actual_h != expected_h:
                    fail(f'previously completed artifact bundle changed since phase {phase} ({rel}); resume refused')
        elif isinstance(entry, str):
            legacy_gates = {
                'SOURCE_RECONSTRUCTION': root / 'model/source_map.json',
                'OPEN_READING': root / 'model/paper_model.json',
                'LENS': root / 'lens/counterfactual.json',
                'LENS_EXECUTION': root / 'lens/counterfactual.json',
                'FREEZE': root / 'model/manifest.json',
                'RENDER': root / 'reader/reader.html'
            }
            g = legacy_gates.get(phase)
            if g is not None:
                if not g.exists():
                    fail(f'previously completed artifact missing since phase {phase} ({g}); resume refused')
                if sha256(g) != entry:
                    fail(f'previously completed artifact changed since phase {phase} ({g}); resume refused')

def handle_status(root, s):
    current = s.get('phase', 'UNKNOWN')
    expected = STANDARD_ORDER.get(current, 'COMPLETE')
    print(json.dumps({
        "phase": current,
        "next": expected,
        "completed_phases": s.get('completed_phases', []),
        "source_sha256": s.get('source_sha256'),
        "base_sha256": s.get('base_sha256'),
    }, indent=2))
    return 0

def handle_next(root, s):
    current = s.get('phase', 'UNKNOWN')
    expected = STANDARD_ORDER.get(current, 'COMPLETE')
    print(expected)
    return 0

def handle_retry(root, s, target):
    target = target.lower().strip()
    if target in LENSES:
        # Retry only this specific lens
        lp = root / 'lens' / f'{target}.json'
        if lp.exists():
            lp.unlink()
        print(f"OK: reset {target} lens for retry; other lenses preserved")
        return 0
    elif target in STANDARD_ORDER or target in ('LENS', 'LENS_EXECUTION'):
        # Reset phase
        print(f"OK: phase {target} ready for retry")
        return 0
    else:
        fail(f"unknown retry target: {target}")

def handle_resume(root, s):
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_common import load_json, sha256
    
    # 1. Check source PDF
    pdf_p = root / 'source/paper.pdf'
    if pdf_p.exists():
        actual_src = sha256(pdf_p)
        if s.get('source_sha256') and s['source_sha256'] != actual_src:
            # Source changed! Invalidate downstream
            s['completed_phases'] = []
            s['phase'] = 'INGEST'
            fail('source/paper.pdf changed since run start; all downstream artifacts invalidated')
            
    # 2. Check baseline manifest
    orman_p = root / 'model/open_reading_manifest.json'
    if orman_p.exists():
        try:
            om = load_json(orman_p)
            base_expected = om.get('base_model_sha256')
            if s.get('base_sha256') and s['base_sha256'] != base_expected:
                # Baseline changed! Invalidate downstream
                s['completed_phases'] = [p for p in s.get('completed_phases', []) if p in ('INGEST', 'SOURCE_RECONSTRUCTION', 'SOURCE_LOCK', 'OPEN_READING')]
                fail('baseline hash changed; downstream lens artifacts invalidated')
            contract_v = om.get('lens_contract_version')
            if s.get('lens_contract_version') and s['lens_contract_version'] != contract_v:
                # Contract version changed! Invalidate downstream
                s['completed_phases'] = [p for p in s.get('completed_phases', []) if p in ('INGEST', 'SOURCE_RECONSTRUCTION', 'SOURCE_LOCK', 'OPEN_READING')]
                fail('lens_contract_version changed; downstream lens artifacts invalidated')
        except Exception as e:
            fail(f'unparseable open_reading_manifest.json: {e}')
            
    # 3. Check bundles
    check_preexisting_bundles(root, s)
    current = s.get('phase')
    expected = STANDARD_ORDER.get(current, 'COMPLETE')
    print(f"Resuming at phase {current}. Next: {expected}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--complete')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--next', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--retry')
    a = ap.parse_args()
    
    root = Path(a.out)
    p = root / 'run_state.json'
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_common import load_json, schema_validate, sha256, validate_run_state

    if not p.exists():
        fail(f'missing {p}')
    errs = validate_run_state(p)
    if errs:
        fail(f'run_state.json schema-invalid: {errs}')
    s = load_json(p)
    
    if a.status:
        return handle_status(root, s)
    if a.next:
        return handle_next(root, s)
    if a.retry:
        return handle_retry(root, s, a.retry)
    if a.resume:
        return handle_resume(root, s)

    if not a.complete:
        fail('must specify --complete <phase>, --status, --next, --resume, or --retry')

    current = s['phase']
    expected = STANDARD_ORDER.get(current)
    
    # Check preexisting artifact bundle hashes first (tamper detection)
    check_preexisting_bundles(root, s, next_phase=a.complete)

    # Check source SHA stability
    if (root / 'source/paper.pdf').exists():
        actual_src = sha256(root / 'source/paper.pdf')
        if s.get('source_sha256') and s['source_sha256'] != actual_src:
            fail('source/paper.pdf changed since run start (resume with changed source refused)')

    # Check transition validity
    valid_step = (expected == a.complete) or COMPAT_NEXT.get((current, a.complete), False)
    if not valid_step:
        fail(f'expected next phase {expected}, got {a.complete}')

    # Validate specific phase gates
    if a.complete == 'SOURCE_RECONSTRUCTION':
        sm = root / 'model/source_map.json'
        fi = root / 'model/figure_inventory.json'
        if not sm.exists() or not fi.exists():
            fail('missing source reconstruction artifacts (model/source_map.json or model/figure_inventory.json)')
        errs = schema_validate(load_json(sm), 'source_map') + schema_validate(load_json(fi), 'figure_inventory')
        if errs:
            fail(f'source reconstruction schema-invalid: {errs}')

    elif a.complete == 'SOURCE_LOCK':
        sm = root / 'model/source_map.json'
        fi = root / 'model/figure_inventory.json'
        pdf = root / 'source/paper.pdf'
        if not sm.exists() or not fi.exists() or not pdf.exists():
            fail('missing artifacts for source lock')
        actual_src = sha256(pdf)
        sm_sha = load_json(sm).get('pdf_sha256')
        fi_sha = load_json(fi).get('source_sha256')
        if sm_sha != actual_src:
            fail('source_map.pdf_sha256 mismatch actual PDF')
        if fi_sha != actual_src:
            fail('figure_inventory.source_sha256 mismatch actual PDF')

    elif a.complete == 'OPEN_READING':
        # Must have completed SOURCE_LOCK
        if current != 'SOURCE_LOCK' and 'SOURCE_LOCK' not in s.get('completed_phases', []):
            fail('SOURCE_LOCK phase is required before OPEN_READING')
        pm_p = root / 'model/paper_model.json'
        if not pm_p.exists():
            fail('missing model/paper_model.json')
        errs = schema_validate(load_json(pm_p), 'paper_model')
        if errs:
            fail(f'open reading model schema-invalid: {errs}')

    elif a.complete == 'BASELINE_LOCK':
        orm_p = root / 'model/open_reading_manifest.json'
        base_p = root / 'model/open_reading_model.json'
        if not orm_p.exists() or not base_p.exists():
            fail('missing baseline lock artifacts (model/open_reading_manifest.json or model/open_reading_model.json)')
        errs = schema_validate(load_json(orm_p), 'open_reading_manifest')
        if errs:
            fail(f'open reading manifest schema-invalid: {errs}')
        om = load_json(orm_p)
        actual_base_h = sha256(base_p)
        if om.get('base_model_sha256') != actual_base_h:
            fail('open_reading_model.json hash does not match open_reading_manifest.base_model_sha256')
        s['base_sha256'] = actual_base_h
        if om.get('lens_contract_version'):
            s['lens_contract_version'] = om['lens_contract_version']

    elif a.complete in ('LENS_EXECUTION', 'LENS'):
        # Must have completed BASELINE_LOCK
        if current != 'BASELINE_LOCK' and 'BASELINE_LOCK' not in s.get('completed_phases', []):
            fail('BASELINE_LOCK phase is required before LENS_EXECUTION')
        import subprocess
        if subprocess.run([sys.executable, str(Path(__file__).with_name('check_lenses.py')), '--out', str(root)]).returncode != 0:
            fail('Lens gate failed')

    elif a.complete == 'RECONCILIATION':
        rec_p = root / 'model/lens_reconciliation.json'
        if not rec_p.exists():
            fail('missing model/lens_reconciliation.json (run merge_lenses.py)')
        errs = schema_validate(load_json(rec_p), 'lens_reconciliation')
        if errs:
            fail(f'lens reconciliation schema-invalid: {errs}')

    elif a.complete == 'FINAL_MODEL':
        pm_p = root / 'model/paper_model.json'
        eg_p = root / 'model/evidence_graph.json'
        if not pm_p.exists() or not eg_p.exists():
            fail('missing model/paper_model.json or model/evidence_graph.json')
        errs = schema_validate(load_json(pm_p), 'paper_model') + schema_validate(load_json(eg_p), 'evidence_graph')
        if errs:
            fail(f'final model or evidence graph schema-invalid: {errs}')

    elif a.complete == 'FREEZE':
        man_p = root / 'model/manifest.json'
        if not man_p.exists():
            fail('missing model/manifest.json')
        manifest = load_json(man_p)
        errs = schema_validate(manifest, 'manifest')
        if errs:
            fail(f'manifest schema-invalid: {errs}')
        if manifest.get('status') != 'FROZEN':
            fail('manifest is not FROZEN')
        if (root / 'source/paper.pdf').exists():
            if manifest.get('source_sha256') != sha256(root / 'source/paper.pdf'):
                fail('manifest source_sha256 != actual source/paper.pdf')
        if s.get('base_sha256') and manifest.get('base_model_sha256') != s['base_sha256']:
            fail('manifest base_model_sha256 != run_state baseline')
        import subprocess
        if subprocess.run([sys.executable, str(Path(__file__).with_name('verify_frozen.py')), '--out', str(root)]).returncode != 0:
            fail('frozen hash re-verification failed')

    elif a.complete == 'RENDER':
        import subprocess
        if subprocess.run([sys.executable, str(Path(__file__).with_name('reader_audit.py')), '--out', str(root)]).returncode != 0:
            fail('Reader audit failed')

    # Record history and update state
    s['history'].append({'phase': current, 'status': 'completed', 'at': datetime.now(timezone.utc).isoformat()})
    s['phase'] = a.complete
    if current not in s.get('completed_phases', []):
        s.setdefault('completed_phases', []).append(current)
    s['history'].append({'phase': a.complete, 'status': 'started', 'at': datetime.now(timezone.utc).isoformat()})
    
    # Record bundle hashes for resume validation
    bundle = get_bundle_hashes(root, a.complete)
    if bundle:
        s.setdefault('artifact_hashes', {})[a.complete] = bundle

    p.write_text(json.dumps(s, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(a.complete)

if __name__ == '__main__':
    main()
