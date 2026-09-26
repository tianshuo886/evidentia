#!/usr/bin/env python3
"""Synthetic Lens Agent Fixture for Evidentia Tier 1 Testing.

Produces schema-valid lens documents wrapped in an AgentResultEnvelope
tagged with execution_kind="SIMULATED_FIXTURE".
"""
import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_common import load_json, schema_validate, sha256

def run_synthetic_lens(task_path, model="fixture-lens-model"):
    tp = Path(task_path)
    task = load_json(tp)
    lens = task['lens']
    root = tp.parent.parent
    if tp.parent.name == 'lens':
        root = tp.parent.parent.parent

    base_p = root / task.get('base_model', 'model/open_reading_model.json')
    base_model = load_json(base_p)
    claims = base_model.get('claims', [])
    default_ev = claims[0].get('evidence', ['p.1']) if claims else ['p.1']

    findings = []
    model_str = str(model)
    if lens == 'author':
        title = base_model.get('paper', {}).get('title', 'Method')
        findings.append({
            "id": f"L-{lens}-01",
            "statement": f"[SIMULATED] Core innovation proposed in {title} advances tested benchmarks.",
            "evidence": default_ev,
            "epistemic": "SUPPORTED",
            "novel_vs_base": True
        })
        if "2" in model_str or "beta" in model_str:
            findings.append({
                "id": f"L-{lens}-02",
                "statement": f"[SIMULATED] Theoretical convergence guarantees hold under stationary assumptions.",
                "evidence": default_ev,
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            })
    elif lens == 'reviewer':
        for idx, lim in enumerate(base_model.get('limitations', [])[:2], 1):
            findings.append({
                "id": f"L-{lens}-{idx:02d}",
                "statement": f"[SIMULATED] Critical limitation: {lim.get('text', 'Bounded scope.')}",
                "evidence": default_ev,
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            })
        if "2" in model_str or "beta" in model_str:
            findings.append({
                "id": f"L-{lens}-03",
                "statement": "[SIMULATED] Baseline comparison omits latest dense benchmark variants.",
                "evidence": default_ev,
                "epistemic": "PARTIAL",
                "novel_vs_base": True
            })
    elif lens == 'mechanism':
        comps = base_model.get('portable_components', [])
        comp_name = comps[0].get('name', 'Architecture') if comps else 'Algorithm'
        findings.append({
            "id": f"L-{lens}-01",
            "statement": f"[SIMULATED] Mechanistic dependency: {comp_name} drives primary representation mapping.",
            "evidence": default_ev,
            "epistemic": "SUPPORTED",
            "novel_vs_base": True
        })
    elif lens == 'builder':
        findings.append({
            "id": f"L-{lens}-01",
            "statement": "[SIMULATED] Hyperparameter stability requires exact normalization specified in p.1.",
            "evidence": default_ev,
            "epistemic": "SUPPORTED",
            "novel_vs_base": True
        })
    elif lens == 'anomaly':
        # Empty findings is explicitly legal for anomaly lens when no anomalies exist in paper
        for idx, a in enumerate(base_model.get('anomalies', [])[:2], 1):
            findings.append({
                "id": f"L-{lens}-{idx:02d}",
                "statement": f"[SIMULATED] Anomaly: {a.get('text', 'Unexpected variance')}",
                "evidence": default_ev,
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            })
    elif lens == 'counterfactual':
        findings.append({
            "id": f"L-{lens}-01",
            "statement": "[SIMULATED] Removing primary feature normalization degrades convergence under noise.",
            "evidence": default_ev,
            "epistemic": "SUPPORTED",
            "novel_vs_base": True
        })

    now_iso = datetime.now(timezone.utc).isoformat()
    src_sha = task.get('source_sha256', sha256(root / 'source/paper.pdf') if (root / 'source/paper.pdf').exists() else "UNKNOWN")
    base_sha = task.get('base_sha256', sha256(base_p))

    lens_doc = {
        "lens": lens,
        "source_sha256": src_sha,
        "base_sha256": base_sha,
        "base_model_sha256": base_sha,
        "lens_contract_version": task.get('lens_contract_version', task.get('contract_version', '1.0')),
        "prompt_version": task.get('prompt_version', '1.0'),
        "findings": findings,
        "notes": f"[SIMULATED] Synthetic fixture execution for {lens} lens.",
        "executor": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-fixture-runner",
            "provider": "evidentia-test-suite",
            "model": model,
            "model_version": "1.0.0",
            "started_at": now_iso,
            "completed_at": now_iso
        }
    }

    envelope = {
        "task_id": task.get("task_id", f"TASK-LENS-{lens.upper()}"),
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": lens_doc["executor"],
        "started_at": now_iso,
        "completed_at": now_iso,
        "result": lens_doc
    }
    return envelope

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: lens_fixture.py <task_path> [<out_path>]")
    res = run_synthetic_lens(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
    else:
        print(json.dumps(res, indent=2))
