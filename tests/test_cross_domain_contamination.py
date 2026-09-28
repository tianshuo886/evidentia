"""Cross-Domain Template Contamination Tests for Evidentia (Issue #8).

Verifies that disparate scientific domains (e.g. Machine Learning vs Plant Physiology / Spectroscopy)
produce dynamically distinct, domain-faithful synthesis and reader reports without template leakage.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from validate_common import load_json

def setup_ml_paper(tmp_path):
    p = tmp_path / 'paper_ml'
    p.mkdir(parents=True, exist_ok=True)
    r = fixture(p)
    pm_path = r / 'model/paper_model.json'
    pm = load_json(pm_path)
    pm['paper']['title'] = "Sparse Transformer Attention for High-Throughput Sequence Modeling"
    pm['questions'] = [{"id": "Q01", "text": "如何降低标准自注意力机制在超长序列输入下的二次方显存开销？", "page": 1}]
    pm['claims'] = [{
        "id": "C01",
        "statement": "所提出的块对角动态稀疏掩码将峰值显存消耗降低了65%，且保持困惑度指标不变。",
        "page": 2,
        "evidence": ["F01"],
        "epistemic": "SUPPORTED",
        "observation": "在8k序列长度下显存占用由24GB下降至8.4GB。",
        "author_interpretation": "稀疏掩码动态捕获了远距离关键语义依赖。",
        "reader_assessment": "在合成基准与语言建模任务上数值表现一致。"
    }]
    pm['methods'] = [{"name": "块对角稀疏注意力算子", "description": "通过分块近似与局部窗口注意力融合实现稀疏化计算"}]
    pm['assumptions'] = [{"id": "A01", "text": "注意力相关度在远离对角线区域呈指数衰减"}]
    pm['limitations'] = [{"id": "B01", "text": "在全连接稠密图任务上存在精度损失"}]
    pm['portable_components'] = [{"id": "PC01", "name": "BlockSparseAttention", "category": "算子", "description_zh": "PyTorch/CUDA稀疏注意力核函数", "source": ["F01"]}]
    pm_path.write_text(json.dumps(pm, indent=2, ensure_ascii=False), encoding='utf-8')
    return r

def setup_plant_spectroscopy_paper(tmp_path):
    p = tmp_path / 'paper_plant'
    p.mkdir(parents=True, exist_ok=True)
    r = fixture(p)
    pm_path = r / 'model/paper_model.json'
    pm = load_json(pm_path)
    pm['paper']['title'] = "Inversion of Forest Canopy Chlorophyll Content Using Airborne Imaging Spectroscopy"
    pm['questions'] = [{"id": "Q01", "text": "如何利用机载高光谱冠层反射率无损反演亚热带常绿阔叶林叶绿素总量？", "page": 1}]
    pm['claims'] = [{
        "id": "C01",
        "statement": "PROSAIL辐射传输模型耦合红边归一化指数（NDRE）能有效解耦冠层结构效应，反演精度达到R2=0.82。",
        "page": 3,
        "evidence": ["F01"],
        "epistemic": "SUPPORTED",
        "observation": "实测林冠破坏性采样叶绿素含量与机载高光谱反演值呈显著正相关（RMSE=4.2 ug/cm2）。",
        "author_interpretation": "PROSAIL模型有效校正了双向反射分布函数（BRDF）与叶面积指数（LAI）的混淆效应。",
        "reader_assessment": "机载与地面同步验证严密，误差在自然林分可接受范围内。"
    }]
    pm['methods'] = [{"name": "PROSAIL辐射传输物理反演模型", "description": "结合冠层辐射几何与叶片光学性质的耦合正向与逆向求解算法"}]
    pm['assumptions'] = [{"id": "A01", "text": "林冠假定为均匀水平均质介质，忽略剧烈坡度阴影干扰"}]
    pm['limitations'] = [{"id": "B01", "text": "在多层复杂异质林冠下散射效应显著增加，反演不确定性增大"}]
    pm['portable_components'] = [{"id": "PC01", "name": "PROSAIL红边反演LUT查找表", "category": "辐射传输查找表", "description_zh": "基于辐射传输方程预计算的冠层生化参数反演查找表", "source": ["F01"]}]
    pm_path.write_text(json.dumps(pm, indent=2, ensure_ascii=False), encoding='utf-8')
    return r

def test_cross_domain_synthesis_and_reader_contamination(tmp_path):
    r_ml = setup_ml_paper(tmp_path)
    r_plant = setup_plant_spectroscopy_paper(tmp_path)

    # Run scientific synthesis and reader rendering on ML paper
    res1 = subprocess.run([PY, str(ROOT / 'scripts/scientific_synthesis_agent.py'), '--out', str(r_ml)], capture_output=True, text=True)
    assert res1.returncode == 0, res1.stdout + res1.stderr
    res2 = subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r_ml)], capture_output=True, text=True)
    assert res2.returncode == 0, res2.stdout + res2.stderr

    # Run scientific synthesis and reader rendering on Plant paper
    res3 = subprocess.run([PY, str(ROOT / 'scripts/scientific_synthesis_agent.py'), '--out', str(r_plant)], capture_output=True, text=True)
    assert res3.returncode == 0, res3.stdout + res3.stderr
    res4 = subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r_plant)], capture_output=True, text=True)
    assert res4.returncode == 0, res4.stdout + res4.stderr

    # Load synthesis artifacts
    synth_ml = load_json(r_ml / 'model/scientific_synthesis.json')
    synth_plant = load_json(r_plant / 'model/scientific_synthesis.json')

    # Load readers
    plant_html = (r_plant / 'reader/paper_reader.html').read_text(encoding='utf-8')
    plant_md = (r_plant / 'reader/paper_reader.md').read_text(encoding='utf-8')

    # 1. Topic titles must be dynamic and distinct (not identical code templates)
    ml_titles = [t['title_zh'] for t in synth_ml['topics']]
    plant_titles = [t['title_zh'] for t in synth_plant['topics']]
    assert ml_titles != plant_titles, "Failure: ML and Plant papers produced identical synthesis topic titles due to code templates!"

    # 2. Plant paper must contain plant science concepts
    assert "林冠" in plant_html or "叶绿素" in plant_html or "高光谱" in plant_html
    assert "PROSAIL" in plant_html
    assert "PROSAIL" in plant_md

    # 3. Plant paper must NOT contain leaked ML boilerplate
    ml_exclusive_terms = [
        "显存",
        "困惑度",
        "CUDA",
        "PyTorch",
        "Transformer",
        "高维、非线性及多模态数据时存在的表征瓶颈",
        "AdamW",
        "独立同分布高斯分布",
        "学习率预热",
        "长尾或极端工况下存在退化风险"
    ]
    for term in ml_exclusive_terms:
        assert term not in plant_html, f"Cross-Domain Contamination: ML term '{term}' leaked into Plant Science Reader!"
        assert term not in plant_md, f"Cross-Domain Contamination: ML term '{term}' leaked into Plant Science Markdown!"
