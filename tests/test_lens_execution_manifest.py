import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from lens_execution_manifest import (
    build_execution_manifest,
    result_payload_sha256,
    validate_execution_manifest,
    issue_dispatch_record,
    validate_dispatch_binding,
    write_core_receipt,
)


def _task():
    return {
        "task_id": "TASK-V3-LENS-ONE",
        "task_type": "LENS_V3",
        "lens": "one",
        "source_sha256": "c35b21d6ca39aa7cc3b79a705d989f1a6e88b99ab43988d74048799e3db926a3",
        "base_sha256": "base-sha",
        "contract_version": "3.0",
        "prompt_version": "3.0",
        "input_artifacts": {
            "source_pdf": "source/paper.pdf",
            "source_map": "model/source_map.json",
            "figure_inventory": "model/figure_inventory.json",
            "lead_reader_draft": "model/paper_understanding_draft.json",
        },
        "forbidden_inputs": ["lens/", "lens_v3/", "project/", "memory/project/"],
        "instructions": "Read only the paper and lead draft.",
    }


def _snapshot(tmp_path):
    run = tmp_path / "run"
    snap = run / "isolated"
    for rel, content in {
        "source/paper.pdf": b"pdf",
        "model/source_map.json": b"{}",
        "model/figure_inventory.json": b"{}",
        "model/paper_understanding_draft.json": b"{}",
    }.items():
        p = snap / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    task_path = run / "tasks" / "lens" / "one.json"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(json.dumps(_task()), encoding="utf-8")
    return run, task_path


def test_manifest_binds_material_inputs_and_result(tmp_path):
    run, task_path = _snapshot(tmp_path)
    task = _task()
    payload = {"schema_version": "3.0", "finding": "bounded"}
    manifest = build_execution_manifest(
        run,
        task,
        task_path=task_path,
        snapshot_root="isolated",
        code_sha="candidate-sha",
        output_sha256=result_payload_sha256(payload),
    )
    validate_execution_manifest(run, task, manifest, result_sha256=result_payload_sha256(payload))


def test_manifest_rejects_sibling_lens_context(tmp_path):
    run, task_path = _snapshot(tmp_path)
    sibling = run / "isolated" / "lens_v3" / "sibling.json"
    sibling.parent.mkdir(parents=True)
    sibling.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden context"):
        build_execution_manifest(run, _task(), task_path=task_path, snapshot_root="isolated")


def test_core_dispatch_binds_inputs_and_is_single_use(tmp_path):
    run, task_path = _snapshot(tmp_path)
    task = _task()
    dispatch = issue_dispatch_record(task_path, code_sha="candidate-sha")
    payload = {"schema_version": "3.0", "finding": "bounded"}
    manifest = build_execution_manifest(
        run, task, task_path=task_path, snapshot_root="isolated",
        code_sha="candidate-sha", output_sha256=result_payload_sha256(payload),
    )
    envelope = {
        "task_id": task["task_id"],
        "execution_binding": {
            "execution_id": dispatch["execution_id"],
            "nonce": dispatch["nonce"],
            "dispatch_sha256": dispatch["dispatch_sha256"],
            "task_sha256": dispatch["task_sha256"],
            "code_sha": "candidate-sha",
        },
        "input_hashes": dispatch["input_hashes"],
        "execution_manifest": manifest,
        "executor": {"kind": "HOST_AGENT", "host": "test", "model": "test"},
        "result": payload,
    }
    dispatch_path, loaded = validate_dispatch_binding(run, task, envelope, payload)
    receipt = write_core_receipt(run, task, envelope, dispatch_path, loaded, result_payload_sha256(payload))
    assert receipt.exists()
    with pytest.raises(ValueError, match="consumed"):
        validate_dispatch_binding(run, task, envelope, payload)


def test_manifest_rejects_input_drift(tmp_path):
    run, task_path = _snapshot(tmp_path)
    task = _task()
    payload = {"schema_version": "3.0"}
    manifest = build_execution_manifest(
        run, task, task_path=task_path, snapshot_root="isolated",
        output_sha256=result_payload_sha256(payload),
    )
    (run / "isolated" / "model" / "source_map.json").write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="material input snapshot"):
        validate_execution_manifest(run, task, manifest, result_sha256=result_payload_sha256(payload))


def test_manifest_rejects_self_hash_mismatch(tmp_path):
    run, task_path = _snapshot(tmp_path)
    task = _task()
    payload = {"schema_version": "3.0"}
    manifest = build_execution_manifest(
        run, task, task_path=task_path, snapshot_root="isolated",
        output_sha256=result_payload_sha256(payload),
    )
    manifest["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="manifest self-hash mismatch"):
        validate_execution_manifest(run, task, manifest, result_sha256=result_payload_sha256(payload))


def _setup_v3_submission(tmp_path):
    from agent_submit import submit_agent_result
    from validate_common import sha256
    run, task_path = _snapshot(tmp_path)
    task_path.unlink()
    v3_task_path = run / "tasks" / "v3" / "lens" / "one.json"
    v3_task_path.parent.mkdir(parents=True, exist_ok=True)
    task = _task()
    task["isolation_proof_required"] = True
    task["target_output"] = "lens_v3/one.json"
    task["output_schema"] = "lens_v3"
    task["source_sha256"] = sha256(run / "isolated" / "source/paper.pdf")
    (run / "source").mkdir(parents=True, exist_ok=True)
    (run / "source/paper.pdf").write_bytes(b"pdf")
    (run / "model").mkdir(parents=True, exist_ok=True)
    (run / "model/source_map.json").write_text("{}", encoding="utf-8")
    (run / "model/figure_inventory.json").write_text("{}", encoding="utf-8")
    (run / "model/paper_understanding_draft.json").write_text("{}", encoding="utf-8")
    v3_task_path.write_text(json.dumps(task), encoding="utf-8")

    dispatch = issue_dispatch_record(v3_task_path, code_sha="candidate-sha")
    payload = {
        "schema_version": "1.0",
        "lens": "one",
        "lens_kind": "core",
        "source_sha256": task["source_sha256"],
        "base_sha256": task["base_sha256"],
        "findings": [{"id": "F01", "statement": "Test finding", "evidence": [], "epistemic": "SUPPORTED", "action": "KEEP"}],
        "summary": "Summary",
    }
    manifest = build_execution_manifest(
        run, task, task_path=v3_task_path, snapshot_root="isolated",
        code_sha="candidate-sha", output_sha256=result_payload_sha256(payload),
    )
    envelope = {
        "task_id": task["task_id"],
        "execution_kind": "HOST_AGENT",
        "executor": {"kind": "HOST_AGENT", "host": "test", "model": "test"},
        "execution_binding": {
            "execution_id": dispatch["execution_id"],
            "nonce": dispatch["nonce"],
            "dispatch_sha256": dispatch["dispatch_sha256"],
            "task_sha256": dispatch["task_sha256"],
            "code_sha": "candidate-sha",
        },
        "input_hashes": dispatch["input_hashes"],
        "execution_manifest": manifest,
        "contract_version": task["contract_version"],
        "prompt_version": task["prompt_version"],
        "result": payload,
    }
    env_path = run / "env.json"
    env_path.write_text(json.dumps(envelope), encoding="utf-8")
    submit_agent_result(run, task["task_id"], env_path)
    return run, task, dispatch


def test_lens_execution_provenance_errors_accepts_valid_run(tmp_path):
    from reader_integrity import lens_execution_provenance_errors
    run, _, _ = _setup_v3_submission(tmp_path)
    assert lens_execution_provenance_errors(run) == []


def test_lens_execution_provenance_errors_catches_envelope_tampering(tmp_path):
    from reader_integrity import lens_execution_provenance_errors
    run, task, _ = _setup_v3_submission(tmp_path)
    run_file = run / "agent_runs" / task["task_id"] / "run-001.json"
    data = json.loads(run_file.read_text(encoding="utf-8"))
    data["result"]["findings"][0]["statement"] = "Tampered statement"
    run_file.write_text(json.dumps(data), encoding="utf-8")
    errors = lens_execution_provenance_errors(run)
    assert any("receipt envelope hash mismatch" in e for e in errors)


def test_lens_execution_provenance_errors_catches_receipt_tampering(tmp_path):
    from reader_integrity import lens_execution_provenance_errors
    run, task, dispatch = _setup_v3_submission(tmp_path)
    rcpt_file = run / "agent_runs" / task["task_id"] / f"receipt-{dispatch['execution_id']}.json"
    data = json.loads(rcpt_file.read_text(encoding="utf-8"))
    data["accepted_at"] = "2099-01-01T00:00:00Z"
    rcpt_file.write_text(json.dumps(data), encoding="utf-8")
    errors = lens_execution_provenance_errors(run)
    assert any("receipt self-hash mismatch" in e for e in errors)


def test_lens_execution_provenance_errors_catches_promoted_output_tampering(tmp_path):
    from reader_integrity import lens_execution_provenance_errors
    run, _, _ = _setup_v3_submission(tmp_path)
    target = run / "lens_v3" / "one.json"
    target.write_text(json.dumps({"tampered": True}), encoding="utf-8")
    errors = lens_execution_provenance_errors(run)
    assert any("promoted output hash mismatch" in e for e in errors)

