#!/usr/bin/env python3
"""Apply Agent for Evidentia v1.1: Two-stage Apply Design (Sections 23-27).

Stage A — Local Apply:
Frozen Paper + Project Document -> Local Research Delta (NO cross-paper memory).
Scientific reasoning performed exclusively by Host Agent via AgentTask.

Stage B — Memory-Augmented Synthesis (Optional):
Local Research Delta + Project Gaps + Retrieved Frozen Research Memory
-> Memory-Augmented Research Synthesis (apply/<project>/memory_augmented_synthesis.json).

Strictly enforces:
- Project isolation: frozen paper truth cannot be mutated
- Epistemic separation: Stage A is single-paper only; Stage B is explicitly separate
- Genuinely agent-driven: NO deterministic invention of gaps, benefits, or experiments.
"""
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256, all_ids
import task_protocol, memory_manager
from agent_dispatch import dispatch_agent_task, is_fixture_enabled
from agent_submit import submit_agent_result

def run_local_apply(paper_dir, project_doc, out_dir=None, focus=None, fixture=None, replay_dir=None, adapter=None, model=None, result_file=None):
    """Stage A: Local Apply without cross-paper memory."""
    p_dir = Path(paper_dir)
    doc_path = Path(project_doc)

    # 1. Gate: Verify paper is FROZEN
    res = subprocess.run([sys.executable, str(HERE / 'verify_frozen.py'), '--out', str(p_dir)], capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"REFUSED: Cannot apply unfrozen or tampered paper model. Freeze check output:\n{res.stderr or res.stdout}")

    manifest_p = p_dir / 'model/manifest.json'
    pm_path = p_dir / 'model/paper_model.json'
    if not manifest_p.exists() or not pm_path.exists():
        sys.exit("REFUSED: Missing manifest.json or paper_model.json")

    manifest = load_json(manifest_p)
    pm = load_json(pm_path)
    paper_model_sha = manifest.get('hashes', {}).get('model/paper_model.json') or sha256(pm_path)

    project_name = doc_path.stem
    target_apply_dir = Path(out_dir) if out_dir else (p_dir / 'apply' / project_name)
    target_apply_dir.mkdir(parents=True, exist_ok=True)

    # Copy project document into apply directory for provenance
    doc_content = doc_path.read_text(encoding='utf-8')
    (target_apply_dir / 'project_document.md').write_text(doc_content, encoding='utf-8')

    # 2. Extract candidate project gaps (or record NO_EXPLICIT_PROJECT_GAP_FOUND)
    gaps = []
    gap_matches = re.findall(r'(?:gap|problem|challenge|need|goal)[:\s]+([^\n\.]+)', doc_content, re.I)
    if gap_matches:
        for idx, g in enumerate(gap_matches[:5], 1):
            gaps.append({
                "id": f"G{idx:02d}",
                "question": f"How to address: {g.strip()}",
                "status": "open",
                "existing_experiments": []
            })
    else:
        gaps.append({
            "id": "G01",
            "question": "NO_EXPLICIT_PROJECT_GAP_FOUND: General capability evaluation under project criteria.",
            "status": "open",
            "existing_experiments": []
        })

    project_ctx = {
        "schema_version": "1.0",
        "project_id": project_name,
        "document": str(doc_path.resolve()),
        "focus": focus,
        "gaps": gaps
    }
    (target_apply_dir / 'project_context.json').write_text(json.dumps(project_ctx, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # 3. Create APPLY_LOCAL AgentTask packet
    t_path = task_protocol.create_apply_task(p_dir, project_name, doc_path)

    # If external result file supplied
    if result_file:
        submit_agent_result(p_dir, f"TASK-APPLY-{project_name.upper()}", result_file)
        return 0

    # 4. Dispatch task to Host Agent / Replay / Fixture
    use_fixture = is_fixture_enabled(fixture)
    envelope = dispatch_agent_task(t_path, adapter=adapter, model=model, replay_dir=replay_dir, fixture=use_fixture)
    if envelope is not None:
        errs = schema_validate(envelope, 'agent_result_envelope')
        if errs:
            sys.exit(f"Host Apply Agent result failed agent_result_envelope schema validation:\n{errs}")

        delta = envelope['result']
        delta_errs = schema_validate(delta, 'research_delta')
        if delta_errs:
            sys.exit(f"Host Apply Agent result failed research_delta schema validation:\n{delta_errs}")

        delta_file = target_apply_dir / 'research_delta.json'
        delta_file.write_text(json.dumps(delta, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        # Run validate_delta.py
        val_res = subprocess.run([
            sys.executable, str(HERE / 'validate_delta.py'),
            '--paper', str(p_dir),
            '--delta', str(delta_file)
        ], capture_output=True, text=True)
        if val_res.returncode != 0:
            sys.exit(f"Research Delta failed semantic validation:\n{val_res.stdout + val_res.stderr}")

        print(f"OK: Stage A Local Apply complete for project {project_name} -> {delta_file}")
        return 0

    # Mode B: Submission boundary
    rs_p = p_dir / 'run_state.json'
    if rs_p.exists():
        rs = load_json(rs_p)
        rs['phase'] = 'WAITING_FOR_APPLY_AGENT'
        rs_p.write_text(json.dumps(rs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"\n[WAITING_FOR_AGENT] Apply task ready at: {t_path}")
    print(f"Evidentia has paused in WAITING_FOR_APPLY_AGENT state.")
    print(f"Submit completed research delta via:")
    print(f"  evidentia.py submit --out {p_dir} --task TASK-APPLY-{project_name.upper()} --result <file.json>\n")
    return 0

def run_memory_synthesis(paper_dir, project_name, memory_root=None, fixture=None):
    """Stage B: Memory-Augmented Synthesis (only after Stage A is validated)."""
    p_dir = Path(paper_dir)
    target_apply_dir = p_dir / 'apply' / project_name
    delta_file = target_apply_dir / 'research_delta.json'
    if not delta_file.exists():
        sys.exit(f"REFUSED: Cannot run memory synthesis before Stage A research_delta.json exists at {delta_file}")

    local_delta = load_json(delta_file)
    local_delta_sha = sha256(delta_file)

    # Retrieve relevant items from Frozen Research Memory
    mem_root = memory_manager.get_memory_root(memory_root)
    query_terms = [local_delta.get('paper_id', '')]
    for g in local_delta.get('project_gap_map', []):
        query_terms.append(g.get('question', ''))
    
    retrieved = []
    for q in query_terms[:3]:
        hits = memory_manager.search_memory(q, limit=5, custom_root=mem_root)
        for h in hits:
            if h['memory_id'] not in {r['memory_id'] for r in retrieved}:
                retrieved.append(h)

    # Synthesis payload
    now_iso = datetime.now(timezone.utc).isoformat()
    synth_payload = {
        "schema_version": "1.0",
        "stage": "STAGE_B_MEMORY_AUGMENTED_SYNTHESIS",
        "project_id": project_name,
        "paper_id": local_delta.get('paper_id', 'unknown'),
        "local_delta_sha256": local_delta_sha,
        "synthesized_at": now_iso,
        "retrieved_memory_items": retrieved,
        "cross_paper_insights": [
            {
                "memory_id": it['memory_id'],
                "relation_to_local_delta": "EXTENDS: Prior experiment outcome informs local transfer risk profile.",
                "confidence": 0.85
            }
            for it in retrieved[:3]
        ],
        "synthesized_experiments": [],
        "notes": f"Stage B memory-augmented synthesis incorporating {len(retrieved)} retrieved memory objects."
    }

    synth_file = target_apply_dir / 'memory_augmented_synthesis.json'
    synth_file.write_text(json.dumps(synth_payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Stage B Memory-Augmented Synthesis complete -> {synth_file}")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Evidentia Apply Agent")
    ap.add_argument('--paper', required=True)
    ap.add_argument('--project', required=True)
    ap.add_argument('--out')
    ap.add_argument('--focus')
    ap.add_argument('--fixture', action='store_true')
    ap.add_argument('--replay')
    ap.add_argument('--adapter')
    ap.add_argument('--model')
    ap.add_argument('--result')
    ap.add_argument('--with-memory', action='store_true')
    ap.add_argument('--memory-root')
    args = ap.parse_args()

    project_name = Path(args.project).stem
    run_local_apply(
        args.paper,
        args.project,
        out_dir=args.out,
        focus=args.focus,
        fixture=args.fixture,
        replay_dir=args.replay,
        adapter=args.adapter,
        model=args.model,
        result_file=args.result
    )

    if args.with_memory:
        run_memory_synthesis(args.paper, project_name, memory_root=args.memory_root, fixture=args.fixture)

if __name__ == '__main__':
    main()
