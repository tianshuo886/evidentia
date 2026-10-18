"""Source-fidelity contracts using redistributable synthetic equations.

Licensed PDF validation is opt-in; heuristic transcription is not verification.
"""
import hashlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from equation_fidelity import clean_math_text, detect_equations_from_pdf, verify_equation_semantic_mutation
from kami_adapter import find_kami_root, render_math_html
from render_paper_reader import render_block_html, render_paper_reader_md


@pytest.fixture
def synthetic_pdf(tmp_path):
    """Exercise real text/layout extraction without a licensed source asset."""
    import fitz

    pdf = tmp_path / "synthetic.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=400)
        page.insert_text((60, 70), "Synthetic equation extraction fixture")
        page.insert_text((60, 130), "y = a + b (1)")
        page.insert_text((60, 220), "z = c / d (2)")
        doc.save(pdf)
    return pdf


def assert_unreviewed_inventory(equations, root):
    assert equations, "Expected numbered equations in the source PDF"
    for eq in equations:
        assert eq["source_confidence"] == "UNCERTAIN"
        assert eq["verification_receipt"]["source_verified"] is False
        assert eq["raw_text"]
        assert eq["latex"]  # Useful proposal, not independently reviewed evidence.
        assert eq["page"] >= 1
        x0, y0, x1, y1 = eq["bbox"]
        assert x1 > x0 and y1 > y0
        crop = root / eq["fallback_asset"]
        assert crop.is_file()
        assert crop.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_synthetic_layout_extraction_preserves_source_uncertainty(synthetic_pdf, tmp_path):
    digest = hashlib.sha256(synthetic_pdf.read_bytes()).hexdigest()
    equations = detect_equations_from_pdf(synthetic_pdf, tmp_path, pdf_sha256=digest)
    assert [eq["equation_number"] for eq in equations] == [1, 2]
    assert [eq["equation_id"] for eq in equations] == ["EQ-01", "EQ-02"]
    assert "y = a + b" in equations[0]["raw_text"]
    assert "z = c / d" in equations[1]["raw_text"]
    assert_unreviewed_inventory(equations, tmp_path)


def test_licensed_pdf_extraction_opt_in(tmp_path):
    configured = os.environ.get("EVIDENTIA_LICENSED_EQUATION_PDF")
    if not configured:
        pytest.skip("Set EVIDENTIA_LICENSED_EQUATION_PDF to opt into licensed PDF validation")
    pdf = Path(configured).expanduser()
    assert pdf.is_file(), "EVIDENTIA_LICENSED_EQUATION_PDF must name an existing PDF"
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert_unreviewed_inventory(
        detect_equations_from_pdf(pdf, tmp_path, pdf_sha256=digest), tmp_path
    )


@pytest.mark.parametrize("source,candidate,error", [
    (r"r = \frac{u}{\Delta t}", r"r = u", "DENOMINATOR_LOSS"),
    (r"q = a + \beta b", r"q = a - \beta b", "OPERATOR_MUTATION"),
    (r"q = \exp(-x)", r"q = (-x)", "EXPONENTIAL_REMOVED"),
    (r"h = \nabla_\theta^2 g", r"h = \nabla_\theta g", "EXPONENT_MUTATION"),
])
def test_supported_math_mutations_are_rejected(source, candidate, error):
    # Positive control prevents an always-rejecting verifier from passing.
    assert verify_equation_semantic_mutation(source, source)[0]
    accepted, reason = verify_equation_semantic_mutation(candidate, source)
    assert not accepted
    assert error in reason


@pytest.mark.parametrize("source,candidate", [
    (r"q = a + \beta b", r"q=a+\beta b"),
    (r"q = a \cdot b", r"q = a \times b"),
    (r"q = \exp(-x)", r"q=\exp(-x)"),
])
def test_formatting_only_changes_are_accepted(source, candidate):
    assert verify_equation_semantic_mutation(candidate, source)[0]


def test_ocr_math_character_normalization():
    assert clean_math_text("  α − β ≤ γ  ") == r"\alpha - \beta \le  \gamma"


@pytest.mark.parametrize("confidence", ["UNCERTAIN", "AMBIGUOUS", "NOT_STATED"])
def test_unverified_html_uses_local_source_crop(synthetic_pdf, tmp_path, confidence):
    equation = detect_equations_from_pdf(synthetic_pdf, tmp_path)[0]
    equation.update(type="equation", source_confidence=confidence)
    html = render_block_html(equation, tmp_path)
    assert "equation-fallback" in html
    assert equation["fallback_asset"] in html
    assert "math-source" not in html
    assert "公式无法可靠重建" not in html
    assert f"id='evidence-{equation['equation_id']}'" in html


def test_missing_transcription_renders_source_crop_in_both_views(synthetic_pdf, tmp_path):
    equation = detect_equations_from_pdf(synthetic_pdf, tmp_path)[0]
    equation.update(type="equation", latex=None)
    manuscript = {"document": {"title": "Synthetic source", "sections": [
        {"id": "math", "title": "Math", "blocks": [equation]}
    ]}}
    html = render_block_html(equation, tmp_path)
    markdown = render_paper_reader_md(manuscript, tmp_path)
    for rendered in (html, markdown):
        assert equation["fallback_asset"] in rendered
        assert "公式无法可靠重建" not in rendered
    assert "equation-fallback" in html
    assert "![公式源图 EQ-01]" in markdown


def test_verified_equation_emits_math_source_not_crop(tmp_path):
    equation = {"type": "equation", "equation_id": "EQ-01",
                "latex": "y = a + b", "source_confidence": "VERIFIED"}
    html = render_block_html(equation, tmp_path)
    assert "math-source" in html
    assert "y = a + b" in html
    assert "equation-fallback" not in html
    assert "id='evidence-EQ-01'" in html


def test_math_rendering_without_backend_fails_explicitly(tmp_path):
    html = render_block_html({"type": "equation", "latex": "y = a + b"}, tmp_path)
    with pytest.raises(RuntimeError, match="MathJax renderer is required"):
        render_math_html(html, kami_root=tmp_path / "missing-backend")
    assert render_math_html("<p>No equations</p>", kami_root=tmp_path) == "<p>No equations</p>"


def test_verified_math_renders_svg_when_backend_is_installed(tmp_path):
    kami_root = find_kami_root()
    if kami_root is None or not (kami_root / "scripts/math_render.py").is_file():
        pytest.skip("Optional SVG integration requires an installed Kami math backend")
    html = render_block_html({"type": "equation", "equation_id": "EQ-01",
                              "latex": "y = a + b", "source_confidence": "VERIFIED"}, tmp_path)
    rendered = render_math_html(html, kami_root=kami_root)
    assert "latex-display-svg" in rendered
    assert "<svg" in rendered
    assert "evidence-EQ-01" in rendered
