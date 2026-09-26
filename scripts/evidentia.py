#!/usr/bin/env python3
"""Unified CLI and Host-agnostic workflow orchestrator for Evidentia v1.1.

Supports:
- run: step-by-step or automated advancement through the Evidentia state machine
- status: inspect current phase, artifacts, and task status
- next: identify the next active task packet or gate
- task: show or generate active agent task packets
- submit: validate and submit Host Agent results (Generic Host Protocol)
- validate: execute schema and gate validation across all available artifacts
- resume: resume execution from saved state with tamper and invalidation checks
- memory: full Frozen Research Memory management interface (commit, search, inspect, relation, snapshot, export, import)
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
    extra_flags = []
    from agent_dispatch import is_fixture_enabled
    if is_fixture_enabled(getattr(args, 'fixture', None)):
        extra_flags.append('--fixture')
    if getattr(args, 'replay', None):
        extra_flags.extend(['--replay', args.replay])
    if getattr(args, 'adapter', None):
        extra_flags.extend(['--adapter', args.adapter])

    # 1. Initialization if not started
    if not rs_path.exists():
        if not getattr(args, 'pdf', None):
            sys.exit("Error: --pdf required to initialize run")
        supp_args = []
        for s in (getattr(args, 'supplement', []) or []):
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
        
        # Generate evidence bundles for Host Agent consumption (Section 12)
        sh(str(HERE / 'evidence_bundle.py'), '--out', str(out_dir))

        # Generate Open Reading task
        import task_protocol
        t_path = task_protocol.create_open_reading_task(out_dir)
        print(f"[3/8] Generated Open Reading task at {t_path}")

    rs = json.loads(rs_path.read_text(encoding='utf-8'))
    phase = rs.get('phase')
    
    # 2. Open Reading execution
    if phase in ('SOURCE_LOCK', 'OPEN_READING_TASK_READY', 'WAITING_FOR_OPEN_READING_AGENT'):
        pm_path = out_dir / 'model/paper_model.json'
        if not pm_path.exists():
            print("[3/8] Executing Open Reading Agent (source-only, O/I/A separation)...")
            sh(str(HERE / 'open_reading_agent.py'), '--task', str(out_dir / 'tasks/open_reading.json'), *extra_flags)

        if not pm_path.exists():
            print(f">>> Workflow paused in WAITING_FOR_OPEN_READING_AGENT. Submit results to continue.")
            return 0

        print("[4/8] Locking Open Reading Baseline...")
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'OPEN_READING')
        sh(str(HERE / 'snapshot_baseline.py'), '--out', str(out_dir))
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'BASELINE_LOCK')
        
        import task_protocol
        task_protocol.create_lens_tasks(out_dir)
        rs = json.loads(rs_path.read_text(encoding='utf-8'))
        phase = rs.get('phase')

    # 3. Six Lens Execution (Standard Mode or Ensemble Mode)
    if phase in ('BASELINE_LOCK', 'LENS_TASKS_READY', 'WAITING_FOR_LENS_AGENTS'):
        lenses = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')
        if mode == 'ensemble':
            print("[5/8] Executing Multi-Model Ensemble Mode across independent models...")
            models = ["ensemble-model-1", "ensemble-model-2"]
            if getattr(args, 'models', None):
                models = [m.strip() for m in args.models.split(',')]

            for l in lenses:
                runs_dir = out_dir / 'lens_runs' / l
                runs_dir.mkdir(parents=True, exist_ok=True)
                for idx, m in enumerate(models, 1):
                    run_file = runs_dir / f"run-{idx:03d}.json"
                    if not run_file.exists():
                        sh(str(HERE / 'lens_agent.py'), '--task', str(out_dir / 'tasks/lens' / f'{l}.json'), '--out', str(run_file), '--model', m, *extra_flags)
                # Reconcile within lens
                sh(str(HERE / 'within_lens_reconciliation.py'), '--runs-dir', str(runs_dir), '--lens', l, '--out', str(out_dir / 'lens' / f'{l}.json'))
            
            # Adaptive Model Escalation
            sh(str(HERE / 'adaptive_escalation.py'), '--lens-dir', str(out_dir / 'lens'), '--out', str(out_dir / 'model/escalations.json'))
        else:
            print("[5/8] Executing Six Independent Lenses (Standard Mode)...")
            for l in lenses:
                lp = out_dir / 'lens' / f'{l}.json'
                if not lp.exists():
                    sh(str(HERE / 'lens_agent.py'), '--task', str(out_dir / 'tasks/lens' / f'{l}.json'), '--out', str(lp), *extra_flags)

        missing_lenses = [l for l in lenses if not (out_dir / 'lens' / f'{l}.json').exists()]
        if missing_lenses:
            print(f">>> Workflow paused in WAITING_FOR_LENS_AGENTS. Missing: {', '.join(missing_lenses)}")
            return 0

        print("[6/8] Validating 6 independent Lenses and Reconciling...")
        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'LENS_EXECUTION')
        sh(str(HERE / 'merge_lenses.py'), '--out', str(out_dir), *extra_flags)

        # Artifact completeness gate for RECONCILIATION
        rec_p = out_dir / 'model/lens_reconciliation.json'
        if not rec_p.exists():
            print(">>> Workflow paused in WAITING_FOR_RECONCILIATION_AGENT.")
            return 0
        from validate_common import load_json, schema_validate
        rec_data = load_json(rec_p)
        rec_errs = schema_validate(rec_data, 'lens_reconciliation')
        if rec_errs:
            sys.exit(f"Reconciliation validation failed:\n{rec_errs}")

        sh(str(HERE / 'phase.py'), '--out', str(out_dir), '--complete', 'RECONCILIATION')

        # Artifact completeness gate for VERIFICATION
        pm_p = out_dir / 'model/paper_model.json'
        pm_data = load_json(pm_p) if pm_p.exists() else {}
        conflicts = pm_data.get('lens_conflicts', [])
        items_needing_verif = [
            it for it in rec_data.get('items', [])
            if it.get('requires_verification') or it.get('status') in ('TENSION', 'CONTRADICTION')
        ]

        all_verified = True
        for it in items_needing_verif:
            v_stat = it.get('verifier_status')
            if not v_stat or v_stat in ('PENDING', 'PENDING_VERIFICATION', 'UNRESOLVED'):
                all_verified = False
                break
        for c in conflicts:
            v_stat = c.get('verifier_status')
            if not v_stat or v_stat in ('PENDING', 'PENDING_VERIFICATION', 'UNRESOLVED'):
                all_verified = False
                break

        if (items_needing_verif or conflicts) and not all_verified:
            print(">>> Workflow paused in WAITING_FOR_VERIFIERS. Verification results pending.")
            return 0

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
    if phase in ('SOURCE_LOCK', 'OPEN_READING_TASK_READY', 'WAITING_FOR_OPEN_READING_AGENT'):
        if not (out_dir / 'model/paper_model.json').exists():
            print("Next: Complete tasks/open_reading.json -> submit via 'evidentia submit --out <dir> --task TASK-OPEN-READING --result <file>'")
            return
    elif phase in ('BASELINE_LOCK', 'LENS_TASKS_READY', 'WAITING_FOR_LENS_AGENTS'):
        missing = [l for l in ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual') if not (out_dir / 'lens' / f'{l}.json').exists()]
        if missing:
            print(f"Next: Complete Lens tasks in tasks/lens/ for: {', '.join(missing)}")
            return
    print(sh(str(HERE / 'phase.py'), '--out', args.out, '--next'))

def handle_submit(args):
    """Generic Host Protocol: submit Host Agent result and promote state (Section 8)."""
    from agent_submit import submit_agent_result
    submit_agent_result(args.out, args.task, args.result)

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

def handle_memory(args):
    sub = args.memory_cmd
    mem_root = args.memory_root
    if sub == 'commit-paper':
        sh(str(HERE / 'memory_manager.py'), 'commit-paper', '--paper', args.paper, *(['--memory-root', mem_root] if mem_root else []))
    elif sub == 'commit-project':
        sh(str(HERE / 'memory_manager.py'), 'commit-project', '--paper', args.paper, '--project', args.project, *(['--memory-root', mem_root] if mem_root else []))
    elif sub == 'record-outcome':
        extra = []
        if args.conditions:
            extra.extend(['--conditions', args.conditions])
        if mem_root:
            extra.extend(['--memory-root', mem_root])
        sh(str(HERE / 'memory_manager.py'), 'record-outcome', '--project', args.project, '--experiment', args.experiment, '--verdict', args.verdict, '--findings', args.findings, *extra)
    elif sub == 'relation':
        extra = []
        if args.source_paper:
            extra.extend(['--source-paper', args.source_paper])
        if args.target_paper:
            extra.extend(['--target-paper', args.target_paper])
        if args.evidence:
            extra.extend(['--evidence'] + args.evidence)
        if mem_root:
            extra.extend(['--memory-root', mem_root])
        sh(str(HERE / 'memory_relation.py'), 'add', '--source', args.source, '--target', args.target, '--type', args.type, '--reason', args.reason, *extra)
    elif sub == 'inspect':
        sh(str(HERE / 'memory_manager.py'), 'inspect', '--id', args.id, *(['--memory-root', mem_root] if mem_root else []))
    elif sub == 'snapshot':
        extra = []
        if args.out:
            extra.extend(['--out', args.out])
        if mem_root:
            extra.extend(['--memory-root', mem_root])
        sh(str(HERE / 'memory_snapshot.py'), *extra)
    elif sub == 'export':
        extra = []
        if args.out:
            extra.extend(['--out', args.out])
        if mem_root:
            extra.extend(['--memory-root', mem_root])
        sh(str(HERE / 'memory_export.py'), *extra)
    elif sub == 'import':
        extra = ['--file', args.file]
        if mem_root:
            extra.extend(['--memory-root', mem_root])
        sh(str(HERE / 'memory_import.py'), *extra)
    elif sub == 'search':
        extra = ['--query', args.query]
        if args.type:
            extra.extend(['--type', args.type])
        if mem_root:
            extra.extend(['--memory-root', mem_root])
        sh(str(HERE / 'memory_manager.py'), 'search', *extra)
    elif sub == 'verify':
        sh(str(HERE / 'memory_manager.py'), 'verify', *(['--memory-root', mem_root] if mem_root else []))
    elif sub == 'rebuild-index':
        sh(str(HERE / 'memory_manager.py'), 'rebuild-index', *(['--memory-root', mem_root] if mem_root else []))

def main():
    parser = argparse.ArgumentParser(description="Evidentia Research OS Unified Orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser("run")
    p_run.add_argument("--pdf", help="Source paper PDF")
    p_run.add_argument("--out", required=True, help="Workspace output directory")
    p_run.add_argument("--mode", choices=["standard", "ensemble"], default="standard")
    p_run.add_argument("--models", help="Comma-separated model identifiers for ensemble mode")
    p_run.add_argument("--supplement", action="append", help="Supplementary PDF files")
    p_run.add_argument("--fixture", action="store_true", help="Use isolated synthetic test fixtures")
    p_run.add_argument("--replay", help="Recorded replay directory")
    p_run.add_argument("--adapter", help="Host agent adapter name (e.g. pi, generic)")

    # status
    p_stat = subparsers.add_parser("status")
    p_stat.add_argument("--out", required=True)

    # next
    p_next = subparsers.add_parser("next")
    p_next.add_argument("--out", required=True)

    # submit
    p_sub = subparsers.add_parser("submit")
    p_sub.add_argument("--out", required=True)
    p_sub.add_argument("--task", required=True)
    p_sub.add_argument("--result", required=True)

    # validate
    p_val = subparsers.add_parser("validate")
    p_val.add_argument("--out", required=True)

    # resume
    p_res = subparsers.add_parser("resume")
    p_res.add_argument("--out", required=True)

    # memory
    p_mem = subparsers.add_parser("memory")
    p_mem.add_argument("--memory-root")
    mem_subs = p_mem.add_subparsers(dest="memory_cmd", required=True)

    # memory commit-paper
    m_cp = mem_subs.add_parser("commit-paper")
    m_cp.add_argument("--paper", required=True)

    # memory commit-project
    m_cprj = mem_subs.add_parser("commit-project")
    m_cprj.add_argument("--paper", required=True)
    m_cprj.add_argument("--project", required=True)

    # memory record-outcome
    m_ro = mem_subs.add_parser("record-outcome")
    m_ro.add_argument("--project", required=True)
    m_ro.add_argument("--experiment", required=True)
    m_ro.add_argument("--verdict", choices=["SUCCESS", "FAILURE", "PARTIAL_SUCCESS", "INCONCLUSIVE"], required=True)
    m_ro.add_argument("--findings", required=True)
    m_ro.add_argument("--conditions")

    # memory relation
    m_rel = mem_subs.add_parser("relation")
    m_rel.add_argument("--source", required=True)
    m_rel.add_argument("--target", required=True)
    m_rel.add_argument("--type", required=True)
    m_rel.add_argument("--reason", required=True)
    m_rel.add_argument("--source-paper")
    m_rel.add_argument("--target-paper")
    m_rel.add_argument("--evidence", nargs="*")

    # memory inspect
    m_ins = mem_subs.add_parser("inspect")
    m_ins.add_argument("--id", required=True)

    # memory snapshot
    m_snap = mem_subs.add_parser("snapshot")
    m_snap.add_argument("--out")

    # memory export
    m_exp = mem_subs.add_parser("export")
    m_exp.add_argument("--out")

    # memory import
    m_imp = mem_subs.add_parser("import")
    m_imp.add_argument("--file", required=True)

    # memory search
    m_search = mem_subs.add_parser("search")
    m_search.add_argument("--query", required=True)
    m_search.add_argument("--type")

    # memory verify
    mem_subs.add_parser("verify")

    # memory rebuild-index
    mem_subs.add_parser("rebuild-index")

    args = parser.parse_args()
    if args.command == "run":
        run_workflow(args)
    elif args.command == "status":
        handle_status(args)
    elif args.command == "next":
        handle_next(args)
    elif args.command == "submit":
        handle_submit(args)
    elif args.command == "validate":
        handle_validate(args)
    elif args.command == "resume":
        handle_resume(args)
    elif args.command == "memory":
        handle_memory(args)

if __name__ == "__main__":
    main()
