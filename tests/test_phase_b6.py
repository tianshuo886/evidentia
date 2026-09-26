"""Phase B6 Evidence Atlas and Apply acceptance tests.

Validates:
- Claim-centric Evidence Atlas HTML rendering with O/I/A separation
- Bidirectional anchor navigation (Claim <-> Evidence)
- Reader audit v2 (detects broken anchors, missing O/I/A, missing conflicts)
- Automated Apply Agent execution generating Transfer Unit v2 and Research Delta
- Unfrozen paper refusal during Apply
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, run, sha_bytes, L
from validate_common import schema_validate, load_json

def test_reader_rendering_and_bidirectional_navigation(tmp_path):
    r = fixture(tmp_path)
    res_render = run('render_reader.py', '--out', str(r))
    assert res_render.returncode == 0, res_render.stdout + res_render.stderr
    
    html_text = (r / 'reader/reader.html').read_text(encoding='utf-8')
    assert 'Claim-Centric Evidence Atlas' in html_text
    assert 'Observation' in html_text
    assert 'Author Interpretation' in html_text
    assert 'Reader Assessment' in html_text

    # Check bidirectional navigation anchors
    assert '<a href="#F01"' in html_text
    assert '<a href="#C01"' in html_text
    assert 'Supports Claims:' in html_text

    # Run reader audit v2
    res_audit = run('reader_audit.py', '--out', str(r))
    assert res_audit.returncode == 0, res_audit.stdout + res_audit.stderr
    assert 'reader_sha256' in res_audit.stdout

def test_reader_audit_detects_broken_anchor(tmp_path):
    r = fixture(tmp_path)
    run('render_reader.py', '--out', str(r))
    
    # Tamper with reader.html to introduce broken anchor link
    rf = r / 'reader/reader.html'
    content = rf.read_text(encoding='utf-8')
    content = content.replace('<a href="#F01"', '<a href="#BROKEN99"')
    rf.write_text(content, encoding='utf-8')

    res_audit = run('reader_audit.py', '--out', str(r))
    assert res_audit.returncode != 0
    assert 'broken anchor links' in res_audit.stdout

def test_apply_agent_execution_and_transfer_unit_v2(tmp_path):
    r = fixture(tmp_path)
    # Freeze the paper first
    res_freeze = run('freeze_check.py', '--out', str(r))
    assert res_freeze.returncode == 0
    
    proj_doc = tmp_path / 'project.md'
    proj_doc.write_text("""# Project Apollo
Goal: Enhance visual feature extraction under low lighting conditions.
Challenge: General benchmark accuracy drops by 12% in night driving scenarios.
Need: A robust multi-scale attention module with efficient memory footprint.
""", encoding='utf-8')
    
    # Run Apply Agent
    res_apply = run('apply_agent.py', '--paper', str(r), '--project', str(proj_doc))
    assert res_apply.returncode == 0, res_apply.stdout + res_apply.stderr
    
    delta_p = r / 'apply/project/research_delta.json'
    assert delta_p.exists()
    
    delta = json.loads(delta_p.read_text(encoding='utf-8'))
    assert not schema_validate(delta, 'research_delta')
    assert len(delta['transfer_units']) >= 1
    
    tu = delta['transfer_units'][0]
    assert tu['verdict'] in ('DIRECT', 'ADAPT', 'INSPIRATION_ONLY', 'REJECT')
    assert 'source_component' in tu
    assert 'compute_constraints' in tu
    assert 'known_risks' in tu
    assert len(tu['source']) >= 1

def test_apply_refuses_unfrozen_paper(tmp_path):
    r = fixture(tmp_path)
    # Do NOT run freeze_check, manifest.json does not exist
    proj_doc = tmp_path / 'proj.md'
    proj_doc.write_text("Goal: testing unfrozen refusal")
    
    res = run('apply_agent.py', '--paper', str(r), '--project', str(proj_doc))
    assert res.returncode != 0
    assert 'REFUSED' in (res.stdout + res.stderr)
