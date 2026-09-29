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

DEFAULT_LAYERS = [
    "一分钟看懂这篇论文",
    "论文到底在解决什么问题",
    "方法到底怎么工作",
    "关键实验逐个说明",
    "证据最终支持了什么",
    "结论与边界",
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
    for layer in DEFAULT_LAYERS:
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
    for layer in DEFAULT_LAYERS:
        assert layer in md_text, f"Missing narrative section in MD: {layer}"

    # 5. Backward compatibility aliases
    assert (reader_dir / 'reader.html').exists()
    assert (reader_dir / 'reader.md').exists()
    assert (reader_dir / 'reader.pdf').exists()
    assert (reader_dir / 'render_ir.json').exists()

    # 6. Negative assertions (Issue #12 Faithful-reading firewall)
    assert "可复用技术内容" not in html_text
    assert "可复用技术内容" not in md_text
    assert "迁移到你的项目" not in html_text
    assert "迁移到你的项目" not in md_text
    assert "建议用于项目" not in html_text
    assert "建议用于项目" not in md_text
    assert "项目适配" not in html_text
    assert not (r / 'apply').exists(), "apply/ must not exist after PAPER_READING"
    assert not (reader_dir / 'technical_extraction.md').exists()
    assert not (reader_dir / 'technical_extraction.html').exists()

    # 7. Run reader audit
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

def test_technical_extraction_mode_positive(tmp_path):
    """Explicit-mode positive test: technical extraction appears only when requested."""
    r = fixture(tmp_path)
    (r / 'run_state.json').write_text(json.dumps({
        "schema_version": "1.0",
        "run_id": "test-run",
        "mode": "evidentia",
        "intent": "PAPER_TECHNICAL_EXTRACTION",
        "phase": "FREEZE",
        "allowed_inputs": ["working/paper.pdf"],
        "forbidden_inputs": ["apply/", "project/", "memory/project/"],
        "artifacts": {}
    }))

    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r),
        '--intent', 'PAPER_TECHNICAL_EXTRACTION'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    reader_dir = r / 'reader'
    html_p = reader_dir / 'paper_reader.html'
    html_text = html_p.read_text(encoding='utf-8')
    assert "论文技术细节提取" in html_text
    assert not (r / 'apply').exists()

    # Dedicated standalone technical extraction artifacts
    assert (reader_dir / 'technical_extraction.md').exists()
    assert (reader_dir / 'technical_extraction.html').exists()
    tech_md = (reader_dir / 'technical_extraction.md').read_text(encoding='utf-8')
    assert "论文技术细节提取" in tech_md
    assert "迁移到你的项目" not in tech_md

def test_project_apply_mode_and_frozen_reader_hash_immutability(tmp_path):
    """Explicit-mode positive test: Project Apply runs only upon request and preserves reader hash."""
    import hashlib
    r = fixture(tmp_path)

    # Build argument reconstruction and freeze paper model
    from build_argument_reconstruction import build_argument_reconstruction
    build_argument_reconstruction(r)

    res_freeze = subprocess.run([
        PY, str(ROOT / 'scripts/freeze_check.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res_freeze.returncode == 0, res_freeze.stdout + res_freeze.stderr

    # 1. Render default paper reader
    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    reader_dir = r / 'reader'
    html_sha = hashlib.sha256((reader_dir / 'paper_reader.html').read_bytes()).hexdigest()
    md_sha = hashlib.sha256((reader_dir / 'paper_reader.md').read_bytes()).hexdigest()

    # 2. Create project document
    proj_doc = tmp_path / 'nebula_project.md'
    proj_doc.write_text("# Project Nebula\nObjective: Nighttime autonomous driving with low compute.", encoding='utf-8')

    # 3. Explicit Apply
    res_apply = subprocess.run([
        PY, str(ROOT / 'scripts/pipeline.py'),
        'apply', '--paper', str(r), '--project', str(proj_doc)
    ], capture_output=True, text=True)
    assert res_apply.returncode == 0, res_apply.stdout + res_apply.stderr

    # 4. Project outputs exist exclusively under apply/nebula_project
    apply_dir = r / 'apply/nebula_project'
    assert apply_dir.exists()
    assert (apply_dir / 'project_reader.html').exists()
    assert (apply_dir / 'project_reader.md').exists()
    assert (apply_dir / 'research_delta.json').exists()

    # 5. Crucially, the frozen paper reader hash remains 100% byte-for-byte identical!
    new_html_sha = hashlib.sha256((reader_dir / 'paper_reader.html').read_bytes()).hexdigest()
    new_md_sha = hashlib.sha256((reader_dir / 'paper_reader.md').read_bytes()).hexdigest()
    assert new_html_sha == html_sha, "Paper Reader HTML was mutated by Apply!"
    assert new_md_sha == md_sha, "Paper Reader Markdown was mutated by Apply!"

