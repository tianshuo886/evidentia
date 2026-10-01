#!/usr/bin/env python3
"""Generic runner for Reader v3 host-agent tasks."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate
from agent_dispatch import dispatch_agent_task


def run(task_path, adapter=None, model=None, replay_dir=None, fixture=None):
    tp = Path(task_path)
    task = load_json(tp)
    envelope = dispatch_agent_task(tp, adapter=adapter, model=model, replay_dir=replay_dir, fixture=fixture)
    if envelope is None:
        print(f"[WAITING_FOR_AGENT] {task['task_id']} -> {task.get('target_output')}")
        return 2
    errs = schema_validate(envelope, "agent_result_envelope")
    if errs:
        raise SystemExit("Agent envelope validation failed:\n" + "\n".join(errs))
    payload = envelope["result"]
    out_schema = task.get("output_schema")
    if out_schema:
        errs = schema_validate(payload, out_schema)
        if errs:
            raise SystemExit(f"{out_schema} validation failed:\n" + "\n".join(errs))
    tasks_ancestor = next((p for p in tp.parents if p.name == "tasks"), None)
    if tasks_ancestor is None:
        raise SystemExit(f"Task path is not inside a workspace tasks/ directory: {tp}")
    root = tasks_ancestor.parent
    target = root / task["target_output"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    runs = root / "agent_runs" / task["task_id"]
    runs.mkdir(parents=True, exist_ok=True)
    idx = len(list(runs.glob("run-*.json"))) + 1
    (runs / f"run-{idx:03d}.json").write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: {task['task_id']} -> {target}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--adapter")
    ap.add_argument("--model")
    ap.add_argument("--replay")
    ap.add_argument("--fixture", action="store_true", default=None)
    args = ap.parse_args()
    raise SystemExit(run(args.task, adapter=args.adapter, model=args.model, replay_dir=args.replay, fixture=args.fixture))


if __name__ == "__main__":
    main()
