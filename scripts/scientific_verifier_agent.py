#!/usr/bin/env python3
"""Scientific Verifier Agent for Evidentia v1.1.

Evaluates candidate assertions against localized evidence packets:
- Receives AgentTask / verification task packet
- Evaluates statement against localized evidence (text, captions, tables, visual asset)
- Assigns verdict in: SUPPORTED, PARTIAL, REJECTED, AMBIGUOUS, INSUFFICIENT_EVIDENCE
- Cites specific evidence IDs and reasoned justification
- Zero keyword-overlap auto-verdicts in production.
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate
from agent_dispatch import dispatch_agent_task
from agent_submit import submit_agent_result

def run_scientific_verifier(task_path, out_path=None, result_file=None, fixture=False, replay_dir=None, adapter=None, model=None):
    tp = Path(task_path)
    if not tp.exists():
        sys.exit(f"Error: Verification task packet not found at {tp}")

    task = load_json(tp)
    target_id = task.get('target_id', 'VERIF-01')
    root = tp.parent.parent
    if tp.parent.name == 'verification':
        root = tp.parent.parent.parent

    target_out = Path(out_path) if out_path else (root / task.get('target_output', f'verification/{target_id}.json'))

    # If external result file supplied
    if result_file:
        submit_agent_result(root, task.get('task_id', f'TASK-VERIF-{target_id}'), result_file)
        return 0

    # Dispatch to Host Agent / Replay / Fixture
    envelope = dispatch_agent_task(tp, adapter=adapter, model=model, replay_dir=replay_dir, fixture=fixture)
    if envelope is not None:
        errs = schema_validate(envelope, 'agent_result_envelope')
        if errs:
            sys.exit(f"Host Verifier result failed agent_result_envelope schema validation:\n{errs}")

        payload = envelope['result']
        v_errs = schema_validate(payload, 'verification_result')
        if v_errs:
            sys.exit(f"Host Verifier result failed verification_result schema validation:\n{v_errs}")

        target_out.parent.mkdir(parents=True, exist_ok=True)
        target_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        return payload

    # Mode B: Submission boundary
    rs_p = root / 'run_state.json'
    if rs_p.exists():
        rs = load_json(rs_p)
        rs['phase'] = 'WAITING_FOR_VERIFIERS'
        rs_p.write_text(json.dumps(rs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"\n[WAITING_FOR_AGENT] Verification task ready at: {tp}")
    print(f"Evidentia has paused in WAITING_FOR_VERIFIERS state.")
    return None

def main():
    ap = argparse.ArgumentParser(description="Evidentia Scientific Verifier Agent")
    ap.add_argument('--task', required=True)
    ap.add_argument('--out')
    ap.add_argument('--result')
    ap.add_argument('--fixture', action='store_true')
    ap.add_argument('--replay')
    ap.add_argument('--adapter')
    ap.add_argument('--model')
    args = ap.parse_args()
    run_scientific_verifier(
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
