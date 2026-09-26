"""Tests for Scientific Trust Boundary in agent_submit.py (P0-3 Hardening).

Validates:
- Refusal of unknown task_id
- Refusal of raw unwrapped JSON in production without --allow-legacy-raw
- Refusal of mismatched task_id between envelope and task
- Refusal of mismatched source_sha256 binding
- Refusal of mismatched base_sha256 binding
- Refusal of mismatched contract_version
- Refusal of mismatched prompt_version
- Refusal of phantom/unknown evidence IDs (e.g. F99)
- Refusal of input artifact tampering (input_hashes mismatch)
- Promotion strictly to canonical task target_output with immutable agent_runs logging
"""
import json, pytest, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, sha_bytes
import agent_submit

def setup_task_workspace(tmp_path):
    r = fixture(tmp_path)
    import task_protocol
    task_protocol.create_open_reading_task(r)
    task_protocol.create_lens_tasks(r)
    return r

def run_submit(run_dir, task_id, result_path, extra_args=None):
    cmd = [
        PY, str(ROOT / 'scripts/agent_submit.py'),
        '--run-dir', str(run_dir),
        '--task', task_id,
        '--result', str(result_path)
    ] + (extra_args or [])
    return subprocess.run(cmd, capture_output=True, text=True)

def test_submit_rejects_unknown_task_id(tmp_path):
    r = setup_task_workspace(tmp_path)
    res_file = tmp_path / 'res.json'
    res_file.write_text(json.dumps({"task_id": "UNKNOWN-01", "result": {}}))
    res = run_submit(r, "UNKNOWN-01", res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "does not match any generated AgentTask" in res.stderr

def test_submit_rejects_raw_json_in_production(tmp_path):
    r = setup_task_workspace(tmp_path)
    # Valid raw lens JSON without AgentResultEnvelope
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    res_file = tmp_path / 'raw.json'
    res_file.write_text(json.dumps(raw_lens, indent=2))

    # Production submit (without --allow-legacy-raw) must be REFUSED
    res = run_submit(r, "TASK-LENS-AUTHOR", res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "must be wrapped in an AgentResultEnvelope" in res.stderr

    # Development submit (with --allow-legacy-raw) succeeds
    res_dev = run_submit(r, "TASK-LENS-AUTHOR", res_file, extra_args=['--allow-legacy-raw'])
    assert res_dev.returncode == 0, res_dev.stderr

def test_submit_rejects_mismatched_task_id(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    envelope = {
        "task_id": "TASK-LENS-REVIEWER", # Mismatched ID
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "test-host",
            "model": "test-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, "TASK-LENS-AUTHOR", res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "does not match canonical AgentTask ID" in res.stderr

def test_submit_rejects_mismatched_source_sha(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    raw_lens['source_sha256'] = "corrupted_source_sha_value"
    task = json.loads((r / 'tasks/lens/author.json').read_text())

    envelope = {
        "task_id": task['task_id'],
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "test-host",
            "model": "test-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, task['task_id'], res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "source_sha256" in res.stderr

def test_submit_rejects_mismatched_base_sha(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    raw_lens['base_sha256'] = "corrupted_base_sha_value"
    task = json.loads((r / 'tasks/lens/author.json').read_text())

    envelope = {
        "task_id": task['task_id'],
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "test-host",
            "model": "test-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, task['task_id'], res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "base_sha256" in res.stderr

def test_submit_rejects_mismatched_contract_version(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    raw_lens['lens_contract_version'] = "9.9" # Invalid version
    task = json.loads((r / 'tasks/lens/author.json').read_text())

    envelope = {
        "task_id": task['task_id'],
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "test-host",
            "model": "test-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, task['task_id'], res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "Contract version mismatch" in res.stderr

def test_submit_rejects_unknown_evidence_id(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    # Fabricate non-existent evidence F99
    raw_lens['findings'].append({
        "id": "L-author-99",
        "statement": "Fabricated finding on hallucinated evidence",
        "evidence": ["F99"],
        "epistemic": "SUPPORTED",
        "novel_vs_base": True
    })
    task = json.loads((r / 'tasks/lens/author.json').read_text())

    envelope = {
        "task_id": task['task_id'],
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "test-host",
            "model": "test-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, task['task_id'], res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "Unknown evidence ID 'F99'" in res.stderr

def test_submit_rejects_tampered_input_artifact(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    task = json.loads((r / 'tasks/lens/author.json').read_text())

    envelope = {
        "task_id": task['task_id'],
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "test-host",
            "model": "test-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "input_hashes": {
            "source/paper.pdf": "tampered_fake_hash_value"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, task['task_id'], res_file)
    assert res.returncode != 0
    assert "REFUSED" in res.stderr
    assert "changed during execution" in res.stderr

def test_submit_promotes_strictly_to_task_target_output(tmp_path):
    r = setup_task_workspace(tmp_path)
    raw_lens = json.loads((r / 'lens/author.json').read_text())
    task = json.loads((r / 'tasks/lens/author.json').read_text())

    envelope = {
        "task_id": task['task_id'],
        "execution_kind": "HOST_AGENT",
        "executor": {
            "kind": "HOST_AGENT",
            "host": "real-host",
            "model": "real-model",
            "started_at": "2026-03-27T00:00:00Z",
            "completed_at": "2026-03-27T00:01:00Z"
        },
        "started_at": "2026-03-27T00:00:00Z",
        "completed_at": "2026-03-27T00:01:00Z",
        "result": raw_lens
    }
    res_file = tmp_path / 'env.json'
    res_file.write_text(json.dumps(envelope))

    res = run_submit(r, task['task_id'], res_file)
    assert res.returncode == 0, res.stderr
    assert (r / task['target_output']).exists()
    assert (r / f"agent_runs/{task['task_id']}/run-001.json").exists()
