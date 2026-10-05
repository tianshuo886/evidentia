"""Synthetic test fixture generator for Reader v3 tasks (tests only)."""
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone

def run_synthetic_v3_task(task_path):
    tp = Path(task_path)
    task = json.loads(tp.read_text(encoding='utf-8'))
    task_id = task.get('task_id', '')
    task_type = task.get('task_type', '')
    now_iso = datetime.now(timezone.utc).isoformat()
    
    src_sha = task.get('source_sha256', '0' * 64)
    base_sha = task.get('base_sha256') or ('1' * 64)
    
    # Resolve workspace root
    tasks_ancestor = next((p for p in tp.parents if p.name == "tasks"), None)
    root = tasks_ancestor.parent if tasks_ancestor else tp.parent.parent

    # Find evidence IDs from figure inventory and source map
    inv_p = root / 'model/figure_inventory.json'
    inv = json.loads(inv_p.read_text(encoding='utf-8')) if inv_p.exists() else {}
    evidence_ids = [it['id'] for it in inv.get('items', []) if it.get('id')]
    ev_ref = ev_ref if evidence_ids else "p.1" 
        
    paper_id = task.get('paper_id') or root.name
    
    if task_type == 'LEAD_READING':
        payload = {
            "schema_version": "1.0",
            "paper_id": paper_id,
            "source_sha256": src_sha,
            "paper_type": "empirical_methodology",
            "paper_characterization": "Synthetic test paper for intent isolation and end-to-end testing.",
            "structure_characterization": "Natural research paper flow from motivation to method and empirical evidence.",
            "argument_topology": {
                "nodes": [
                    {
                        "id": "N01", "role": "problem", "proposition": "Motivation and challenge statement",
                        "source_anchors": ["p.1"], "evidence_refs": ["p.1"], "epistemic_status": "SUPPORTED"
                    },
                    {
                        "id": "N02", "role": "method", "proposition": "Proposed methodology and core mechanics",
                        "source_anchors": ["p.1"], "evidence_refs": ["p.1"], "epistemic_status": "SUPPORTED"
                    },
                    {
                        "id": "N03", "role": "evidence", "proposition": "Empirical evaluation and performance bounds",
                        "source_anchors": ["p.1"], "evidence_refs": [ev_ref], "epistemic_status": "SUPPORTED"
                    }
                ],
                "relations": [
                    {"from": "N01", "to": "N02", "relation": "addressed_by"},
                    {"from": "N02", "to": "N03", "relation": "evaluated_by"}
                ]
            },
            "narrative": (
                "This paper provides a detailed study of empirical methodology. "
                "The authors establish a clear motivation based on existing gaps, "
                "introduce a novel structural mechanism, and evaluate it rigorously across standard benchmarks. "
                "The results demonstrate consistent gains while clearly identifying operational boundaries and limitations."
            ),
            "decisive_evidence": [
                {
                    "evidence": ["p.1", ev_ref],
                    "why_it_matters": "Confirms the core experimental finding without relying on external assumptions."
                }
            ],
            "uncertainties": [
                "Sensitivity under out-of-distribution inputs requires targeted exploration."
            ]
        }
    elif task_type == 'LENS_V3':
        lens_name = task.get('lens', 'argument_narrative')
        payload = {
            "schema_version": "1.0",
            "lens": lens_name,
            "lens_kind": task.get('lens_kind', 'core'),
            "source_sha256": src_sha,
            "base_sha256": base_sha,
            "summary": f"Synthetic finding for {lens_name}.",
            "findings": [
                {
                    "id": f"FIND-{lens_name[:2].upper()}-01",
                    "statement": f"Lens finding for {lens_name}.",
                    "evidence": ["p.1", ev_ref],
                    "epistemic": "SUPPORTED",
                    "action": "KEEP",
                    "importance": "MAJOR",
                    "reason": "Test fixture finding.",
                    "cross_cutting_checks": {"anomaly": None, "counterfactual": None}
                }
            ]
        }
    elif task_type == 'REVISION_MEMO':
        payload = {
            "schema_version": "1.0",
            "paper_id": paper_id,
            "source_sha256": src_sha,
            "summary": "Reconciled synthetic findings into editorial guidance.",
            "revisions": [
                {
                    "id": "REV-01",
                    "priority": "P1",
                    "action": "REWRITE",
                    "instruction": "Preserve method details.",
                    "rationale": "Clarifies presentation.",
                    "evidence": ["p.1", ev_ref],
                    "source_lenses": ["argument_narrative"]
                }
            ],
            "unresolved": []
        }
    elif task_type == 'NARRATIVE_PLAN':
        payload = {
            "schema_version": "1.0",
            "paper_id": paper_id,
            "source_sha256": src_sha,
            "paper_characterization": "Synthetic test paper structure.",
            "rationale": "Organic three-part structure.",
            "sections": [
                {
                    "id": "SEC-01",
                    "title": "研究背景与动机",
                    "purpose": "Introduce motivation and core setting.",
                    "evidence_refs": ["p.1"],
                    "source_anchors": ["p.1"]
                },
                {
                    "id": "SEC-02",
                    "title": "核心方法与机理设计",
                    "purpose": "Explain the architectural method.",
                    "evidence_refs": ["p.1", ev_ref],
                    "source_anchors": ["p.1"]
                },
                {
                    "id": "SEC-03",
                    "title": "实验验证与科学边界",
                    "purpose": "Examine results and limits.",
                    "evidence_refs": [ev_ref],
                    "source_anchors": ["p.1"]
                }
            ],
            "uncertainties": ["Test uncertainty description."]
        }
    elif task_type == 'LEAD_WRITING':
        plan_p = root / 'model/narrative_plan.json'
        plan = json.loads(plan_p.read_text(encoding='utf-8')) if plan_p.exists() else {}
        sections = plan.get('sections', [])
        
        # Check if intent is technical extraction
        is_tech = False
        rs_p = root / 'run_state.json'
        if rs_p.exists():
            rs = json.loads(rs_p.read_text(encoding='utf-8'))
            if rs.get('intent') == 'PAPER_TECHNICAL_EXTRACTION':
                is_tech = True

        sec_docs = []
        for i, s in enumerate(sections, 1):
            sec_docs.append({
                "id": s["id"],
                "title": s["title"],
                "lead_paragraph": f"Section {i} synthetic lead text discussing the core claims.",
                "blocks": [
                    {
                        "id": f"B{i:02d}-01",
                        "type": "paragraph",
                        "text": f"Detailed academic discussion referencing primary sources [p.1, {ev_ref}].",
                        "evidence_refs": ["p.1", ev_ref]
                    }
                ]
            })
        if is_tech:
            sec_docs.append({
                "id": "technical_extraction",
                "title": "论文技术细节提取",
                "lead_paragraph": "本章节提取论文核心算法与实验细节。",
                "blocks": [
                    {
                        "id": "B-TECH-01",
                        "type": "paragraph",
                        "text": f"算法伪代码与参数细节整理 [p.1, {ev_ref}].",
                        "evidence_refs": ["p.1", ev_ref]
                    }
                ]
            })
            
        payload = {
            "schema_version": "3.0",
            "paper_id": paper_id,
            "source_sha256": src_sha,
            "created_at": now_iso,
            "narrative_plan_ref": "model/narrative_plan.json",
            "document": {
                "title": "合成测试论文深度精读报告",
                "subtitle": "针对测试用例的严密学术重构",
                "paper_meta": {
                    "authors": ["Test Author"],
                    "year": 2026,
                    "venue": "Test Venue"
                },
                "sections": sec_docs
            }
        }
    else:
        payload = {"status": "OK", "source_sha256": src_sha}

    executor = {
        "kind": "SIMULATED_FIXTURE",
        "host": "synthetic-v3-fixture",
        "model": "fixture-gemini-v3",
        "started_at": now_iso,
        "completed_at": now_iso
    }
    envelope = {
        "task_id": task_id,
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": executor,
        "started_at": now_iso,
        "completed_at": now_iso,
        "input_hashes": {},
        "contract_version": task.get("contract_version", "3.0"),
        "prompt_version": task.get("prompt_version", "3.0"),
        "result": payload
    }

    if task.get("isolation_proof_required"):
        from lens_execution_manifest import issue_dispatch_record, build_execution_manifest, result_payload_sha256
        dispatch = issue_dispatch_record(tp)
        snapshot_dir = root / f"provenance/lens/{task_id}"
        if not snapshot_dir.exists():
            from prepare_lens_isolation import prepare
            prepare(root)
        snapshot_rel = str(snapshot_dir.relative_to(root))
        out_sha = result_payload_sha256(payload)
        code_sha = dispatch.get("code_sha") or "4139ca7b0b1ae72c0930801df5e50653b59a7e92"
        manifest = build_execution_manifest(
            root, task, task_path=tp, output_sha256=out_sha, code_sha=code_sha, executor=executor, snapshot_root=snapshot_rel
        )
        envelope["input_hashes"] = dispatch["input_hashes"]
        envelope["execution_binding"] = {
            "execution_id": dispatch["execution_id"],
            "nonce": dispatch["nonce"],
            "dispatch_sha256": dispatch["dispatch_sha256"],
            "task_sha256": dispatch["task_sha256"],
            "code_sha": code_sha
        }
        envelope["execution_manifest"] = manifest

    return envelope
