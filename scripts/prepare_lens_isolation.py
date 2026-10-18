#!/usr/bin/env python3
"""Prepare one filesystem-only input snapshot per Reader-v3 Lens task.

The snapshot contains only task-declared material inputs.  A host Lens worker
must read this directory, write its envelope there, and submit through the
core gateway; sibling Lens outputs are deliberately never copied.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from lens_execution_manifest import _normalise_rel
from storage_links import link_or_copy, link_tree
from validate_common import load_json


def prepare(root: Path) -> list[Path]:
    root = Path(root).resolve()
    task_dir = root / "tasks/v3/lens"
    if not task_dir.exists():
        raise FileNotFoundError(task_dir)
    prepared = []
    for task_path in sorted(task_dir.glob("*.json")):
        task = load_json(task_path)
        task_id = str(task["task_id"])
        snapshot = root / "provenance/lens" / task_id
        if snapshot.exists():
            shutil.rmtree(snapshot)
        snapshot.mkdir(parents=True)
        values = []
        for value in (task.get("input_artifacts") or {}).values():
            values.extend(value if isinstance(value, list) else [value])
        for value in values:
            if not isinstance(value, str):
                continue
            rel = _normalise_rel(value)
            source = root / rel
            destination = snapshot / rel
            if source.is_file():
                # Hard-link, don't copy: the Lens still sees a complete isolated
                # view, but the bytes are stored once (Issue #55).
                link_or_copy(source, destination)
            elif source.is_dir():
                link_tree(source, destination)
            else:
                raise FileNotFoundError(f"missing Lens input {rel} for {task_id}")
        (snapshot / "task.json").write_text(
            json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        prepared.append(snapshot)
    return prepared


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    for path in prepare(Path(args.out)):
        print(path)


if __name__ == "__main__":
    main()
