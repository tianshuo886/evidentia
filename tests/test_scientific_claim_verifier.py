
"""Adversarial and cross-paper test suite for Scientific Claim Verification and Modal Calibration (Issue #41).

Verifies:
1. Modal certainty overclaim rejection (UNJUSTIFIED_CERTAINTY_OVERCLAIM)
2. Causality / necessity overclaim rejection (UNJUSTIFIED_CAUSALITY_OVERCLAIM)
3. Synergy overclaim without statistical controls (SYNERGY_OVERCLAIM_WITHOUT_CONTROLS)
4. Percentage points vs percentage confusion (PERCENTAGE_VS_POINTS_CONFUSION)
5. Unverified convention stated as fact (UNVERIFIED_CONVENTION_STATED_AS_FACT / UNRESOLVED)
6. Internal audit vocabulary & tag leakage rejection (AUDIT_VOCABULARY_LEAKAGE)
7. Synthetic candidate-claim extraction never self-verifies
8. Known-paper identifiers do not activate a cached answer path
9. Dynamic claim extraction for arbitrary unseen papers
10. Rendered HTML / Markdown audit leakage immunity
"""
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Sample paper identity used by this test only. Production code carries no
# per-paper registry (Issue #46).
SYNTHETIC_SOURCE_SHA = "a" * 64
SCRIPTS = ROOT / "scripts"

import sys
sys.path.insert(0, str(SCRIPTS))

from scientific_claim_verifier import (
    verify_text_claims,
    build_claim_ledger_for_manuscript,
    verify_reader_scientific_integrity,
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
        "该设计旨在缓解有限测试条件下的误差，而无法完全杜绝漏检。"
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
        "消融实验证实了 Module A 跨层级门控连接在目标检测中的不可替代性。",
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
        "消融实验表明，Module A 模块在当前 Detector baseline 基线配置下为细长地物识别提供了关键的精度增益。",
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
        "Module A 与 Module B 两大模块联合消融展现出强烈的协同效应，产生了超越简单相加的巨大质变。",
        "在联合消融评估中，Module A 与 Module B 模块联合产生了显著的超加性协同增益。"
    ]
    for span in bad_synergy:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "SYNERGY_OVERCLAIM_WITHOUT_CONTROLS"]
        assert len(matched) >= 1, f"Expected SYNERGY_OVERCLAIM_WITHOUT_CONTROLS on: {span!r}"
        assert matched[0]["verdict"] == "QUALIFIED"


def test_additive_gain_reporting_passes():
    """Accurately reporting additive cumulative gains passes."""
    clean_gain = (
        "两项模块联合使用时，以适度的参数增加将检测精度提升 2 个百分点，"
        "展现出良好的增量累加效果（Module A 与 Module B 单独测试均有提升）。"
    )
    diags = verify_text_claims(clean_gain)
    assert not any(d["rule"] == "SYNERGY_OVERCLAIM_WITHOUT_CONTROLS" for d in diags)


# ==============================================================================
# 4. PERCENTAGE VS PERCENTAGE POINTS CONFUSION
# ==============================================================================

def test_percentage_vs_points_confusion_fails_closed():
    """Confusing percentage points with percentage fails closed."""
    bad_units = [
        "从 60% 提升至 62%，检测精度提升了 2%。",
        "在合成数据集上，总体精度从 60% 提升至 62%，大幅增长了 2% 的幅度。",
        "合成消融结果显示，单独引入一个模块使 mAP 提升了 0.88 个百分比。"
    ]
    for span in bad_units:
        diags = verify_text_claims(span)
        matched = [d for d in diags if d["rule"] == "PERCENTAGE_VS_POINTS_CONFUSION"]
        assert len(matched) >= 1, f"Expected PERCENTAGE_VS_POINTS_CONFUSION on: {span!r}"
        assert matched[0]["verdict"] == "CONTRADICTED"


def test_percentage_points_precision_passes():
    """Correct usage of percentage points (pp / 百分点) passes."""
    good_units = [
        "从 60% 提升至 62%（净提升 2 个百分点）。",
        "从 60% 提升至 62%，增量为 2 pp。",
        "合成指标上升 0.88 个百分点。"
    ]
    for span in good_units:
        diags = verify_text_claims(span)
        assert not any(d["rule"] == "PERCENTAGE_VS_POINTS_CONFUSION" for d in diags)


# ==============================================================================
# 5. UNVERIFIED EVALUATION CONVENTIONS
# ==============================================================================

def test_unverified_evaluation_convention_is_left_to_source_review():
    """A generic averaging claim is not judged using a benchmark-specific answer."""
    prose = "该研究的指标采用宏平均算法计算。"
    assert not any(d["rule"] == "UNVERIFIED_CONVENTION_STATED_AS_FACT" for d in verify_text_claims(prose))


def test_identity_does_not_select_a_cached_answer(tmp_path):
    """Changing paper_id/source hash does not switch the claim extraction path."""
    def make(paper_id, source_sha, title):
        return {
            "schema_version": "3.0", "paper_id": paper_id, "source_sha256": source_sha,
            "document": {"title": title, "paper_meta": {}, "sections": [
                {"id": "results", "title": "Results", "blocks": [
                    {"type": "paragraph", "text": "A controlled measurement improves from 60% to 62%, an increase of 2%."},
                    {"type": "paragraph", "text": "The aggregation convention is not disclosed."},
                ]}
            ]}
        }
    a = build_claim_ledger_for_manuscript(tmp_path, make("SYNTHETIC-A", "a"*64, "Synthetic A"))
    b = build_claim_ledger_for_manuscript(tmp_path, make("SYNTHETIC-B", "b"*64, "Synthetic B"))
    assert [c["verdict"] for c in a["claims"]] == [c["verdict"] for c in b["claims"]]
    assert a["verification_summary"]["status"] == b["verification_summary"]["status"] == "NEEDS_REVIEW"

# ==============================================================================
# 6. INTERNAL AUDIT VOCABULARY LEAKAGE
# ==============================================================================

def test_audit_vocabulary_leakage_fails_closed():
    """Bracketed audit tags and internal pipeline instructions fail closed."""
    leaked_spans = [
        "在对方案进行审查时【科学核验：放行】，系统记录了如下指标。",
        "根据【证据核验】结果，该模块表现优异。",
        "此处经过【审查透镜】确认，符合相关要求。",
        "作者团队【核验结论】指出所报告的测量结果。",
        "科研执行中必须严格恪守输入边界，杜绝任何未经声明的上下文注入。",
        "该流程由 Internal Agent 统一编排并输出最终结果。"
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
# 7. Synthetic Candidate Ledger
# ==============================================================================

def test_any_paper_uses_dynamic_unverified_claim_candidates(tmp_path):
    """Paper identity must not select a cached answer set; extraction stays UNVERIFIED."""
    root = tmp_path / "synthetic_workspace"
    root.mkdir()
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "SYNTHETIC-PAPER-01",
        "source_sha256": SYNTHETIC_SOURCE_SHA,
        "document": {
            "title": "Synthetic Measurement Study",
            "paper_meta": {
                "authors": ["A. Researcher"],
                "venue": "Synthetic Methods Workshop",
                "year": 2026,
                "preprint_status": "UNKNOWN",
                "venue_verified_externally": False
            },
            "orientation": {"lead": "合成测量研究说明"},
            "sections": [
                {"id": "sec-01", "title": "Measurement setup", "blocks": [
                    {"type": "paragraph", "text": "The method projects the input measurement into a normalized representation."},
                    {"type": "paragraph", "text": "Under the stated condition, the measured error decreases by 3.2 percentage points."},
                    {"type": "paragraph", "text": "The paper reports an unexplained convention that remains unresolved."},
                ]}
            ]
        }
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    errs = list(schema_validate(ledger, "claim_ledger"))
    assert not errs, f"Claim ledger schema error: {errs}"

    claims = ledger["claims"]
    # Issue #46: a known paper must not receive a cached, hardcoded claim set.
    # Claims come from the manuscript under review, not from a paper registry.
    assert claims, "a manuscript must still produce candidate statements"
    assert not any(
        str(c["claim_id"]).startswith("CLM-PAPER-")
        for c in claims
    ), "benchmark-specific claim templates must not reach production verdicts"
    assert ledger["verification_summary"]["status"] != "PASS"
    assert not any(
        c.get("attribution", {}).get("source_confirmed") for c in claims
    )
    # Epistemic categories still come from the manuscript text itself.
    categories = {c["epistemic_category"] for c in claims}
    assert categories, "every extracted statement carries an epistemic category"


# ==============================================================================
# 8. No Paper-Specific Fast Path
# ==============================================================================

def test_second_synthetic_identity_uses_same_dynamic_path(tmp_path):
    """A second synthetic identity follows the same generic candidate path."""
    root = tmp_path / "synthetic_workspace_b"
    root.mkdir()
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "SYNTHETIC-PAPER-B",
        "source_sha256": "b" * 64,
        "document": {
            "title": "Synthetic Projection Study B",
            "paper_meta": {
                "authors": ["B. Researcher"],
                "venue": "Synthetic Workshop",
                "year": 2017,
                "venue_verified_externally": True
            },
            "sections": [
                {"id": "sec-01", "title": "Model Architecture", "blocks": [{"type": "paragraph", "text": "Transformer architecture."}]}
            ]
        }
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    errs = list(schema_validate(ledger, "claim_ledger"))
    assert not errs, f"Synthetic ledger schema error: {errs}"

    claims = ledger["claims"]
    claim_ids = {c["claim_id"] for c in claims}
    # No hardcoded per-paper template may inject claims (#46).
    assert not any(cid.startswith("CLM-PAPER-") for cid in claim_ids)
    assert claims
    # Issue #46: deterministic extraction performs no source comparison, so a
    # ledger built from the manuscript alone is NEEDS_REVIEW, never PASS.
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert not any(
        c.get("attribution", {}).get("source_confirmed") for c in ledger["claims"]
    ), "extraction must not claim source confirmation"


def test_third_synthetic_identity_uses_same_dynamic_path(tmp_path):
    """A third synthetic identity follows the same generic candidate path."""
    root = tmp_path / "synthetic_workspace_c"
    root.mkdir()
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "SYNTHETIC-PAPER-C",
        "source_sha256": "c" * 64,
        "document": {
            "title": "Synthetic Adaptation Study C",
            "paper_meta": {
                "authors": ["C. Researcher"],
                "venue": "Synthetic Methods Workshop",
                "year": 2022,
                "venue_verified_externally": True
            },
            "sections": [
                {"id": "sec-01", "title": "Problem Statement", "blocks": [{"type": "paragraph", "text": "Low-rank parameterization."}]}
            ]
        }
    }
    ledger = build_claim_ledger_for_manuscript(root, manuscript)
    errs = list(schema_validate(ledger, "claim_ledger"))
    assert not errs, f"Synthetic ledger schema error: {errs}"

    claims = ledger["claims"]
    claim_ids = {c["claim_id"] for c in claims}
    assert not any(cid.startswith("CLM-PAPER-") for cid in claim_ids)
    assert claims
    # Issue #46: deterministic extraction performs no source comparison, so a
    # ledger built from the manuscript alone is NEEDS_REVIEW, never PASS.
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert not any(
        c.get("attribution", {}).get("source_confirmed") for c in ledger["claims"]
    ), "extraction must not claim source confirmation"


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
    # Issue #46: deterministic extraction performs no source comparison, so a
    # ledger built from the manuscript alone is NEEDS_REVIEW, never PASS.
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert not any(
        c.get("attribution", {}).get("source_confirmed") for c in ledger["claims"]
    ), "extraction must not claim source confirmation"


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
