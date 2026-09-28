"""Regression tests for Intent Router and Project Boundary Isolation (P0 Workstream D).

Validates:
- Default evidentia run operates exclusively in PAPER_READING intent
- Workflow terminates at PAPER_COMPLETE
- Project files in workspace do NOT trigger Apply
- Zero project context files or apply/ directories created during paper reading
- Paper Reader contains zero project-specific statements
- Apply is strictly explicit-request-only
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable

def test_paper_reading_intent_isolation(tmp_path):
    out_dir = tmp_path / 'paper_workspace'
    
    # Place a project document right next to the workspace
    project_doc = tmp_path / 'my_secret_project.md'
    project_doc.write_text("""# Project DeepSight
Objective: Autonomous driving perception in dense fog.
Existing bottleneck: 30% mAP drop under foggy sensor conditions.
""", encoding='utf-8')
    
    # Create synthetic paper
    pdf_path = tmp_path / 'paper.pdf'
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Contrastive Representation Learning for Foggy Scenarios\n\nAbstract\nWe present a robust method.", fontsize=12)
    doc.save(str(pdf_path))
    
    # Run evidentia default workflow
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--fixture'
    ], capture_output=True, text=True)
    
    assert res.returncode == 0, res.stdout + res.stderr
    
    # 1. State machine validation
    rs_p = out_dir / 'run_state.json'
    assert rs_p.exists()
    rs = json.loads(rs_p.read_text(encoding='utf-8'))
    assert rs.get('intent') == 'PAPER_READING'
    assert rs.get('phase') in ('COMPLETE', 'PAPER_COMPLETE')
    
    # 2. Strict artifact isolation: NO apply directory or research delta created
    apply_dir = out_dir / 'apply'
    assert not apply_dir.exists(), f"Isolation violated: apply directory created during default paper read: {list(apply_dir.glob('*'))}"
    
    # 3. Paper reader purity
    html_p = out_dir / 'reader/paper_reader.html'
    assert html_p.exists()
    html_text = html_p.read_text(encoding='utf-8')
    assert 'DeepSight' not in html_text
    assert 'PROJECT RESEARCH DELTA' not in html_text
    
    md_p = out_dir / 'reader/paper_reader.md'
    assert md_p.exists()
    md_text = md_p.read_text(encoding='utf-8')
    assert 'DeepSight' not in md_text

def test_apply_requires_explicit_invocation(tmp_path):
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper.pdf'
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Foundational Visual Representation Learning\n", fontsize=12)
    doc.save(str(pdf_path))
    
    # Complete paper read first
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0
    
    proj_doc = tmp_path / 'apollo.md'
    proj_doc.write_text("# Project Apollo\nNeed: robust feature extractor under night conditions.", encoding='utf-8')
    
    # Explicit apply command
    res_apply = subprocess.run([
        PY, str(ROOT / 'scripts/pipeline.py'),
        'apply', '--paper', str(out_dir), '--project', str(proj_doc)
    ], capture_output=True, text=True)
    assert res_apply.returncode == 0, res_apply.stdout + res_apply.stderr
    
    # Now apply exists in separate subfolder
    apply_proj = out_dir / 'apply/apollo'
    assert apply_proj.exists()
    assert (apply_proj / 'research_delta.json').exists()
    assert (apply_proj / 'project_reader.html').exists()
    assert (apply_proj / 'project_reader.md').exists()
    
    # Crucially, the Paper Reader remains untouched and immutable!
    paper_html = (out_dir / 'reader/paper_reader.html').read_text(encoding='utf-8')
    assert 'apollo' not in paper_html.lower()
