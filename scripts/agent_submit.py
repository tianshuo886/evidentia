#!/usr/bin/env python3
"""Submission handler for Host Agent results (Generic Host Protocol).

Validates submitted AgentResultEnvelope against schema and phase invariants,
unpacks result payload to target path, and updates run_state.json.
"""
import argparse, json, os, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256

def submit_agent_result(run_dir, task_id, result_path):
    r_dir = Path(run_dir)
    res_p = Path(result_path)
    if not res_p.exists():
        sys.exit(f"Error: Result file not found at {res_p}")

    raw_data = load_json(res_p)

    # Check if wrapped in AgentResultEnvelope
    if 'result' in raw_data and 'executor' in raw_data:
        envelope = raw_data
        payload = envelope['result']
    else:
        # Wrap raw result into standard envelope
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = raw_data
        envelope = {
            "task_id": task_id,
            "execution_kind": "HOST_AGENT",
            "executor": {
                "kind": "HOST_AGENT",
                "host": "external-host-agent",
                "model": "submitted-model",
                "started_at": now_iso,
                "completed_at": now_iso
            },
            "started_at": now_iso,
            "completed_at": now_iso,
            "result": payload
        }

    # Validate envelope
    errs = schema_validate(envelope, 'agent_result_envelope')
    if errs:
        sys.exit(f"REFUSED: Submitted result failed agent_result_envelope schema validation:\n{errs}")

    task_upper = task_id.upper()
    target_output = None
    output_schema = None

    if 'OPEN-READING' in task_upper or 'OPEN_READING' in task_upper:
        output_schema = 'paper_model'
        target_output = r_dir / 'model/paper_model.json'
    elif 'LENS' in task_upper:
        output_schema = 'lens'
        lens_name = payload.get('lens')
        if not lens_name:
            for l in ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual'):
                if l in task_id.lower():
                    lens_name = l
                    break
        target_output = r_dir / f'lens/{lens_name}.json'
    elif 'RECONCILIATION' in task_upper:
        output_schema = 'lens_reconciliation'
        target_output = r_dir / 'model/lens_reconciliation.json'
    elif 'VERIF' in task_upper:
        output_schema = 'verification_result'
        target_id = payload.get('target_id', 'result')
        target_output = r_dir / f'verification/{target_id}.json'
    elif 'APPLY' in task_upper:
        output_schema = 'research_delta'
        proj_id = payload.get('project', {}).get('name', 'project')
        target_output = r_dir / f'apply/{proj_id}/research_delta.json'

    if output_schema:
        schema_errs = schema_validate(payload, output_schema)
        if schema_errs:
            sys.exit(f"REFUSED: Submitted payload failed {output_schema} schema validation:\n{schema_errs}")

    if target_output:
        target_output.parent.mkdir(parents=True, exist_ok=True)
        target_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f"OK: Saved validated Host Agent result -> {target_output}")

    # Record envelope in run_dir/agent_runs/
    runs_dir = r_dir / 'agent_runs' / task_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_idx = len(list(runs_dir.glob('run-*.json'))) + 1
    (runs_dir / f"run-{run_idx:03d}.json").write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    return 0

def main():
    ap = argparse.ArgumentParser(description="Evidentia Host Agent Result Submitter")
    ap.add_argument('--run-dir', '--out', required=True, dest='run_dir')
    ap.add_argument('--task', required=True)
    ap.add_argument('--result', required=True)
    args = ap.parse_args()
    submit_agent_result(args.run_dir, args.task, args.result)

if __name__ == '__main__':
    main()
