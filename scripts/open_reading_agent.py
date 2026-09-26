#!/usr/bin/env python3
"""Standard Open Reading Agent Shell for Evidentia v1.1.

Strictly adheres to Section 5.1:
- Mode A: Dispatches AgentTask to configured Host Agent / Replay / Fixture
- Mode B: Sets WAITING_FOR_OPEN_READING_AGENT and stops cleanly
- Zero fabrication of scientific claims, interpretations, or assessments in production.
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate
from agent_dispatch import dispatch_agent_task
from agent_submit import submit_agent_result

def run_open_reading(task_path, out_path=None, result_file=None, fixture=False, replay_dir=None, adapter=None, model=None):
    tp = Path(task_path)
    if not tp.exists():
        sys.exit(f"Error: Task packet not found at {tp}")

    task = load_json(tp)
    root = tp.parent.parent
    target_out = Path(out_path) if out_path else (root / task.get('target_output', 'model/paper_model.json'))

    # If external result file is supplied
    if result_file:
        submit_agent_result(root, task.get('task_id', 'TASK-OPEN-READING'), result_file)
        return 0

    # Dispatch to Host Agent / Replay / Fixture
    envelope = dispatch_agent_task(tp, adapter=adapter, model=model, replay_dir=replay_dir, fixture=fixture)
    if envelope is not None:
        errs = schema_validate(envelope, 'agent_result_envelope')
        if errs:
            sys.exit(f"Host Agent result failed agent_result_envelope schema validation:\n{errs}")
        
        payload = envelope['result']
        pm_errs = schema_validate(payload, 'paper_model')
        if pm_errs:
            sys.exit(f"Host Agent result failed paper_model schema validation:\n{pm_errs}")

        target_out.parent.mkdir(parents=True, exist_ok=True)
        target_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        runs_dir = root / 'agent_runs/TASK-OPEN-READING'
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / 'run-001.json').write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        print(f"OK: Open Reading successfully completed by {envelope.get('executor', {}).get('host', 'agent')} -> {target_out}")
        return 0

    # Mode B: Submission boundary when no agent is active
    rs_p = root / 'run_state.json'
    if rs_p.exists():
        rs = load_json(rs_p)
        rs['phase'] = 'WAITING_FOR_OPEN_READING_AGENT'
        rs_p.write_text(json.dumps(rs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"\n[WAITING_FOR_AGENT] Open Reading task ready at: {tp}")
    print(f"Evidentia has paused in WAITING_FOR_OPEN_READING_AGENT state.")
    print(f"Submit completed reading via:")
    print(f"  evidentia.py submit --out {root} --task TASK-OPEN-READING --result <file.json>\n")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Evidentia Open Reading Agent Runner")
    ap.add_argument('--task', required=True)
    ap.add_argument('--out')
    ap.add_argument('--result')
    ap.add_argument('--fixture', action='store_true', help="Enable isolated synthetic fixture for testing")
    ap.add_argument('--replay', help="Directory containing recorded replay envelopes")
    ap.add_argument('--adapter')
    ap.add_argument('--model')
    args = ap.parse_args()
    run_open_reading(
        args.task,
        out_path=args.out,
        result_file=args.result,
        fixture=args.fixture,
        replay_dir=args.replay,
        adapter=args.adapter,
        model=args.model
    )

if __name__ == '__main__':
    main()
