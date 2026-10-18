"""Generic math teaching contracts, independent of paper-specific answers."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from equation_fidelity import derive_equation_pedagogy
from reader_math_explanation_audit import audit_single_equation, audit_math_pedagogy
from render_paper_reader import render_block_html, render_paper_reader_md
from validate_common import schema_validate


@pytest.fixture
def ratio_equation():
    return {
        "equation_id": "EQ-01", "page": 1, "equation_number": 1,
        "paper_label": "Eq. (1)", "raw_text": "r = u / v",
        "latex": r"r = \frac{u}{v}", "source_confidence": "VERIFIED",
        "explanation": "该比值用输入测量 u 除以参考尺度 v 得到归一化结果 r，要求参考尺度非零。",
        "pedagogy": {
            "role": "测量值的尺度归一化",
            "explanation_priority": "MUST_EXPLAIN",
            "symbol_definitions": [
                {"symbol": "u", "name": "测量值", "interpretation": "输入测量值"},
                {"symbol": "v", "name": "参考尺度", "interpretation": "非零参考尺度"},
            ],
            "input_output": {"inputs": ["u", "v"], "outputs": ["r"]},
            "term_interpretations": [
                {"term": "u", "role": "分子", "intuition": "输入测量值决定比值大小"},
                {"term": "v", "role": "分母", "intuition": "非零参考尺度用于归一化"},
            ],
            "assumptions": ["v 不等于零"],
            "implementation_proxy": "合成示例仅使用输入测量；未声称任何额外工程代理。",
            "source_anchors": ["synthetic fixture p.1"],
        },
    }


def manuscript_for(equation):
    block = dict(equation, type="equation", evidence_id=equation["equation_id"])
    return {
        "schema_version": "2.0", "paper_id": "synthetic-math",
        "source_sha256": hashlib.sha256(equation["raw_text"].encode()).hexdigest(),
        "created_at": "2026-01-01T00:00:00Z",
        "document": {"title": "Synthetic mathematics", "paper_meta": {}, "sections": [
            {"id": "math", "title": "Normalization", "blocks": [block]}
        ]},
    }


def test_schemas_validate_synthetic_structured_pedagogy(ratio_equation):
    assert schema_validate(ratio_equation, "equation") == []
    assert schema_validate(manuscript_for(ratio_equation), "narrative_manuscript") == []


@pytest.mark.parametrize("field,value", [
    ("explanation_priority", "UNKNOWN"),
    ("symbol_definitions", [{"symbol": "u"}]),
    ("term_interpretations", [{"term": "u"}]),
])
def test_equation_schema_rejects_invalid_teaching_fields(ratio_equation, field, value):
    ratio_equation["pedagogy"][field] = value
    assert schema_validate(ratio_equation, "equation")


@pytest.mark.parametrize("latex", [r"r = \frac{u}{v}", r"p = \exp(-x)", r"s = \sum_i x_i"])
def test_generic_operators_require_explanation(latex):
    pedagogy = derive_equation_pedagogy(latex, latex, role_zh="合成算子的计算定义")
    assert pedagogy["explanation_priority"] == "MUST_EXPLAIN"
    assert pedagogy["role"] == "合成算子的计算定义"
    assert pedagogy["input_output"]["inputs"]
    assert pedagogy["input_output"]["outputs"]
    # Automatic hints must not invent source anchors or implementation proxies.
    assert pedagogy["source_anchors"] == []
    assert pedagogy["implementation_proxy"] is None


def test_derivation_uses_raw_text_when_latex_is_missing():
    raw = "r = u / v"
    assert derive_equation_pedagogy(None, raw) == derive_equation_pedagogy(raw, raw)


def test_explanation_priority_is_independent_of_equation_number():
    simple = "x = y"
    material = r"r = \frac{u}{v}"
    for number in (1, 3, 17, 120):
        assert derive_equation_pedagogy(simple, simple, eq_num=number)[
            "explanation_priority"
        ] == derive_equation_pedagogy(simple, simple)["explanation_priority"]
        assert derive_equation_pedagogy(material, material, eq_num=number)[
            "explanation_priority"
        ] == "MUST_EXPLAIN"


def test_audit_priority_uses_equation_structure_not_number():
    simple = {"latex": "x = y", "explanation": "The synthetic output equals the input."}
    results = [
        audit_single_equation({**simple, "equation_number": number}, "")
        for number in (1, 6, 15, 120)
    ]
    assert {result["priority"] for result in results} == {"AUDIT_ONLY"}


def test_material_equation_without_explanation_fails(ratio_equation):
    ratio_equation["explanation"] = "比值公式"
    result = audit_single_equation(ratio_equation, full_context_text="")
    assert not result["passed"]
    assert any("UNEXPLAINED_MATERIAL_EQUATION" in issue for issue in result["issues"])


def test_structured_explanation_covers_terms(ratio_equation):
    result = audit_single_equation(ratio_equation, full_context_text="")
    assert result["passed"], result
    assert result["checks"]["term_coverage"] == 1.0


def test_missing_term_grounding_fails(ratio_equation):
    ratio_equation["explanation"] = "这里说明计算结果可用于后续实验，但没有解释任何关键组成项。"
    result = audit_single_equation(ratio_equation, full_context_text="")
    assert not result["passed"]
    assert result["checks"]["term_coverage"] == 0.0
    assert any("INSUFFICIENT_TERM_GROUNDING" in issue for issue in result["issues"])


def test_auxiliary_equation_allows_concise_definition():
    equation = {"equation_id": "EQ-AUX", "latex": "S = {a, b}",
                "explanation": "集合 S 定义为包含两个候选元素 a 与 b 的有限集合。",
                "explanation_priority": "CONCISE_DEFINE"}
    result = audit_single_equation(equation, full_context_text="")
    assert result["passed"], result
    assert result["checks"]["has_concise_def"]


def test_html_and_markdown_preserve_teaching_content(tmp_path, ratio_equation):
    manuscript = manuscript_for(ratio_equation)
    html = render_block_html(manuscript["document"]["sections"][0]["blocks"][0], tmp_path)
    markdown = render_paper_reader_md(manuscript, tmp_path)
    for marker in ("eq-role", "eq-terms", "eq-proxy"):
        assert marker in html
    for marker in ("**角色定位**", "**核心项解析与数学直觉**", "**工程实现与代理说明**"):
        assert marker in markdown
    pedagogy = ratio_equation["pedagogy"]
    for rendered in (html, markdown):
        assert pedagogy["role"] in rendered
        assert pedagogy["implementation_proxy"] in rendered
        for term in pedagogy["term_interpretations"]:
            assert term["intuition"] in rendered
    audit = audit_math_pedagogy(tmp_path, manuscript=manuscript, html_text=html, md_text=markdown)
    assert audit["status"] == "PASSED", audit
    assert audit["equations_count"] == 1
    assert audit["score"] == 1.0


def test_workspace_audit_falls_back_to_source_map(tmp_path, ratio_equation):
    silent = copy.deepcopy(ratio_equation)
    silent["equation_id"] = "EQ-02"
    silent["paper_label"] = "Eq. (2)"
    silent["explanation"] = ""
    model = tmp_path / "model"
    model.mkdir()
    (model / "source_map.json").write_text(json.dumps({"pages": [
        {"number": 1, "equations": [ratio_equation, silent]}
    ]}), encoding="utf-8")
    result = audit_math_pedagogy(tmp_path, manuscript={}, html_text="", md_text="")
    assert result["status"] == "FAILED"
    assert result["equations_count"] == 2
    assert result["passed_count"] == 1
    assert result["score"] == 0.5
    assert any("UNEXPLAINED_MATERIAL_EQUATION" in error for error in result["errors"])
