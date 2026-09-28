"""Tests for Cross-Lens Scientific Synthesis (P0 Workstream B).

Validates:
- Organizes scientific knowledge by topic/question (SYN-01, SYN-02...)
- Retains diverse perspectives from all 6 independent Lenses
- Strictly preserves contradictions and anomalies without majority voting
- Schema validates against schemas/scientific_synthesis.schema.json
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, sha_bytes, L
from validate_common import schema_validate

def test_scientific_synthesis_preserves_lenses_and_conflicts(tmp_path):
    r = fixture(tmp_path)
    
    # Inject diverse findings across the 6 Lenses
    (r / 'lens/author.json').write_text(json.dumps({
        'lens': 'author', 'source_sha256': 'pdf', 'base_sha256': 'base', 'base_model_sha256': 'base',
        'lens_contract_version': '1.0', 'prompt_version': '1.0',
        'findings': [{'id': 'F-AUTH-01', 'statement': '提出的稀疏注意力机制在全数据集上显著降低内存消耗。', 'evidence': ['F01']}]
    }), encoding='utf-8')
    
    (r / 'lens/reviewer.json').write_text(json.dumps({
        'lens': 'reviewer', 'source_sha256': 'pdf', 'base_sha256': 'base', 'base_model_sha256': 'base',
        'lens_contract_version': '1.0', 'prompt_version': '1.0',
        'findings': [{'id': 'F-REV-01', 'statement': '基准对比缺乏等显存算力条件下的精细调优，消融控制组不充分。', 'evidence': ['F01']}]
    }), encoding='utf-8')

    (r / 'lens/mechanism.json').write_text(json.dumps({
        'lens': 'mechanism', 'source_sha256': 'pdf', 'base_sha256': 'base', 'base_model_sha256': 'base',
        'lens_contract_version': '1.0', 'prompt_version': '1.0',
        'findings': [{'id': 'F-MECH-01', 'statement': '稀疏掩码通过动态阈值截断无关注意力权重，形成局部连通因果链条。', 'evidence': ['F01']}]
    }), encoding='utf-8')

    (r / 'lens/builder.json').write_text(json.dumps({
        'lens': 'builder', 'source_sha256': 'pdf', 'base_sha256': 'base', 'base_model_sha256': 'base',
        'lens_contract_version': '1.0', 'prompt_version': '1.0',
        'findings': [{'id': 'F-BLD-01', 'statement': '自定义 CUDA 核函数对输入矩阵维度有对齐限制，迁移需注意算子开销。', 'evidence': ['F01']}]
    }), encoding='utf-8')

    (r / 'lens/anomaly.json').write_text(json.dumps({
        'lens': 'anomaly', 'source_sha256': 'pdf', 'base_sha256': 'base', 'base_model_sha256': 'base',
        'lens_contract_version': '1.0', 'prompt_version': '1.0',
        'findings': [{'id': 'F-ANO-01', 'statement': '在短序列极端工况下，由于阈值开销导致整体推理延迟不降反升。', 'evidence': ['F01']}]
    }), encoding='utf-8')

    (r / 'lens/counterfactual.json').write_text(json.dumps({
        'lens': 'counterfactual', 'source_sha256': 'pdf', 'base_sha256': 'base', 'base_model_sha256': 'base',
        'lens_contract_version': '1.0', 'prompt_version': '1.0',
        'findings': [{'id': 'F-CF-01', 'statement': '性能增益可能仅是由于显存释放后间接增大了 batch size 的正则化效应。', 'evidence': ['F01']}]
    }), encoding='utf-8')

    # Inject a recorded tension conflict in lens_reconciliation.json
    (r / 'model/lens_reconciliation.json').write_text(json.dumps({
        'schema_version': '1.0', 'source_sha256': 'pdf', 'base_model_sha256': 'base',
        'items': [
            {
                'id': 'REC-001',
                'canonical_statement': '关于短序列场景下延迟指标的争议',
                'status': 'TENSION',
                'source': ['F01'],
                'supporting_lenses': ['author', 'anomaly']
            }
        ]
    }), encoding='utf-8')

    # Run scientific_synthesis_agent.py
    res = subprocess.run([
        PY, str(ROOT / 'scripts/scientific_synthesis_agent.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    synth_p = r / 'model/scientific_synthesis.json'
    assert synth_p.exists()
    
    synth = json.loads(synth_p.read_text(encoding='utf-8'))
    errs = schema_validate(synth, 'scientific_synthesis')
    assert not errs, f"scientific_synthesis schema error: {errs}"

    topics = synth['topics']
    assert len(topics) >= 4
    
    # 1. Verify Topic-centered organization
    assert all(t['topic_id'].startswith('SYN-') for t in topics)
    assert all('title_zh' in t and 'core_conclusion_zh' in t for t in topics)
    
    # 2. Verify diverse lens contributions preserved
    all_contributing = {l for t in topics for l in t['contributing_lenses']}
    assert 'author' in all_contributing
    assert 'reviewer' in all_contributing
    assert 'mechanism' in all_contributing
    assert 'builder' in all_contributing
    assert 'anomaly' in all_contributing
    assert 'counterfactual' in all_contributing

    # 3. Verify Contradiction / Tension is preserved without majority-voting
    tension_topic = next((t for t in topics if t.get('confidence') == 'TENSION'), None)
    assert tension_topic is not None, "Contradiction was improperly erased or majority-voted away!"
    assert '冲突保留' in tension_topic['core_conclusion_zh'] or '短序列' in tension_topic['title_zh']
