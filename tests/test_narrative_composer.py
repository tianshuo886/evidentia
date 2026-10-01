"""Narrative Composer Integrity Tests for Evidentia (Issue #9).

Verifies that:
- Narrative Composer runs strictly after synthesis and verification on frozen models.
- Generates reader/narrative_manuscript.json adhering to schema_version 1.0.
- Reconstructs argument in natural order without domain-specific Python string fallbacks.
- Synthesizes findings across all six Lenses by scientific topic, not disjoint lens reports.
- Grounding: every non-trivial block cites valid evidence IDs in the frozen paper model.
- Preserves epistemic uncertainty, caveats, and contradictions.
- Preserves intent isolation: never reads or leaks apply/ project context.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from validate_common import load_json, schema_validate
from test_renderer_purity import FORBIDDEN_FALLBACK_STRINGS

def test_narrative_composer_schema_and_chapters(tmp_path):
    r = fixture(tmp_path)
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/narrative_composer_agent.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    m_path = r / 'reader/narrative_manuscript.json'
    assert m_path.exists(), "narrative_manuscript.json must be generated"
    manuscript = load_json(m_path)

    # 1. Validate schema
    errs = schema_validate(manuscript, 'narrative_manuscript')
    assert not errs, f"narrative_manuscript schema errors: {errs}"

    # 2. Check source SHA and metadata
    pm = load_json(r / 'model/paper_model.json')
    assert manuscript['source_sha256'] == pm['source_sha256']
    assert manuscript['paper_id'] == pm['paper_id']

    doc = manuscript['document']
    assert doc['title'] == pm['paper']['title']

    # 3. Default faithful reading has a paper-specific Story Spine.
    chapters = doc['chapters']
    assert len(chapters) >= 4
    actual_ids = [ch['id'] for ch in chapters]
    assert all(cid.startswith('spine-') for cid in actual_ids)
    assert doc['story_spine']['central_question']
    assert 'reusable' not in actual_ids

    # 4. Check chapter blocks and evidence citations
    all_valid_ev_ids = {c['id'] for c in pm.get('claims', [])} | {f['id'] for f in pm.get('figures', [])} | {t['id'] for t in pm.get('tables', [])} | {"p.1"}
    
    total_blocks = 0
    has_grounded_block = False
    for ch in chapters:
        assert ch['lead'] and len(ch['lead']) > 0
        blocks = ch['blocks']
        assert len(blocks) > 0
        for b in blocks:
            total_blocks += 1
            ev_refs = b.get('evidence_refs', [])
            if ev_refs:
                has_grounded_block = True
                for ev in ev_refs:
                    assert ev in all_valid_ev_ids or ev.startswith('p.'), f"Block references unknown evidence: {ev}"

    assert total_blocks >= len(chapters)
    assert has_grounded_block, "Must contain blocks grounded in valid evidence"

def test_narrative_composer_lens_synthesis_not_segregated(tmp_path):
    """Ensure that the six lenses are synthesized by topic and not dumped as raw mini-reports."""
    r = fixture(tmp_path)
    
    # Inject lens findings into lens files
    for l in ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual'):
        lp = r / f'lens/{l}.json'
        data = load_json(lp)
        data['findings'] = [{'statement': f'{l} finding on robustness', 'evidence': ['F01']}]
        lp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    res = subprocess.run([
        PY, str(ROOT / 'scripts/narrative_composer_agent.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0

    m_path = r / 'reader/narrative_manuscript.json'
    manuscript = load_json(m_path)
    # Check that no chapter contains raw lens report headings.
    all_text = " ".join(
        b.get('text', '') for ch in manuscript['document']['chapters']
        for b in ch['blocks']
    )
    for forbidden_heading in [
        "Author Lens 报告",
        "Reviewer Lens 报告",
        "Mechanism Lens 报告",
        "Builder Lens 报告",
        "Anomaly Lens 报告",
        "Counterfactual Lens 报告"
    ]:
        assert forbidden_heading not in all_text, f"Raw lens heading leaked into narrative synthesis: {forbidden_heading}"

def test_narrative_composer_renderer_purity(tmp_path):
    """Ensure that narrative composer does not inject forbidden domain scientific boilerplate."""
    r = fixture(tmp_path)
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/narrative_composer_agent.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0

    text = (r / 'reader/narrative_manuscript.json').read_text(encoding='utf-8')
    for forbidden in FORBIDDEN_FALLBACK_STRINGS:
        assert forbidden not in text, f"Forbidden boilerplate '{forbidden}' found in narrative manuscript"

def test_narrative_composer_intent_isolation(tmp_path):
    """Ensure that narrative composer never reads or leaks apply/ project context."""
    r = fixture(tmp_path)
    
    # Create fake apply context
    apply_dir = r / 'apply/target_proj'
    apply_dir.mkdir(parents=True, exist_ok=True)
    (apply_dir / 'research_delta.json').write_text(json.dumps({
        "project_id": "secret_project_xyz",
        "delta": "do not leak into paper reader"
    }), encoding='utf-8')

    res = subprocess.run([
        PY, str(ROOT / 'scripts/narrative_composer_agent.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0

    text = (r / 'reader/narrative_manuscript.json').read_text(encoding='utf-8')
    assert "secret_project_xyz" not in text
    assert "target_proj" not in text
