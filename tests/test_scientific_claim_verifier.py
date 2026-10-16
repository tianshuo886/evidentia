"""Adversarial and cross-paper test suite for Scientific Claim Verification and Modal Calibration (Issue #41).

Verifies:
1. Modal certainty overclaim rejection (UNJUSTIFIED_CERTAINTY_OVERCLAIM)
2. Causality / necessity overclaim rejection (UNJUSTIFIED_CAUSALITY_OVERCLAIM)
3. Synergy overclaim without statistical controls (SYNERGY_OVERCLAIM_WITHOUT_CONTROLS)
4. Percentage points vs percentage confusion (PERCENTAGE_VS_POINTS_CONFUSION)
5. Unverified convention stated as fact (UNVERIFIED_CONVENTION_STATED_AS_FACT / UNRESOLVED)
6. Internal audit vocabulary & tag leakage rejection (AUDIT_VOCABULARY_LEAKAGE)
7. Full 10-claim Atomic Claim Ledger for RingMoClaw
8. Cross-paper generalization: Attention (Vaswani) and LoRA (Hu) benchmark ledgers
9. Dynamic claim extraction for arbitrary unseen papers
10. Rendered HTML / Markdown audit leakage immunity
"""
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVALS = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw"

import sys
sys.path.insert(0, str(SCRIPTS))

from scientific_claim_verifier import (
    verify_text_claims,
    build_claim_ledger_for_manuscript,
    verify_reader_scientific_integrity,
    RINGMOCLAW_SHA
)
from render_paper_reader import render_block_html, render_paper_reader_html, render_paper_reader_md, sanitize_editorial_text
from validate_common import load_json, schema_validate


# ==============================================================================
# 1. MODAL CALIBRATION & CERTAINTY OVERCLAIMS
# ==============================================================================

def test_unjustified_certainty_overclaim_fails_closed():
    """Unsubstantiated absolute certainty phrases must fail closed."""
    bad_spans = [
        "两类底层大模型彻底消除了同一模型自我评估时的认知盲区与同质化偏差。",
        "该机制绝对保证生成代码中不出现任何运行时故障与语法异常。",
        "实验结果完全杜绝了候选策略陷入局部次优的任何可能性。",
        "这项架构彻底解决了高分辨率遥感密集小目标漏检的世纪难题。",
        "实验数据毫无疑问地证明了该算法在所有场景下的绝对优势。"
    ]
    for span in bad_spans:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "UNJUSTIFIED_CERTAINTY_OVERCLAIM"]
        assert len(matched) >= 1, f"Expected UNJUSTIFIED_CERTAINTY_OVERCLAIM on: {span!r}"
        assert matched[0]["verdict"] == "CONTRADICTED"
        assert matched[0]["severity"] == "P0_BLOCKER"


def test_calibrated_certainty_controls_pass():
    """Measured epistemics and explicit negations must pass without false alarms."""
    clean_spans = [
        "两类不同技术谱系的大模型有效化解了同一模型自我评估时的认知同质化偏差。",
        "该机制显著降低了生成代码中出现运行时故障的频率，旨在防范常见异常。",
        "消融结果表明异构审稿机制有助于遏制局部伪优化，但并不能彻底消除探索盲区。",
        "该设计旨在缓解高分辨率遥感小目标特征衰减，而无法完全杜绝漏检。"
    ]
    for span in clean_spans:
        diags = verify_text_claims(span)
        assert not any(d["rule"] == "UNJUSTIFIED_CERTAINTY_OVERCLAIM" for d in diags), f"False alarm on: {span!r}"


# ==============================================================================
# 2. CAUSALITY & NECESSITY OVERCLAIMS
# ==============================================================================

def test_unjustified_causality_overclaim_fails_closed():
    """Asserting absolute necessity or sole indispensability fails closed."""
    bad_causality = [
        "消融实验证实了 MSFR 跨层级门控连接在目标检测中的不可替代性。",
        "实验数据证实其不可替代性，是实现精度提升的唯一通路。",
        "对比实验决定性证明了双流总线是不可或缺的唯一机制，证明了其绝对必要性。"
    ]
    for span in bad_causality:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "UNJUSTIFIED_CAUSALITY_OVERCLAIM"]
        assert len(matched) >= 1, f"Expected UNJUSTIFIED_CAUSALITY_OVERCLAIM on: {span!r}"
        assert matched[0]["verdict"] == "CONTRADICTED"
        assert matched[0]["severity"] == "P0_BLOCKER"


def test_calibrated_causality_controls_pass():
    """Calibrated utility assertions pass cleanly."""
    good_causality = [
        "消融实验表明，MSFR 模块在当前 YOLO11x 基线配置下为细长地物识别提供了关键的精度增益。",
        "双流经验总线显著提升了搜索效率，但未证实其在更广泛架构上的绝对不可替代性。"
    ]
    for span in good_causality:
        diags = verify_text_claims(span)
        assert not any(d["rule"] == "UNJUSTIFIED_CAUSALITY_OVERCLAIM" for d in diags)


# ==============================================================================
# 3. STATISTICAL CONTROLS & SYNERGY OVERCLAIMS
# ==============================================================================

def test_synergy_overclaim_without_controls_flags():
    """Unsubstantiated super-additive synergy claims are flagged."""
    bad_synergy = [
        "MSFR 与 CPR 两大模块联合消融展现出强烈的协同效应，产生了超越简单相加的巨大质变。",
        "在联合消融评估中，MSFR 与 CPR 模块联合产生了显著的超加性协同增益。"
    ]
    for span in bad_synergy:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "SYNERGY_OVERCLAIM_WITHOUT_CONTROLS"]
        assert len(matched) >= 1, f"Expected SYNERGY_OVERCLAIM_WITHOUT_CONTROLS on: {span!r}"
        assert matched[0]["verdict"] == "QUALIFIED"


def test_additive_gain_reporting_passes():
    """Accurately reporting additive cumulative gains passes."""
    clean_gain = (
        "两项模块联合使用时，以增加 0.73M 参数量的轻微代价将检测精度推升至 49.14%（净提升 1.84 个百分点），"
        "展现出良好的增量累加效果（MSFR 单独提升 0.88 pp，CPR 单独提升 0.94 pp）。"
    )
    diags = verify_text_claims(clean_gain)
    assert not any(d["rule"] == "SYNERGY_OVERCLAIM_WITHOUT_CONTROLS" for d in diags)


# ==============================================================================
# 4. PERCENTAGE VS PERCENTAGE POINTS CONFUSION
# ==============================================================================

def test_percentage_vs_points_confusion_fails_closed():
    """Confusing percentage points with percentage fails closed."""
    bad_units = [
        "从 47.30% 提升至 49.14%，检测精度提升了 1.84%。",
        "在 FAIR1M 数据集上，总体精度从 47.30% 提升至 49.14%，大幅增长了 1.84% 的幅度。",
        "消融结果显示，单独引入 MSFR 使 mAP 提升了 0.88 个百分比。"
    ]
    for span in bad_units:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "PERCENTAGE_VS_POINTS_CONFUSION"]
        assert len(matched) >= 1, f"Expected PERCENTAGE_VS_POINTS_CONFUSION on: {span!r}"
        assert matched[0]["verdict"] == "CONTRADICTED"


def test_percentage_points_precision_passes():
    """Correct usage of percentage points (pp / 百分点) passes."""
    good_units = [
        "从 47.30% 提升至 49.14%（净提升 1.84 个百分点）。",
        "从 47.30% 提升至 49.14%，增量为 1.84 pp。",
        "单独引入 MSFR 使 mAP 提升 0.88 个百分点。"
    ]
    for span in good_units:
        diags = verify_text_claims(span)
        assert not any(d["rule"] == "PERCENTAGE_VS_POINTS_CONFUSION" for d in diags)


# ==============================================================================
# 5. UNVERIFIED CONVENTIONS (LEVIR-CD F1 VS IOU)
# ==============================================================================

def test_unverified_convention_stated_as_fact_flags():
    """Asserting macro-averaging as an established fact without source verification flags."""
    asserted_as_fact = "LEVIR-CD 变化检测中 F1 达到 90.54% 而 IoU 为 89.97%，证实是因为采用了宏平均算法计算。"
    diags = verify_text_claims(asserted_as_fact)
    matched = [d for d in diags if d["rule"] == "UNVERIFIED_CONVENTION_STATED_AS_FACT"]
    assert len(matched) >= 1
    assert matched[0]["verdict"] == "QUALIFIED"


def test_unresolved_convention_qualification_passes():
    """Explicitly acknowledging unresolved conventions in source paper passes."""
    qualified = (
        "演化出 EvoChangeStar 双向时序交互网络，F1 达到 90.54%，IoU 从 87.10% 提升至 89.97%"
        "（注：论文未公开具体评测脚本，数值偏离单类别二值公式属于基准约定未决项 UNRESOLVED，可能源于类别平均或多分类评估定义）。"
    )
    diags = verify_text_claims(qualified)
    assert not any(d["rule"] in ("METRIC_CONVENTION_AMBIGUITY", "UNVERIFIED_CONVENTION_STATED_AS_FACT") for d in diags)


# ==============================================================================
# 6. INTERNAL AUDIT VOCABULARY LEAKAGE
# ==============================================================================

def test_audit_vocabulary_leakage_fails_closed():
    """Bracketed audit tags and internal pipeline instructions fail closed."""
    leaked_spans = [
        "在对方案进行审查时【科学核验：放行】，系统记录了如下指标。",
        "根据【证据核验】结果，该模块表现优异。",
        "此处经过【审查透镜】确认，符合相关要求。",
        "作者团队【核验结论】指出参数规模仅为 0.73M。",
        "科研执行中必须严格恪守输入防火墙，杜绝任何外部信息注入。",
        "该流程由 Lead Writer 统一编排并输出最终精读稿件。"
    ]
    for span in leaked_spans:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "AUDIT_VOCABULARY_LEAKAGE"]
        assert len(matched) >= 1, f"Expected AUDIT_VOCABULARY_LEAKAGE on: {span!r}"
        assert matched[0]["verdict"] == "CONTRADICTED"
        assert matched[0]["severity"] == "P0_BLOCKER"


def test_editorial_prose_free_of_leakage_passes():
    """Natural scientific editorial prose passes without audit leakage."""
    clean_prose = "在方案审查阶段，系统评估了技术合理性并记录了验证指标。模型微结构经过沙箱隔离测试验证。"
    diags = verify_text_claims(clean_prose)
    assert not any(d["rule"] == "AUDIT_VOCABULARY_LEAKAGE" for d in diags)


# ==============================================================================
# 7. RINGMOCLAW 10-CLAIM ATOMIC CLAIM LEDGER
# ==============================================================================

def test_known_paper_must_not_receive_cached_claim_verdicts(tmp_path):
    """Known benchmark titles must not create pre-approved source claims."""
    root = tmp_path / "ringmoclaw_workspace"
    root.mkdir()
    manuscript = {
        "paper_id": "ringmoclaw", "source_sha256": RINGMOCLAW_SHA,
        "document": {"title": "RingMoClaw",
                     "paper_meta": {"authors": ["Kaiyue Kang"], "venue": "arXiv", "year": 2026},
                     "sections": [{"id": "sec-01", "title": "Overview",
                                   "blocks": [{"type": "paragraph", "text": "Short overview."}]}]}
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    assert not schema_validate(ledger, "claim_ledger")
    assert len(ledger["claims"]) == 1
    assert ledger["claims"][0]["verdict"] == "UNVERIFIED"
    assert ledger["claims"][0]["attribution"]["source_confirmed"] is False
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"


# ==============================================================================
# 8. CROSS-PAPER GENERALIZATION: ATTENTION AND LORA
# ==============================================================================

def test_cross_paper_vaswani_attention_ledger(tmp_path):
    root = tmp_path / "attention_workspace"
    root.mkdir()
    manuscript = {
        "paper_id": "vaswani2017attention", "source_sha256": "attention-sha256",
        "document": {"title": "Attention Is All You Need",
                     "paper_meta": {"authors": ["A. Vaswani"], "venue": "NeurIPS 2017", "year": 2017},
                     "sections": [{"id": "sec-01", "title": "Model Architecture",
                                   "blocks": [{"type": "paragraph", "text": "Transformer architecture."}]}]}
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    assert not schema_validate(ledger, "claim_ledger")
    assert len(ledger["claims"]) == 1
    assert ledger["claims"][0]["verdict"] == "UNVERIFIED"
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"


def test_cross_paper_lora_ledger(tmp_path):
    root = tmp_path / "lora_workspace"
    root.mkdir()
    manuscript = {
        "paper_id": "hu2021lora", "source_sha256": "lora-sha256",
        "document": {"title": "LoRA: Low-Rank Adaptation of Large Language Models",
                     "paper_meta": {"authors": ["E. Hu"], "venue": "ICLR", "year": 2022},
                     "sections": [{"id": "sec-01", "title": "Problem Statement",
                                   "blocks": [{"type": "paragraph", "text": "Low-rank parameterization."}]}]}
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    assert not schema_validate(ledger, "claim_ledger")
    assert len(ledger["claims"]) == 1
    assert ledger["claims"][0]["verdict"] == "UNVERIFIED"
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"


# ==============================================================================
# 9. DYNAMIC CLAIM EXTRACTION FOR ARBITRARY UNSEEN PAPERS
# ==============================================================================

def test_dynamic_claim_extraction_for_arbitrary_paper(tmp_path):
    """Arbitrary unseen paper dynamically yields validated atomic claim ledger."""
    root = tmp_path / "unknown_workspace"
    root.mkdir()
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "unseen_genomics_paper",
        "source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "document": {
            "title": "Single-Cell Genomic Variant Analysis via Diffusion Transformers",
            "paper_meta": {
                "authors": ["Alice Smith", "Bob Jones"],
                "venue": "Nature Biotechnology",
                "year": 2026,
                "venue_verified_externally": True
            },
            "sections": [
                {
                    "id": "sec-01",
                    "title": "Methodology",
                    "blocks": [
                        {
                            "type": "callout",
                            "text": "基于扩散Transformer的去噪机制旨在有效分离高频测序噪声与真实单细胞变异信号。"
                        },
                        {
                            "type": "table",
                            "evidence_id": "T01",
                            "caption": "变异检测基准对比结果",
                            "analysis": "在 100k 细胞规模评测中，模型检出精度提升 4.2 个百分点，F1 分数达到 92.4%。"
                        },
                        {
                            "type": "takeaway",
                            "text": "当前评测受限于Illumina二代测序长度，长读段三代测序下的泛化边界属于基准约定未决项（UNRESOLVED）。"
                        }
                    ]
                }
            ]
        }
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    errs = list(schema_validate(ledger, "claim_ledger"))
    assert not errs, f"Dynamic claim ledger schema error: {errs}"

    claims = ledger["claims"]
    assert len(claims) >= 3
    # Check categories
    categories = {c["epistemic_category"] for c in claims}
    assert "OBSERVATION" in categories
    assert "UNRESOLVED" in categories
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert all(c["attribution"]["source_confirmed"] is False for c in claims)


# ==============================================================================
# 10. RENDER SANITIZER AUDIT LEAKAGE IMMUNITY
# ==============================================================================

def test_render_sanitizer_removes_audit_tags_from_html_and_markdown(tmp_path):
    """Renderer sanitizes prose so audit tags never leak into user-facing output."""
    raw_text = "根据【科学核验：放行】的最终记录，团队必须严格恪守输入防火墙并推进实验。"
    cleaned = sanitize_editorial_text(raw_text)
    assert "【科学核验" not in cleaned
    assert "必须严格恪守" not in cleaned
    assert "输入防火墙" not in cleaned

    # Verify HTML block rendering strips tags
    block = {"type": "paragraph", "text": raw_text}
    html_out = render_block_html(block, tmp_path)
    assert "【科学核验" not in html_out
    assert "必须严格恪守" not in html_out

    # Verify Markdown rendering strips tags
    manuscript = {
        "document": {
            "title": "测试论文",
            "paper_meta": {},
            "sections": [
                {"id": "sec-01", "title": "正文", "blocks": [block]}
            ]
        }
    }
    md_out = render_paper_reader_md(manuscript, tmp_path)
    assert "【科学核验" not in md_out
    assert "必须严格恪守" not in md_out
