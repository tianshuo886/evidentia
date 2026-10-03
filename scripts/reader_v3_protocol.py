#!/usr/bin/env python3
"""Host-neutral Reader v3 task protocol.

Reader v3 keeps scientific writing in strong-model tasks and deterministic code
in orchestration/validation only. The default execution contract assumes one
active harness and one strong model; all specialist passes are context-isolated.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, sha256
from task_protocol import validate_and_write_task
from executor_meta import build_executor_metadata
from lens_registry import select_lenses


def _source_sha(root: Path) -> str:
    pdf = root / "source/paper.pdf"
    if not pdf.exists():
        raise FileNotFoundError(f"Missing source paper: {pdf}")
    return sha256(pdf)


def create_lead_reader_task(root: Path) -> Path:
    root = Path(root)
    source_sha = _source_sha(root)
    task = {
        "task_id": "TASK-V3-LEAD-READING",
        "task_type": "LEAD_READING",
        "required_capability": "DEEP_SCIENTIFIC_READING",
        "scientific_contract": (
            "Read the complete paper as a strong scientific reader before specialist critique. "
            "Produce a coherent open-form Paper Understanding Draft, not a schema-shaped summary."
        ),
        "description": "Reader v3 Lead Reader full-paper understanding pass.",
        "input_artifacts": {
            "source_pdf": "source/paper.pdf",
            "source_map": "model/source_map.json",
            "figure_inventory": "model/figure_inventory.json",
            "visual_verification_dir": "visual/"
        },
        "target_output": "model/paper_understanding_draft.json",
        "output_schema": "paper_understanding_draft",
        "source_sha256": source_sha,
        "base_sha256": None,
        "contract_version": "3.0",
        "prompt_version": "3.0",
        "allowed_inputs": ["source/", "source_pages/", "assets/", "model/source_map.json", "model/figure_inventory.json", "visual/"],
        "forbidden_inputs": ["lens/", "lens_v3/", "apply/", "project/", "memory/project/"],
        "prohibited_context": ["PROJECT_APPLY", "RESEARCH_MEMORY", "prior Lens conclusions"],
        "constraints": [
            "STRONG_MODEL_FIRST",
            "COMPLETE_PAPER_STORY",
            "SOURCE_GROUNDED",
            "NO_PROJECT_TRANSFER",
            "EXPLICIT_UNCERTAINTY"
        ],
        "instructions": (
            "Read the paper as a whole. Your primary job is complete natural scientific understanding, not auditing. "
            "Begin by asking: How does this particular paper actually construct its case? Reconstruct its own "
            "paper/structure characterization and an open, ordered argument topology with source/evidence-grounded "
            "nodes and relations. Choose node roles and relations that fit this paper; observation, hypothesis, "
            "theorem, assumption, experiment, design choice, mechanism, contradiction, measurement, taxonomy branch, "
            "boundary, result and unresolved issue are examples, never a required checklist. Preserve structurally "
            "unusual forms such as proofs, taxonomies, reviews, measurement protocols, or multi-part empirical cases. "
            "Then explain the paper in natural prose, identify decisive/source-critical evidence, and record uncertainty "
            "and open issues. Do not force a problem→gap→method→experiment→result→limitation story. Do not expose "
            "internal Evidentia terminology or discuss the user's project. Classify paper_type using a concise category."
        ),
        "executor_template": build_executor_metadata()
    }
    return validate_and_write_task(task, root / "tasks/v3/lead_reading.json")


def create_lens_tasks(root: Path) -> list[Path]:
    root = Path(root)
    draft_p = root / "model/paper_understanding_draft.json"
    if not draft_p.exists():
        raise FileNotFoundError("Lead Reader draft must exist before Lens v3 tasks are created")
    draft = load_json(draft_p)
    source_sha = _source_sha(root)
    base_sha = sha256(draft_p)
    selected = select_lenses(draft.get("paper_type", ""), draft.get("narrative", ""))
    out = []
    for lens in selected:
        lid = lens["id"]
        task = {
            "task_id": f"TASK-V3-LENS-{lid.upper().replace('-', '_')}",
            "task_type": "LENS_V3",
            "lens": lid,
            "lens_kind": lens["kind"],
            "paper_type": draft.get("paper_type", "unknown"),
            "selection_reason": (
                "universal core lens" if lens["kind"] == "core"
                else f"selected for paper_type={draft.get('paper_type', 'unknown')}"
            ),
            "required_capability": lens["capability"],
            "scientific_contract": (
                f"Independent {lens['title']} reread. Inspect the shared paper and Lead Reader draft, "
                "but do not read other Lens outputs. Return corrections/additions, not a competing full summary."
            ),
            "description": f"Reader v3 independent specialist pass: {lens['title']}.",
            "input_artifacts": {
                "source_pdf": "source/paper.pdf",
                "source_map": "model/source_map.json",
                "figure_inventory": "model/figure_inventory.json",
                "lead_reader_draft": "model/paper_understanding_draft.json"
            },
            "target_output": f"lens_v3/{lid}.json",
            "output_schema": "lens_v3",
            "source_sha256": source_sha,
            "base_sha256": base_sha,
            "contract_version": "3.0",
            "prompt_version": "3.0",
            "allowed_inputs": [
                "source/", "source_pages/", "assets/",
                "model/source_map.json", "model/figure_inventory.json",
                "model/paper_understanding_draft.json"
            ],
            "forbidden_inputs": ["lens/", "lens_v3/", "apply/", "project/", "memory/project/"],
            "prohibited_context": ["other Lens outputs", "PROJECT_APPLY", "RESEARCH_MEMORY"],
            "constraints": ["CONTEXT_ISOLATED", "NO_MAJORITY_VOTING", "NO_PROJECT_TRANSFER"],
            "instructions": (
                f"Role: {lens['title']}.\n"
                "Answer only this role's scientific questions. Cite source evidence IDs/pages for every material finding.\n"
                + "\n".join(f"- {q}" for q in lens["questions"])
                + "\nCross-cutting checks: record a real anomaly when relevant; test a serious counterfactual/alternative "
                  "explanation when relevant. Do not force either when the evidence does not support one. "
                  "Use action KEEP/EXPAND/CORRECT/QUALIFY/VERIFY/NONE to tell the later editor how the Lead Reader draft should change."
            ),
            "executor_template": build_executor_metadata()
        }
        out.append(validate_and_write_task(task, root / f"tasks/v3/lens/{lid}.json"))
    manifest = {
        "schema_version": "3.0",
        "paper_type": draft.get("paper_type", "unknown"),
        "base_sha256": base_sha,
        "same_model_default": True,
        "context_isolated": True,
        "lenses": [{"id": x["id"], "kind": x["kind"], "title": x["title"]} for x in selected]
    }
    manifest_p = root / "model/lens_v3_manifest.json"
    manifest_p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def create_narrative_plan_task(root: Path) -> Path:
    root = Path(root)
    draft_p = root / "model/paper_understanding_draft.json"
    memo_p = root / "model/revision_memo.json"
    for p in (draft_p, memo_p):
        if not p.exists():
            raise FileNotFoundError(f"Missing prerequisite: {p}")
    draft = load_json(draft_p)
    source_sha = _source_sha(root)
    task = {
        "task_id": "TASK-V3-NARRATIVE-PLAN",
        "task_type": "NARRATIVE_PLAN",
        "required_capability": "SCIENTIFIC_NARRATIVE_PLANNING",
        "scientific_contract": "Design an open paper-specific narrative plan before final composition; fixed universal chapter slots are forbidden.",
        "description": "Paper-specific dynamic narrative plan for the Lead Writer.",
        "input_artifacts": {"source_pdf": "source/paper.pdf", "lead_reader_draft": "model/paper_understanding_draft.json", "revision_memo": "model/revision_memo.json"},
        "target_output": "model/narrative_plan.json",
        "output_schema": "narrative_plan",
        "source_sha256": source_sha,
        "base_sha256": sha256(draft_p),
        "contract_version": "3.0",
        "prompt_version": "3.1",
        "allowed_inputs": ["source/", "source_pages/", "assets/", "model/paper_understanding_draft.json", "model/revision_memo.json"],
        "forbidden_inputs": ["apply/", "project/", "memory/project/", "reader/paper_reader_ir.json", "reader/render_ir.json"],
        "prohibited_context": ["PROJECT_APPLY", "RESEARCH_MEMORY", "legacy Reader IR"],
        "constraints": ["PAPER_SPECIFIC_STRUCTURE", "OPEN_ORDER", "SOURCE_GROUNDED", "NO_FIXED_STORY_SLOTS", "PRESERVE_UNCERTAINTY"],
        "instructions": (
            "Determine the paper's own narrative architecture from the Lead Reader comprehension and Revision Memo. "
            "Return ordered dynamic sections. Each section needs a title, purpose, proposition or question when one "
            "exists, evidence refs, source anchors, and local figure/table/equation bindings when relevant. The count, "
            "identity and order must be chosen by the paper, not by a universal template. A section may be a proof "
            "step, taxonomy branch, measurement protocol, design trade-off, contradiction, result cluster, or another "
            "form. Do not read or emit any legacy Reader IR."
        ),
        "executor_template": build_executor_metadata()
    }
    return validate_and_write_task(task, root / "tasks/v3/narrative_plan.json")


def create_revision_memo_task(root: Path) -> Path:
    root = Path(root)
    manifest_p = root / "model/lens_v3_manifest.json"
    if not manifest_p.exists():
        raise FileNotFoundError("Missing model/lens_v3_manifest.json")
    manifest = load_json(manifest_p)
    lens_files = [f"lens_v3/{x['id']}.json" for x in manifest["lenses"]]
    missing = [p for p in lens_files if not (root / p).exists()]
    if missing:
        raise FileNotFoundError("Missing Lens v3 outputs: " + ", ".join(missing))
    source_sha = _source_sha(root)
    task = {
        "task_id": "TASK-V3-REVISION-MEMO",
        "task_type": "REVISION_MEMO",
        "required_capability": "SCIENTIFIC_EDITORIAL_RECONCILIATION",
        "scientific_contract": (
            "Act as a scientific editor. Reconcile independent specialist rereads into a Revision Memo only. "
            "Do not write the final Reader and do not decide disagreements by voting."
        ),
        "description": "Reader v3 Council/Editor revision memo.",
        "input_artifacts": {
            "source_pdf": "source/paper.pdf",
            "lead_reader_draft": "model/paper_understanding_draft.json",
            "lens_manifest": "model/lens_v3_manifest.json",
            "lens_outputs": lens_files
        },
        "target_output": "model/revision_memo.json",
        "output_schema": "revision_memo",
        "source_sha256": source_sha,
        "base_sha256": sha256(root / "model/paper_understanding_draft.json"),
        "contract_version": "3.0",
        "prompt_version": "3.0",
        "allowed_inputs": ["source/", "source_pages/", "assets/", "model/paper_understanding_draft.json", "model/lens_v3_manifest.json", "lens_v3/"],
        "forbidden_inputs": ["apply/", "project/", "memory/project/"],
        "prohibited_context": ["PROJECT_APPLY", "RESEARCH_MEMORY"],
        "constraints": ["REVISION_MEMO_ONLY", "NO_MAJORITY_VOTING", "PRESERVE_UNRESOLVED"],
        "instructions": (
            "Read the Lead Reader draft and all six independent Lens reports. Produce a concise editorial Revision Memo. "
            "Each revision must say exactly what the Lead Writer should add, rewrite, correct, qualify, remove or verify; "
            "why; which evidence supports the change; and which Lens(es) raised it. Merge duplicates, preserve real conflicts, "
            "and leave genuinely unresolved points unresolved. Do not produce a new paper summary."
        ),
        "executor_template": build_executor_metadata()
    }
    return validate_and_write_task(task, root / "tasks/v3/revision_memo.json")


def create_lead_writer_task(root: Path) -> Path:
    root = Path(root)
    draft_p = root / "model/paper_understanding_draft.json"
    memo_p = root / "model/revision_memo.json"
    manifest_p = root / "model/lens_v3_manifest.json"
    plan_p = root / "model/narrative_plan.json"
    for p in (draft_p, memo_p, manifest_p, plan_p):
        if not p.exists():
            raise FileNotFoundError(f"Missing prerequisite: {p}")
    manifest = load_json(manifest_p)
    lens_files = [f"lens_v3/{x['id']}.json" for x in manifest["lenses"]]
    source_sha = _source_sha(root)
    task = {
        "task_id": "TASK-V3-LEAD-WRITING",
        "task_type": "LEAD_WRITING",
        "required_capability": "SCIENTIFIC_NARRATIVE_WRITING",
        "scientific_contract": (
            "Write the final Chinese-first Paper Reader as a coherent open-form scientific explanation. "
            "The Reader must be authored by the strong model, not assembled from fixed prose templates."
        ),
        "description": "Reader v3 Lead Writer final narrative pass.",
        "input_artifacts": {
            "source_pdf": "source/paper.pdf",
            "source_map": "model/source_map.json",
            "figure_inventory": "model/figure_inventory.json",
            "lead_reader_draft": "model/paper_understanding_draft.json",
            "revision_memo": "model/revision_memo.json",
            "narrative_plan": "model/narrative_plan.json",
            "lens_outputs": lens_files
        },
        "target_output": "reader/narrative_manuscript.json",
        "output_schema": "narrative_manuscript",
        "source_sha256": source_sha,
        "base_sha256": sha256(draft_p),
        "contract_version": "3.0",
        "prompt_version": "3.1",
        "allowed_inputs": [
            "source/", "source_pages/", "assets/",
            "model/source_map.json", "model/figure_inventory.json",
            "model/paper_understanding_draft.json", "model/revision_memo.json",
            "model/narrative_plan.json", "model/lens_v3_manifest.json", "lens_v3/"
        ],
        "forbidden_inputs": ["apply/", "project/", "memory/project/"],
        "prohibited_context": ["PROJECT_APPLY", "RESEARCH_MEMORY"],
        "constraints": [
            "CHINESE_FIRST", "PAPER_SPECIFIC_STRUCTURE", "OPEN_ORDER", "CONTINUOUS_NARRATIVE",
            "INLINE_EVIDENCE", "NO_INTERNAL_PIPELINE_VOCABULARY", "NO_PROJECT_TRANSFER"
        ],
        "instructions": (
            "Return a narrative_manuscript v3 object. Re-read source evidence whenever the draft, plan or Revision Memo requires it. "
            "Write for a researcher who has not read the paper: first explain how this particular paper constructs its case, "
            "then follow the supplied paper-specific plan without turning it into pipeline jargon. Use the plan's dynamic "
            "section structure rather than fixed slots; do not add universal problem, gap, method, experiment, result or "
            "limitation sections merely because they are conventional. Place verified figures/tables/equations locally "
            "where they advance the scientific argument; each visual block must explain what question it addresses, what it shows, "
            "what it supports, and what it does not prove. The primary prose must never mention Lens names, Council, O/I/A, schemas, "
            "hashes, task IDs, pipeline phases or audit machinery. Do not create project-transfer or reusable-component advice. "
            "Preserve uncertainty instead of filling gaps with generic prose."
        ),
        "executor_template": build_executor_metadata()
    }
    return validate_and_write_task(task, root / "tasks/v3/lead_writing.json")
