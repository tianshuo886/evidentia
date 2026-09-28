"""Tests for Chinese-first Narrative Scientific Reader & Evidence Atlas (Issue #9 / P0 Workstream C).

Validates:
- Tripartite Separation: Evidentia owns truth, AI owns narrative, Kami owns presentation.
- Dedicated semantic Narrative Manuscript (narrative_manuscript.json).
- Split surfaces:
  * Primary Paper Reader (paper_reader.html, paper_reader.pdf, paper_reader.md)
  * Secondary Inspection Evidence Atlas (evidence_atlas.html, evidence_atlas.json)
- Kami Chinese long-doc presentation backend integration:
  * Parchment background, ink-blue accent, serif typography.
  * Cover, TOC, chapter rhythm, lead paragraphs, callouts, takeaways.
  * Kami delivery & automated QA checks (placeholders, visual, orphans, density, fonts).
- Preservation of backward compatibility aliases (reader.html, reader.md, reader.pdf, render_ir.json).
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture
from validate_common import schema_validate, load_json

SEVEN_LAYERS = [
    "一分钟看懂这篇论文",
    "论文到底在解决什么问题",
    "方法到底怎么工作",
    "关键实验逐个说明",
    "综合科学判断",
    "可复用技术内容",
    "证据审计附录"
]

def test_chinese_reader_ir_and_dual_rendering(tmp_path):
    r = fixture(tmp_path)
    
    # Run render_reader.py
    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    reader_dir = r / 'reader'
    
    # 1. Narrative Manuscript IR validation
    man_p = reader_dir / 'narrative_manuscript.json'
    assert man_p.exists()
    man = load_json(man_p)
    errs_man = schema_validate(man, 'narrative_manuscript')
    assert not errs_man, f"narrative_manuscript schema errors: {errs_man}"

    # 2. Legacy IR compatibility validation
    ir_p = reader_dir / 'paper_reader_ir.json'
    assert ir_p.exists()
    ir = load_json(ir_p)
    errs_ir = schema_validate(ir, 'paper_reader_ir')
    assert not errs_ir, f"paper_reader_ir schema errors: {errs_ir}"

    # 3. HTML Reader validation (Kami long-doc layout)
    html_p = reader_dir / 'paper_reader.html'
    assert html_p.exists()
    html_text = html_p.read_text(encoding='utf-8')
    for layer in SEVEN_LAYERS:
        assert layer in html_text, f"Missing narrative section in HTML: {layer}"
    
    # Verify Kami long-doc elements
    assert "class=\"cover\"" in html_text
    assert "class=\"toc\"" in html_text
    assert "class=\"chapter\"" in html_text
    assert "TsangerJinKai02" in html_text or "Source Han Serif" in html_text
    assert "#f5f4ed" in html_text  # parchment background
    assert "#1B365D" in html_text  # brand accent
    
    # Verify primary reader is NOT dominated by dashboard cards
    assert ".section-card" not in html_text
    assert ".oia-grid" not in html_text
    assert "badge-epistemic-supported" not in html_text

    # Verify audit details tag is used in appendix
    assert '<details' in html_text
    assert 'Observation' in html_text
    assert 'Author Interpretation' in html_text
    assert 'Reader Assessment' in html_text

    # 4. Markdown Reader validation
    md_p = reader_dir / 'paper_reader.md'
    assert md_p.exists()
    md_text = md_p.read_text(encoding='utf-8')
    for layer in SEVEN_LAYERS:
        assert layer in md_text, f"Missing narrative section in MD: {layer}"

    # 5. Backward compatibility aliases
    assert (reader_dir / 'reader.html').exists()
    assert (reader_dir / 'reader.md').exists()
    assert (reader_dir / 'reader.pdf').exists()
    assert (reader_dir / 'render_ir.json').exists()

    # 6. Run reader audit
    res_audit = subprocess.run([
        PY, str(ROOT / 'scripts/reader_audit.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res_audit.returncode == 0, res_audit.stdout + res_audit.stderr

def test_reader_split_paper_reader_and_evidence_atlas(tmp_path):
    """Verify that Paper Reader and Evidence Atlas are decoupled and serve distinct purposes."""
    r = fixture(tmp_path)
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    reader_dir = r / 'reader'
    paper_reader_html = (reader_dir / 'paper_reader.html').read_text(encoding='utf-8')
    atlas_html = (reader_dir / 'evidence_atlas.html').read_text(encoding='utf-8')

    # 1. Primary Paper Reader: Editorial, continuous prose, links to atlas
    assert "evidence_atlas.html" in paper_reader_html
    assert "打开完整证据图谱" in paper_reader_html

    # 2. Evidence Atlas: Audit-focused, full claim/evidence cards, O/I/A grid
    assert "Evidence Atlas" in atlas_html
    assert "oia-grid" in atlas_html
    assert "Observation (客观实证)" in atlas_html
    assert "Author Interpretation (作者推断)" in atlas_html
    assert "Reader Assessment (读者研判)" in atlas_html
    assert "C01" in atlas_html
    assert "F01" in atlas_html
    assert "p.1" in atlas_html
    assert "paper_reader.html" in atlas_html  # bidirectional return link to primary reader

def test_kami_presentation_backend_and_audit(tmp_path):
    """Verify that Kami presentation backend delivers PDF and passes automated checks."""
    r = fixture(tmp_path)
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    reader_dir = r / 'reader'
    pdf_p = reader_dir / 'paper_reader.pdf'
    assert pdf_p.exists()
    assert pdf_p.stat().st_size > 10000, "PDF must be rendered with content"

    audit_p = reader_dir / 'kami_audit.json'
    assert audit_p.exists(), "Kami audit report must be written"
    report = load_json(audit_p)
    assert report['status'] == 'OK', f"Kami audit failed: {report}"
