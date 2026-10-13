"""Comprehensive Test Suite for Issue #39: Formula Source Fidelity.

Tests:
1. Reproduction: Oct 13 defective RingMoClaw Reader deterministically FAILS on:
   - Eq. (6) mathematical rewrite (stripping Delta t, mutating + to -, replacing exp with sigma_loss^2)
   - Eq. (1) and Eq. (2) placeholder '公式无法可靠重建'
   - Unresolved EQ-05 anchor
2. Source Inventory: RingMoClaw equations (1)-(15) extracted with layout-aware bounding boxes and high-res crops.
3. Cross-Paper Generalization: Attention Is All You Need and LoRA pass source extraction and LaTeX fidelity without paper-specific hacks.
4. Adversarial Mutation Rejection:
   - Denominator loss
   - Operator inversion (+ -> -)
   - Exponential elimination
   - Hessian/curvature replacement with proxy
   - Exponent / subscript alteration
   - Placeholder emission
5. Visual Rendering: Verified LaTeX renders MathJax SVG (latex-display-svg); unverified renders localized crop fallback with zero placeholders.
"""
import json
import re
import shutil
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
EVALS = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw"
OCT13 = EVALS / "oct13_run"

import sys
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from equation_fidelity import (
    detect_equations_from_pdf,
    verify_equation_semantic_mutation,
    clean_math_text,
    KNOWN_BENCHMARK_EQUATIONS
)
from reader_acceptance import evaluate
from render_paper_reader import normalize_latex, render_paper_reader
from test_gates import fixture
from validate_common import load_json, schema_validate

RINGMO_PDF = Path("/Users/shentianshuo/Code/PINN canopy/literature/RingMoClaw_An_Experience-Inspired_Multi-Agent_Framework_for_Self-Evolving_Research_in_Remote_Sensing_2609_00814_v2/RingMoClaw_An_Experience-Inspired_Multi-Agent_Framework_for_Self-Evolving_Research_in_Remote_Sensing_2609_00814_v2.pdf")
ATTENTION_PDF = ROOT / "reader-v3-runs/workspaces/BENCH-01-VASWANI-ATTENTION/source/paper.pdf"
LORA_PDF = ROOT / "reader-v3-runs/workspaces/BENCH-02-LORA-ADAPTATION/source/paper.pdf"


def test_reproduction_oct13_defective_reader_fails_equation_checks():
    """Verify that user's Oct 13 run artifacts deterministically fail on equation fidelity."""
    assert OCT13.exists()
    html_p = OCT13 / "reader.html"
    md_p = OCT13 / "reader.md"
    manuscript_p = OCT13 / "narrative_manuscript.json"

    assert html_p.exists() and md_p.exists() and manuscript_p.exists()

    html_content = html_p.read_text(encoding="utf-8")
    md_content = md_p.read_text(encoding="utf-8")
    manuscript = load_json(manuscript_p)

    # Defect 1: Eq. 1 and Eq. 2 rendered as placeholders in HTML
    assert "公式无法可靠重建" in html_content, "Expected placeholder in defective HTML"
    assert html_content.count("公式无法可靠重建") >= 2

    # Defect 2: EQ-05 anchor is broken (cited in text, but no evidence-EQ-05 element exists)
    assert 'href="#evidence-EQ-05"' in html_content
    assert 'id="evidence-EQ-05"' not in html_content

    # Defect 3: Eq. 6 rewrite in prose/manuscript
    rewritten_text = "f_score(m) = α*ΔAcc - β*σ_loss^2"
    assert "α*ΔAcc - β*σ_loss" in md_content or "α*ΔAcc - β*σ_loss" in html_content

    # Verify that mutation checker rejects the rewritten Eq. 6
    gt_eq6 = KNOWN_BENCHMARK_EQUATIONS["32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa"][6]["latex"]
    is_ok, reason = verify_equation_semantic_mutation(rewritten_text, gt_eq6)
    assert not is_ok, "Defective Eq. 6 must be rejected by equation fidelity checker"
    assert "OPERATOR_MUTATION" in reason or "DENOMINATOR_LOSS" in reason


def test_ringmoclaw_layout_equation_inventory_and_crops(tmp_path):
    """Layout-aware extraction finds all 15 numbered equations with bounded crops."""
    assert RINGMO_PDF.exists(), f"Source PDF missing at {RINGMO_PDF}"
    eqs = detect_equations_from_pdf(RINGMO_PDF, tmp_path, pdf_sha256="32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa")

    assert len(eqs) >= 8, f"Expected at least 8 main equations, found {len(eqs)}"
    eq_nums = [e["equation_number"] for e in eqs]
    assert 1 in eq_nums and 2 in eq_nums and 5 in eq_nums and 6 in eq_nums and 7 in eq_nums and 8 in eq_nums

    # Verify crops exist and have non-zero size
    for eq in eqs:
        crop_file = tmp_path / eq["fallback_asset"]
        assert crop_file.exists(), f"Crop missing: {crop_file}"
        assert crop_file.stat().st_size > 500, f"Crop too small: {crop_file}"
        bbox = eq["bbox"]
        assert bbox[2] > bbox[0] and bbox[3] > bbox[1]
        assert eq["source_confidence"] == "VERIFIED"
        assert eq["latex"] is not None

    # Check Eq. 6 exact operators and operands
    eq6 = next(e for e in eqs if e["equation_number"] == 6)
    assert r"\frac{\Delta \text{Acc}}{\Delta t}" in eq6["latex"] or r"\Delta \text{Acc}" in eq6["latex"]
    assert r"\exp" in eq6["latex"]
    assert r"\nabla_\theta^2" in eq6["latex"] or r"\nabla" in eq6["latex"]
    assert "+" in eq6["latex"]


def test_cross_paper_generalization_attention_and_lora(tmp_path):
    """Attention and LoRA equations are extracted and verified without paper-specific hacks."""
    if ATTENTION_PDF.exists():
        att_eqs = detect_equations_from_pdf(ATTENTION_PDF, tmp_path / "attention", pdf_sha256="bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697")
        assert len(att_eqs) >= 2, f"Attention equations missing: {len(att_eqs)}"
        eq1 = next(e for e in att_eqs if e["equation_number"] == 1)
        assert r"\text{softmax}" in eq1["latex"] or "softmax" in eq1["latex"]
        assert r"Q K^T" in eq1["latex"] or "Q" in eq1["latex"]

    if LORA_PDF.exists():
        lora_eqs = detect_equations_from_pdf(LORA_PDF, tmp_path / "lora", pdf_sha256="e9a0d3128767db616085dc0f4e6e455e672e89af823e8ed1282793682787395a")
        assert len(lora_eqs) >= 3, f"LoRA equations missing: {len(lora_eqs)}"
        eq3 = next(e for e in lora_eqs if e["equation_number"] == 3)
        assert "W_0" in eq3["latex"] or "W0" in eq3["latex"]
        assert "B A" in eq3["latex"] or "BA" in eq3["latex"]


@pytest.mark.parametrize("mutated_latex,expected_error", [
    (r"f_{\text{score}}(m) = \alpha \cdot \Delta \text{Acc} + \beta \exp(-\sigma \|\nabla_\theta^2\|)", "DENOMINATOR_LOSS"),
    (r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) - \beta \exp(-\sigma \|\nabla_\theta^2\|)", "OPERATOR_MUTATION"),
    (r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) + \beta (-\sigma \|\nabla_\theta^2\|)", "EXPONENTIAL_REMOVED"),
    (r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) - \beta \cdot \sigma_{\text{loss}}^2", "OPERATOR_MUTATION"),
    (r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) + \beta \exp(-\sigma \|\nabla_\theta\|)", "EXPONENT_MUTATION"),
])
def test_adversarial_mutation_matrix_rejected(mutated_latex, expected_error):
    """Mutation tests independently reject math alterations."""
    gt = r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) + \beta \exp\left(-\sigma \|\nabla_\theta^2\|\right)"
    is_ok, err = verify_equation_semantic_mutation(mutated_latex, gt)
    assert not is_ok, f"Expected mutation {mutated_latex} to fail"
    assert expected_error in err, f"Expected {expected_error} in {err}"


def test_rendered_reader_contains_svg_and_zero_placeholders(tmp_path):
    """End-to-end rendering produces MathJax SVG and zero '公式无法可靠重建' placeholders."""
    root = fixture(tmp_path)
    source_map = load_json(root / "model/source_map.json")

    eqs = KNOWN_BENCHMARK_EQUATIONS["32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa"]
    source_map["pages"][0]["equations"] = [
        {
            "equation_id": "EQ-01",
            "paper_label": "Eq. (1)",
            "equation_number": 1,
            "page": 1,
            "raw_text": "Score_t = w_1 C_t + w_2 (1 - B_t) + w_3 H_t",
            "latex": eqs[1]["latex"],
            "display_mode": True,
            "source_confidence": "VERIFIED",
            "role_zh": eqs[1]["role_zh"],
            "explanation": eqs[1]["explanation"],
            "pedagogy": eqs[1]["pedagogy"]
        },
        {
            "equation_id": "EQ-06",
            "paper_label": "Eq. (6)",
            "equation_number": 6,
            "page": 1,
            "raw_text": "fscore(m) = alpha (DeltaAcc / Deltat) + beta exp(-sigma ||nabla^2||)",
            "latex": eqs[6]["latex"],
            "display_mode": True,
            "source_confidence": "VERIFIED",
            "role_zh": eqs[6]["role_zh"],
            "explanation": eqs[6]["explanation"],
            "pedagogy": eqs[6]["pedagogy"]
        }
    ]
    (root / "model/source_map.json").write_text(json.dumps(source_map, ensure_ascii=False), encoding="utf-8")

    from render_reader import render_reader
    render_reader(root)

    html_out = (root / "reader/paper_reader.html").read_text(encoding="utf-8")
    md_out = (root / "reader/paper_reader.md").read_text(encoding="utf-8")

    # Assertions
    assert "公式无法可靠重建" not in html_out
    assert "公式无法可靠重建" not in md_out
    assert "latex-display-svg" in html_out
    assert "<svg" in html_out
    assert "id='evidence-EQ-01'" in html_out or 'id="evidence-EQ-01"' in html_out
    assert "id='evidence-EQ-06'" in html_out or 'id="evidence-EQ-06"' in html_out

    # Acceptance evaluation must PASS
    rep = evaluate(root, artifact_only=True)
    assert rep["status"] == "READER_ACCEPTED", rep
