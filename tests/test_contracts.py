import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_init_run_is_source_only():
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);pdf=r/'p.pdf';pdf.write_bytes(b'%PDF fake')
  p=subprocess.run([sys.executable,str(ROOT/'scripts/init_run.py'),'--pdf',str(pdf),'--out',str(r/'out')],capture_output=True,text=True)
  assert p.returncode==0
  state=json.loads((r/'out/run_state.json').read_text());assert state['mode']=='evidentia';assert 'project' not in json.dumps(state).lower()
def test_lens_runner_requires_base_model():
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);(r/'source').mkdir();(r/'source/paper.pdf').write_bytes(b'x');(r/'model').mkdir()
  p=subprocess.run([sys.executable,str(ROOT/'scripts/lens_runner.py'),'--out',str(r)],capture_output=True,text=True)
  assert p.returncode!=0

def test_skill_frontmatter_valid():
    skill_path = ROOT / 'SKILL.md'
    text = skill_path.read_text(encoding='utf-8')
    assert text.startswith('---\n')
    end_idx = text.find('\n---\n', 4)
    assert end_idx != -1
    fm_raw = text[4:end_idx]
    try:
        import yaml
        fm = yaml.safe_load(fm_raw)
    except ImportError:
        # Fallback minimal parser
        fm = {}
        for line in fm_raw.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip()
    assert fm.get('name') == 'evidentia'
    assert 'description' in fm and len(fm['description']) > 10
    assert 'license' in fm
    assert 'compatibility' in fm
    # argument-hint must NOT be top-level
    assert 'argument-hint' not in fm
    # metadata must contain version and argument-hint
    metadata = fm.get('metadata')
    assert isinstance(metadata, dict)
    assert 'version' in metadata
    assert 'argument-hint' in metadata

def test_capability_matrix_audit_clean():
    matrix_file = ROOT / 'capability_matrix.json'
    assert matrix_file.exists()
    matrix = json.loads(matrix_file.read_text(encoding='utf-8'))
    assert matrix.get('schema_version') in ('1.0', '2.0')
    valid_statuses = {"IMPLEMENTED", "PARTIAL", "DECLARED_ONLY", "MISSING", "DEPRECATED"}
    ids = set()
    for cap in matrix.get('capabilities', []):
        assert cap['id'] not in ids
        ids.add(cap['id'])
        assert cap['status'] in valid_statuses
    required_ids = [
        "source_reconstruction", "source_lock", "open_reading_base", "baseline_lock",
        "standard_agent_execution", "independent_lens_execution",
        "deterministic_pre_reconciliation", "semantic_cross_lens_reconciliation",
        "evidence_verifier", "canonical_paper_model", "evidence_graph", "freeze_integrity",
        "reader_evidence_atlas", "reader_visual_qa", "project_apply_execution", "research_delta",
        "ensemble_execution", "within_lens_reconciliation", "adaptive_model_escalation",
        "frozen_research_memory", "evaluation_framework", "ci_release_engineering"
    ]
    for req in required_ids:
        assert req in ids, f"Missing required capability: {req}"

def test_no_hardcoded_scientific_pseudo_agent_templates_in_production_scripts():
    """Section 10 regression test: production scripts must not contain pre-written scientific conclusions."""
    import re
    scripts_dir = ROOT / 'scripts'
    forbidden_patterns = [
        r'LENS_FINDINGS_TEMPLATES',
        r'specialized CUDA kernel',
        r'improved gradient flow in the residual',
        r'convergence rate by 20%',
        r'\+5% accuracy on target'
    ]
    for py_file in scripts_dir.glob('*.py'):
        content = py_file.read_text(encoding='utf-8')
        for pat in forbidden_patterns:
            assert not re.search(pat, content, re.I), f"Forbidden pseudo-agent pattern '{pat}' found in {py_file.name}"


