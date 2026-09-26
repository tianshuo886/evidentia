#!/usr/bin/env python3
"""Synthetic Apply Agent Fixture for Evidentia Tier 1 Testing.

Produces schema-valid research_delta documents wrapped in an
AgentResultEnvelope tagged with execution_kind="SIMULATED_FIXTURE".
"""
import json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_common import load_json, schema_validate, sha256, all_ids

def run_synthetic_apply(paper_dir, project_doc, focus=None):
    p_dir = Path(paper_dir)
    doc_path = Path(project_doc)
    if not doc_path.exists():
        if (p_dir / project_doc).exists():
            doc_path = p_dir / project_doc

    pm_path = p_dir / 'model/paper_model.json'
    manifest_p = p_dir / 'model/manifest.json'
    pm = load_json(pm_path) if pm_path.exists() else {}
    manifest = load_json(manifest_p) if manifest_p.exists() else {}

    paper_model_sha = manifest.get('hashes', {}).get('model/paper_model.json')
    if not paper_model_sha:
        paper_model_sha = sha256(pm_path) if pm_path.exists() else "UNKNOWN"
    source_sha = manifest.get('source_sha256', "UNKNOWN")
    project_name = doc_path.stem
    doc_content = doc_path.read_text(encoding='utf-8') if doc_path.exists() else ""

    pm_ids = all_ids(pm)
    valid_source_ids = [k for k, v in pm_ids.items() if v in ('figures', 'tables', 'experiments', 'methods')]
    primary_source_id = valid_source_ids[0] if valid_source_ids else "p.1"

    available_comps = pm.get('portable_components', [])
    comp_name = available_comps[0].get('name', 'Core Component') if available_comps else "Method Architecture"
    tu_comp_ids = [c['id'] for c in available_comps] if available_comps else []

    # Extract gaps or record NO_EXPLICIT_PROJECT_GAP_FOUND
    gap_matches = re.findall(r'(?:gap|problem|challenge|need|goal)[:\s]+([^\n\.]+)', doc_content, re.I)
    gaps = []
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
            "question": "General task performance optimization under project constraints.",
            "status": "open",
            "existing_experiments": []
        })

    reread = [{
        "source": [primary_source_id],
        "finding": f"[SIMULATED] Paper component {comp_name} addresses project gap {gaps[0]['id']}.",
        "gap_ids": [gaps[0]['id']]
    }]

    changed_beliefs = [{
        "before": "[SIMULATED] Feature representation requires heavy multi-stage preprocessing.",
        "after": f"[SIMULATED] {comp_name} provides stable representations with direct normalization.",
        "reason": f"[SIMULATED] Grounded in {primary_source_id} empirical ablation findings.",
        "source": [primary_source_id],
        "gap_ids": [gaps[0]['id']]
    }]

    new_evidence = [{
        "finding": f"[SIMULATED] {comp_name} achieves robust convergence across baseline tests.",
        "source": [primary_source_id],
        "gap_ids": [gaps[0]['id']]
    }]

    new_unknowns = [{
        "question": "[SIMULATED] Robustness under extreme project noise remains unmeasured.",
        "source": [primary_source_id],
        "gap_ids": [gaps[0]['id']]
    }]

    transfer_units = []
    if tu_comp_ids:
        for idx, cid in enumerate(tu_comp_ids[:3], 1):
            transfer_units.append({
                "id": f"TU-{idx:02d}",
                "component_ids": [cid],
                "gap_ids": [gaps[0]['id']],
                "verdict": "ADAPT",
                "reason_codes": ["different_data_regime"],
                "reason": f"[SIMULATED] Component {cid} provides proven methodology but requires project adaptation.",
                "source": [primary_source_id],
                "source_component": comp_name,
                "required_assumptions": ["[SIMULATED] Input tensor normalization matches source paper"],
                "input_contract": "Float32 Tensor [B, C, H, W]",
                "output_contract": "Classification logits [B, NumClasses]",
                "data_regime": "Project sensory data distribution",
                "label_semantics": "Task taxonomy",
                "physical_assumptions": "Stationary background distribution",
                "compute_constraints": "Compatible with standard project GPU budget",
                "deployment_constraints": "Inference latency acceptable",
                "expected_benefit": "PROJECT_INFERENCE: Potential accuracy improvement under project criteria",
                "known_risks": ["[SIMULATED] Potential domain mismatch under uncalibrated noise"]
            })

    experiments = [{
        "id": "EXP-01",
        "source": [primary_source_id],
        "delta_vs_current_plan": f"[SIMULATED] Substitute current encoder with {comp_name}.",
        "hypothesis": f"[SIMULATED] {comp_name} will reduce training iterations to reach target accuracy.",
        "integration_point": "Project pipeline feature extractor layer",
        "cost": "Low (2 GPU hours)",
        "risk": "Low (fallback to baseline encoder)",
        "decision_value_success": "Adopt adapted component permanently.",
        "decision_value_failure": "Retain baseline encoder.",
        "gap_ids": [gaps[0]['id']]
    }]

    delta = {
        "schema_version": "1.0",
        "paper_id": Path(paper_dir).name,
        "paper_model_sha256": paper_model_sha,
        "project": {
            "name": project_name,
            "document": str(doc_path.resolve())
        },
        "project_gap_map": gaps,
        "contextual_reread": reread,
        "changed_beliefs": changed_beliefs,
        "new_evidence": new_evidence,
        "new_unknowns": new_unknowns,
        "transfer_units": transfer_units,
        "invalidated_plans": [],
        "experiments": experiments,
        "no_new_actionable_experiment": False
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    envelope = {
        "task_id": f"TASK-APPLY-{project_name.upper()}",
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-apply-runner",
            "provider": "evidentia-test-suite",
            "model": "synthetic-apply-v1",
            "started_at": now_iso,
            "completed_at": now_iso
        },
        "started_at": now_iso,
        "completed_at": now_iso,
        "result": delta
    }
    return envelope

def run_synthetic_memory_synthesis(task_path):
    tp = Path(task_path)
    task = load_json(tp)
    root = tp.parent.parent
    if tp.parent.name == 'apply':
        root = tp.parent.parent.parent

    mb_rel = task.get('input_artifacts', {}).get('memory_bundle', '')
    mb_file = root / mb_rel if mb_rel else None
    mb_data = load_json(mb_file) if (mb_file and mb_file.exists()) else {}
    retrieved = mb_data.get('retrieved_memory_items', [])
    local_delta_sha = mb_data.get('local_delta_sha256') or task.get('local_delta_sha256', 'UNKNOWN')

    now_iso = datetime.now(timezone.utc).isoformat()
    insights = []
    for it in retrieved[:3]:
        insights.append({
            "memory_id": it['memory_id'],
            "relation_to_local_delta": "[SIMULATED] Prior finding provides complementary data regime bounds.",
            "confidence": 0.85,
            "epistemic_state": "SUPPORTED"
        })

    synth = {
        "schema_version": "1.0",
        "stage": "STAGE_B_MEMORY_AUGMENTED_SYNTHESIS",
        "origin_type": "MEMORY_SYNTHESIS",
        "project_id": task.get('project_id', 'project'),
        "paper_id": Path(root).name,
        "local_delta_sha256": local_delta_sha,
        "based_on_local_delta_sha256": local_delta_sha,
        "synthesized_at": now_iso,
        "retrieved_memory_items": retrieved,
        "cross_paper_insights": insights,
        "synthesized_experiments": [],
        "notes": f"[SIMULATED] Synthetic memory synthesis fixture incorporating {len(retrieved)} retrieved memory objects."
    }

    envelope = {
        "task_id": task.get('task_id', 'TASK-MEMORY-SYNTHESIS'),
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-apply-runner",
            "provider": "evidentia-test-suite",
            "model": "synthetic-memory-synthesis-v1",
            "started_at": now_iso,
            "completed_at": now_iso
        },
        "started_at": now_iso,
        "completed_at": now_iso,
        "result": synth
    }
    return envelope

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit("Usage: apply_fixture.py <paper_dir> <project_doc> [<out_path>]")
    env = run_synthetic_apply(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps(env['result'], indent=2) + '\n', encoding='utf-8')
    else:
        print(json.dumps(env, indent=2))
