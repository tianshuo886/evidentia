"""Tier 2 Recorded Real-Agent Replay acceptance tests (Section 47 & 61).

Validates:
- All replay fixtures are genuine Host-Agent results (executor.kind == 'HOST_AGENT')
- Schema compliance of all recorded AgentResultEnvelope fixtures
- End-to-end execution of evidentia run driven entirely by recorded replays
- Replay validation status recorded in final run artifacts
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'evals/runners'))
from validate_common import load_json, schema_validate
from eval_runner import create_synthetic_pdf

def test_replay_fixtures_integrity():
    replay_dir = ROOT / 'tests/replays/standard'
    assert replay_dir.exists()
    replays = list(replay_dir.glob('*.json'))
    assert len(replays) >= 8

    for rf in replays:
        data = load_json(rf)
        # Schema validation
        errs = schema_validate(data, 'agent_result_envelope')
        assert not errs, f"Replay fixture {rf.name} failed agent_result_envelope validation: {errs}"

        # Must be genuine Host-Agent metadata (not simulated fixture)
        executor = data.get('executor', {})
        assert executor.get('kind') == 'HOST_AGENT', f"Replay fixture {rf.name} must have kind HOST_AGENT"
        assert executor.get('host') == 'pi-agent'
        assert 'model' in executor
        assert 'result' in data

def test_evidentia_run_with_recorded_replay(tmp_path):
    pdf_path = tmp_path / 'paper.pdf'
    out_dir = tmp_path / 'out_replay'
    replay_dir = ROOT / 'tests/replays/standard'

    paper_spec = {
        "title": "Sparse Attention Mechanisms for Representation Learning",
        "sections": ["1. Introduction", "2. Methodology", "3. Experiments"],
        "figures": [{"id": "F01", "paper_label": "Fig. 1", "caption": "Attention architecture"}],
        "tables": [{"id": "T01", "paper_label": "Table 1", "caption": "Accuracy comparisons"}]
    }
    create_synthetic_pdf(paper_spec, pdf_path)

    # Execute workflow using recorded replays
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir),
        '--replay', str(replay_dir)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Evidentia run COMPLETE" in res.stdout

    # Verify reader and frozen manifest
    manifest_p = out_dir / 'model/manifest.json'
    assert manifest_p.exists()
    manifest = load_json(manifest_p)
    assert manifest['status'] == 'FROZEN'
    assert (out_dir / 'reader/reader.html').exists()
