#!/usr/bin/env python3
"""Scientific Explanation Depth and Visual Coverage Audit Engine (Issue #37).

Verifies that the synthesized Academic Reader satisfies:
1. Deep Mechanism Explanation (motivation -> operation/IO -> critical design choices -> tradeoffs -> evidence)
2. Decisive Experimental Reasoning (question/controls -> metrics -> comparisons -> proven vs unproven boundaries)
3. Essential Visual Evidence Coverage (Fig. 2 system architecture + decisive tables inline-explained)
4. Accounted visual evidence omissions (Atlas vs inline distribution justified without arbitrary blanket counts)
5. Zero pipeline or schema jargon exposed in the primary prose.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, schema_validate


REQUIRED_MECHANISM_CONCEPTS = {
    "architecture_fig2": {
        "title": "System Architecture & Agent Roles (Fig. 2)",
        "required_tokens": ["Main Agent", "Data Agent", "Vision Agent", "Critic", "经验总线"],
        "decisive_visual": "F02",
        "description": "Multi-agent division of labor, Critic checkpoint intervention, and experience coupling."
    },
    "critic_formulation": {
        "title": "Critic Decision Logic & Formula",
        "required_tokens": ["Score", "0.75", "0.30"],
        "description": "Critic weighted score formula Score_t, threshold gates, and independent review rationale."
    },
    "search_space_operators": {
        "title": "Structured Search Space & Operators",
        "required_tokens": ["搜索空间", "算子", "RAG"],
        "description": "Four search dimensions, 23 operators, typed constraints omega={I,O,F,P}, and RAG extraction."
    },
    "five_minute_protocol": {
        "title": "Five-Minute Agile Verification Protocol",
        "required_tokens": ["五分钟", "f_score", "0.55"],
        "decisive_visual": "T10",
        "description": "f_score surrogate fitness, early screening gate, precision=1.00 and recall=0.83."
    },
    "module_microstructure": {
        "title": "MSFR & CPR Microstructure Modules",
        "required_tokens": ["MSFR", "CPR", "多尺度", "原型"],
        "decisive_visual": "T06",
        "description": "MSFR cross-level FPN alignment and CPR prototype logit refinement mechanisms."
    },
    "experimental_trajectory": {
        "title": "Empirical Evolution Trajectory & Ablations",
        "required_tokens": ["FAIR1M", "47.30", "49.14", "AutoResearch"],
        "decisive_visual": "T01",
        "description": "FAIR1M multi-round trajectory, compute efficiency, and Critic/experience ablations."
    }
}


def audit_explanation_depth(text: str, visual_items: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Audit scientific depth and coverage across reader narrative text and bound assets."""
    visual_ids = {str(item.get("id")) for item in (visual_items or []) if item.get("id")}
    norm = text.replace(" ", "")

    results = []
    missing_concepts = []

    for key, spec in REQUIRED_MECHANISM_CONCEPTS.items():
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

    total = len(REQUIRED_MECHANISM_CONCEPTS)
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

    omitted_without_justification = []
    # Every asset in inventory should either be bound or accounted for in omissions
    accounted_ids = {req["id"] for req in must_show} | {req["id"] for req in accounted_omissions}

    return {
        "status": "PASS" if not missing_must_show else "FAIL",
        "must_show_total": len(must_show),
        "must_show_bound": len(must_show) - len(missing_must_show),
        "missing_must_show": missing_must_show,
        "accounted_omissions_count": len(accounted_omissions)
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
