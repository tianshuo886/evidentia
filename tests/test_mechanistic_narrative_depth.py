"""Generic representation depth and substantive visual interpretation tests."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reader_depth_audit import audit_reader_mechanistic_depth
from reader_acceptance import GATES
from test_deep_explanation_and_coverage import reader_with_visuals


@pytest.mark.parametrize("text", [
    "The input feature matrix is projected into a smaller representation before pooling.",
    "输入张量先经过矩阵投影，再沿空间维度加权聚合为低维表征。",
])
def test_representation_mechanics_present(tmp_path, monkeypatch, text):
    monkeypatch.delenv("EVIDENTIA_FIXTURE_ACCEPTANCE", raising=False)
    report = audit_reader_mechanistic_depth(tmp_path, reader_with_visuals(text=text))
    assert report["status"] == "PASS"
    assert report["errors"] == []


def test_missing_representation_mechanics_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("EVIDENTIA_FIXTURE_ACCEPTANCE", raising=False)
    report = audit_reader_mechanistic_depth(tmp_path, reader_with_visuals(text="The method works well."))
    assert report["status"] == "DEFICIT"
    assert any(d["type"] == "LACKS_REPRESENTATION_DEPTH" for d in report["diagnostics"])


@pytest.mark.parametrize("kind", ["figure", "table"])
def test_shallow_placeholder_visual_analysis_fails_depth_gate(tmp_path, kind):
    manuscript = reader_with_visuals("F01")
    visual = manuscript["document"]["sections"][0]["blocks"][1]
    visual.update(type=kind, caption="Short caption", analysis="Short caption")
    report = audit_reader_mechanistic_depth(tmp_path, manuscript)
    assert report["status"] == "DEFICIT"
    assert {"SHALLOW_VISUAL_ANALYSIS", "PLACEHOLDER_VISUAL_ANALYSIS"} <= {
        d["type"] for d in report["diagnostics"]}


def test_substantive_visual_grounding_passes_depth_gate(tmp_path):
    report = audit_reader_mechanistic_depth(tmp_path, reader_with_visuals("F01", "T01"))
    assert report["status"] == "PASS"
    assert report["errors"] == []
    assert report["bound_visuals_count"] == 2


def test_mechanistic_depth_gate_integrated_in_reader_acceptance():
    assert "mechanistic_depth" in GATES
