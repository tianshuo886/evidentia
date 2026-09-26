#!/usr/bin/env python3
"""Unified CLI and Host-agnostic workflow orchestrator for Evidentia v1.0.

Supports:
- run: step-by-step or automated advancement through the Evidentia state machine
- status: inspect current phase, artifacts, and task status
- next: identify the next active task packet or gate
- task: show or generate active agent task packets
- submit: validate and submit Host Agent results (Section 8 Generic Host Protocol)
- validate: execute schema and gate validation across all available artifacts
- resume: resume execution from saved state with tamper and invalidation checks
- memory: full Frozen Research Memory management interface (commit, search, inspect, verify)
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

def sh(*args):
    cmd = [PY] + list(args)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + res.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()

def run_workflow(args):
    out_dir = Path(args.out)
    rs_path = out_dir / 'run_state.json'
    mode = getattr(args, 'mode', 'standard') or 'standard'
    
    # 1. Initialization if not started
    if not rs_path.exists():
        if not args.pdf:
            sys.exit("Error: --pdf required to initialize run")
        supp_args = []
        for s in (args.supplement or []):
            supp_args.extend(['--supplement', s])
            
        print("[1/8] Initializing source-only workspace...")
        sh(str(HERE / 'init_run.py'), '--pdf', args.pdf, '--out', str(out_dir), *supp_args)
        
        print("[2/8] Reconstructing paper source evidence (text + visual track)...")
        sh(str(HERE / 'extract_structure.py'), '--pdf', str(out_dir / 'source/paper.pdf'), '--out', str(out_dir / 'model/source_map.json'), *supp_args)
        sh(str(HERE / 'extract_figs.py'), '--pdf', str(out_dir / 'source/paper.pdf'), '--out', str(out_dir / 'assets/figures'), '--inventory', str(out_dir / 'model/figure_inventory.json'))
        sh(str(HERE / 'link_mentions.py'), '--source-map', str(out_dir / 'model/source_map.json'), '--inventory', str(out_dir / 'model/figure_inventory.json'))
        
        # Advance phases
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'SOURCE_RECONSTRUCTION')
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'SOURCE_LOCK')
        
        # Generate Open Reading task
        import task_protocol
        t_path = task_protocol.create_open_reading_task(out_dir)
        print(f"[3/8] Generated Open Reading task at {t_path}")

    rs = json.loads(rs_path.read_text(encoding='utf-8'))
    phase = rs.get('phase')
    
    # 2. Open Reading execution
    if phase == 'SOURCE_LOCK':
        pm_path = out_dir / 'model/paper_model.json'
        if not pm_path.exists():
            print("[3/8] Executing Open Reading Agent (source-only, O/I/A separation)...")
            sh(str(HERE / 'open_reading_agent.py'), '--task', str(out_dir / 'tasks/open_reading.json'))

        print("[4/8] Locking Open Reading Baseline...")
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'OPEN_READING')
        sh(str(HERE / 'snapshot_baseline.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'BASELINE_LOCK')
        
        import task_protocol
        task_protocol.create_lens_tasks(out_dir)
        rs = json.loads(rs_path.read_text(encoding='utf-8'))
        phase = rs.get('phase')

    # 3. Six Lens Execution (Standard Mode or Ensemble Mode)
    if phase == 'BASELINE_LOCK':
        lenses = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')
        if mode == 'ensemble':
            print("[5/8] Executing Multi-Model Ensemble Mode across independent models...")
            models = ["model-alpha", "model-beta"]
            for l in lenses:
                runs_dir = out_dir / 'lens_runs' / l
                runs_dir.mkdir(parents=True, exist_ok=True)
                for idx, m in enumerate(models, 1):
                    run_file = runs_dir / f"run-{idx:03d}.json"
                    if not run_file.exists():
                        sh(str(HERE / 'lens_agent.py'), '--task', str(out_dir / 'tasks/lens' / f'{l}.json'), '--out', str(run_file), '--model', m)
                # Reconcile within lens
                sh(str(HERE / 'within_lens_reconciliation.py'), '--runs-dir', str(runs_dir), '--lens', l, '--out', str(out_dir / 'lens' / f'{l}.json'))
            
            # Adaptive Model Escalation
            sh(str(HERE / 'adaptive_escalation.py'), '--lens-dir', str(out_dir / 'lens'), '--out', str(out_dir / 'model/escalations.json'))
        else:
            print("[5/8] Executing Six Independent Lenses (Standard Mode)...")
            for l in lenses:
                lp = out_dir / 'lens' / f'{l}.json'
                if not lp.exists():
                    sh(str(HERE / 'lens_agent.py'), '--task', str(out_dir / 'tasks/lens' / f'{l}.json'), '--out', str(lp))

        print("[6/8] Validating 6 independent Lenses and Reconciling...")
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'LENS_EXECUTION')
        sh(str(HERE / 'merge_lenses.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'RECONCILIATION')
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'VERIFICATION')
        
        print("[7/8] Building Evidence Graph and Final Model...")
        sh(str(HERE / 'build_graph.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'FINAL_MODEL')
        
        print("[8/8] Hardened Freeze Check & Rendering Reader...")
        sh(str(HERE / 'freeze_check.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'FREEZE')
        sh(str(HERE / 'render_reader.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'RENDER')
        sh(str(HERE / 'reader_audit.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'COMPLETE')
        print(f"\n>>> Evidentia run COMPLETE! Final Reader ready at {out_dir}/reader/reader.html")
        return 0

    if phase == 'COMPLETE':
        print(f">>> Run is already COMPLETE at {out_dir}. Reader: {out_dir}/reader/reader.html")
        return 0
        
    print(f">>> Current phase: {phase}. Run 'evidentia.py next --out {out_dir}' to inspect next step.")
    return 0

def handle_status(args):
    print(sh(str(HERE / 'phase.py'), '--out', args.out, '--status'))

def handle_next(args):
    out_dir = Path(args.out)
    rs_p = out_dir / 'run_state.json'
    if not rs_p.exists():
        print("Run not initialized. Next: run with --pdf <path> --out <dir>")
        return
    rs = json.loads(rs_p.read_text(encoding='utf-8'))
    phase = rs.get('phase')
    if phase == 'SOURCE_LOCK':
        if not (out_dir / 'model/paper_model.json').exists():
            print("Next: Complete tasks/open_reading.json -> submit via 'evidentia submit --task TASK-OPEN-READING --result <file>'")
            return
    elif phase == 'BASELINE_LOCK':
        missing = [l for l in ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual') if not (out_dir / 'lens' / f'{l}.json').exists()]
        if missing:
            print(f"Next: Complete Lens tasks in tasks/lens/ for: {', '.join(missing)}")
            return
    print(sh(str(HERE / 'phase.py'), '--out', args.out, '--next'))

def handle_submit(args):
    """Generic Host Protocol: submit Host Agent result and promote state (Section 8)."""
    out_dir = Path(args.out)
    result_path = Path(args.result)
    if not result_path.exists():
        sys.exit(f"Error: Result file {result_path} does not exist.")

    sys.path.insert(0, str(HERE))
    from validate_common import load_json, schema_validate
    res_data = load_json(result_path)

    # If envelope is used
    payload = res_data.get('result', res_data)
    task_id = args.task or res_data.get('task_id', '')

    if 'OPEN-READING' in task_id.upper():
        target = out_dir / 'model/paper_model.json'
        errs = schema_validate(payload, 'paper_model')
        if errs:
            sys.exit(f"Submission failed paper_model schema validation:\n{errs}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f"OK: Submitted {task_id} -> {target}")
        # Run next workflow step
        sh(str(HERE / 'evidentia.py'), 'run', '--out', str(out_dir))
    elif 'LENS' in task_id.upper():
        lens_name = payload.get('lens') or (task_id.split('-')[-1].lower() if '-' in task_id else 'author')
        target = out_dir / 'lens' / f'{lens_name}.json'
        errs = schema_validate(payload, 'lens')
        if errs:
            sys.exit(f"Submission failed lens schema validation:\n{errs}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f"OK: Submitted {task_id} -> {target}")
    else:
        sys.exit(f"Unsupported task submission type: {task_id}")

def handle_validate(args):
    out_dir = Path(args.out)
    print(f"Validating artifacts in {out_dir}...")
    from validate_common import load_json, schema_validate
    checks = [
        ('model/source_map.json', 'source_map'),
        ('model/figure_inventory.json', 'figure_inventory'),
        ('model/paper_model.json', 'paper_model'),
        ('model/open_reading_manifest.json', 'open_reading_manifest'),
        ('model/evidence_graph.json', 'evidence_graph'),
        ('model/manifest.json', 'manifest')
    ]
    passed = 0
    total = 0
    for rel, schema_name in checks:
        fp = out_dir / rel
        if fp.exists():
            total += 1
            errs = schema_validate(load_json(fp), schema_name)
            if errs:
                print(f"FAIL {rel}: {errs}")
            else:
                passed += 1
                print(f"OK   {rel}")
    print(f"Validation summary: {passed}/{total} present artifacts passed schema validation.")

def handle_resume(args):
    print(sh(str(HERE / 'phase.py'), '--out', args.out, '--resume'))

def handle_memory(args, extra_args):
    cmd = [PY, str(HERE / 'memory_manager.py'), args.memory_action] + extra_args
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + res.stderr)
        sys.exit(res.returncode)
    print(res.stdout.strip())

def main():
    ap = argparse.ArgumentParser(description="Evidentia Unified Workflow CLI v1.0")
    sp = ap.add_subparsers(dest='command', required=True)

    # run
    p_run = sp.add_parser('run', help="Run workflow advancement")
    p_run.add_argument('--pdf', help="Source paper PDF path")
    p_run.add_argument('--out', required=True, help="Output directory")
    p_run.add_argument('--supplement', action='append', default=[], help="Optional supplement PDF")
    p_run.add_argument('--mode', choices=['standard', 'ensemble'], default='standard')

    # status
    p_status = sp.add_parser('status', help="Show current workflow status")
    p_status.add_argument('--out', required=True)

    # next
    p_next = sp.add_parser('next', help="Show next task or phase")
    p_next.add_argument('--out', required=True)

    # submit
    p_sub = sp.add_parser('submit', help="Submit Host Agent result")
    p_sub.add_argument('--task', required=True, help="Task ID (e.g. TASK-OPEN-READING)")
    p_sub.add_argument('--result', required=True, help="Path to result JSON")
    p_sub.add_argument('--out', required=True, help="Output run directory")

    # validate
    p_val = sp.add_parser('validate', help="Validate schemas and gates")
    p_val.add_argument('--out', required=True)

    # resume
    p_res = sp.add_parser('resume', help="Resume run with tamper/invalidation check")
    p_res.add_argument('--out', required=True)

    # memory
    p_mem = sp.add_parser('memory', help="Frozen Research Memory operations")
    p_mem.add_argument('memory_action', choices=['commit-paper', 'commit-project', 'record-outcome', 'search', 'verify', 'rebuild-index'])

    args, unknown = ap.parse_known_args()
    if args.command == 'run':
        return run_workflow(args)
    elif args.command == 'status':
        return handle_status(args)
    elif args.command == 'next':
        return handle_next(args)
    elif args.command == 'submit':
        return handle_submit(args)
    elif args.command == 'validate':
        return handle_validate(args)
    elif args.command == 'resume':
        return handle_resume(args)
    elif args.command == 'memory':
        return handle_memory(args, unknown)

if __name__ == '__main__':
    main()
