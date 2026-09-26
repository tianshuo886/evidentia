"""Phase B1 Deterministic Core v2 acceptance tests.

Validates:
- Formal state machine transitions & lock requirements (test_source_lock_required, test_baseline_lock_required)
- Artifact bundle hashing and tamper detection (test_phase_bundle_tamper_fails)
- Resume & retry granularity (test_resume_only_retries_failed_task)
- Contract version invalidation (test_contract_change_invalidates_downstream)
- Hardened freeze gates (test_visual_review_required_blocks_freeze, test_unverified_critical_conflict_blocks_freeze)
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, run, sha_bytes, L

def test_source_lock_required(tmp_path):
    r = fixture(tmp_path)
    # Set phase to SOURCE_RECONSTRUCTION without SOURCE_LOCK
    rs_path = r / 'run_state.json'
    src_sha = sha_bytes((r / 'source/paper.pdf').read_bytes())
    state = {
        'schema_version': '1.0',
        'run_id': 'r-test',
        'mode': 'evidentia',
        'phase': 'SOURCE_RECONSTRUCTION',
        'source_sha256': src_sha,
        'base_sha256': None,
        'allowed_inputs': ['working/paper.pdf'],
        'artifacts': {},
        'completed_phases': ['INGEST'],
        'artifact_hashes': {},
        'history': []
    }
    rs_path.write_text(json.dumps(state, indent=2))
    
    # Trying to jump directly to OPEN_READING must fail
    res = run('phase.py', '--out', str(r), '--complete', 'OPEN_READING')
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert 'SOURCE_LOCK' in out or 'expected next phase SOURCE_LOCK' in out or 'REFUSED' in out

    # Transitioning to SOURCE_LOCK succeeds
    res_lock = run('phase.py', '--out', str(r), '--complete', 'SOURCE_LOCK')
    assert res_lock.returncode == 0, res_lock.stdout + res_lock.stderr

    # Now transitioning to OPEN_READING succeeds
    res_open = run('phase.py', '--out', str(r), '--complete', 'OPEN_READING')
    assert res_open.returncode == 0, res_open.stdout + res_open.stderr

def test_baseline_lock_required(tmp_path):
    r = fixture(tmp_path)
    rs_path = r / 'run_state.json'
    src_sha = sha_bytes((r / 'source/paper.pdf').read_bytes())
    state = {
        'schema_version': '1.0',
        'run_id': 'r-test',
        'mode': 'evidentia',
        'phase': 'OPEN_READING',
        'source_sha256': src_sha,
        'base_sha256': None,
        'allowed_inputs': ['working/paper.pdf'],
        'artifacts': {},
        'completed_phases': ['INGEST', 'SOURCE_RECONSTRUCTION', 'SOURCE_LOCK'],
        'artifact_hashes': {},
        'history': []
    }
    rs_path.write_text(json.dumps(state, indent=2))
    
    # Trying to jump directly to LENS_EXECUTION without BASELINE_LOCK must fail
    res = run('phase.py', '--out', str(r), '--complete', 'LENS_EXECUTION')
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert 'BASELINE_LOCK' in out or 'expected next phase BASELINE_LOCK' in out or 'REFUSED' in out

    # Completing BASELINE_LOCK succeeds
    res_lock = run('phase.py', '--out', str(r), '--complete', 'BASELINE_LOCK')
    assert res_lock.returncode == 0, res_lock.stdout + res_lock.stderr

    # Now completing LENS_EXECUTION succeeds
    res_lens = run('phase.py', '--out', str(r), '--complete', 'LENS_EXECUTION')
    assert res_lens.returncode == 0, res_lens.stdout + res_lens.stderr

def test_phase_bundle_tamper_fails(tmp_path):
    r = fixture(tmp_path)
    rs_path = r / 'run_state.json'
    src_sha = sha_bytes((r / 'source/paper.pdf').read_bytes())
    sm_sha = sha_bytes((r / 'model/source_map.json').read_bytes())
    fi_sha = sha_bytes((r / 'model/figure_inventory.json').read_bytes())
    
    state = {
        'schema_version': '1.0',
        'run_id': 'r-test',
        'mode': 'evidentia',
        'phase': 'SOURCE_RECONSTRUCTION',
        'source_sha256': src_sha,
        'base_sha256': None,
        'allowed_inputs': ['working/paper.pdf'],
        'artifacts': {},
        'completed_phases': ['INGEST'],
        'artifact_hashes': {
            'SOURCE_RECONSTRUCTION': {
                'model/source_map.json': sm_sha,
                'model/figure_inventory.json': fi_sha
            }
        },
        'history': []
    }
    rs_path.write_text(json.dumps(state, indent=2))
    
    # Tamper with one file in the bundle
    (r / 'model/figure_inventory.json').write_text((r / 'model/figure_inventory.json').read_text() + ' ')
    
    # Advancing must fail with bundle tamper detection
    res = run('phase.py', '--out', str(r), '--complete', 'SOURCE_LOCK')
    assert res.returncode != 0
    out = res.stdout + res.stderr
    assert 'artifact bundle changed' in out or 'REFUSED' in out

def test_resume_only_retries_failed_task(tmp_path):
    r = fixture(tmp_path)
    # Write valid run_state.json
    rs_path = r / 'run_state.json'
    src_sha = sha_bytes((r / 'source/paper.pdf').read_bytes())
    base_sha = sha_bytes((r / 'model/open_reading_model.json').read_bytes())
    state = {
        'schema_version': '1.0',
        'run_id': 'r-test',
        'mode': 'evidentia',
        'phase': 'BASELINE_LOCK',
        'source_sha256': src_sha,
        'base_sha256': base_sha,
        'allowed_inputs': ['working/paper.pdf'],
        'artifacts': {},
        'completed_phases': ['INGEST', 'SOURCE_RECONSTRUCTION', 'SOURCE_LOCK', 'OPEN_READING', 'BASELINE_LOCK'],
        'artifact_hashes': {},
        'history': []
    }
    rs_path.write_text(json.dumps(state, indent=2))

    # Corrupt or delete only mechanism lens
    (r / 'lens/mechanism.json').unlink()
    
    # Other lenses exist
    for l in ('author', 'reviewer', 'builder', 'anomaly', 'counterfactual'):
        assert (r / 'lens' / f'{l}.json').exists()
        
    res = run('phase.py', '--out', str(r), '--retry', 'mechanism')
    assert res.returncode == 0, res.stdout + res.stderr
    assert 'mechanism' in (res.stdout + res.stderr)
    
    # The other 5 lenses are preserved untouched
    for l in ('author', 'reviewer', 'builder', 'anomaly', 'counterfactual'):
        assert (r / 'lens' / f'{l}.json').exists()

def test_contract_change_invalidates_downstream(tmp_path):
    r = fixture(tmp_path)
    rs_path = r / 'run_state.json'
    src_sha = sha_bytes((r / 'source/paper.pdf').read_bytes())
    base_sha = sha_bytes((r / 'model/open_reading_model.json').read_bytes())
    
    state = {
        'schema_version': '1.0',
        'run_id': 'r-test',
        'mode': 'evidentia',
        'phase': 'LENS_EXECUTION',
        'source_sha256': src_sha,
        'base_sha256': base_sha,
        'lens_contract_version': '1.0',
        'allowed_inputs': ['working/paper.pdf'],
        'artifacts': {},
        'completed_phases': ['INGEST', 'SOURCE_RECONSTRUCTION', 'SOURCE_LOCK', 'OPEN_READING', 'BASELINE_LOCK'],
        'artifact_hashes': {},
        'history': []
    }
    rs_path.write_text(json.dumps(state, indent=2))
    
    # Modify lens_contract_version in open_reading_manifest.json to 2.0
    orm_p = r / 'model/open_reading_manifest.json'
    orm = json.loads(orm_p.read_text())
    orm['lens_contract_version'] = '2.0'
    orm_p.write_text(json.dumps(orm, indent=2))
    
    # Resume detects changed contract and refuses / invalidates
    res = run('phase.py', '--out', str(r), '--resume')
    assert res.returncode != 0
    assert 'lens_contract_version changed' in (res.stdout + res.stderr)

def test_visual_review_required_blocks_freeze(tmp_path):
    r = fixture(tmp_path)
    fi_p = r / 'model/figure_inventory.json'
    fi = json.loads(fi_p.read_text())
    
    # Case A: needs_visual_review == True
    fi['items'][0]['needs_visual_review'] = True
    fi_p.write_text(json.dumps(fi, indent=2))
    res = run('freeze_check.py', '--out', str(r))
    assert res.returncode != 0
    assert 'needs_visual_review' in res.stdout

    # Case B: review_required non-empty
    fi['items'][0]['needs_visual_review'] = False
    fi['review_required'] = ['F01']
    fi_p.write_text(json.dumps(fi, indent=2))
    res2 = run('freeze_check.py', '--out', str(r))
    assert res2.returncode != 0
    assert 'review_required' in res2.stdout

def test_unverified_critical_conflict_blocks_freeze(tmp_path):
    r = fixture(tmp_path)
    pm_p = r / 'model/paper_model.json'
    pm = json.loads(pm_p.read_text())
    
    # Add a critical conflict without verifier result
    pm['lens_conflicts'].append({
        'id': 'CONF-01',
        'target': 'C01',
        'findings': ['F01'],
        'critical': True,
        'verifier_status': None
    })
    pm_p.write_text(json.dumps(pm, indent=2))
    
    res = run('freeze_check.py', '--out', str(r))
    assert res.returncode != 0
    assert 'critical conflict' in res.stdout
