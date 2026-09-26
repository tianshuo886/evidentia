"""Phase B3 Standard Mode Agent Execution acceptance tests.

Validates:
- Host-neutral task protocol generation (open_reading.json, lens/*.json, reconciliation.json)
- Executor metadata structure and completeness (no silent omission)
- CLI subcommands (status, next, validate, resume)
- Complete host loop advancement through evidentia.py run
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, run, sha_bytes, L
from executor_meta import build_executor_metadata, REQUIRED_FIELDS

def test_executor_metadata_fields():
    meta = build_executor_metadata(
        host="test-host",
        provider="test-provider",
        model="test-model"
    )
    for field in REQUIRED_FIELDS:
        assert field in meta, f"Missing required executor field: {field}"
        assert meta[field] is not None
        assert len(str(meta[field])) > 0

def test_task_protocol_generation(tmp_path):
    r = fixture(tmp_path)
    import task_protocol
    
    # 1. Open Reading task
    orp = task_protocol.create_open_reading_task(r)
    assert orp.exists()
    ordata = json.loads(orp.read_text())
    assert ordata['task_id'] == 'TASK-OPEN-READING'
    assert 'PROJECT_INVISIBLE' in ordata['constraints']
    assert 'paper_model' in ordata['output_schema']
    
    # 2. Six Lens tasks
    lps = task_protocol.create_lens_tasks(r)
    assert len(lps) == 6
    for lp in lps:
        assert lp.exists()
        ldata = json.loads(lp.read_text())
        assert ldata['lens'] in L
        assert 'instructions' in ldata
        assert 'executor_template' in ldata

    # 3. Reconciliation task
    recp = task_protocol.create_reconciliation_task(r)
    assert recp.exists()
    recdata = json.loads(recp.read_text())
    assert recdata['task_id'] == 'TASK-RECONCILIATION'

def test_evidentia_cli_commands(tmp_path):
    r = fixture(tmp_path)
    # Write valid run_state
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

    # Test status
    res_status = run('evidentia.py', 'status', '--out', str(r))
    assert res_status.returncode == 0, res_status.stdout + res_status.stderr
    assert 'BASELINE_LOCK' in res_status.stdout

    # Test next
    res_next = run('evidentia.py', 'next', '--out', str(r))
    assert res_next.returncode == 0
    assert 'LENS' in (res_next.stdout + res_next.stderr)

    # Test validate
    res_val = run('evidentia.py', 'validate', '--out', str(r))
    assert res_val.returncode == 0
    assert 'passed schema validation' in res_val.stdout

def test_evidentia_run_advancement(tmp_path):
    r = fixture(tmp_path)
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

    # Call evidentia.py run when all 6 lenses are already populated
    res_run = run('evidentia.py', 'run', '--out', str(r))
    assert res_run.returncode == 0, res_run.stdout + res_run.stderr
    assert 'Evidentia run COMPLETE' in res_run.stdout
    assert (r / 'reader/reader.html').exists()
    assert (r / 'model/manifest.json').exists()
    assert json.loads((r / 'model/manifest.json').read_text())['status'] == 'FROZEN'
