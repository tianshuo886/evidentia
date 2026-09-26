"""Phase B4 Semantic Reconciliation and Verifier acceptance tests.

Validates:
- Deterministic pre-clustering and Finding Cluster generation (cluster_id, members, relation)
- Verification task & result schemas (verification_task.schema.json, verification_result.schema.json)
- Evidence-localized verification without whole-paper dependence (verifier.py)
- Refusal of majority voting (evidence-grounded epistemic state)
- Automatic verification triggering on cross-lens tension/conflicts
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, run, sha_bytes, L
from validate_common import schema_validate, load_json

def test_verification_schemas():
    task_data = {
        "task_id": "TASK-VERIF-01",
        "target_id": "C01",
        "target_type": "claim",
        "statement": "Our method improves accuracy by 15% on benchmark dataset.",
        "localized_evidence": {
            "source_ids": ["F01", "T01"],
            "captions": ["Figure 1: Benchmark accuracy curves."],
            "page": 4,
            "surrounding_text": "As observed in Table 1, our method achieves 92.5% vs 77.5% baseline (+15.0%).",
            "figure_asset": "assets/figures/fig01.png"
        },
        "trigger_reason": "critical_causal_claim",
        "verification_criteria": "Direct numerical match in Table 1 or Figure 1."
    }
    errs = schema_validate(task_data, 'verification_task')
    assert not errs, f"verification_task schema errors: {errs}"

    result_data = {
        "task_id": "TASK-VERIF-01",
        "target_id": "C01",
        "status": "SUPPORTED",
        "reasoning": "Table 1 explicitly lists 92.5% vs 77.5%, matching the 15% improvement claim.",
        "grounding_evidence": ["F01", "T01"],
        "epistemic_impact": "Claim marked VERIFIED in canonical model.",
        "executor_metadata": {
            "host": "test-host",
            "model": "verifier-model"
        }
    }
    errs2 = schema_validate(result_data, 'verification_result')
    assert not errs2, f"verification_result schema errors: {errs2}"

def test_verifier_execution(tmp_path):
    import verifier
    task_file = tmp_path / 'task.json'
    out_file = tmp_path / 'result.json'
    
    # Test SUPPORTED
    task_data = {
        "task_id": "TASK-V1",
        "target_id": "TEST-01",
        "target_type": "finding",
        "statement": "The model reduces training latency significantly across all benchmarks.",
        "localized_evidence": {
            "source_ids": ["T01"],
            "captions": ["Table 1: Training latency across benchmarks."],
            "surrounding_text": "The model reduces training latency significantly across all benchmarks from 50ms to 20ms.",
            "page": 3
        },
        "trigger_reason": "high_impact_finding"
    }
    task_file.write_text(json.dumps(task_data, indent=2))
    
    res = verifier.run_verification(task_file, out_file)
    assert res['status'] == 'SUPPORTED'
    assert out_file.exists()
    assert not schema_validate(load_json(out_file), 'verification_result')

    # Test REJECTED (contradiction in localized text)
    task_data_refuted = {
        "task_id": "TASK-V2",
        "target_id": "TEST-02",
        "target_type": "finding",
        "statement": "The method succeeds in extreme noisy conditions.",
        "localized_evidence": {
            "source_ids": ["F02"],
            "captions": ["Figure 2: Noise robustness."],
            "surrounding_text": "However, the method fails to maintain accuracy and contradicts initial robustness assumptions under high noise.",
            "page": 4
        },
        "trigger_reason": "cross_lens_contradiction"
    }
    task_file.write_text(json.dumps(task_data_refuted, indent=2))
    res2 = verifier.run_verification(task_file, out_file)
    assert res2['status'] == 'REJECTED'

def test_merge_creates_finding_clusters_and_triggers_verification(tmp_path):
    r = fixture(tmp_path)
    # Inject a tension: reviewer claims failure, author claims success on same evidence F01
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

    res = run('merge_lenses.py', '--out', str(r))
    assert res.returncode == 0, res.stdout + res.stderr

    # Check lens_reconciliation.json for Finding Cluster fields
    rec = json.loads((r / 'model/lens_reconciliation.json').read_text())
    items = rec['items']
    assert len(items) >= 2
    for item in items:
        assert 'cluster_id' in item
        assert 'members' in item
        assert 'relation' in item
        assert 'canonical_statement' in item

    # Check that TENSION was recorded and verified
    tension_items = [i for i in items if i.get('status') == 'TENSION']
    assert len(tension_items) == 2
    assert all(i.get('requires_verification') is True for i in tension_items)

    # Check verification task was generated and executed
    pm = json.loads((r / 'model/paper_model.json').read_text())
    assert len(pm['lens_conflicts']) >= 1
    conf = pm['lens_conflicts'][0]
    assert conf.get('verifier_status') in ('SUPPORTED', 'PARTIAL', 'REJECTED', 'AMBIGUOUS', 'INSUFFICIENT_EVIDENCE')
