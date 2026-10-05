#!/usr/bin/env python3
"""Deterministic execution-boundary manifests for Reader-v3 Lens runs.

A Lens result is auditable only when the host records the material inputs that
were visible from an isolated execution root.  This module deliberately does
not infer isolation from task declarations or model prose: it snapshots the
actual input root, rejects forbidden/sibling Lens paths, and binds the snapshot
to the task, code, prompt and result hashes.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from validate_common import sha256

MANIFEST_SCHEMA_VERSION = "1.0"
DISPATCH_SCHEMA_VERSION = "1.0"
RECEIPT_SCHEMA_VERSION = "1.0"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _iter_files(root: Path, rel: str):
    target = root / rel
    if target.is_file():
        yield target
    elif target.is_dir():
        yield from (p for p in sorted(target.rglob("*")) if p.is_file())


def _normalise_rel(path: str) -> str:
    return str(Path(path)).replace("\\", "/").lstrip("./")


def _forbidden_matches(root: Path, forbidden: list[str]) -> list[str]:
    found: set[str] = set()
    for pattern in forbidden:
        rel = _normalise_rel(pattern)
        target = root / rel
        if target.exists():
            found.add(rel.rstrip("/"))
        # A forbidden directory may be nested in an otherwise permitted root.
        if rel.endswith("/"):
            for p in root.glob(rel + "**"):
                if p.exists():
                    found.add(str(p.relative_to(root)))
    # Lens sibling outputs are forbidden even when a task packet accidentally
    # omits the generic lens_v3/ declaration.
    for dirname in ("lens", "lens_v3"):
        target = root / dirname
        if target.exists():
            found.add(dirname)
    return sorted(found)


def _git_code_sha(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN_CODE_SHA"


def material_input_hashes(root: Path, task: dict[str, Any]) -> dict[str, str]:
    """Hash exact task-declared material inputs, deterministically."""
    hashes: dict[str, str] = {}
    for value in (task.get("input_artifacts") or {}).values():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            rel = _normalise_rel(item)
            for path in _iter_files(root, rel):
                hashes[str(path.relative_to(root))] = sha256(path)
    return dict(sorted(hashes.items()))


def build_execution_manifest(
    root: Path,
    task: dict[str, Any],
    *,
    task_path: Path | None = None,
    output_sha256: str | None = None,
    code_sha: str | None = None,
    executor: dict[str, Any] | None = None,
    snapshot_root: str = ".",
) -> dict[str, Any]:
    """Build a manifest and fail closed if the root contains forbidden context."""
    root = Path(root).resolve()
    snapshot = Path(snapshot_root)
    if snapshot.is_absolute() or ".." in snapshot.parts:
        raise ValueError("snapshot_root must be a relative path inside the run workspace")
    root = (root / snapshot).resolve()
    forbidden = _forbidden_matches(root, list(task.get("forbidden_inputs") or []))
    if forbidden:
        raise ValueError(
            "Lens execution root contains forbidden context; use an isolated root: "
            + ", ".join(forbidden)
        )
    task_file_sha = sha256(task_path) if task_path and Path(task_path).exists() else None
    material = material_input_hashes(root, task)
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "boundary": "filesystem_snapshot",
        "snapshot_root": snapshot_root,
        "task_id": task.get("task_id"),
        "lens_id": task.get("lens"),
        "source_sha256": task.get("source_sha256"),
        "base_sha256": task.get("base_sha256"),
        "contract_version": task.get("contract_version"),
        "prompt_version": task.get("prompt_version"),
        "task_sha256": task_file_sha,
        "task_prompt_sha256": hashlib.sha256(str(task.get("instructions", "")).encode("utf-8")).hexdigest(),
        "code_sha": code_sha or _git_code_sha(root),
        "material_inputs": material,
        "forbidden_paths_checked": sorted(set(task.get("forbidden_inputs") or []) | {"lens/", "lens_v3/"}),
        "forbidden_paths_present": [],
        "sibling_lens_outputs_present": False,
        "executor": executor or {},
        "output_sha256": output_sha256,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def validate_execution_manifest(
    root: Path,
    task: dict[str, Any],
    manifest: dict[str, Any],
    *,
    result_sha256: str | None = None,
) -> None:
    """Validate a submitted manifest against the task and current isolated root."""
    run_root = Path(root).resolve()
    snapshot = Path(manifest.get("snapshot_root", "."))
    if snapshot.is_absolute() or ".." in snapshot.parts:
        raise ValueError("execution manifest snapshot_root escapes the run workspace")
    root = (run_root / snapshot).resolve()
    required = {
        "schema_version", "boundary", "snapshot_root", "task_id", "lens_id", "source_sha256",
        "contract_version", "prompt_version", "material_inputs", "manifest_sha256",
        "forbidden_paths_checked", "forbidden_paths_present", "sibling_lens_outputs_present",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError("execution manifest missing required fields: " + ", ".join(missing))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION or manifest.get("boundary") != "filesystem_snapshot":
        raise ValueError("unsupported execution manifest schema/boundary")
    if manifest.get("task_id") != task.get("task_id"):
        raise ValueError("execution manifest task_id mismatch")
    if manifest.get("lens_id") != task.get("lens"):
        raise ValueError("execution manifest lens_id mismatch")
    for key in ("source_sha256", "base_sha256", "contract_version", "prompt_version"):
        expected = task.get(key)
        if expected is not None and manifest.get(key) != expected:
            raise ValueError(f"execution manifest {key} mismatch")
    if manifest.get("forbidden_paths_present"):
        raise ValueError("execution manifest records forbidden context")
    if manifest.get("sibling_lens_outputs_present") is not False:
        raise ValueError("execution manifest does not prove sibling Lens exclusion")
    actual_forbidden = _forbidden_matches(root, list(task.get("forbidden_inputs") or []))
    if actual_forbidden:
        raise ValueError("isolated execution root contains forbidden context: " + ", ".join(actual_forbidden))
    actual = material_input_hashes(root, task)
    if actual != manifest.get("material_inputs"):
        raise ValueError("execution material input snapshot does not match the submitted root")
    source_rel = task.get("input_artifacts", {}).get("source_pdf")
    if isinstance(source_rel, str) and task.get("source_sha256"):
        if actual.get(_normalise_rel(source_rel)) != task.get("source_sha256"):
            raise ValueError("execution source PDF hash does not match the task source_sha256")
    unsigned = dict(manifest)
    claimed_sha = unsigned.pop("manifest_sha256", None)
    if claimed_sha != canonical_sha256(unsigned):
        raise ValueError("execution manifest self-hash mismatch")
    if result_sha256 is not None and manifest.get("output_sha256") != result_sha256:
        raise ValueError("execution manifest output hash mismatch")


def result_payload_sha256(payload: dict[str, Any]) -> str:
    return canonical_sha256(payload)


def _workspace_root(task_path: Path) -> Path:
    task_path = Path(task_path).resolve()
    for parent in task_path.parents:
        if parent.name == "tasks":
            return parent.parent
    raise ValueError(f"task path is not inside a tasks/ directory: {task_path}")


def _current_code_sha(root: Path) -> str:
    return os.environ.get("ISSUE22_VALIDATION_CODE_SHA") or _git_code_sha(root)


def issue_dispatch_record(
    task_path: Path,
    *,
    code_sha: str | None = None,
    ttl_seconds: int = 86400,
) -> dict[str, Any]:
    """Issue one core-owned, single-use dispatch binding before host handoff."""
    task_path = Path(task_path).resolve()
    root = _workspace_root(task_path)
    task = json.loads(task_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    execution_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "schema_version": DISPATCH_SCHEMA_VERSION,
        "execution_id": execution_id,
        "nonce": secrets.token_urlsafe(24),
        "status": "ISSUED",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "task_id": task.get("task_id"),
        "task_sha256": sha256(task_path),
        "code_sha": code_sha or _current_code_sha(root),
        "source_sha256": task.get("source_sha256"),
        "base_sha256": task.get("base_sha256"),
        "contract_version": task.get("contract_version"),
        "prompt_version": task.get("prompt_version"),
        "target_output": task.get("target_output") or task.get("output"),
        "input_hashes": material_input_hashes(root, task),
    }
    record["dispatch_sha256"] = canonical_sha256(record)
    out_dir = root / "agent_runs" / str(task.get("task_id"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"dispatch-{execution_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


def _load_dispatch(root: Path, task: dict[str, Any], execution_id: str) -> tuple[Path, dict[str, Any]]:
    path = Path(root) / "agent_runs" / str(task.get("task_id")) / f"dispatch-{execution_id}.json"
    if not path.exists():
        raise ValueError("unknown or missing core dispatch record")
    return path, json.loads(path.read_text(encoding="utf-8"))


def validate_dispatch_binding(
    root: Path,
    task: dict[str, Any],
    envelope: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Validate a single-use dispatch and the complete input snapshot."""
    binding = envelope.get("execution_binding")
    if not isinstance(binding, dict):
        raise ValueError("missing execution_binding")
    execution_id = binding.get("execution_id")
    if not execution_id or not binding.get("nonce"):
        raise ValueError("execution_binding must include execution_id and nonce")
    dispatch_path, dispatch = _load_dispatch(root, task, execution_id)
    if dispatch.get("schema_version") != DISPATCH_SCHEMA_VERSION:
        raise ValueError("unsupported dispatch schema")
    if dispatch.get("status") != "ISSUED":
        raise ValueError("dispatch has already been consumed or revoked")
    if dispatch.get("nonce") != binding.get("nonce"):
        raise ValueError("dispatch nonce mismatch")
    if dispatch.get("dispatch_sha256") != binding.get("dispatch_sha256"):
        raise ValueError("dispatch hash mismatch")
    if dispatch.get("task_sha256") != binding.get("task_sha256"):
        raise ValueError("dispatch task hash mismatch")
    run_root = next((p.parent for p in dispatch_path.parents if p.name == "agent_runs"), None)
    if run_root is None:
        raise ValueError("dispatch record is outside an agent workspace")
    # The dispatch record already binds the canonical task; re-hash the unique
    # task packet found by the submitter rather than trusting envelope prose.
    matches = list((run_root / "tasks").rglob("*.json"))
    task_hash_matches = [p for p in matches if sha256(p) == dispatch.get("task_sha256")]
    if len(task_hash_matches) != 1:
        raise ValueError("canonical task hash is missing or ambiguous")
    if task.get("task_id") != dispatch.get("task_id"):
        raise ValueError("dispatch task_id mismatch")
    code_sha = binding.get("code_sha")
    if code_sha != dispatch.get("code_sha"):
        raise ValueError("dispatch code SHA mismatch")
    if dispatch.get("source_sha256") != task.get("source_sha256"):
        raise ValueError("dispatch source SHA mismatch")
    expected_inputs = dispatch.get("input_hashes") or {}
    supplied_inputs = envelope.get("input_hashes")
    if not isinstance(supplied_inputs, dict) or supplied_inputs != expected_inputs:
        raise ValueError("complete input manifest does not match the core dispatch")
    actual_inputs = material_input_hashes(run_root, task)
    if actual_inputs != expected_inputs:
        raise ValueError("core dispatch input manifest no longer matches workspace artifacts")
    for rel in expected_inputs:
        if not (run_root / rel).is_file():
            raise ValueError(f"dispatch input artifact is missing: {rel}")
    expires = datetime.fromisoformat(str(dispatch["expires_at"]))
    if datetime.now(timezone.utc) > expires:
        raise ValueError("dispatch has expired")
    if result_payload_sha256(payload) != (envelope.get("execution_manifest") or {}).get("output_sha256"):
        raise ValueError("execution manifest output hash mismatch")
    return dispatch_path, dispatch


def write_core_receipt(
    root: Path,
    task: dict[str, Any],
    envelope: dict[str, Any],
    dispatch_path: Path,
    dispatch: dict[str, Any],
    output_sha256: str,
) -> Path:
    """Write one append-only acceptance receipt and consume the dispatch."""
    runs_dir = Path(root) / "agent_runs" / str(task.get("task_id"))
    receipt_path = runs_dir / f"receipt-{dispatch['execution_id']}.json"
    if receipt_path.exists():
        raise ValueError("replayed execution: acceptance receipt already exists")
    envelope_sha = canonical_sha256(envelope)
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": str(uuid.uuid4()),
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "execution_id": dispatch["execution_id"],
        "dispatch_sha256": dispatch["dispatch_sha256"],
        "task_id": task.get("task_id"),
        "task_sha256": dispatch["task_sha256"],
        "code_sha": dispatch["code_sha"],
        "input_hashes": dispatch["input_hashes"],
        "output_sha256": output_sha256,
        "envelope_sha256": envelope_sha,
        "target_output": dispatch.get("target_output"),
        "executor": envelope.get("executor", {}),
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    consumed = dict(dispatch)
    consumed["status"] = "CONSUMED"
    consumed["consumed_at"] = receipt["accepted_at"]
    consumed["receipt_sha256"] = receipt["receipt_sha256"]
    dispatch_path.write_text(json.dumps(consumed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt_path
