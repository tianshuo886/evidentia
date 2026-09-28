"""Argument Recovery Tests for Evidentia (Issue #8).

Verifies that a human or downstream evaluator can recover the paper's central scientific argument
directly and solely from `reader/paper_reader.md` without opening any internal JSON artifacts.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from validate_common import load_json

def test_argument_recovery_from_markdown_alone(tmp_path):
    r = fixture(tmp_path)
    
    # Configure a distinct paper with clear argumentative trajectory
    pm_path = r / 'model/paper_model.json'
    pm = load_json(pm_path)
    pm['paper']['title'] = "Causal Graph Neural Diffusion for Spatiotemporal Forecasting"
    pm['questions'] = [{
        "id": "Q01",
        "text": "如何解决时空预测模型因空间伪相关性导致的跨域分布泛化失效问题？",
        "page": 1
    }]
    pm['claims'] = [
        {
            "id": "C01",
            "statement": "基于因果结构方程的图神经扩散（CGND）在4个跨城市时空基准上将分布外预测误差降低了23.4%。",
            "page": 2,
            "evidence": ["F01"],
            "epistemic": "SUPPORTED",
            "observation": "在传感器发生局部断连的测试场景中，CGND预测均方误差保持在0.18，明显优于基线模型的0.31。",
            "author_interpretation": "因果图掩码有效阻断了由交通拥堵偶然伴随引发的伪空间依赖扩散。",
            "reader_assessment": "消融实验支持因果图掩码在局部扰动下的去偏效果。"
        }
    ]
    pm['methods'] = [
        {
            "name": "因果图神经扩散算法 (CGND)",
            "description": "结合偏微分扩散方程与因果约束图的端到端时空预测模型"
        }
    ]
    pm['assumptions'] = [{"id": "A01", "text": "假定未观测到的全局潜变量不破坏时空因果图的马尔可夫条件"}]
    pm['limitations'] = [{"id": "B01", "text": "计算开销随传感器节点规模呈二次方增长，需采用子图采样"}]
    pm['anomalies'] = [{"id": "ANO-01", "text": "在极端突发暴雨天气下，传感器全局失真导致因果图拓扑估计发生抖动"}]
    pm['unresolved'] = [{"id": "U01", "issue": "动态时变因果图在流式在线计算中的收敛保证仍待理论证明"}]
    pm_path.write_text(json.dumps(pm, indent=2, ensure_ascii=False), encoding='utf-8')

    # Execute renderer
    res = subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    md_path = r / 'reader/paper_reader.md'
    assert md_path.exists(), "reader/paper_reader.md must exist"
    md_content = md_path.read_text(encoding='utf-8')

    # Evaluate that key scientific argument components are recoverable solely from markdown text:
    
    # 1. Central Question
    assert "时空预测" in md_content or "伪相关性" in md_content, "Central question must be recoverable from markdown"
    
    # 2. Central Thesis / Proposition
    assert "CGND" in md_content or "因果图神经扩散" in md_content, "Central method/thesis must be recoverable"
    assert "23.4%" in md_content or "分布外预测" in md_content, "Central claim effect size must be recoverable"
    
    # 3. Decisive Evidence
    assert "F01" in md_content, "Decisive figure evidence ID must be identifiable"
    assert "实证证据解析" in md_content or "关键实验" in md_content, "Evidence section must be present"
    
    # 4. Weakest Link / Limitation / Boundary
    assert "计算开销" in md_content or "马尔可夫" in md_content or "适用边界" in md_content, "Boundaries/limitations must be recoverable"
    
    # 5. Anomaly / Extreme condition
    assert "暴雨" in md_content or "突发" in md_content or "反常" in md_content, "Anomalies must be recoverable"
    
    # 6. Unresolved Question
    assert "动态时变" in md_content or "在线计算" in md_content or "未决问题" in md_content, "Unresolved scientific question must be recoverable"

    # 7. Form factor: Reader is continuous Chinese prose, not a raw JSON dump
    assert not md_content.startswith("{"), "Markdown must be prose, not raw JSON"
    assert "## 1. 一分钟看懂这篇论文" in md_content
    assert "## 2. 论文到底在解决什么问题" in md_content
    assert "## 4. 关键实验逐个说明" in md_content
    assert "## 5. 综合科学判断" in md_content
