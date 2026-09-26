#!/usr/bin/env python3
"""Host-Agent Lens Runner Shell for Evidentia v1.1.

Strictly adheres to Section 5 and Section 13:
- Mode A: Dispatches Lens AgentTask to configured Host Agent / Replay / Fixture
- Mode B: Sets WAITING_FOR_LENS_AGENTS and stops cleanly
- Zero fabrication of scientific findings in production code.
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate
from agent_dispatch import dispatch_agent_task
from agent_submit import submit_agent_result

def run_lens(task_path, out_path=None, result_file=None, model=None, host=None, fixture=False, replay_dir=None, adapter=None):
    tp = Path(task_path)
    if not tp.exists():
        sys.exit(f"Error: Task packet not found at {tp}")

    task = load_json(tp)
    lens = task['lens']
    root = tp.parent.parent
    if tp.parent.name == 'lens':
        root = tp.parent.parent.parent

    target_out = Path(out_path) if out_path else (root / task.get('target_output', task.get('output', f'lens/{lens}.json')))

    # If external result file supplied
    if result_file:
        submit_agent_result(root, task.get('task_id', f'TASK-LENS-{lens.upper()}'), result_file)
        return 0

    # Dispatch to Host Agent / Replay / Fixture
    envelope = dispatch_agent_task(tp, adapter=adapter, model=model, replay_dir=replay_dir, fixture=fixture)
    if envelope is not None:
        errs = schema_validate(envelope, 'agent_result_envelope')
        if errs:
            sys.exit(f"Host Agent result failed agent_result_envelope schema validation:\n{errs}")

        payload = envelope['result']
        lens_errs = schema_validate(payload, 'lens')
        if lens_errs:
            sys.exit(f"Host Agent result failed lens schema validation:\n{lens_errs}")

        target_out.parent.mkdir(parents=True, exist_ok=True)
        target_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        runs_dir = root / f'agent_runs/TASK-LENS-{lens.upper()}'
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_idx = len(list(runs_dir.glob('run-*.json'))) + 1
        (runs_dir / f"run-{run_idx:03d}.json").write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        print(f"OK: Lens {lens} successfully completed by {envelope.get('executor', {}).get('model', 'agent')} -> {target_out}")
        return 0

    # Mode B: Submission boundary when no agent is active
    rs_p = root / 'run_state.json'
    if rs_p.exists():
        rs = load_json(rs_p)
        rs['phase'] = 'WAITING_FOR_LENS_AGENTS'
        rs_p.write_text(json.dumps(rs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"\n[WAITING_FOR_AGENT] Lens task {lens} ready at: {tp}")
    print(f"Evidentia has paused in WAITING_FOR_LENS_AGENTS state.")
    print(f"Submit completed lens pass via:")
    print(f"  evidentia.py submit --out {root} --task TASK-LENS-{lens.upper()} --result <file.json>\n")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Evidentia Lens Agent Runner")
    ap.add_argument('--task', required=True)
    ap.add_argument('--out')
    ap.add_argument('--result')
    ap.add_argument('--model')
    ap.add_argument('--host')
    ap.add_argument('--fixture', action='store_true', help="Enable isolated synthetic fixture for testing")
    ap.add_argument('--replay', help="Directory containing recorded replay envelopes")
    ap.add_argument('--adapter')
    args = ap.parse_args()
    run_lens(
        args.task,
        out_path=args.out,
        result_file=args.result,
        model=args.model,
        host=args.host,
        fixture=args.fixture,
        replay_dir=args.replay,
        adapter=args.adapter
    )

if __name__ == '__main__':
    main()
