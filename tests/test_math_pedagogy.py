"""Comprehensive Test Suite for Issue #40: Formula Pedagogy.

Tests:
1. Teaching Core Equations: RingMoClaw Reader teaches Eq. (1), (2), (5), (6) and accounts for (3), (4), (7).
   - Eq. (1): Explains C_t, 1 - B_t bottleneck inversion, H_t, stage weights, and decision logic.
   - Eq. (2): Explains state transition operator Pi_update, inputs (s_t, c_t, Score_t).
   - Eq. (5): Explains global memory update with Score_t quality filter.
   - Eq. (6): Explains DeltaAcc / Delta t rate, exp(-sigma ||nabla^2||) stability penalty, CV_50 proxy,
     >0.55 promotion threshold, and unstated hyperparameter coefficients.
2. Cross-Paper Generalization:
   - Attention Is All You Need Eq. (1): Teaches 1/sqrt(d_k) scaling factor preventing softmax gradient saturation.
   - LoRA Eq. (3): Teaches low-rank matrix decomposition BA and alpha/r scale factor.
3. Adversarial Counterexamples:
   - Silent equation (rendered without explanation) FAILS audit with UNEXPLAINED_MATERIAL_EQUATION.
   - Inverted math explanation (claiming 1 - B_t rewards bottlenecks) FAILS audit with MATHEMATICAL_CONTRADICTION.
   - Trivial/auxiliary equation with concise definition PASSES audit.
4. Rendering Parity:
   - Both HTML and Markdown render equation role badges, term breakdowns, and proxy callouts.
5. Schema Validation:
   - Both schemas validate rich pedagogy fields.
"""
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"

import sys
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from equation_fidelity import (
    KNOWN_BENCHMARK_EQUATIONS,
    derive_equation_pedagogy,
    detect_equations_from_pdf
)
from reader_math_explanation_audit import (
    audit_single_equation,
    audit_math_pedagogy
)
from render_reader import render_reader
from test_gates import fixture
from validate_common import load_json, schema_validate

RINGMO_PDF = Path("/Users/shentianshuo/Code/PINN canopy/literature/RingMoClaw_An_Experience-Inspired_Multi-Agent_Framework_for_Self-Evolving_Research_in_Remote_Sensing_2609_00814_v2/RingMoClaw_An_Experience-Inspired_Multi-Agent_Framework_for_Self-Evolving_Research_in_Remote_Sensing_2609_00814_v2.pdf")
RINGMO_SHA = "32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa"


def test_schema_validates_rich_pedagogy():
    """Verify that equation and narrative_manuscript schemas accept structured pedagogy."""
    eq_schema = load_json(ROOT / "schemas/equation.schema.json")
    manuscript_schema = load_json(ROOT / "schemas/narrative_manuscript.schema.json")

    sample_eq = {
        "equation_id": "EQ-06",
        "page": 8,
        "raw_text": "fscore(m) = alpha (DeltaAcc/Deltat) + beta exp(-sigma ||nabla^2||)",
        "latex": r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) + \beta \exp\left(-\sigma \|\nabla_\theta^2\|\right)",
        "pedagogy": {
            "role": "五分钟敏捷早筛适应度打分函数",
            "explanation_priority": "MUST_EXPLAIN",
            "symbol_definitions": [
                {"symbol": r"\Delta \text{Acc}", "name": "精度增益", "interpretation": "初期微缩验证精度增益"}
            ],
            "input_output": {
                "inputs": ["微缩子集试训数据", "耗时 Delta t"],
                "outputs": ["标量评分 f_score"]
            },
            "term_interpretations": [
                {"term": r"\frac{\Delta \text{Acc}}{\Delta t}", "role": "单位时间变化率", "intuition": "衡量算力利用效率"}
            ],
            "assumptions": ["早筛表现与全量收敛正相关"],
            "implementation_proxy": "以最后50步损失变异系数作为二阶曲率代理",
            "source_anchors": ["p.8 Section 3.3.3"]
        }
    }
    assert schema_validate(sample_eq, "equation") == []


def test_ringmoclaw_pedagogy_teaches_core_equations():
    """Verify that RingMoClaw pedagogy comprehensively teaches Eq. 1, 2, 5, 6 and defines 3, 4, 7."""
    eqs = KNOWN_BENCHMARK_EQUATIONS[RINGMO_SHA]

    # Eq. (1): Critic 打分函数
    eq1 = eqs[1]
    ped1 = eq1["pedagogy"]
    assert ped1["explanation_priority"] == "MUST_EXPLAIN"
    term_terms = [t["term"] for t in ped1["term_interpretations"]]
    assert "1 - B_t" in term_terms
    assert any("反转" in t["intuition"] or "抑制" in t["intuition"] for t in ped1["term_interpretations"] if t["term"] == "1 - B_t")
    assert any(s["symbol"] == "C_t" for s in ped1["symbol_definitions"])
    assert any(s["symbol"] == "H_t" for s in ped1["symbol_definitions"])

    # Eq. (2): Main Agent 状态转移
    eq2 = eqs[2]
    ped2 = eq2["pedagogy"]
    assert any("update" in t.get("term", "").lower() or "pi" in t.get("term", "").lower() or r"\Pi" in t.get("term", "") for t in ped2["term_interpretations"])

    # Eq. (5): 全局记忆更新规则
    eq5 = eqs[5]
    ped5 = eq5["pedagogy"]
    assert ped5["explanation_priority"] == "MUST_EXPLAIN"
    assert any("Filter" in t["term"] for t in ped5["term_interpretations"])

    # Eq. (6): 五分钟敏捷早筛打分函数
    eq6 = eqs[6]
    ped6 = eq6["pedagogy"]
    assert ped6["explanation_priority"] == "MUST_EXPLAIN"
    # Terms
    terms_dict = {t["term"]: t["intuition"] for t in ped6["term_interpretations"]}
    assert any("Delta" in k and "t" in k for k in terms_dict.keys())
    assert any("exp" in k or r"\exp" in k for k in terms_dict.keys())
    # Proxy
    assert "CV_50" in ped6["implementation_proxy"] or "变异系数" in ped6["implementation_proxy"]
    assert "50" in ped6["implementation_proxy"]
    assert "> 0.55" in ped6["implementation_proxy"] or ">0.55" in ped6["implementation_proxy"]
    assert "未开源" in ped6["implementation_proxy"] or "未公开" in ped6["implementation_proxy"]

    # Eqs. (3), (4), (7): Concise definitions
    for num in (3, 4, 7):
        eq = eqs[num]
        assert eq["pedagogy"]["explanation_priority"] == "CONCISE_DEFINE"
        assert len(eq["pedagogy"]["role"]) > 5


def test_cross_paper_pedagogy_attention_and_lora():
    """Verify non-RingMo papers exhibit paper-specific, non-generic mathematical explanations."""
    att_sha = "bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697"
    lora_sha = "e9a0d3128767db616085dc0f4e6e455e672e89af823e8ed1282793682787395a"

    # Attention Eq. 1
    att_eq1 = KNOWN_BENCHMARK_EQUATIONS[att_sha][1]
    att_ped = att_eq1["pedagogy"]
    assert att_ped["explanation_priority"] == "MUST_EXPLAIN"
    scaling_term = next(t for t in att_ped["term_interpretations"] if "sqrt" in t["term"])
    assert "方差" in scaling_term["intuition"] or "饱和" in scaling_term["intuition"] or "梯度" in scaling_term["intuition"]

    # LoRA Eq. 3
    lora_eq3 = KNOWN_BENCHMARK_EQUATIONS[lora_sha][3]
    lora_ped = lora_eq3["pedagogy"]
    assert lora_ped["explanation_priority"] == "MUST_EXPLAIN"
    lora_terms = {t["term"]: t["intuition"] for t in lora_ped["term_interpretations"]}
    assert any("BA" in k or "Delta W" in k for k in lora_terms.keys())
    assert any("低秩" in v or "显存" in v or "参数量" in v for v in lora_terms.values())


def test_adversarial_counterexamples_rejected_by_audit():
    """Verify that silent equations and mathematically contradictory explanations FAIL audit."""
    # Counterexample 1: Silent equation (rendered with only a 5-word generic title)
    silent_eq = {
        "equation_id": "EQ-01",
        "paper_label": "Eq. (1)",
        "equation_number": 1,
        "latex": r"\text{Score}_t = w_1 C_t + w_2 (1 - B_t) + w_3 H_t",
        "explanation": "打分公式",
        "explanation_priority": "MUST_EXPLAIN"
    }
    res_silent = audit_single_equation(silent_eq, full_context_text="这里给出了打分公式。")
    assert not res_silent["passed"]
    assert any("UNEXPLAINED_MATERIAL_EQUATION" in issue for issue in res_silent["issues"])

    # Counterexample 2: Mathematically contradictory explanation (claiming 1 - B_t rewards bottlenecks)
    inverted_eq = {
        "equation_id": "EQ-01",
        "paper_label": "Eq. (1)",
        "equation_number": 1,
        "latex": r"\text{Score}_t = w_1 C_t + w_2 (1 - B_t) + w_3 H_t",
        "explanation": "Critic 多维结构化打分函数：结合阶段完成度 C_t 与瓶颈危害度 B_t，当瓶颈越严重时得分越高，奖励严重瓶颈方案。",
        "explanation_priority": "MUST_EXPLAIN"
    }
    res_inverted = audit_single_equation(inverted_eq, full_context_text="打分函数当瓶颈越严重时得分越高，奖励严重瓶颈。")
    assert not res_inverted["passed"]
    assert any("MATHEMATICAL_CONTRADICTION" in issue for issue in res_inverted["issues"])

    # Counterexample 3: False claim about Eq. 6 computing exact Hessian
    false_hessian_eq = {
        "equation_id": "EQ-06",
        "paper_label": "Eq. (6)",
        "equation_number": 6,
        "latex": r"f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) + \beta \exp\left(-\sigma \|\nabla_\theta^2\|\right)",
        "explanation": "五分钟敏捷早筛打分：工程实现中直接精确计算了全参数二阶 Hessian 矩阵作为稳定性指标。",
        "explanation_priority": "MUST_EXPLAIN"
    }
    res_hessian = audit_single_equation(false_hessian_eq, full_context_text="系统直接精确计算全参数二阶Hessian矩阵。")
    assert not res_hessian["passed"]
    assert any("MATHEMATICAL_CONTRADICTION" in issue for issue in res_hessian["issues"])

    # Positive Counterexample: Trivial equation with concise definition PASSES
    trivial_eq = {
        "equation_id": "EQ-03",
        "paper_label": "Eq. (3)",
        "equation_number": 3,
        "latex": r"\mathcal{S} = \{\mathcal{S}_{\text{arch}}, \mathcal{S}_{\text{train}}, \mathcal{S}_{\text{data}}, \mathcal{S}_{\text{intg}}\}",
        "explanation": "遥感自主演化搜索空间划分为架构、训练、数据与系统集成四维正交子空间。",
        "explanation_priority": "CONCISE_DEFINE"
    }
    res_trivial = audit_single_equation(trivial_eq, full_context_text="搜索空间定义为四维正交子空间。")
    assert res_trivial["passed"]


def test_end_to_end_rendered_reader_contains_pedagogy(tmp_path):
    """Verify that end-to-end rendered HTML and Markdown contain pedagogical breakdowns."""
    root = fixture(tmp_path)
    source_map = load_json(root / "model/source_map.json")

    # Inject verified RingMoClaw equations with pedagogy
    eqs = KNOWN_BENCHMARK_EQUATIONS[RINGMO_SHA]
    source_map["pages"][0]["equations"] = [
        {
            "equation_id": "EQ-01",
            "paper_label": "Eq. (1)",
            "equation_number": 1,
            "page": 1,
            "raw_text": "Score_t = w1 C_t + w2 (1 - B_t) + w3 H_t",
            "latex": eqs[1]["latex"],
            "display_mode": True,
            "source_confidence": "VERIFIED",
            "role_zh": eqs[1]["role_zh"],
            "explanation": eqs[1]["explanation"],
            "pedagogy": eqs[1]["pedagogy"]
        },
        {
            "equation_id": "EQ-06",
            "paper_label": "Eq. (6)",
            "equation_number": 6,
            "page": 1,
            "raw_text": "fscore(m) = alpha (DeltaAcc / Deltat) + beta exp(-sigma ||nabla^2||)",
            "latex": eqs[6]["latex"],
            "display_mode": True,
            "source_confidence": "VERIFIED",
            "role_zh": eqs[6]["role_zh"],
            "explanation": eqs[6]["explanation"],
            "pedagogy": eqs[6]["pedagogy"]
        }
    ]
    (root / "model/source_map.json").write_text(json.dumps(source_map, ensure_ascii=False), encoding="utf-8")

    # Render reader
    render_reader(root)

    html_text = (root / "reader/paper_reader.html").read_text(encoding="utf-8")
    md_text = (root / "reader/paper_reader.md").read_text(encoding="utf-8")

    # Verify HTML contains pedagogy tags
    assert "eq-role" in html_text
    assert "eq-terms" in html_text
    assert "eq-proxy" in html_text
    assert "反转瓶颈" in html_text or "1 - B_t" in html_text
    assert "变异系数" in html_text or "CV_50" in html_text

    # Verify Markdown contains pedagogical sections
    assert "**角色定位**" in md_text
    assert "**核心项解析与数学直觉**" in md_text
    assert "**工程实现与代理说明**" in md_text

    # Verify Math Explanation Audit PASSES
    audit_res = audit_math_pedagogy(root)
    assert audit_res["status"] == "PASSED", audit_res
    assert audit_res["score"] == 1.0
