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
