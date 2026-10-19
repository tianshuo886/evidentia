"""Synthetic offline delivery, anchor resolution, and renderer parity checks."""
import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reader_delivery_audit import audit_delivery_integrity
from render_paper_reader import render_paper_reader_html, render_paper_reader_md, KAMI_LONG_DOC_CSS
from reader_acceptance import GATES


def delivery_manuscript(tmp_path):
    """A tiny image and manuscript, with no source PDF or benchmark corpus."""
    (tmp_path / "assets").mkdir(exist_ok=True)
    (tmp_path / "assets/plot.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="))
    return {"schema_version": "3.0", "paper_id": "synthetic-delivery", "source_sha256": "a" * 64,
            "document": {"title": "Synthetic feature study", "subtitle": "Controlled comparison",
                "paper_meta": {"authors": ["A. Researcher"], "year": 2025, "venue": "Synthetic preprint"},
                "orientation": {"lead": "A small representation experiment."},
                "sections": [{"id": "representation", "title": "Representation and evidence", "blocks": [
                    {"type": "paragraph", "text": "A feature projection is compared under a fixed budget.", "evidence_refs": ["F01", "T01", "p.1"]},
                    {"type": "figure", "evidence_id": "F01", "asset": "assets/plot.png", "page": 1,
                     "caption": "Synthetic projection", "analysis": "The figure shows an input matrix mapped into a smaller feature representation; it explains the operator rather than proving a universal performance guarantee."},
                    {"type": "table", "evidence_id": "T01", "page": 1, "caption": "Controlled scores",
                     "analysis": "Baseline accuracy is 60% and Projection accuracy is 62% at the same budget. This two-point increase has no uncertainty interval, so cross-task superiority remains untested."},
                ]}]}}


def test_defective_artifact_fails_delivery_audit(tmp_path):
    html = r'''<h1>2025 · 2025</h1><a href="#missing">Missing</a>
    <a id="loop" href="#loop">Loop</a><p>Text\nmore text</p>
    <p>〔p.1〕<span class="evidence-cites">[p.1]</span></p>
    <img src="assets/missing.png">'''
    report = audit_delivery_integrity(html, root=tmp_path)
    assert report["status"] == "FAIL"
    assert len(report["errors"]) == 6
    diag = report["diagnostics"]
    assert diag["unresolved_targets"] == ["missing"]
    assert diag["self_links"] == ["loop"]
    assert len(diag["literal_slash_n"]) == 1
    assert diag["duplicate_year"] == "2025 · 2025"
    assert diag["duplicate_citations"] == 1
    assert diag["missing_assets"] == ["assets/missing.png"]


def test_regenerated_reader_passes_delivery_audit(tmp_path):
    manuscript = delivery_manuscript(tmp_path)
    html = render_paper_reader_html(manuscript, tmp_path)
    md = render_paper_reader_md(manuscript, tmp_path)
    report = audit_delivery_integrity(html, md_text=md, root=tmp_path)
    assert report["status"] == "PASS", report["errors"]
    assert report["errors"] == []
    for token in ("Synthetic feature study", "Controlled scores", "F01", "T01", "Baseline", "60%", "62%"):
        assert token in html and token in md
    assert not (tmp_path / "source/paper.pdf").exists()


def test_duplicate_markdown_citations_fail():
    report = audit_delivery_integrity("<p>Clean text</p>", md_text="Claim 〔p.1〕 〔p.1〕")
    assert report["status"] == "FAIL"
    assert report["diagnostics"]["duplicate_citations"] == 1


def test_latex_n_commands_are_not_literal_newlines():
    report = audit_delivery_integrity(r"<p>\nabla x \neq y \nu</p>")
    assert report["status"] == "PASS"
    assert report["diagnostics"]["literal_slash_n"] == []


def test_delivery_integrity_gate_registered_in_acceptance():
    assert {"delivery_integrity", "formula_pedagogy", "mechanistic_depth"} <= set(GATES)


def test_css_figure_dimensions_and_print_rules():
    assert "max-height: 520px" not in KAMI_LONG_DOC_CSS
    for rule in ("max-height: 76vh", "evidentia-lightbox", "object-fit: contain", "@media print", "break-before: page", "break-inside: avoid"):
        assert rule in KAMI_LONG_DOC_CSS


def test_image_relocatable_onerror_handler(tmp_path):
    html = render_paper_reader_html(delivery_manuscript(tmp_path), tmp_path)
    assert re.findall(r'<img [^>]*onerror=[\'"][^\'"]*[\'"]', html)
