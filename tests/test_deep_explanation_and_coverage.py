
"""Paper-independent narrative depth and visual coverage regressions."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reader_depth_audit import audit_reader_mechanistic_depth, audit_visual_evidence_selection
from scientific_claim_verifier import verify_text_claims


@pytest.fixture
def coverage_expectations(tmp_path):
    expectations = {"visual_evidence_selection": {
        "must_show": [{"id": "F01", "label": "Representation flow"},
                      {"id": "T01", "label": "Controlled comparison"}],
        "accounted_omissions": [{"id": "F03", "reason": "Repeated examples retained in the atlas"}],
    }}
    (tmp_path / "coverage_expectations.json").write_text(json.dumps(expectations))
    return expectations


def reader_with_visuals(*ids, text="输入特征矩阵经过投影，再以权重聚合得到紧凑表征。"):
    return {"paper_id": "synthetic-depth", "source_sha256": "a" * 64,
            "document": {"title": "Synthetic study", "sections": [{
                "id": "method", "title": "Method", "blocks": [
                    {"type": "paragraph", "text": text},
                    *[{"type": "table" if eid.startswith("T") else "figure", "evidence_id": eid,
                       "caption": "Synthetic controlled evidence",
                       "analysis": "图表展示输入特征经过投影后的表示变化，并对照固定训练预算下的基线结果；这些观察支持当前设置中的增益，但并不代表其他任务上仍有同样效果。"}
                      for eid in ids],
                ]}]}}


def test_coverage_expectations_fixture_valid(coverage_expectations):
    selection = coverage_expectations["visual_evidence_selection"]
    required = {item["id"] for item in selection["must_show"]}
    omitted = {item["id"] for item in selection["accounted_omissions"]}
    assert required == {"F01", "T01"}
    assert required.isdisjoint(omitted)
    assert all(item["reason"] for item in selection["accounted_omissions"])


def test_defective_reader_fails_depth_audit(tmp_path, coverage_expectations, monkeypatch):
    monkeypatch.delenv("EVIDENTIA_FIXTURE_ACCEPTANCE", raising=False)
    report = audit_reader_mechanistic_depth(tmp_path, reader_with_visuals(text="方法很好，结果不错。"))
    assert report["status"] == "DEFICIT"
    kinds = {d["type"] for d in report["diagnostics"]}
    assert {"LACKS_REPRESENTATION_DEPTH", "MISSING_MUST_SHOW"} <= kinds
    assert {d["target"] for d in report["diagnostics"] if d["type"] == "MISSING_MUST_SHOW"} == {"F01", "T01"}


def test_corrected_reader_achieves_complete_depth(tmp_path, coverage_expectations, monkeypatch):
    monkeypatch.delenv("EVIDENTIA_FIXTURE_ACCEPTANCE", raising=False)
    report = audit_reader_mechanistic_depth(tmp_path, reader_with_visuals("F01", "T01"))
    assert report["status"] == "PASS"
    assert report["errors"] == []
    assert report["bound_visuals_count"] == 2


def test_visual_selection_audit_passes_without_omissions(coverage_expectations):
    report = audit_visual_evidence_selection([{"id": "F01"}, {"id": "T01"}], coverage_expectations)
    assert report["status"] == "PASS"
    assert report["must_show_bound"] == report["must_show_total"] == 2
    assert report["missing_must_show"] == []
    assert report["accounted_omissions_count"] == 1


def test_visual_selection_reports_missing_asset(coverage_expectations):
    report = audit_visual_evidence_selection([{"id": "F01"}, {"id": "F99"}], coverage_expectations)
    assert report["status"] == "FAIL"
    assert [item["id"] for item in report["missing_must_show"]] == ["T01"]
    assert report["must_show_bound"] == 1


def test_narrative_purity_no_internal_machinery_leaked():
    text = "读者独立评估：本实验仅比较固定预算下的两种特征投影，尚不能推广到所有任务。"
    assert verify_text_claims(text) == []
    assert any(d["rule"] == "AUDIT_VOCABULARY_LEAKAGE"
               for d in verify_text_claims(text + "【门禁检查通过】"))


def test_mechanism_audit_without_paper_expectations_is_not_run():
    from reader_depth_audit import audit_explanation_depth

    report = audit_explanation_depth("A synthetic paragraph with no current-paper audit plan.")
    assert report["overall_status"] == "NOT_RUN"
    assert report["concepts_audited"] == 0
    assert report["score"] is None
