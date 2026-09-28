"""Narrative Grounding and Provenance Tests for Evidentia (Issue #8).

Verifies that:
- Final narrative assertions and narrative_units retain argument, claim, and evidence provenance.
- Narrative units in reader/paper_reader_ir.json resolve to valid argument units in model/argument_reconstruction.json.
- Narrative claims resolve to valid claims in model/paper_model.json and authentic evidence items.
- reader_audit.py enforces narrative grounding gates and fails on dangling narrative references or missing provenance.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from validate_common import load_json

def test_narrative_units_retain_provenance(tmp_path):
    r = fixture(tmp_path)
    
    # Run render_reader.py
    res = subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    ir_path = r / 'reader/paper_reader_ir.json'
    assert ir_path.exists(), "reader/paper_reader_ir.json must exist"
    ir = load_json(ir_path)

    # 1. Narrative units must exist and be non-empty
    assert 'narrative_units' in ir, "paper_reader_ir.json must contain narrative_units"
    units = ir['narrative_units']
    assert len(units) >= 3, "Must have narrative units for core sections"

    # 2. Check reference resolution against ground truth artifacts
    arg_doc = load_json(r / 'model/argument_reconstruction.json')
    valid_arg_ids = {u['id'] for u in arg_doc.get('argument_units', [])}
    
    pm = load_json(r / 'model/paper_model.json')
    valid_claim_ids = {c['id'] for c in pm.get('claims', [])}

    for u in units:
        assert 'section_id' in u
        assert 'heading_zh' in u
        assert 'narrative_text_zh' in u
        assert len(u['narrative_text_zh']) > 0

        # Argument unit references must resolve
        for arg_id in u.get('argument_unit_ids', []):
            assert arg_id in valid_arg_ids, f"Narrative unit {u['section_id']} references dangling argument unit {arg_id}"

        # Claim references must resolve
        for cid in u.get('claim_ids', []):
            assert cid in valid_claim_ids, f"Narrative unit {u['section_id']} references dangling claim {cid}"

def test_decisive_experiments_retain_argument_and_evidence_refs(tmp_path):
    r = fixture(tmp_path)
    subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], check=True)

    ir = load_json(r / 'reader/paper_reader_ir.json')
    exps = ir.get('decisive_experiments', [])
    assert len(exps) > 0

    for exp in exps:
        assert 'id' in exp
        assert 'evidence_refs' in exp
        assert 'promotion_status' in exp
        assert exp['promotion_status'] in ('narrative_core', 'narrative_support', 'uncertain', 'audit_only')
        assert exp['id'] in exp['evidence_refs']

def test_reader_audit_catches_dangling_narrative_argument_ref(tmp_path):
    r = fixture(tmp_path)
    subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], check=True)

    # Tamper with paper_reader_ir.json by injecting a dangling argument unit reference
    ir_p = r / 'reader/paper_reader_ir.json'
    ir = load_json(ir_p)
    ir['narrative_units'][0]['argument_unit_ids'].append('ARG-DANGLING-99')
    ir_p.write_text(json.dumps(ir, indent=2, ensure_ascii=False), encoding='utf-8')

    # Audit must detect dangling argument reference
    res_audit = subprocess.run([PY, str(ROOT / 'scripts/reader_audit.py'), '--out', str(r)], capture_output=True, text=True)
    assert res_audit.returncode != 0
    assert 'unknown argument unit: ARG-DANGLING-99' in res_audit.stdout

def test_reader_audit_catches_dangling_narrative_evidence_ref(tmp_path):
    r = fixture(tmp_path)
    subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], check=True)

    # Tamper with paper_reader_ir.json by injecting a phantom evidence reference
    ir_p = r / 'reader/paper_reader_ir.json'
    ir = load_json(ir_p)
    ir['narrative_units'][0]['evidence_ids'].append('F99_PHANTOM')
    ir_p.write_text(json.dumps(ir, indent=2, ensure_ascii=False), encoding='utf-8')

    # Audit must detect dangling evidence reference
    res_audit = subprocess.run([PY, str(ROOT / 'scripts/reader_audit.py'), '--out', str(r)], capture_output=True, text=True)
    assert res_audit.returncode != 0
    assert 'unknown evidence: F99_PHANTOM' in res_audit.stdout

def test_reader_audit_catches_missing_narrative_units(tmp_path):
    r = fixture(tmp_path)
    subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], check=True)

    # Tamper by wiping narrative_units
    ir_p = r / 'reader/paper_reader_ir.json'
    ir = load_json(ir_p)
    ir['narrative_units'] = []
    ir_p.write_text(json.dumps(ir, indent=2, ensure_ascii=False), encoding='utf-8')

    res_audit = subprocess.run([PY, str(ROOT / 'scripts/reader_audit.py'), '--out', str(r)], capture_output=True, text=True)
    assert res_audit.returncode != 0
    assert 'missing narrative_units' in res_audit.stdout
