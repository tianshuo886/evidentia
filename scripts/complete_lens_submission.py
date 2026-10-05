#!/usr/bin/env python3
"""Wrap one isolated Lens payload and submit it through the core gateway."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from agent_submit import submit_agent_result
from executor_meta import build_executor_metadata
from lens_execution_manifest import (
    build_execution_manifest,
    result_payload_sha256,
)
from validate_common import load_json, schema_validate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--dispatch", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--code-sha", required=True)
    args = ap.parse_args()

    run_root = Path(args.run_root).resolve()
    task_path = run_root / "tasks/v3/lens" / f"{args.task.replace('TASK-V3-LENS-', '').lower()}.json"
    if not task_path.exists():
        matches = [p for p in (run_root / "tasks/v3/lens").glob("*.json") if load_json(p).get("task_id") == args.task]
        if len(matches) != 1:
            raise SystemExit(f"cannot resolve canonical task packet for {args.task}")
        task_path = matches[0]
    task = load_json(task_path)
    payload = load_json(args.result)
    errors = schema_validate(payload, "lens_v3")
    if errors:
        raise SystemExit("Lens payload failed schema validation: " + " | ".join(errors))
    dispatch = load_json(args.dispatch)
    execution_id = dispatch["execution_id"]
    snapshot = Path(args.snapshot).resolve()
    try:
        snapshot_root = str(snapshot.relative_to(run_root))
    except ValueError as exc:
        raise SystemExit("snapshot must be inside run root") from exc
    output_sha = result_payload_sha256(payload)
    executor = build_executor_metadata(
        host=os.environ.get("ORCA_HOST", "orca-isolated-lens"),
        provider=os.environ.get("PI_PROVIDER", "openai-codex"),
        model=os.environ.get("PI_MODEL", "UNKNOWN"),
        tool_profile="paper-only-isolated-snapshot",
    )
    executor["kind"] = "HOST_AGENT"
    manifest = build_execution_manifest(
        run_root,
        task,
        task_path=task_path,
        output_sha256=output_sha,
        code_sha=args.code_sha,
        executor=executor,
        snapshot_root=snapshot_root,
    )
    envelope = {
        "task_id": args.task,
        "execution_kind": "HOST_AGENT",
        "executor": executor,
        "input_hashes": dispatch["input_hashes"],
        "execution_binding": {
            "execution_id": execution_id,
            "nonce": dispatch["nonce"],
            "dispatch_sha256": dispatch["dispatch_sha256"],
            "task_sha256": dispatch["task_sha256"],
            "code_sha": args.code_sha,
        },
        "execution_manifest": manifest,
        "contract_version": task.get("contract_version"),
        "prompt_version": task.get("prompt_version"),
        "result": payload,
    }
    snapshot.joinpath("envelope.json").write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(envelope, handle, ensure_ascii=False)
        temp_path = handle.name
    try:
        submit_agent_result(run_root, args.task, temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)
    print(f"OK: accepted {args.task} execution {execution_id}")


if __name__ == "__main__":
    main()
