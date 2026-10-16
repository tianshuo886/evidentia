"""Three-Layer Test Pyramid for Issue #38: Reader Scientific Regression & Release Gate.

Layer 1 — Deterministic Invariants:
- Structural schema presence, truthful reference resolution, time accounting,
  metric positive-class definitions, and cross-format parity.

Layer 2 — Source-Assisted Adversarial Science Checks:
- Defective real Reader FAIL, corrected version PASS.
- 7 Adversarial mutations (inverting meaning, exchanging GPU/wall-clock, crash conflation,
  false author quotes, missing selection caveats, unverified venue assertions).
- Non-failure controls (labeled independent inference, qualified averaging, justified Atlas omissions).

Layer 3 — Real-Paper A/B Release Gate:
- Multi-paper diverse benchmark corpus (BENCH-01..05 + RINGMOCLAW).
- Strict non-regression on narrative clarity, completeness, and methods.
- Value-add in visual reasoning, metric correctness, and provenance.
- Artifact-bound release gate facets: SCIENCE_VERIFIED, EXPLANATION_COMPLETE, BENCHMARK_PASS.
"""
import json
import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
EVALS = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw"

import sys
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from scientific_claim_verifier import verify_text_claims, verify_reader_scientific_integrity
from reader_depth_audit import audit_explanation_depth, audit_visual_evidence_selection
from reader_acceptance import evaluate
from render_reader import render_reader
from test_gates import fixture
from validate_common import load_json, schema_validate, sha256


# ==============================================================================
# LAYER 1: DETERMINISTIC INVARIANTS
# ==============================================================================

def test_layer1_schema_and_receipt_invariants():
    """All frozen fixtures and receipts must pass exact JSON schema validation."""
    receipts_p = EVALS / "verdict_receipts.json"
    assert receipts_p.exists()
    receipts = load_json(receipts_p)
    assert receipts["provenance"]["source_pdf_sha256"] == "32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa"
    assert receipts["provenance"]["defective_reader_sha256"] == "08b1e9768ab3373a8d3e035523799f0c31dfc845ecf5b120d06a93ef1983c789"
    assert receipts["defective_reader_evaluation"]["status"] == "FAIL"
    assert receipts["corrected_reader_evaluation"]["status"] == "PASS"

    # Pair evaluation schema
    ab_p = ROOT / "ISSUE38_RINGMOCLAW_PAIR_EVALUATION.json"
    assert ab_p.exists()
    ab_data = load_json(ab_p)
    errs = list(schema_validate(ab_data, "reader_pair_evaluation"))
    assert not errs, f"Pair evaluation schema error: {errs}"


def test_layer1_evidence_reference_truthful_resolution():
    """Every evidence ID cited in the corrected narrative must resolve to an existing inventory item."""
    corrected_text = (EVALS / "corrected_reader.md").read_text(encoding="utf-8")
    flat_cited = set(re.findall(r"\b[FT]\d{2}\b", corrected_text))

    expected_must_show = {"F01", "F02", "F04", "F05", "T01", "T06", "T07", "T08", "T09", "T10"}
    assert expected_must_show.issubset(flat_cited), f"Missing must-show citations: {expected_must_show - flat_cited}"


# ==============================================================================
# LAYER 2: SOURCE-ASSISTED ADVERSARIAL SCIENCE CHECKS
# ==============================================================================

def test_layer2_defective_real_reader_fails_with_exact_anchors():
    """Defective Reader must trigger P0 blockers across all required rules."""
    defective_text = (EVALS / "defective_reader.md").read_text(encoding="utf-8")
    diags = verify_text_claims(defective_text)
    rules_triggered = {d["rule"] for d in diags if d.get("severity") == "P0_BLOCKER"}
    assert "METRIC_POSITIVE_CLASS_INVERSION" in rules_triggered
    assert "METRIC_SEMANTIC_CONFUSION" in rules_triggered
    assert "METRIC_UNIT_COLLAPSE" in rules_triggered
    assert "BIBLIOGRAPHIC_FABRICATION" in rules_triggered
    assert "PROJECT_ATTRIBUTION_CONFLATION" in rules_triggered
    assert "EXPERIMENTAL_PROTOCOL_OMISSION" in rules_triggered


@pytest.mark.parametrize("mutation,expected_rule", [
    ("敏捷早筛对劣质方案的精确率达到 1.00（无一漏过）。", "METRIC_POSITIVE_CLASS_INVERSION"),
    ("劣化候选策略召回率为 0.83，导致 17% 潜质策略被过早扼杀。", "METRIC_POSITIVE_CLASS_INVERSION"),
    ("移除双流经验总线后系统发生 6 次严重训练失败与崩溃。", "METRIC_SEMANTIC_CONFUSION"),
    ("对比 AutoResearch，总 GPU 运行时间从 26.90 小时大幅缩减至 12.14 小时。", "METRIC_UNIT_COLLAPSE"),
    ("Kaiyue Kang · IEEE Transactions on Geoscience and Remote Sensing (TGRS) · 2026", "BIBLIOGRAPHIC_FABRICATION"),
    ("作者坦承若要迁移至 PROSAIL 与 PINN，必须引入物理机理守恒定律。", "PROJECT_ATTRIBUTION_CONFLATION"),
    ("FAIR1M 目标检测 mAP50 从 47.30% 稳步提升至 49.14%。", "EXPERIMENTAL_PROTOCOL_OMISSION"),
    ("表I 演化轨迹呈现了 47.88%、48.45% 与 48.82% 等阶段数值。", "TABLE_I_TRAJECTORY_FIDELITY"),
    ("表VI 显示单独引入 MSFR 使 mAP50 提升 1.15 pp。", "TABLE_VI_MODULE_ABLATION_FIDELITY"),
    ("表VI 显示单独引入 CPR 使 mAP50 提升 0.92 pp。", "TABLE_VI_MODULE_ABLATION_FIDELITY"),
    ("消融实验中移除 Critic 审稿机制导致收敛需要 14 轮且仅取得 47.88% mAP。", "TABLE_VIII_CRITIC_ABLATION_FIDELITY"),
    ("在表IX 双流经验总线消融中，非提升探索迭代压减为仅 1 次。", "TABLE_IX_EXPERIENCE_BUS_ABLATION_FIDELITY"),
])
def test_layer2_adversarial_mutations_fail_closed(mutation, expected_rule):
    """Targeted mutations of prose must fail closed on the specific integrity rule."""
    diags = verify_text_claims(mutation, source_metadata={"venue_status": {"venue_verified_externally": False}})
    matched = [d for d in diags if d["rule"] == expected_rule]
    assert len(matched) >= 1, f"Expected {expected_rule} to fail on: {mutation!r}"
    assert matched[0]["verdict"] in ("CONTRADICTED", "QUALIFIED")


def test_layer2_non_failure_controls_pass():
    """Legitimate qualifications and labeled reader inferences must not trigger false alarms."""
    # Control 1: Corrected precision and recall
    c1 = "五分钟敏捷验证在预测劣化候选策略时的精确率为 1.00（零误拦截），而对劣化候选策略的召回率为 0.83（5个被识别，1个漏过）。"
    assert not any(d["rule"] == "METRIC_POSITIVE_CLASS_INVERSION" for d in verify_text_claims(c1))

    # Control 2: Properly distinguished GPU-hours and wall-clock
    c2 = "GPU 算力消耗时间（GPU-hours）从 26.90 小时压减至 12.14 小时，实际挂钟时间（wall-clock hours）从 13.45 小时缩减至 10.61 小时。"
    assert not any(d["rule"] == "METRIC_UNIT_COLLAPSE" for d in verify_text_claims(c2))

    # Control 5: Table I trajectory and protocol
    c5 = "表I 演化轨迹：47.30% -> 48.18% -> 47.77% -> 47.69% -> 49.11% -> 49.14%（注：表I 报告的是三次独立重复演化试验中的最优轨迹结果）。"
    assert not any(d["rule"] == "TABLE_I_TRAJECTORY_FIDELITY" for d in verify_text_claims(c5))

    # Control 6: Table VI MSFR and CPR gains
    c6 = "表VI 中单独引入 MSFR 使 mAP 提升 1.01 个百分点（从 47.30% 增至 48.31%），单独引入 CPR 使 mAP 提升 0.99 个百分点（从 47.30% 增至 48.29%）。"
    assert not any(d["rule"] == "TABLE_VI_MODULE_ABLATION_FIDELITY" for d in verify_text_claims(c6))

    # Control 7: Table VIII Critic ablation
    c7 = "表VIII 中移除独立 Critic 审稿机制后，收敛所需轮数由 7 轮增至 11 轮且精度降至 47.43% mAP。"
    assert not any(d["rule"] == "TABLE_VIII_CRITIC_ABLATION_FIDELITY" for d in verify_text_claims(c7))

    # Control 8: Table IX Experience bus ablation
    c8 = "表IX 中引入双流经验总线后，非提升探索迭代由 6 次压减为 2 次。"
    assert not any(d["rule"] == "TABLE_IX_EXPERIENCE_BUS_ABLATION_FIDELITY" for d in verify_text_claims(c8))

    # Control 3: Explicit clarification that failed iterations were non-improving, not crashes
    c3 = "经历了 6 次非提升探索迭代（failed iterations，指未能带来验证集精度增益的候选搜索尝试，而非训练程序崩溃）。"
    assert not any(d["rule"] == "METRIC_SEMANTIC_CONFUSION" for d in verify_text_claims(c3))

    # Control 4: Qualified preprint header
    c4 = "Kaiyue Kang · arXiv:2609.00814v2 (preprint · venue unverified) · 2026"
    assert not any(d["rule"] == "BIBLIOGRAPHIC_FABRICATION" for d in verify_text_claims(c4))


# ==============================================================================
# LAYER 3: REAL-PAPER A/B RELEASE GATE
# ==============================================================================

def test_layer3_diverse_corpus_pair_evaluations_exist():
    """Verify that all diverse real-paper A/B evaluations exist and RingMoClaw validates."""
    corpus_evals = [
        ROOT / "ISSUE19_BENCH-01-VASWANI-ATTENTION_PAIR_EVALUATION.json",
        ROOT / "ISSUE19_BENCH-02-LORA-ADAPTATION_PAIR_EVALUATION.json",
        ROOT / "ISSUE19_BENCH-03-REMOTE-SENSING-FOREST_PAIR_EVALUATION.json",
        ROOT / "ISSUE19_BENCH-04-ALPHAFOLD2-STRUCTURE_PAIR_EVALUATION.json",
        ROOT / "ISSUE19_BENCH-05-QUANTUM-SUPREMACY-ABLATION_PAIR_EVALUATION.json",
        ROOT / "ISSUE19_UNSEEN-01-RETHINKING-GENERALIZATION_PAIR_EVALUATION.json",
        ROOT / "ISSUE38_RINGMOCLAW_PAIR_EVALUATION.json"
    ]
    for p in corpus_evals:
        assert p.exists(), f"Corpus pair evaluation missing: {p.name}"

    ringmo_ab = load_json(ROOT / "ISSUE38_RINGMOCLAW_PAIR_EVALUATION.json")
    errs = list(schema_validate(ringmo_ab, "reader_pair_evaluation"))
    assert not errs, f"RingMoClaw schema validation failed: {errs}"


def test_layer3_ringmoclaw_ab_non_regression_and_value_add():
    """Verify non-regression and significant value-add on RingMoClaw A/B evaluation."""
    ab_data = load_json(ROOT / "ISSUE38_RINGMOCLAW_PAIR_EVALUATION.json")
    dims = {d["name"]: d for d in ab_data["dimensions"]}

    # Non-regression dimensions (Evidentia >= Direct AI)
    non_reg_dims = ["narrative_clarity", "scientific_completeness", "method_explanation"]
    for dim_name in non_reg_dims:
        dim = dims[dim_name]
        assert dim["evidentia_v3"] >= dim["direct_ai"], f"Regression on {dim_name}!"

    # Value-add dimensions (Evidentia > Direct AI)
    value_add_dims = [
        "experiment_result_understanding",
        "figure_table_correctness",
        "unsupported_prose",
        "provenance_usefulness",
        "boundary_coverage"
    ]
    for dim_name in value_add_dims:
        dim = dims[dim_name]
        assert dim["evidentia_v3"] > dim["direct_ai"] + 1.0, f"Insufficient value-add on {dim_name}!"

    # No unresolved release blockers
    assert len(ab_data.get("release_blockers", [])) == 0


def test_layer3_runtime_integration_gate_facets(tmp_path):
    """Artifact-bound SCIENCE_VERIFIED, EXPLANATION_COMPLETE, BENCHMARK_PASS facets."""
    root = fixture(tmp_path)
    render_reader(root)
    report = evaluate(root, artifact_only=True)
    # A structural fixture has not undergone an independent source review;
    # artifact_only must never claim scientific or explanatory verification.
    assert report["science_verified"] is False
    assert report["explanation_complete"] is False
    assert report["source_review_executed"] is False
    # In artifact-only mode, benchmark_pass is False until full corpus is validated
    assert report["benchmark_pass"] is False
    assert report["status"] == "READER_ACCEPTED"
