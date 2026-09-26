#!/usr/bin/env python3
"""Semantic Cross-Lens Reconciliation Agent for Evidentia v1.1.

Evaluates candidate finding clusters across six independent lenses:
- Assigns semantic relation: AGREEMENT, COMPLEMENTARY, PARTIAL_AGREEMENT, TENSION, CONTRADICTION, ORTHOGONAL, UNRESOLVED
- Formulates canonical finding statement
- Identifies findings requiring localized evidence verification
- Strictly enforces Principle 4: NO majority voting.
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate
from agent_dispatch import dispatch_agent_task
from agent_submit import submit_agent_result

def run_reconciliation_agent(task_path, out_path=None, result_file=None, fixture=False, replay_dir=None, adapter=None, model=None):
    tp = Path(task_path)
    if not tp.exists():
        sys.exit(f"Error: Task packet not found at {tp}")

    task = load_json(tp)
    root = tp.parent.parent
    target_out = Path(out_path) if out_path else (root / task.get('target_output', 'model/lens_reconciliation.json'))

    # If external result file supplied
    if result_file:
        submit_agent_result(root, task.get('task_id', 'TASK-RECONCILIATION'), result_file)
        return 0

    # Dispatch to Host Agent / Replay / Fixture
    envelope = dispatch_agent_task(tp, adapter=adapter, model=model, replay_dir=replay_dir, fixture=fixture)
    if envelope is not None:
        errs = schema_validate(envelope, 'agent_result_envelope')
        if errs:
            sys.exit(f"Host Reconciliation Agent result failed agent_result_envelope schema validation:\n{errs}")

        payload = envelope['result']
        rec_errs = schema_validate(payload, 'lens_reconciliation')
        if rec_errs:
            sys.exit(f"Host Reconciliation Agent result failed lens_reconciliation schema validation:\n{rec_errs}")

        target_out.parent.mkdir(parents=True, exist_ok=True)
        target_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        return payload

    # Mode B: Submission boundary
    rs_p = root / 'run_state.json'
    if rs_p.exists():
        rs = load_json(rs_p)
        rs['phase'] = 'WAITING_FOR_RECONCILIATION_AGENT'
        rs_p.write_text(json.dumps(rs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"\n[WAITING_FOR_AGENT] Reconciliation task ready at: {tp}")
    print(f"Evidentia has paused in WAITING_FOR_RECONCILIATION_AGENT state.")
    print(f"Submit completed reconciliation via:")
    print(f"  evidentia.py submit --out {root} --task TASK-RECONCILIATION --result <file.json>\n")
    return None

def main():
    ap = argparse.ArgumentParser(description="Evidentia Semantic Reconciliation Agent")
    ap.add_argument('--task', required=True)
    ap.add_argument('--out')
    ap.add_argument('--result')
    ap.add_argument('--fixture', action='store_true', default=None)
    ap.add_argument('--replay')
    ap.add_argument('--adapter')
    ap.add_argument('--model')
    args = ap.parse_args()
    run_reconciliation_agent(
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
