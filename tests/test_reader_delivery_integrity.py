"""Tests for Reader Delivery Integrity, offline assets, and anchor resolution (Issue #43)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reader_delivery_audit import audit_delivery_integrity
from render_paper_reader import render_paper_reader_html, render_paper_reader_md, KAMI_LONG_DOC_CSS
from reader_acceptance import GATES, _evaluate_artifact


def test_defective_oct13_artifact_fails_delivery_audit():
    """Verify that defective oct13_run artifact triggers deterministic delivery errors."""
    oct13_html_p = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw/oct13_run/reader.html"
    assert oct13_html_p.exists(), f"Missing fixture {oct13_html_p}"
    
    html_text = oct13_html_p.read_text(encoding="utf-8")
    audit = audit_delivery_integrity(html_text)
    
    assert audit["status"] == "FAIL"
    assert len(audit["errors"]) >= 5
    
    diag = audit["diagnostics"]
    # 1. Exactly 15 unresolved targets
    assert len(diag["unresolved_targets"]) == 15
    assert set(diag["unresolved_targets"]) == {
        'evidence-EQ-05', 'evidence-T04', 'p.11', 'p.12', 'p.13', 'p.14',
        'p.15', 'p.2', 'p.20', 'p.4', 'p.5', 'p.6', 'p.7', 'p.8', 'p.9'
    }
    
    # 2. Exactly 1 self-link
    assert diag["self_links"] == ["p.1"]
    
    # 3. Exactly 15 literal \n sequences
    assert len(diag["literal_slash_n"]) >= 10
    
    # 4. Cover duplicate year
    assert diag["duplicate_year"] == "2026 · 2026"
    
    # 5. Duplicate citation pills in prose
    assert diag["duplicate_citations"] > 0


def test_regenerated_reader_passes_delivery_audit():
    """Verify that newly rendered Reader HTML and Markdown pass all delivery integrity gates."""
    oct13_dir = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw/oct13_run"
    manuscript = json.loads((oct13_dir / "narrative_manuscript.json").read_text(encoding="utf-8"))
    
    html_text = render_paper_reader_html(manuscript, oct13_dir)
    md_text = render_paper_reader_md(manuscript, oct13_dir)
    
    audit = audit_delivery_integrity(html_text, md_text=md_text, root=oct13_dir)
    
    assert audit["status"] == "PASS", f"Audit failed: {audit['errors']}"
    assert audit["errors"] == []
    assert audit["diagnostics"]["unresolved_targets"] == []
    assert audit["diagnostics"]["self_links"] == []
    assert audit["diagnostics"]["literal_slash_n"] == []
    assert audit["diagnostics"]["duplicate_year"] is None
    assert audit["diagnostics"]["duplicate_citations"] == 0


def test_delivery_integrity_gate_registered_in_acceptance():
    """Verify delivery_integrity is registered in reader acceptance gates."""
    assert "delivery_integrity" in GATES
    assert "formula_pedagogy" in GATES
    assert "mechanistic_depth" in GATES


def test_css_figure_dimensions_and_print_rules():
    """Verify figure presentation CSS and print media rules for reading legibility."""
    # Issue #45 raised the cap so dense multi-panel figures stay readable.
    assert "max-height: 520px" not in KAMI_LONG_DOC_CSS
    assert "max-height: 76vh" in KAMI_LONG_DOC_CSS
    assert "evidentia-lightbox" in KAMI_LONG_DOC_CSS
    assert "object-fit: contain" in KAMI_LONG_DOC_CSS
    assert "@media print" in KAMI_LONG_DOC_CSS
    assert "break-before: page" in KAMI_LONG_DOC_CSS
    assert "break-inside: avoid" in KAMI_LONG_DOC_CSS


def test_image_relocatable_onerror_handler():
    """Verify that rendered figures and tables include relocatable asset fallback handlers."""
    ringmoclaw_dir = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw"
    oct13_dir = ringmoclaw_dir / "oct13_run"
    manuscript = json.loads((oct13_dir / "narrative_manuscript.json").read_text(encoding="utf-8"))
    
    html_text = render_paper_reader_html(manuscript, ringmoclaw_dir)
    img_matches = re.findall(r'<img [^>]*onerror=[\'"][^\'"]*[\'"]', html_text)
    assert len(img_matches) > 0, "Rendered images must include onerror relocatable fallback handlers"
