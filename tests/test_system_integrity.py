"""System integrity and comprehensive end-to-end integration tests for Evidentia.

Validates:
1. Real PDF-to-Frozen-Reader autonomous end-to-end execution (Standard Mode)
2. Real Multi-Model Ensemble Mode end-to-end execution
3. Post-freeze mutation refusal (immutable freeze cannot be rewritten)
4. Missing artifact refusal during resume
5. Conflict verification with strict paper_model.schema.json validation
6. Apply end-to-end validation with validate_delta.py
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'evals/runners'))
from test_gates import fixture, run, sha_bytes, L
from validate_common import schema_validate, load_json
from eval_runner import create_synthetic_pdf

def test_real_pdf_to_frozen_reader_end_to_end(tmp_path):
    pdf_path = tmp_path / 'paper.pdf'
    out_dir = tmp_path / 'out_standard'
    
    paper_spec = {
        "title": "Sparse Attention Mechanisms for Representation Learning",
        "sections": ["1. Introduction", "2. Methodology", "3. Experiments"],
        "figures": [{"id": "F01", "paper_label": "Fig. 1", "caption": "Attention architecture"}],
        "tables": [{"id": "T01", "paper_label": "Table 1", "caption": "Accuracy comparisons"}]
    }
    create_synthetic_pdf(paper_spec, pdf_path)
    
    # Run evidentia master workflow
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--mode', 'standard'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Evidentia run COMPLETE" in res.stdout

    # Verify frozen manifest and reader
    manifest = json.loads((out_dir / 'model/manifest.json').read_text())
    assert manifest['status'] == 'FROZEN'
    assert (out_dir / 'reader/reader.html').exists()
    
    res_audit = subprocess.run([
        PY, str(ROOT / 'scripts/reader_audit.py'),
        '--out', str(out_dir)
    ], capture_output=True, text=True)
    assert res_audit.returncode == 0, res_audit.stdout + res_audit.stderr

def test_real_ensemble_mode_end_to_end(tmp_path):
    pdf_path = tmp_path / 'paper_ens.pdf'
    out_dir = tmp_path / 'out_ensemble'
    
    paper_spec = {
        "title": "Ensemble Diversity in Evidentia Research Systems",
        "sections": ["1. Introduction", "2. Analysis", "3. Results"],
        "figures": [{"id": "F01", "paper_label": "Fig. 1", "caption": "Multi-model variance"}],
        "tables": []
    }
    create_synthetic_pdf(paper_spec, pdf_path)
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/evidentia.py'),
        'run', '--pdf', str(pdf_path), '--out', str(out_dir), '--mode', 'ensemble'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Evidentia run COMPLETE" in res.stdout
    
    # Verify lens_runs and within-lens reconciliation
    assert (out_dir / 'lens_runs/reviewer/run-001.json').exists()
    assert (out_dir / 'lens_runs/reviewer/run-002.json').exists()
    
    reviewer_doc = json.loads((out_dir / 'lens/reviewer.json').read_text())
    assert reviewer_doc['executor']['mode'] == 'ensemble'
    assert len(reviewer_doc['executor']['models']) >= 2
    for f in reviewer_doc['findings']:
        assert 'within_lens_status' in f

def test_post_freeze_mutation_refuses_rewriting(tmp_path):
    r = fixture(tmp_path)
    res_freeze = run('freeze_check.py', '--out', str(r))
    assert res_freeze.returncode == 0
    
    # Mutate paper_model.json after freeze
    pm_p = r / 'model/paper_model.json'
    pm = json.loads(pm_p.read_text())
    pm['claims'][0]['statement'] = "Mutated post-freeze claim"
    pm_p.write_text(json.dumps(pm))
    
    # Freeze check must fail closed and refuse to rewrite manifest
    res_tamper = run('freeze_check.py', '--out', str(r))
    assert res_tamper.returncode != 0
    assert 'REFUSED' in (res_tamper.stdout + res_tamper.stderr)
    assert 'Manifest is already FROZEN and cannot be rewritten' in (res_tamper.stdout + res_tamper.stderr)

def test_resume_refuses_missing_previously_hashed_artifact(tmp_path):
    r = fixture(tmp_path)
    rs_path = r / 'run_state.json'
    sm_sha = sha_bytes((r / 'model/source_map.json').read_bytes())
    fi_sha = sha_bytes((r / 'model/figure_inventory.json').read_bytes())
    
    state = {
        'schema_version': '1.0',
        'run_id': 'r-test',
        'mode': 'evidentia',
        'phase': 'SOURCE_RECONSTRUCTION',
        'source_sha256': sha_bytes((r / 'source/paper.pdf').read_bytes()),
        'base_sha256': None,
        'allowed_inputs': ['working/paper.pdf'],
        'artifacts': {},
        'completed_phases': ['INGEST'],
        'artifact_hashes': {
            'SOURCE_RECONSTRUCTION': {
                'model/source_map.json': sm_sha,
                'model/figure_inventory.json': fi_sha
            }
        },
        'history': []
    }
    rs_path.write_text(json.dumps(state, indent=2))
    
    # Delete source_map.json
    (r / 'model/source_map.json').unlink()
    
    res = run('phase.py', '--out', str(r), '--complete', 'SOURCE_LOCK')
    assert res.returncode != 0
    assert 'previously completed artifact bundle missing' in (res.stdout + res.stderr)

def test_conflict_verifies_and_validates_paper_model_schema(tmp_path):
    r = fixture(tmp_path)
    # Inject conflict into lenses
    p_rev = r / 'lens/reviewer.json'
    d_rev = json.loads(p_rev.read_text())
    d_rev['findings'].append({
        'id': 'L-reviewer-01',
        'statement': 'Method exhibits severe instability under perturbation on F01',
        'evidence': ['F01'],
        'epistemic': 'SUPPORTED',
        'novel_vs_base': True
    })
    p_rev.write_text(json.dumps(d_rev, indent=2))

    p_auth = r / 'lens/author.json'
    d_auth = json.loads(p_auth.read_text())
    d_auth['findings'].append({
        'id': 'L-author-01',
        'statement': 'Method maintains stable performance across perturbations on F01',
        'evidence': ['F01'],
        'epistemic': 'SUPPORTED',
        'novel_vs_base': True
    })
    p_auth.write_text(json.dumps(d_auth, indent=2))

    res_merge = run('merge_lenses.py', '--out', str(r))
    assert res_merge.returncode == 0, res_merge.stdout + res_merge.stderr

    # Validate paper_model.json schema with real conflicts
    pm = json.loads((r / 'model/paper_model.json').read_text())
    errs = schema_validate(pm, 'paper_model')
    assert not errs, f"paper_model schema errors with conflicts: {errs}"
    assert len(pm['lens_conflicts']) >= 1
    assert pm['lens_conflicts'][0]['verifier_status'] is not None

def test_apply_end_to_end_passes_validate_delta(tmp_path):
    r = fixture(tmp_path)
    res_freeze = run('freeze_check.py', '--out', str(r))
    assert res_freeze.returncode == 0
    
    proj_doc = tmp_path / 'project.md'
    proj_doc.write_text("""# Project Apollo
Goal: Enhance visual feature extraction under low lighting conditions.
Need: A robust multi-scale attention module with efficient memory footprint.
""", encoding='utf-8')
    
    res_apply = run('apply_agent.py', '--paper', str(r), '--project', str(proj_doc))
    assert res_apply.returncode == 0, res_apply.stdout + res_apply.stderr
    
    # Run validate_delta.py
    delta_p = r / 'apply/project/research_delta.json'
    res_val = run('validate_delta.py', '--paper', str(r), '--delta', str(delta_p))
    assert res_val.returncode == 0, res_val.stdout + res_val.stderr
    assert '"status": "OK"' in res_val.stdout
