"""Tests for First-Class Argument Reconstruction (Issue #8).

Validates:
- Schema validation against schemas/argument_reconstruction.schema.json
- Persisted artifact at model/argument_reconstruction.json
- Separation of Author Argument vs Evidentia-Assessed Argument
- Typed scientific reasoning relations (motivates, tests, supports, qualifies, etc.)
- Typed semantic roles (problem, hypothesis, method_rationale, result, etc.)
- Explicit evidence promotion (narrative_core, narrative_support, audit_only, uncertain)
"""
import json, pytest, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from validate_common import schema_validate, load_json
from build_argument_reconstruction import build_argument_reconstruction, build_argument_topology, classify_evidence_promotion

def test_argument_reconstruction_schema_and_artifact_generation(tmp_path):
    r = fixture(tmp_path)
    
    # Run argument reconstruction builder
    recon = build_argument_reconstruction(r)
    
    # 1. Verify file exists
    arg_p = r / 'model/argument_reconstruction.json'
    assert arg_p.exists(), "model/argument_reconstruction.json was not created"
    
    # 2. Schema validation
    errs = schema_validate(recon, 'argument_reconstruction')
    assert not errs, f"argument_reconstruction schema errors: {errs}"
    
    # 3. Check core properties
    assert recon['central_question']
    assert recon['central_thesis']
    assert len(recon['argument_units']) >= 3
    assert len(recon['argument_relations']) >= 2

def test_author_argument_vs_assessed_argument_separation(tmp_path):
    r = fixture(tmp_path)
    recon = build_argument_reconstruction(r)
    
    # Verify both sections exist and are distinct
    assert 'author_argument' in recon, "Missing author_argument section"
    assert 'assessed_argument' in recon, "Missing assessed_argument section"
    
    author_arg = recon['author_argument']
    assessed_arg = recon['assessed_argument']
    
    assert author_arg['thesis']
    assert len(author_arg['progression']) > 0
    assert assessed_arg['justified_thesis']
    assert isinstance(assessed_arg['supported_units'], list)
    
    # Check that relations explicitly distinguish origins
    origins = {rel['origin'] for rel in recon['argument_relations']}
    assert 'author' in origins, "Relations must include author-originated reasoning edges"
    assert 'evidentia_assessment' in origins, "Relations must include evidentia_assessment-originated edges"
    
    # Verify author edges use appropriate relations
    author_rels = [rel['relation_type'] for rel in recon['argument_relations'] if rel['origin'] == 'author']
    assert any(r in ('motivates', 'tests', 'supports', 'addresses') for r in author_rels)
    
    # Verify assessed edges use assessment relations
    assessed_rels = [rel['relation_type'] for rel in recon['argument_relations'] if rel['origin'] == 'evidentia_assessment']
    assert any(r in ('supports', 'qualifies', 'weakens', 'contradicts', 'leaves_open') for r in assessed_rels)

def test_argument_topology_and_semantic_roles(tmp_path):
    r = fixture(tmp_path)
    recon = build_argument_reconstruction(r)
    
    units = recon['argument_units']
    roles = {u['semantic_role'] for u in units}
    
    # Must contain fundamental scientific reasoning roles
    assert 'problem' in roles, "Must have a problem unit"
    assert any(r in ('hypothesis', 'method_rationale', 'premise') for r in roles), "Must have hypothesis/method rationale"
    assert any(r in ('result', 'observation') for r in roles), "Must have result/observation"
    assert 'conclusion' in roles, "Must have conclusion unit"
    
    # All units must have explanatory narrative in Chinese
    for u in units:
        assert len(u['proposition']) > 0
        assert len(u['explanatory_narrative']) > 0
        assert u['id'].startswith('ARG-')

def test_evidence_promotion_structure(tmp_path):
    r = fixture(tmp_path)
    pm = load_json(r / 'model/paper_model.json')
    
    # Add multiple figures: some core, some secondary, some with caveats
    pm['figures'] = [
        {"id": "F01", "paper_label": "Fig. 1", "role": "critical", "depth": "deep", "supports_claims": ["C01"]},
        {"id": "F02", "paper_label": "Fig. 2", "role": "supporting", "depth": "shallow", "supports_claims": ["C01"]},
        {"id": "F03", "paper_label": "Fig. 3", "role": "catalog", "depth": "unassigned", "supports_claims": []}
    ]
    pm['claims'] = [
        {"id": "C01", "statement": "Core Claim", "evidence": ["F01"], "epistemic": "SUPPORTED"},
        {"id": "C02", "statement": "Uncertain Claim", "evidence": ["F04"], "epistemic": "AMBIGUOUS"}
    ]
    
    promo = classify_evidence_promotion(pm)
    
    assert "narrative_core" in promo
    assert "narrative_support" in promo
    assert "audit_only" in promo
    assert "uncertain" in promo
    assert "evidence_roles" in promo
    
    # F01 is linked to core claim -> narrative_core
    assert "F01" in promo["narrative_core"]
    # F04 is linked to ambiguous claim -> uncertain
    assert "F04" in promo["uncertain"]
    # F03 has no claim link -> audit_only
    assert "F03" in promo["audit_only"]
