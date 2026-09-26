#!/usr/bin/env python3
"""Synthetic Open Reading Agent Fixture for Evidentia Tier 1 Testing.

Produces schema-valid paper_model payloads explicitly wrapped in an
AgentResultEnvelope tagged with execution_kind="SIMULATED_FIXTURE".
"""
import json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_common import load_json, schema_validate, sha256

def sanitize_figure(inv_fig, claims):
    fid = inv_fig.get('id', 'F01')
    return {
        "id": fid,
        "paper_label": inv_fig.get('paper_label', fid),
        "page": inv_fig.get('page', 1),
        "caption_original": inv_fig.get('caption_original', 'Caption') or 'Caption',
        "caption_status": "OK",
        "role": "critical",
        "depth": "deep",
        "file": inv_fig.get('file'),
        "bbox": inv_fig.get('bbox', []),
        "caption_bbox": inv_fig.get('caption_bbox', []),
        "subfigures": inv_fig.get('subfigures', []),
        "extraction_method": inv_fig.get('extraction_method', 'embedded') or 'embedded',
        "confidence": inv_fig.get('confidence', 0.9),
        "inspection": "inspected",
        "observation": f"[SIMULATED] Data displayed in {fid}",
        "author_interpretation": "[SIMULATED] Claimed performance trend",
        "reader_assessment": "[SIMULATED] Numerically consistent in tested regime",
        "supports_claims": [c['id'] for c in claims if fid in c.get('evidence', [])],
        "limitations": [],
        "open_questions": []
    }

def sanitize_table(inv_tab, claims):
    tid = inv_tab.get('id', 'T01')
    return {
        "id": tid,
        "paper_label": inv_tab.get('paper_label', tid),
        "page": inv_tab.get('page', 1),
        "caption_original": inv_tab.get('caption_original', 'Table caption') or 'Table caption',
        "caption_status": "OK",
        "role": "critical",
        "depth": "deep",
        "file": inv_tab.get('file'),
        "inspection": "inspected",
        "supports_claims": [c['id'] for c in claims if tid in c.get('evidence', [])]
    }

def run_synthetic_open_reading(task_path):
    tp = Path(task_path)
    task = load_json(tp)
    root = tp.parent.parent

    sm_path = root / task['input_artifacts']['source_map']
    inv_path = root / task['input_artifacts']['figure_inventory']
    sm = load_json(sm_path)
    inv = load_json(inv_path)
    pdf_sha = sm.get('pdf_sha256', task.get('source_sha256', 'UNKNOWN'))

    all_sections = []
    first_page_text = ""
    for p in sm.get('pages', []):
        all_sections.extend(p.get('sections', []))
        if p.get('number') == 1 and not first_page_text:
            first_page_text = p.get('text', '') or " ".join(p.get('sections', []))

    title_match = re.search(r'^(?:[0-9\.\s]+)?([A-Z][^\n\.\?]{8,120})', first_page_text)
    paper_title = title_match.group(1).strip() if title_match else "Reconstructed Research Paper"

    clean_sections = [s for s in all_sections if len(s.split()) < 8][:6]
    natural_structure = clean_sections if clean_sections else ["Introduction", "Methodology", "Experiments", "Discussion"]

    raw_figs = [item for item in inv.get('items', []) if item.get('kind') == 'figure']
    raw_tables = [item for item in inv.get('items', []) if item.get('kind') == 'table']

    claims = []
    for idx, f in enumerate(raw_figs[:4], 1):
        cid = f"C{idx:02d}"
        fid = f.get('id')
        cap = f.get('caption_original', '')
        claims.append({
            "id": cid,
            "statement": f"[SIMULATED] Experimental results in {f.get('paper_label', fid)} establish core methodology performance.",
            "page": f.get('page', 1),
            "evidence": [fid],
            "epistemic": "SUPPORTED",
            "evidence_scope": "IN_PAPER_EVIDENCE",
            "observation": f"[SIMULATED] Direct measurements from {f.get('paper_label', fid)}: {cap[:180] or 'Data points recorded.'}",
            "author_interpretation": f"[SIMULATED] Authors claim {fid} demonstrates method advantage.",
            "reader_assessment": "[SIMULATED] The trend is empirically verified within the tested scope.",
            "origin_type": "DIRECT_SOURCE"
        })

    for idx, t in enumerate(raw_tables[:3], len(claims) + 1):
        cid = f"C{idx:02d}"
        tid = t.get('id')
        cap = t.get('caption_original', '')
        claims.append({
            "id": cid,
            "statement": f"[SIMULATED] Benchmark comparisons in {t.get('paper_label', tid)} confirm quantitative advantages.",
            "page": t.get('page', 1),
            "evidence": [tid],
            "epistemic": "SUPPORTED",
            "evidence_scope": "IN_PAPER_EVIDENCE",
            "observation": f"[SIMULATED] Tabular cells from {t.get('paper_label', tid)}: {cap[:180] or 'Numerical values recorded.'}",
            "author_interpretation": f"[SIMULATED] Authors claim {tid} validates performance gains.",
            "reader_assessment": "[SIMULATED] Numerical deltas are mathematically consistent.",
            "origin_type": "DIRECT_SOURCE"
        })

    if not claims:
        claims.append({
            "id": "C01",
            "statement": "[SIMULATED] Primary method formulation achieves stable convergence.",
            "page": 1,
            "evidence": ["p.1"],
            "epistemic": "SUPPORTED",
            "evidence_scope": "IN_PAPER_EVIDENCE",
            "observation": "[SIMULATED] Theoretical derivations on p.1.",
            "author_interpretation": "[SIMULATED] Authors claim stability under standard assumptions.",
            "reader_assessment": "[SIMULATED] Derivations are logically consistent.",
            "origin_type": "DIRECT_SOURCE"
        })

    figs = [sanitize_figure(f, claims) for f in raw_figs]
    tables = [sanitize_table(t, claims) for t in raw_tables]

    first_ev = claims[0]['evidence'][0] if claims and claims[0]['evidence'] else "p.1"
    portable_components = [{
        "id": "PC01",
        "name": "Core Methodology Block",
        "io": "Input features -> Target representation",
        "page": 1,
        "source": [first_ev]
    }]

    now_iso = datetime.now(timezone.utc).isoformat()

    result_model = {
        "schema_version": "1.0",
        "source_sha256": pdf_sha,
        "paper_id": Path(root).name,
        "created_at": now_iso,
        "generator_version": "evidentia-v1.1-fixture",
        "paper_type": "method",
        "paper": {
            "title": paper_title,
            "authors": ["Reconstructed Paper Authors"],
            "year": 2025,
            "venue": "Academic Venue",
            "doi": "10.0000/evidentia.reconstructed",
            "pdf_sha256": pdf_sha
        },
        "natural_structure": natural_structure,
        "questions": [{
            "id": "Q01",
            "text": f"How does the method presented in {paper_title} advance current research boundaries?",
            "page": 1
        }],
        "claims": claims,
        "observations": [],
        "author_interpretations": [],
        "reader_assessments": [],
        "experiments": [],
        "figures": figs,
        "tables": tables,
        "methods": [],
        "data": {
            "sources": [],
            "scale": "",
            "preprocessing": "",
            "splits": "",
            "leakage_risk": "",
            "metrics": ""
        },
        "assumptions": [{
            "id": "A01",
            "text": "Data distribution remains stationary across training and evaluation splits."
        }],
        "limitations": [{
            "id": "B01",
            "text": "Evaluation is primarily bounded to benchmark datasets evaluated in the text."
        }],
        "open_questions": [{
            "id": "Q02",
            "text": "Scalability to multimodal streaming inputs remains unexplored.",
            "source": ["p.1"]
        }],
        "anomalies": [],
        "side_findings": [],
        "portable_components": portable_components,
        "argument_chain": [
            "Empirical evidence establishes baseline methodology efficacy."
        ],
        "unresolved": [],
        "coverage": {
            "supplement": "NOT_APPLICABLE",
            "methods_appendix": "ABSENT",
            "ablations": "ABSENT",
            "negative_results": "ABSENT"
        },
        "lens_synthesis": [],
        "lens_conflicts": []
    }

    envelope = {
        "task_id": task.get("task_id", "TASK-OPEN-READING"),
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-fixture-runner",
            "provider": "evidentia-test-suite",
            "model": "synthetic-open-reading-v1",
            "model_version": "1.0.0",
            "started_at": now_iso,
            "completed_at": now_iso
        },
        "started_at": now_iso,
        "completed_at": now_iso,
        "result": result_model
    }
    return envelope

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: open_reading_fixture.py <task_path> [<out_path>]")
    res = run_synthetic_open_reading(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
    else:
        print(json.dumps(res, indent=2))
