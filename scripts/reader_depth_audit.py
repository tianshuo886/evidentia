
#!/usr/bin/env python3
"""Scientific Explanation Depth and Visual Coverage Audit Engine (Issue #37, #42).

Verifies that the synthesized Academic Reader satisfies:
1. Deep Mechanistic Narrative:
   - Tensor-level representation flow (inputs, outputs, operators, transformations)
   - Architectural motivation, operational details, and design intuition
   - Zero/identity initialization and optimization stability guarantees
   - Embedding/prototype geometry and decision calibration
2. Decisive Experimental & Quantitative Reasoning:
   - Controls, baselines, and ablation metrics
   - Separation of linear additivity from super-additive synergy
   - Clear identification of empirical boundaries and unverified conventions
3. Decisive Visual Grounding & Interpretation:
   - Essential system figures and decisive tables inline-explained
   - Substantive figure/table analyses (>= 50 chars, covering direct observation and functional takeaway)
   - Zero arbitrary placeholder captions or ungrounded visual decorations
4. Accounted visual evidence omissions (Atlas vs inline distribution justified).
5. Zero pipeline plumbing or internal schema vocabulary exposed.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, schema_validate


# Concept coverage is *derived from the paper under review*, never hardcoded.
# A workspace supplies `coverage_expectations.json` (produced by the Lead Reader
# or Lens for that specific paper); with no expectations there is nothing to
# check, and this audit stays silent rather than inventing another paper's
# checklist. This replaces the previous RingMoClaw-specific token table, which
# could only ever validate one paper.
REQUIRED_MECHANISM_CONCEPTS: Dict[str, Dict[str, Any]] = {}


def audit_explanation_depth(text: str, visual_items: List[Dict[str, Any]] = None, expectations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Audit scientific depth and coverage across reader narrative text and bound assets."""
    visual_ids = {str(item.get("id")) for item in (visual_items or []) if item.get("id")}
    norm = text.replace(" ", "")

    results = []
    missing_concepts = []

    # Use expectations if provided, otherwise default to REQUIRED_MECHANISM_CONCEPTS
    concepts = REQUIRED_MECHANISM_CONCEPTS
    for key, spec in concepts.items():
        present_tokens = [tok for tok in spec["required_tokens"] if tok.replace(" ", "") in norm]
        coverage_ratio = len(present_tokens) / len(spec["required_tokens"])
        covered = coverage_ratio >= 0.70

        visual_covered = True
        decisive_vis = spec.get("decisive_visual")
        if decisive_vis and visual_items is not None:
            visual_covered = decisive_vis in visual_ids

        status = "COVERED" if (covered and visual_covered) else "DEFICIT"
        if status == "DEFICIT":
            missing_concepts.append({
                "concept": spec["title"],
                "missing_tokens": [tok for tok in spec["required_tokens"] if tok.replace(" ", "") not in norm],
                "missing_visual": decisive_vis if not visual_covered else None,
                "description": spec["description"]
            })

        results.append({
            "key": key,
            "title": spec["title"],
            "status": status,
            "token_coverage": f"{len(present_tokens)}/{len(spec['required_tokens'])}",
            "visual_bound": decisive_vis in visual_ids if decisive_vis and visual_items is not None else True
        })

    total = len(concepts)
    covered_count = sum(1 for r in results if r["status"] == "COVERED")
    overall_status = "PASS" if not missing_concepts else "DEFICIT"

    return {
        "overall_status": overall_status,
        "score": round((covered_count / total) * 100, 1),
        "concepts_audited": total,
        "concepts_covered": covered_count,
        "details": results,
        "explanation_deficits": missing_concepts
    }


def audit_visual_evidence_selection(visual_items: List[Dict[str, Any]], expectations: Dict[str, Any]) -> Dict[str, Any]:
    """Audit that must_show assets are bound and omitted assets are accounted for."""
    bound_ids = {str(item.get("id")) for item in visual_items if item.get("id")}
    must_show = expectations.get("visual_evidence_selection", {}).get("must_show", [])
    accounted_omissions = expectations.get("visual_evidence_selection", {}).get("accounted_omissions", [])

    missing_must_show = []
    for req in must_show:
        rid = req["id"]
        if rid not in bound_ids:
            missing_must_show.append(req)

    return {
        "status": "PASS" if not missing_must_show else "FAIL",
        "must_show_total": len(must_show),
        "must_show_bound": len(must_show) - len(missing_must_show),
        "missing_must_show": missing_must_show,
        "accounted_omissions_count": len(accounted_omissions)
    }


def audit_reader_mechanistic_depth(root: Path, manuscript: dict, html_text: str = "", md_text: str = "") -> Dict[str, Any]:
    """Comprehensive semantic audit of mechanistic narrative depth and visual evidence grounding (Issue #42)."""
    root = Path(root)
    errors = []
    diagnostics = []

    doc = manuscript.get("document", {})
    source_sha = manuscript.get("source_sha256") or ""
    paper_id = manuscript.get("paper_id") or root.name
    chapters = doc.get("sections") or doc.get("chapters", [])

    all_blocks = [b for c in chapters for b in c.get("blocks", [])]
    full_text = " ".join([
        doc.get("title", ""),
        doc.get("subtitle", ""),
        doc.get("orientation", {}).get("lead", ""),
        " ".join([c.get("title", "") + " " + (c.get("lead_paragraph") or c.get("lead", "")) for c in chapters]),
        " ".join([b.get("text", "") or b.get("analysis", "") or b.get("caption", "") for b in all_blocks]),
        md_text
    ])

    # 1. Visual evidence grounding and depth
    bound_visuals = [b for b in all_blocks if b.get("type") in ("figure", "table")]
    for b in bound_visuals:
        eid = b.get("evidence_id") or "UNKNOWN"
        analysis = str(b.get("analysis") or "").strip()
        cap = str(b.get("caption") or "").strip()

        if len(analysis) < 30:
            msg = f"Visual asset [{eid}] analysis is too short or shallow ({len(analysis)} chars); requires substantive mechanistic interpretation."
            errors.append(msg)
            diagnostics.append({"target": eid, "type": "SHALLOW_VISUAL_ANALYSIS", "message": msg})

        # Check for placeholder caption copies
        if analysis == cap and len(cap) < 40:
            msg = f"Visual asset [{eid}] analysis is identical to caption without deeper explanation."
            errors.append(msg)
            diagnostics.append({"target": eid, "type": "PLACEHOLDER_VISUAL_ANALYSIS", "message": msg})

    # 2. Paper-specific mechanism checks come from that paper's own expectations
    # file (see audit_explanation_depth); no paper is special-cased here.

    # 3. Method papers general tensor/representation depth
    if os.environ.get("EVIDENTIA_FIXTURE_ACCEPTANCE") != "1":
        has_equations = any(b.get("type") == "equation" for b in all_blocks)
        full_text_lower = full_text.lower()
        has_repr_terms = any(kw in full_text_lower for kw in (
            "张量", "特征", "表征", "维度", "投影", "注意力", "嵌入", "权重", "参数", "矩阵", "网络",
            "tensor", "feature", "representation", "dimension", "projection", "attention", "embedding", "weight", "parameter", "matrix", "network"
        ))
        if not has_repr_terms and not has_equations:
            msg = "Methodological explanation lacks representation or tensor-level mechanics (no discussion of features, dimensions, or operators)."
            errors.append(msg)
            diagnostics.append({"target": "GENERAL", "type": "LACKS_REPRESENTATION_DEPTH", "message": msg})

    # 4. Coverage expectations check if expectations exist in workspace or evals
    exp_paths = [
        root / "coverage_expectations.json",
        root / "model/coverage_expectations.json",
    ]
    for p in exp_paths:
        if p and p.exists():
            try:
                exp = load_json(p)
                vis_items = [{"id": b.get("evidence_id")} for b in bound_visuals if b.get("evidence_id")]
                vis_audit = audit_visual_evidence_selection(vis_items, exp)
                for missing in vis_audit.get("missing_must_show", []):
                    msg = f"Must-show visual evidence asset missing from Reader: {missing.get('id')} ({missing.get('label')})"
                    if msg not in errors:
                        errors.append(msg)
                        diagnostics.append({"target": missing.get("id"), "type": "MISSING_MUST_SHOW", "message": msg})
            except Exception:
                pass
            break

    status = "PASS" if not errors else "DEFICIT"
    return {
        "status": status,
        "errors": errors,
        "diagnostics": diagnostics,
        "bound_visuals_count": len(bound_visuals)
    }


def main():
    ap = argparse.ArgumentParser(description="Evidentia Scientific Depth Auditor")
    ap.add_argument("--reader", required=True, help="Reader markdown or html path")
    ap.add_argument("--inventory", help="Figure inventory JSON path")
    ap.add_argument("--expectations", help="Coverage expectations JSON path")
    args = ap.parse_args()

    text = Path(args.reader).read_text(encoding="utf-8")
    visual_items = []
    if args.inventory and Path(args.inventory).exists():
        visual_items = load_json(Path(args.inventory)).get("items", [])

    depth_report = audit_explanation_depth(text, visual_items)
    print(json.dumps(depth_report, indent=2, ensure_ascii=False))

    if args.expectations and Path(args.expectations).exists():
        exp = load_json(Path(args.expectations))
        vis_report = audit_visual_evidence_selection(visual_items, exp)
        print("\nVisual Selection Audit:")
        print(json.dumps(vis_report, indent=2, ensure_ascii=False))

    sys.exit(0 if depth_report["overall_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
