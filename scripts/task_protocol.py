#!/usr/bin/env python3
"""Host-neutral task protocol for Evidentia Agent Execution.

Generates and validates schema-compliant AgentTask packets for:
- Open Reading (tasks/open_reading.json)
- Six Lenses (tasks/lens/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json)
- Cross-Lens Reconciliation (tasks/reconciliation.json)
- Localized Verification (tasks/verification/{id}.json)
- Contextual Apply Local (tasks/apply/{project_id}.json)
- Memory-Augmented Synthesis (tasks/apply/{project_id}_memory_synthesis.json)

Enforces:
- Exact compliance with agent_task.schema.json
- Memory Firewall enforcement before task writing
- Provenance and SHA-256 bindings
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256
from executor_meta import build_executor_metadata
import memory_manager

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
        "in figures, tables, and ablations that contradict the main narrative. Empty findings are valid if none exist."
    ),
    'counterfactual': (
        "Reason counterfactually: what if key design choices, datasets, loss terms, or conditions were modified? "
        "Stress-test the necessity of claimed components and predict failure surfaces."
    )
}

def validate_and_write_task(task, out_path):
    """Validate task against agent_task.schema.json and Memory Firewall before writing."""
    errs = schema_validate(task, 'agent_task')
    if errs:
        raise ValueError(f"Task {task.get('task_id')} failed agent_task schema validation:\n{errs}")
    
    ok, reason = memory_manager.enforce_open_reading_firewall(task)
    if not ok:
        raise ValueError(f"Task {task.get('task_id')} failed Memory Firewall:\n{reason}")
    
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out_path

def get_source_and_base_shas(root):
    root = Path(root)
    src_pdf = root / 'source/paper.pdf'
    base_model = root / 'model/open_reading_model.json'
    src_sha = sha256(src_pdf) if src_pdf.exists() else "UNKNOWN_SOURCE_SHA"
    base_sha = sha256(base_model) if base_model.exists() else None
    return src_sha, base_sha

def create_open_reading_task(root):
    root = Path(root)
    src_sha, _ = get_source_and_base_shas(root)
    
    task = {
        "task_id": "TASK-OPEN-READING",
        "task_type": "OPEN_READING",
        "required_capability": "SCIENTIFIC_OPEN_READING",
        "scientific_contract": "Project-independent Open Reading baseline: strict O/I/A separation, source-grounded claims, explicit uncertainty.",
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
        ],
        "prohibited_context": [
            "RESEARCH_MEMORY",
            "cross-paper memory",
            "project_context",
            "apply",
            "prior_deltas"
        ],
        "source_sha256": src_sha,
        "base_sha256": None,
        "contract_version": "1.0",
        "prompt_version": "1.0",
        "executor_template": build_executor_metadata()
    }
    out_p = root / 'tasks/open_reading.json'
    return validate_and_write_task(task, out_p)

def create_lens_tasks(root):
    root = Path(root)
    src_sha, base_sha = get_source_and_base_shas(root)
    orm_p = root / 'model/open_reading_manifest.json'

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
            "task_type": "LENS",
            "lens": lens,
            "required_capability": f"SCIENTIFIC_LENS_{lens.upper()}",
            "scientific_contract": f"Independent {lens} lens rereading bound strictly to frozen baseline.",
            "description": f"Independent {lens} lens rereading pass.",
            "input_artifacts": {
                "source_pdf": "source/paper.pdf",
                "base_model": "model/open_reading_model.json"
            },
            "source_pdf": "source/paper.pdf",
            "base_model": "model/open_reading_model.json",
            "output": f"lens/{lens}.json",
            "target_output": f"lens/{lens}.json",
            "output_schema": "lens",
            "source_sha256": src_sha,
            "base_sha256": base_sha,
            "base_model_sha256": base_sha,
            "contract_version": contract_v,
            "lens_contract_version": contract_v,
            "prompt_version": prompt_v,
            "prohibited_context": [
                "RESEARCH_MEMORY",
                "cross-paper memory",
                "project_context",
                "apply",
                "prior_deltas"
            ],
            "instructions": LENS_PROMPTS[lens],
            "executor_template": build_executor_metadata()
        }
        out_p = root / f"tasks/lens/{lens}.json"
        validate_and_write_task(task, out_p)
        created.append(out_p)
    return created

def create_reconciliation_task(root):
    root = Path(root)
    src_sha, base_sha = get_source_and_base_shas(root)

    task = {
        "task_id": "TASK-RECONCILIATION",
        "task_type": "RECONCILIATION",
        "required_capability": "SEMANTIC_RECONCILIATION",
        "scientific_contract": "Semantic reconciliation: classify candidate finding cluster relations without majority voting.",
        "description": "Semantic reconciliation and clustering across six independent lens passes.",
        "input_artifacts": {
            "lenses": [f"lens/{l}.json" for l in LENSES],
            "candidate_clusters": "model/candidate_clusters.json",
            "open_reading_model": "model/open_reading_model.json"
        },
        "target_output": "model/lens_reconciliation.json",
        "output_schema": "lens_reconciliation",
        "source_sha256": src_sha,
        "base_sha256": base_sha,
        "contract_version": "1.0",
        "prompt_version": "1.0",
        "prohibited_context": [
            "RESEARCH_MEMORY",
            "project_context",
            "apply"
        ],
        "instructions": (
            "Analyze findings from all six independent lenses and candidate clusters. "
            "Categorize relations into: AGREEMENT, COMPLEMENTARY, PARTIAL_AGREEMENT, TENSION, CONTRADICTION, ORTHOGONAL, UNRESOLVED. "
            "Preserve all supporting_lenses for every item. Never erase scientific tension or contradiction."
        )
    }
    out_p = root / 'tasks/reconciliation.json'
    return validate_and_write_task(task, out_p)

def create_verification_task(root, target_id, claim_or_statement, localized_evidence, trigger_reason="high_impact_finding"):
    root = Path(root)
    src_sha, base_sha = get_source_and_base_shas(root)

    task = {
        "task_id": f"TASK-VERIF-{target_id}",
        "task_type": "VERIFICATION",
        "required_capability": "EVIDENCE_LOCALIZED_VERIFICATION",
        "scientific_contract": "Evaluate candidate statement against localized source evidence; assign verdict with cited evidence and reason.",
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
        "input_artifacts": {
            "source_pdf": "source/paper.pdf"
        },
        "target_output": f"verification/{target_id}.json",
        "output_schema": "verification_result",
        "source_sha256": src_sha,
        "base_sha256": base_sha,
        "contract_version": "1.0",
        "prompt_version": "1.0",
        "prohibited_context": [
            "project_context",
            "external_speculation"
        ],
        "instructions": (
            "Verify the candidate statement against the localized evidence ONLY. "
            "Do not rely on unverified whole-paper narrative. "
            "Inspect the localized figure, table cells, or text segment. "
            "Determine whether the evidence strictly supports, partially supports, rejects, or is insufficient."
        )
    }
    out_p = root / f"tasks/verification/{target_id}.json"
    return validate_and_write_task(task, out_p)

def create_apply_task(root, project_id, project_doc):
    root = Path(root)
    src_sha, base_sha = get_source_and_base_shas(root)

    task = {
        "task_id": f"TASK-APPLY-{project_id}",
        "task_type": "APPLY_LOCAL",
        "project_id": project_id,
        "project_doc": str(project_doc),
        "required_capability": "PROJECT_APPLY_LOCAL",
        "scientific_contract": "Project-specific contextual reread against frozen paper truth without mutating paper facts or using cross-paper memory.",
        "frozen_paper_model": "model/paper_model.json",
        "manifest": "model/manifest.json",
        "input_artifacts": {
            "paper_model": "model/paper_model.json",
            "manifest": "model/manifest.json",
            "project_document": f"apply/{project_id}/project_document.md",
            "project_context": f"apply/{project_id}/project_context.json"
        },
        "target_output": f"apply/{project_id}/research_delta.json",
        "output_schema": "research_delta",
        "source_sha256": src_sha,
        "base_sha256": base_sha,
        "contract_version": "1.0",
        "prompt_version": "1.0",
        "prohibited_context": [
            "RESEARCH_MEMORY",
            "cross-paper memory"
        ],
        "instructions": (
            "Perform project-specific contextual reread against the FROZEN paper facts. "
            "Paper truth must not be mutated. "
            "Identify project gaps, map applicable components, and produce typed Transfer Units "
            "(DIRECT, ADAPT, INSPIRATION_ONLY, REJECT) with required assumptions and experiment decisions."
        )
    }
    out_p = root / f"tasks/apply/{project_id}.json"
    return validate_and_write_task(task, out_p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--generate-all', action='store_true')
    a = ap.parse_args()
    r = Path(a.out)
    create_open_reading_task(r)
    create_lens_tasks(r)
    create_reconciliation_task(r)
    print("OK: generated schema-valid standard task packets")

if __name__ == '__main__':
    main()
