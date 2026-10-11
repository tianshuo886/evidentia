"""Test suite for Issue #37: Deep Explanation and Visual Coverage.

Verifies:
1. Figure 2 (F02) and Roman-numeral tables (T01-T10) are successfully extracted and bound
2. Defective Reader fails depth audit due to missing architecture and explanation deficits
3. Corrected Reader satisfies all 6 core explanation areas and binds 9 must-show assets
4. Visual evidence selection audit accounts for Figs. 6-9 and all tables without arbitrary blanket counts
5. Zero internal pipeline vocabulary (Lens, Council, O/I/A) leaked into final narrative
"""
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVALS = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw"

import sys
sys.path.insert(0, str(SCRIPTS))

from reader_depth_audit import audit_explanation_depth, audit_visual_evidence_selection
from validate_common import load_json


def test_coverage_expectations_fixture_valid():
    """Verify that coverage expectations fixture is complete and well-structured."""
    exp_p = EVALS / "coverage_expectations.json"
    assert exp_p.exists()
    exp = load_json(exp_p)
    assert len(exp["knowledge_coverage_requirements"]) >= 7
    must_show = exp["visual_evidence_selection"]["must_show"]
    accounted = exp["visual_evidence_selection"]["accounted_omissions"]
    must_show_ids = {m["id"] for m in must_show}
    accounted_ids = {a["id"] for a in accounted}

    # F02 must be required
    assert "F02" in must_show_ids
    assert "T01" in must_show_ids
    assert "T06" in must_show_ids
    assert "T07" in must_show_ids
    assert "T08" in must_show_ids
    assert "T09" in must_show_ids
    assert "T10" in must_show_ids

    # Figs 6-9 must be accounted for
    assert {"F06", "F07", "F08", "F09"}.issubset(accounted_ids)


def test_defective_reader_fails_depth_audit():
    """Defective Reader fails depth audit due to missing F02 and incomplete mechanisms."""
    defective_text = (EVALS / "defective_reader.md").read_text(encoding="utf-8")
    res = audit_explanation_depth(defective_text, visual_items=[])
    assert res["overall_status"] == "DEFICIT"
    assert res["score"] < 60.0
    deficits = [d["concept"] for d in res["explanation_deficits"]]
    assert any("Fig. 2" in d or "Architecture" in d for d in deficits)


def test_corrected_reader_achieves_complete_depth():
    """Corrected Reader covers all 6 key concepts and achieves 100% score."""
    corrected_text = (EVALS / "corrected_reader.md").read_text(encoding="utf-8")
    exp = load_json(EVALS / "coverage_expectations.json")
    must_show_items = [{"id": m["id"]} for m in exp["visual_evidence_selection"]["must_show"]]

    res = audit_explanation_depth(corrected_text, visual_items=must_show_items)
    assert res["overall_status"] == "PASS"
    assert res["score"] == 100.0
    assert len(res["explanation_deficits"]) == 0


def test_visual_selection_audit_passes_without_omissions():
    """Visual selection audit accounts for all must-show assets and Atlas omissions."""
    exp = load_json(EVALS / "coverage_expectations.json")
    must_show_items = [{"id": m["id"]} for m in exp["visual_evidence_selection"]["must_show"]]

    vis_res = audit_visual_evidence_selection(must_show_items, exp)
    assert vis_res["status"] == "PASS"
    assert vis_res["must_show_bound"] == len(exp["visual_evidence_selection"]["must_show"])
    assert len(vis_res["missing_must_show"]) == 0
    assert vis_res["accounted_omissions_count"] >= 9


def test_narrative_purity_no_internal_machinery_leaked():
    """Check that neither Lens, Council, O/I/A, nor task IDs leak into narrative."""
    corrected_text = (EVALS / "corrected_reader.md").read_text(encoding="utf-8")
    forbidden = ["Author Lens", "Reviewer Lens", "Mechanism Lens", "Lens Council", "TASK-V3", "O/I/A", "schema_version"]
    for term in forbidden:
        assert term not in corrected_text, f"Internal term leaked: {term}"
