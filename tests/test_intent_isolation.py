"""Regression tests for Intent Router and Project Boundary Isolation (Issue #12 Faithful-reading Firewall).

Validates:
- Default evidentia run operates exclusively in PAPER_READING intent
- Workflow terminates at PAPER_COMPLETE
- Project files in workspace do NOT trigger Apply
- Zero project context files or apply/ directories created during paper reading
- Paper Reader contains zero project-specific statements
- Apply is strictly explicit-request-only
- Scenario 1: Prompt “帮我深读这篇论文。” -> faithful Reader only, no reuse/project section
- Scenario 2: Prompt “把论文中可复现的算法与实验细节整理出来。” -> paper-scoped technical extraction, no project context
- Scenario 3: Prompt “结合我的项目看看哪些内容值得借鉴。” -> explicit Project Apply, separate artifact, frozen reader unchanged
- Scenario 4: Project files exist in workspace, but prompt is only deep reading -> project files never accessed
- Scenario 5: Memory contains relevant project context, but prompt is only deep reading -> memory never influences reader
"""
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from intent_router import route_intent, get_intent_boundaries, audit_workspace_access, enforce_task_firewall

def make_test_pdf(pdf_path: Path, title: str = "Contrastive Representation Learning"):
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), f"{title}\n\nAbstract\nWe present a robust method for perception.", fontsize=12)
    doc.save(str(pdf_path))


def test_intent_router_classifications():
    """Unit test for intent router deterministic classifications."""
    assert route_intent("帮我深读这篇论文。") == "PAPER_READING"
    assert route_intent("阅读这篇论文并总结主要实验") == "PAPER_READING"
    assert route_intent("") == "PAPER_READING"
    assert route_intent(None) == "PAPER_READING"

    assert route_intent("把论文中可复现的算法与实验细节整理出来。") == "PAPER_TECHNICAL_EXTRACTION"
    assert route_intent("提取这篇论文中可以复现的技术细节") == "PAPER_TECHNICAL_EXTRACTION"
    assert route_intent("哪些方法组件可以独立实现") == "PAPER_TECHNICAL_EXTRACTION"
    assert route_intent("把算法/损失/预处理整理出来") == "PAPER_TECHNICAL_EXTRACTION"

    assert route_intent("结合我的项目看看哪些内容值得借鉴。") == "PROJECT_APPLY"
    assert route_intent("应用到我们的工作中") == "PROJECT_APPLY"
    assert route_intent("/evidentia-apply") == "PROJECT_APPLY"

    assert route_intent("查看研究记忆库中的历史关联") == "MEMORY_OPERATION"
    assert route_intent("/evidentia-memory") == "MEMORY_OPERATION"

    # Explicit override takes precedence
    assert route_intent("结合我的项目", explicit="PAPER_READING") == "PAPER_READING"


def test_intent_boundaries_definition():
    """Verify input boundaries declared for each intent."""
    reading_b = get_intent_boundaries("PAPER_READING")
    assert "source/" in reading_b["allowed_inputs"]
    assert "apply/" in reading_b["forbidden_inputs"]
    assert "project/" in reading_b["forbidden_inputs"]
    assert "memory/project/" in reading_b["forbidden_inputs"]

    tech_b = get_intent_boundaries("PAPER_TECHNICAL_EXTRACTION")
    assert "apply/" in tech_b["forbidden_inputs"]
    assert "project/" in tech_b["forbidden_inputs"]

    apply_b = get_intent_boundaries("PROJECT_APPLY")
    assert "apply/" in apply_b["allowed_inputs"]


def test_scenario_1_faithful_reading_prompt(tmp_path):
    """Scenario 1: Prompt “帮我深读这篇论文。” -> faithful Reader only. No reuse/project section."""
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper1.pdf'
    make_test_pdf(pdf_path, "Faithful Reading Benchmark Paper")

    # Run with prompt "帮我深读这篇论文。"
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir),
        '--prompt', '帮我深读这篇论文。', '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    rs = json.loads((out_dir / 'run_state.json').read_text(encoding='utf-8'))
    assert rs['intent'] == 'PAPER_READING'
    assert 'apply/' in rs['forbidden_inputs']

    # Reader must not have reuse / transfer / technical extraction section
    html_text = (out_dir / 'reader/paper_reader.html').read_text(encoding='utf-8')
    md_text = (out_dir / 'reader/paper_reader.md').read_text(encoding='utf-8')
    for term in ("可复用技术内容", "迁移复用建议", "迁移到你的项目", "建议用于项目", "项目适配"):
        assert term not in html_text
        assert term not in md_text

    # No apply/ directory or standalone technical extraction
    assert not (out_dir / 'apply').exists()
    assert not (out_dir / 'reader/technical_extraction.md').exists()
    assert not (out_dir / 'reader/technical_extraction.html').exists()


def test_scenario_2_technical_extraction_prompt(tmp_path):
    """Scenario 2: Prompt “把论文中可复现的算法与实验细节整理出来。” -> paper-scoped technical extraction."""
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper2.pdf'
    make_test_pdf(pdf_path, "Technical Extraction Benchmark Paper")

    # Run with prompt "把论文中可复现的算法与实验细节整理出来。"
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir),
        '--prompt', '把论文中可复现的算法与实验细节整理出来。', '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    rs = json.loads((out_dir / 'run_state.json').read_text(encoding='utf-8'))
    assert rs['intent'] == 'PAPER_TECHNICAL_EXTRACTION'

    # Technical extraction chapter MUST exist
    # Technical extraction is an explicit secondary artifact so the primary
    # Reader remains a paper narrative rather than a schema dump.
    tech_html = (out_dir / 'reader/technical_extraction.html').read_text(encoding='utf-8')
    assert "论文技术细节提取" in tech_html

    # Standalone technical extraction artifacts MUST exist
    tech_md = out_dir / 'reader/technical_extraction.md'
    tech_html_path = out_dir / 'reader/technical_extraction.html'
    assert tech_md.exists()
    assert tech_html_path.exists()
    assert "论文技术细节提取" in tech_md.read_text(encoding='utf-8')

    # MUST remain paper-scoped: NO apply directory, NO project transfer recommendations
    assert not (out_dir / 'apply').exists()
    tech_surface = tech_html_path.read_text(encoding='utf-8')
    assert "迁移到你的项目" not in tech_surface
    assert "建议用于项目" not in tech_surface


def test_scenario_3_project_apply_prompt(tmp_path):
    """Scenario 3: Prompt “结合我的项目看看哪些内容值得借鉴。” -> explicit Apply, frozen reader unchanged."""
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper3.pdf'
    make_test_pdf(pdf_path, "Apply Benchmark Paper")

    # 1. Complete paper read first (default)
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    paper_html = out_dir / 'reader/paper_reader.html'
    paper_md = out_dir / 'reader/paper_reader.md'
    html_sha = hashlib.sha256(paper_html.read_bytes()).hexdigest()
    md_sha = hashlib.sha256(paper_md.read_bytes()).hexdigest()

    # 2. Check prompt routing for project apply
    assert route_intent("结合我的项目看看哪些内容值得借鉴。") == "PROJECT_APPLY"

    # 3. Create project document
    proj_doc = tmp_path / 'orion.md'
    proj_doc.write_text("# Project Orion\nNeed: robust feature extractor under night conditions.", encoding='utf-8')

    # 4. Run Apply
    res_apply = subprocess.run([
        PY, str(ROOT / 'scripts/pipeline.py'),
        'apply', '--paper', str(out_dir), '--project', str(proj_doc)
    ], capture_output=True, text=True)
    assert res_apply.returncode == 0, res_apply.stdout + res_apply.stderr

    # 5. Project outputs exist exclusively under apply/orion/
    apply_orion = out_dir / 'apply/orion'
    assert apply_orion.exists()
    assert (apply_orion / 'research_delta.json').exists()
    assert (apply_orion / 'project_reader.html').exists()
    assert (apply_orion / 'project_reader.md').exists()

    # 6. Frozen paper reader remains 100% byte-for-byte immutable!
    assert hashlib.sha256(paper_html.read_bytes()).hexdigest() == html_sha
    assert hashlib.sha256(paper_md.read_bytes()).hexdigest() == md_sha
    assert 'orion' not in paper_html.read_text(encoding='utf-8').lower()


def test_scenario_4_project_files_in_workspace_never_accessed(tmp_path):
    """Scenario 4: Project files exist in workspace, but prompt is only deep reading -> project files never accessed."""
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper4.pdf'
    make_test_pdf(pdf_path, "Perception in Adverse Weather")

    # Place multiple project documents and code alongside the workspace
    project_doc = tmp_path / 'top_secret_project_polaris.md'
    project_doc.write_text("""# Project Polaris
Confidential proprietary architecture.
Target metric: 95% precision on edge TPU.
""", encoding='utf-8')

    project_code = tmp_path / 'polaris_model.py'
    project_code.write_text("""class PolarisArchitecture: pass\n""", encoding='utf-8')

    # Deep reading run
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir),
        '--prompt', '帮我深读这篇论文。', '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    # Check allowed_inputs in run_state
    rs = json.loads((out_dir / 'run_state.json').read_text(encoding='utf-8'))
    for item in rs['allowed_inputs']:
        assert 'polaris' not in str(item).lower()
        assert 'project' not in str(item).lower()

    # Verify Paper Reader contains ZERO mention of Project Polaris
    html_text = (out_dir / 'reader/paper_reader.html').read_text(encoding='utf-8')
    assert 'polaris' not in html_text.lower()
    assert 'edge tpu' not in html_text.lower()
    assert not (out_dir / 'apply').exists()


def test_scenario_5_memory_contains_project_context_never_influences_reader(tmp_path):
    """Scenario 5: Memory contains relevant project context, but prompt is only deep reading -> memory never influences reader."""
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper5.pdf'
    make_test_pdf(pdf_path, "LiDAR Feature Fusion")

    mem_root = tmp_path / 'research_memory'
    from memory_manager import get_memory_root, record_outcome
    m_root = get_memory_root(mem_root)

    # Pre-populate memory with project-specific outcome
    record_outcome(
        project_id="ProjectHelios",
        experiment_id="EXP-HELIOS-01",
        verdict="FAILURE",
        findings="Proprietary ProjectHelios sensor calibration failed at 50Hz.",
        conditions="Outdoor rain test",
        custom_root=m_root
    )

    # Deep reading run with prompt
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir),
        '--prompt', '帮我深读这篇论文。', '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    # Paper Reader must not contain any reference to ProjectHelios
    html_text = (out_dir / 'reader/paper_reader.html').read_text(encoding='utf-8')
    md_text = (out_dir / 'reader/paper_reader.md').read_text(encoding='utf-8')
    assert 'helios' not in html_text.lower()
    assert 'helios' not in md_text.lower()
    assert '50hz' not in html_text.lower()
    assert not (out_dir / 'apply').exists()


def test_paper_reading_intent_isolation(tmp_path):
    """Legacy test ensuring backward compatibility of default paper read isolation."""
    out_dir = tmp_path / 'paper_workspace'
    project_doc = tmp_path / 'my_secret_project.md'
    project_doc.write_text("""# Project DeepSight
Objective: Autonomous driving perception in dense fog.
Existing bottleneck: 30% mAP drop under foggy sensor conditions.
""", encoding='utf-8')
    
    pdf_path = tmp_path / 'paper.pdf'
    make_test_pdf(pdf_path, "Contrastive Representation Learning for Foggy Scenarios")
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    
    rs_p = out_dir / 'run_state.json'
    assert rs_p.exists()
    rs = json.loads(rs_p.read_text(encoding='utf-8'))
    assert rs.get('intent') == 'PAPER_READING'
    assert rs.get('phase') in ('COMPLETE', 'PAPER_COMPLETE')
    
    apply_dir = out_dir / 'apply'
    assert not apply_dir.exists()
    
    html_text = (out_dir / 'reader/paper_reader.html').read_text(encoding='utf-8')
    assert 'DeepSight' not in html_text
    assert 'PROJECT RESEARCH DELTA' not in html_text


def test_apply_requires_explicit_invocation(tmp_path):
    """Legacy test ensuring Apply requires explicit invocation and preserves Reader."""
    out_dir = tmp_path / 'paper_workspace'
    pdf_path = tmp_path / 'paper.pdf'
    make_test_pdf(pdf_path, "Foundational Visual Representation Learning")
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--fixture'
    ], capture_output=True, text=True)
    assert res.returncode == 0
    
    proj_doc = tmp_path / 'apollo.md'
    proj_doc.write_text("# Project Apollo\nNeed: robust feature extractor under night conditions.", encoding='utf-8')
    
    res_apply = subprocess.run([
        PY, str(ROOT / 'scripts/pipeline.py'),
        'apply', '--paper', str(out_dir), '--project', str(proj_doc)
    ], capture_output=True, text=True)
    assert res_apply.returncode == 0, res_apply.stdout + res_apply.stderr
    
    apply_proj = out_dir / 'apply/apollo'
    assert apply_proj.exists()
    assert (apply_proj / 'research_delta.json').exists()
    assert (apply_proj / 'project_reader.html').exists()
    assert (apply_proj / 'project_reader.md').exists()
    
    paper_html = (out_dir / 'reader/paper_reader.html').read_text(encoding='utf-8')
    assert 'apollo' not in paper_html.lower()
