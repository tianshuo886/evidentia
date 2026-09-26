#!/usr/bin/env python3
"""Host-neutral task protocol for Evidentia Standard Mode Agent Execution.

Generates and validates task packets for:
- Open Reading (tasks/open_reading.json)
- Six Lenses (tasks/lens/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json)
- Cross-Lens Reconciliation (tasks/reconciliation.json)
- Localized Verification (tasks/verification/{id}.json)
- Contextual Apply (tasks/apply/{project_id}.json)
"""
import argparse, json, os, sys
from pathlib import Path

LENSES = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')

LENS_PROMPTS = {
    'author': (
        "Reconstruct the strongest possible intended scientific contribution from the author's point of view. "
        "Highlight core claims, theoretical motivations, key innovations, and intended interpretations of experiments."
    ),
    'reviewer': (
        "Perform a critical peer review audit. Identify unstated assumptions, missing baseline comparisons, "
        "confounds, statistical weaknesses, causal overclaims, and unsupported assertions."
    ),
    'mechanism': (
        "Deconstruct the causal and technical mechanisms. How does each component mechanically operate? "
        "Trace what causes the reported performance, failure modes, and mechanistic boundaries."
    ),
    'builder': (
        "Evaluate practical engineering and re-implementation feasibility. Identify implementation ambiguities, "
        "unspecified hyperparameters, data dependencies, computational budget requirements, and portability."
    ),
    'anomaly': (
        "Audit anomalous data points, unexplained variance, outliers, negative results, or unexpected behavior "
        "in figures, tables, and ablations that contradict the main narrative."
    ),
    'counterfactual': (
        "Reason counterfactually: what if key design choices, datasets, loss terms, or conditions were modified? "
        "Stress-test the necessity of claimed components and predict failure surfaces."
    )
}

def create_open_reading_task(root):
    root = Path(root)
    tasks_dir = root / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    task = {
        "task_id": "TASK-OPEN-READING",
        "task_type": "OPEN_READING",
        "description": "Project-independent initial reading of the reconstructed source paper.",
        "input_artifacts": {
            "source_pdf": "source/paper.pdf",
            "source_map": "model/source_map.json",
            "figure_inventory": "model/figure_inventory.json"
        },
        "target_output": "model/paper_model.json",
        "output_schema": "paper_model",
        "instructions": (
            "Read only the supplied paper and its reconstructed source map/inventory. "
            "The external project is strictly invisible. "
            "Rigidly separate Observation (what the data directly shows), Author Interpretation (what authors claim it means), "
            "and Reader Assessment (your objective scientific critique). "
            "Ground every claim in concrete figure, table, or experiment IDs from the inventory. "
            "Explicitly register uncertainties, limitations, assumptions, and anomalies."
        ),
        "constraints": [
            "PROJECT_INVISIBLE",
            "SOURCE_GROUNDED",
            "O_I_A_SEPARATION",
            "EXPLICIT_UNCERTAINTY"
        ]
    }
    out_p = tasks_dir / 'open_reading.json'
    out_p.write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out_p

def create_lens_tasks(root):
    root = Path(root)
    lens_tasks_dir = root / 'tasks' / 'lens'
    lens_tasks_dir.mkdir(parents=True, exist_ok=True)
    
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_common import load_json, sha256
    from executor_meta import build_executor_metadata

    src_pdf = root / 'source/paper.pdf'
    base_model = root / 'model/open_reading_model.json'
    orm_p = root / 'model/open_reading_manifest.json'

    src_sha = sha256(src_pdf) if src_pdf.exists() else "UNKNOWN"
    base_sha = sha256(base_model) if base_model.exists() else "UNKNOWN"
    contract_v = "1.0"
    prompt_v = "1.0"
    if orm_p.exists():
        om = load_json(orm_p)
        contract_v = om.get('lens_contract_version', '1.0')
        prompt_v = om.get('prompt_version', '1.0')

    created = []
    for lens in LENSES:
        task = {
            "task_id": f"TASK-LENS-{lens.upper()}",
            "lens": lens,
            "source_pdf": "source/paper.pdf",
            "base_model": "model/open_reading_model.json",
            "output": f"lens/{lens}.json",
            "source_sha256": src_sha,
            "base_sha256": base_sha,
            "base_model_sha256": base_sha,
            "lens_contract_version": contract_v,
            "prompt_version": prompt_v,
            "instructions": LENS_PROMPTS[lens],
            "target_output": f"lens/{lens}.json",
            "output_schema": "lens",
            "executor_template": build_executor_metadata()
        }
        out_p = lens_tasks_dir / f"{lens}.json"
        out_p.write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        created.append(out_p)
    return created

def create_reconciliation_task(root):
    root = Path(root)
    tasks_dir = root / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task = {
        "task_id": "TASK-RECONCILIATION",
        "task_type": "RECONCILIATION",
        "description": "Semantic reconciliation and clustering across six independent lens passes.",
        "input_artifacts": {
            "lenses": [f"lens/{l}.json" for l in LENSES],
            "open_reading_model": "model/open_reading_model.json"
        },
        "target_output": "model/lens_reconciliation.json",
        "output_schema": "lens_reconciliation",
        "instructions": (
            "Analyze findings from all six independent lenses. "
            "Cluster findings sharing identical or complementary evidence. "
            "Categorize relations into: AGREEMENT, COMPLEMENTARY, PARTIAL_AGREEMENT, TENSION, CONTRADICTION, ORTHOGONAL, UNRESOLVED. "
            "Preserve all supporting_lenses for every item. Never erase scientific tension or contradiction."
        )
    }
    out_p = tasks_dir / 'reconciliation.json'
    out_p.write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out_p

def create_verification_task(root, target_id, claim_or_statement, localized_evidence):
    root = Path(root)
    verif_dir = root / 'tasks' / 'verification'
    verif_dir.mkdir(parents=True, exist_ok=True)

    task = {
        "task_id": f"TASK-VERIF-{target_id}",
        "task_type": "VERIFICATION",
        "target_id": target_id,
        "statement": claim_or_statement,
        "localized_evidence": localized_evidence,
        "allowed_verdicts": [
            "SUPPORTED",
            "PARTIAL",
            "REJECTED",
            "AMBIGUOUS",
            "INSUFFICIENT_EVIDENCE"
        ],
        "target_output": f"verification/{target_id}.json",
        "instructions": (
            "Verify the candidate statement against the localized evidence ONLY. "
            "Do not rely on the whole paper narrative or general knowledge. "
            "Inspect the localized figure, table cells, or text segment. "
            "Determine whether the evidence strictly supports, partially supports, rejects, or is insufficient."
        )
    }
    out_p = verif_dir / f"{target_id}.json"
    out_p.write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out_p

def create_apply_task(root, project_id, project_doc):
    root = Path(root)
    apply_dir = root / 'tasks' / 'apply'
    apply_dir.mkdir(parents=True, exist_ok=True)

    task = {
        "task_id": f"TASK-APPLY-{project_id}",
        "task_type": "APPLY",
        "project_id": project_id,
        "project_doc": project_doc,
        "frozen_paper_model": "model/paper_model.json",
        "manifest": "model/manifest.json",
        "target_output": f"apply/{project_id}/research_delta.json",
        "output_schema": "research_delta",
        "instructions": (
            "Perform project-specific contextual reread against the FROZEN paper facts. "
            "Paper truth must not be mutated. "
            "Identify project gaps, map applicable components, and produce typed Transfer Units "
            "(DIRECT, ADAPT, INSPIRATION_ONLY, REJECT) with required assumptions and experiment decisions."
        )
    }
    out_p = apply_dir / f"{project_id}.json"
    out_p.write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out_p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--generate-all', action='store_true')
    a = ap.parse_args()
    r = Path(a.out)
    create_open_reading_task(r)
    create_lens_tasks(r)
    create_reconciliation_task(r)
    print("OK: generated standard task packets")

if __name__ == '__main__':
    main()
