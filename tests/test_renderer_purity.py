"""Renderer Purity Tests for Evidentia (Issue #8).

Enforces the target invariant:
"Renderer must be scientifically dumb. Production renderer code may format scientific
content, but may not author new mechanisms, limitations, causal claims, hyperparameters,
or recommendations."
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture

FORBIDDEN_FALLBACK_STRINGS = [
    "AdamW",
    "独立同分布高斯分布",
    "高维、非线性及多模态数据时存在的表征瓶颈",
    "多尺度特征注意力约束损失",
    "隐式正则化效应",
    "长尾或极端工况下存在退化风险",
    "学习率预热策略",
    "增大模型容量"
]

def test_renderer_static_code_purity():
    """Verify that scripts/render_reader.py and related presentation/narrative scripts do not contain hardcoded domain scientific boilerplate."""
    target_scripts = [
        ROOT / 'scripts/render_reader.py',
        ROOT / 'scripts/render_paper_reader.py',
        ROOT / 'scripts/render_evidence_atlas.py',
        ROOT / 'scripts/narrative_composer_agent.py',
        ROOT / 'scripts/kami_adapter.py'
    ]
    
    violations = []
    for script_p in target_scripts:
        if not script_p.exists():
            continue
        src = script_p.read_text(encoding='utf-8')
        for s in FORBIDDEN_FALLBACK_STRINGS:
            if s in src:
                violations.append((script_p.name, s))
            
    assert not violations, f"Renderer Purity violation: scripts contain hardcoded scientific boilerplate: {violations}"

def test_renderer_runtime_purity_on_minimal_paper(tmp_path):
    """Verify that rendering a minimal non-ML paper produces no fabricated domain concepts."""
    r = fixture(tmp_path)
    
    # Overwrite paper model with a minimal plant science paper
    pm_path = r / 'model/paper_model.json'
    pm = json.loads(pm_path.read_text(encoding='utf-8'))
    pm['paper']['title'] = "Spectroscopic Estimation of Canopy Chlorophyll in Winter Wheat"
    pm['questions'] = [{"id": "Q01", "text": "如何利用近红外高光谱波段无损反演小麦冠层叶绿素含量？", "page": 1}]
    pm['claims'] = [{
        "id": "C01",
        "statement": "705nm与750nm的比值植被指数与小麦冠层叶绿素含量具有最高相关性。",
        "page": 1,
        "evidence": ["F01"],
        "epistemic": "SUPPORTED",
        "observation": "实测光谱反射率曲线在红边区域斜率与实验室测定叶绿素呈线性相关。",
        "author_interpretation": "红边两波段比值有效消除了土壤背景与冠层几何效应。",
        "reader_assessment": "在测试田块内相关性得到验证。"
    }]
    pm['methods'] = [{
        "name": "红边高光谱差分反演算法",
        "description": "基于双波段光谱比值建立物理与经验混合反演方程"
    }]
    pm['assumptions'] = [{"id": "A01", "text": "冠层光照条件在测量期间保持晴朗无云"}]
    pm['limitations'] = [{"id": "B01", "text": "仅在冬小麦拔节期至抽穗期进行了农田原位测试"}]
    pm['portable_components'] = []
    pm_path.write_text(json.dumps(pm, indent=2, ensure_ascii=False), encoding='utf-8')
    
    # Remove any cached argument reconstruction or synthesis
    for f in ('model/argument_reconstruction.json', 'model/scientific_synthesis.json'):
        p = r / f
        if p.exists():
            p.unlink()

    # Run render_reader.py
    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    html_text = (r / 'reader/paper_reader.html').read_text(encoding='utf-8')
    md_text = (r / 'reader/paper_reader.md').read_text(encoding='utf-8')

    # Assert that no ML fallback strings leaked into either the HTML or Markdown Reader
    for forbidden in FORBIDDEN_FALLBACK_STRINGS:
        assert forbidden not in html_text, f"Leaked forbidden boilerplate '{forbidden}' in HTML reader!"
        assert forbidden not in md_text, f"Leaked forbidden boilerplate '{forbidden}' in Markdown reader!"

    # Verify that the paper's actual plant science domain was preserved
    assert "冠层叶绿素" in html_text
    assert "冬小麦" in html_text
    assert "冠层叶绿素" in md_text
