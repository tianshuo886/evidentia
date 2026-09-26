"""Phase B5 Multi-Model Ensemble acceptance tests.

Validates:
- Execution configuration schema (standard vs ensemble, strategy)
- Multi-model data model (lens_runs/ -> within_lens_reconciliation -> canonical lens)
- Within-lens status (MODEL_SINGLETON, CROSS_MODEL_CONVERGENCE, MODEL_CONFLICT)
- Adaptive model escalation trigger rules
- Pi adapter host isolation
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'adapters/pi'))
from validate_common import schema_validate, load_json

def test_execution_config_schema():
    cfg_standard = {
        "schema_version": "1.0",
        "execution": {
            "mode": "standard",
            "default_model": "claude-3-7-sonnet"
        }
    }
    assert not schema_validate(cfg_standard, 'execution_config')

    cfg_ensemble = {
        "schema_version": "1.0",
        "execution": {
            "mode": "ensemble"
        },
        "ensemble": {
            "strategy": "adaptive",
            "models": ["gemini-2.5-pro", "claude-3-7-sonnet", "gpt-4o"],
            "max_escalations": 3,
            "escalation_triggers": ["critical_uncertainty", "unexpected_anomaly"]
        }
    }
    assert not schema_validate(cfg_ensemble, 'execution_config')

def test_within_lens_reconciliation(tmp_path):
    from within_lens_reconciliation import reconcile_lens_runs
    
    # Run 1 from Model A
    run_1 = {
        "run_id": "run-001",
        "executor": {"model": "model-a"},
        "findings": [
            {
                "id": "L-reviewer-01",
                "statement": "Missing baseline comparison against SOTA on Table 2",
                "evidence": ["T02"],
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            },
            {
                "id": "L-reviewer-02",
                "statement": "Hyperparameter sensitivity not evaluated",
                "evidence": ["F03"],
                "epistemic": "PARTIAL",
                "novel_vs_base": True
            }
        ]
    }
    
    # Run 2 from Model B
    run_2 = {
        "run_id": "run-002",
        "executor": {"model": "model-b"},
        "findings": [
            # Same finding as Run 1 -> should converge
            {
                "id": "L-reviewer-01-b",
                "statement": "Missing baseline comparison against SOTA on Table 2",
                "evidence": ["T02"],
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            },
            # Contradicting finding on F03 -> should flag conflict
            {
                "id": "L-reviewer-03-b",
                "statement": "Hyperparameters are thoroughly justified and robust",
                "evidence": ["F03"],
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            },
            # Unique finding only in Model B -> singleton
            {
                "id": "L-reviewer-04-b",
                "statement": "Learning rate schedule causes early saturation",
                "evidence": ["F01"],
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            }
        ]
    }
    
    merged = reconcile_lens_runs([run_1, run_2])
    
    # Check convergence on first item
    conv_items = [m for m in merged if m['within_lens_status'] == 'CROSS_MODEL_CONVERGENCE']
    assert len(conv_items) == 1
    assert set(conv_items[0]['models']) == {"model-a", "model-b"}

    # Check singleton
    singleton_items = [m for m in merged if m['within_lens_status'] == 'MODEL_SINGLETON']
    assert len(singleton_items) == 1
    assert singleton_items[0]['models'] == ["model-b"]

    # Check conflict
    conflict_items = [m for m in merged if m['within_lens_status'] == 'MODEL_CONFLICT']
    assert len(conflict_items) >= 2

def test_adaptive_escalation_rules(tmp_path):
    from adaptive_escalation import evaluate_escalation
    
    lens_dir = tmp_path / 'lens'
    lens_dir.mkdir()
    
    # Anomaly lens with novel finding -> should trigger ESCALATE_SECOND_MODEL
    (lens_dir / 'anomaly.json').write_text(json.dumps({
        "findings": [
            {
                "id": "L-anomaly-01",
                "statement": "Severe performance degradation on minority group in Fig. 4",
                "evidence": ["F04"],
                "epistemic": "SUPPORTED",
                "novel_vs_base": True
            }
        ]
    }))
    
    # Reviewer lens with epistemic uncertainty -> should trigger ESCALATE_VERIFIER
    (lens_dir / 'reviewer.json').write_text(json.dumps({
        "findings": [
            {
                "id": "L-reviewer-01",
                "statement": "Ablation on loss term is inconclusive",
                "evidence": ["T03"],
                "epistemic": "INSUFFICIENT_EVIDENCE",
                "novel_vs_base": True
            }
        ]
    }))
    
    escalations = evaluate_escalation(lens_dir)
    assert len(escalations) == 2
    actions = {e['action'] for e in escalations}
    assert "ESCALATE_SECOND_MODEL" in actions
    assert "ESCALATE_VERIFIER" in actions

def test_pi_adapter_isolation(tmp_path):
    from pi_adapter import PiAdapter
    adapter = PiAdapter(default_model="gemini-2.5-pro", available_models=["gemini-2.5-pro", "claude-3-7-sonnet"])
    
    # Test routing
    standard_m = adapter.route_model("LENS", lens="author", escalation=False)
    assert standard_m == "gemini-2.5-pro"
    
    escalated_m = adapter.route_model("LENS", lens="author", escalation=True)
    assert escalated_m == "claude-3-7-sonnet"
    
    # Test task dispatch packet formatting
    dummy_task = tmp_path / 'task.json'
    dummy_task.write_text(json.dumps({"task_id": "T01", "task_type": "LENS", "lens": "reviewer"}))
    packet = adapter.dispatch_task(dummy_task)
    assert packet['task_id'] == 'T01'
    assert packet['host_adapter'] == 'pi'
    assert 'executor_metadata' in packet
    assert packet['executor_metadata']['host'] == 'pi'
