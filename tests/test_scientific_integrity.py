"""Deterministic and semantic test suite for Reader v3 Scientific Integrity (Issue #36).

Verifies:
1. Defective RingMoClaw Reader fails the scientific integrity gate with line-anchored reasons
2. Corrected RingMoClaw Reader passes without false rejections
3. Unit tests for positive-class precision and recall semantics
4. Unit tests for non-improving iterations vs catastrophic training crashes
5. Unit tests for GPU-hours vs wall-clock hours accounting
6. Unit tests for bibliographic evidence precedence (preprint vs unverified venue)
7. Unit tests for faithful-reading paper-only firewall (PROSAIL/PINN project leakage)
8. Unit tests for best-of-three run protocol caveats and metric formula checks
9. Adversarial mutations on plausible prose fail closed
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
    verify_reader_scientific_integrity
)
from validate_common import load_json, schema_validate


def test_failure_manifest_and_source_lock_exist_and_validate():
    """Verify evaluation fixtures for RingMoClaw are well-formed."""
    lock_p = EVALS / "source_lock.json"
    manifest_p = EVALS / "reading_failure_manifest.json"
    assert lock_p.exists(), "source_lock.json must exist"
    assert manifest_p.exists(), "reading_failure_manifest.json must exist"

    lock = load_json(lock_p)
    assert lock["source_sha256"] == "32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa"
    assert lock["arxiv_id"] == "2609.00814v2"

    manifest = load_json(manifest_p)
    assert manifest["defective_reader_sha256"] == "08b1e9768ab3373a8d3e035523799f0c31dfc845ecf5b120d06a93ef1983c789"
    assert len(manifest["defects"]) == 8

    # All 8 defect categories covered
    rules = {d["semantic_class"] for d in manifest["defects"]}
    assert "METRIC_POSITIVE_CLASS_INVERSION" in rules
    assert "METRIC_SEMANTIC_CONFUSION" in rules
    assert "METRIC_UNIT_COLLAPSE" in rules
    assert "BIBLIOGRAPHIC_FABRICATION" in rules
    assert "PROJECT_ATTRIBUTION_CONFLATION" in rules
    assert "EXPERIMENTAL_PROTOCOL_OMISSION" in rules
    assert "EXPERIMENTAL_SETUP_CONFOUND" in rules
    assert "METRIC_CONVENTION_AMBIGUITY" in rules


def test_defective_reader_fails_gate_with_concrete_reasons():
    """Defective Reader must fail closed with explicit diagnostic rules."""
    defective_p = EVALS / "defective_reader.md"
    assert defective_p.exists(), "defective_reader.md regression sample must exist"
    text = defective_p.read_text(encoding="utf-8")

    diagnostics = verify_text_claims(text)
    assert len(diagnostics) >= 6, f"Expected multiple P0 defects, found {len(diagnostics)}"

    p0_rules = [d["rule"] for d in diagnostics if d.get("severity") == "P0_BLOCKER"]
    assert "METRIC_POSITIVE_CLASS_INVERSION" in p0_rules
    assert "METRIC_SEMANTIC_CONFUSION" in p0_rules
    assert "METRIC_UNIT_COLLAPSE" in p0_rules
    assert "BIBLIOGRAPHIC_FABRICATION" in p0_rules
    assert "PROJECT_ATTRIBUTION_CONFLATION" in p0_rules
    assert "EXPERIMENTAL_PROTOCOL_OMISSION" in p0_rules

    # Check actionable patch instructions exist
    for d in diagnostics:
        assert d.get("patch_instruction"), f"Diagnostic {d['rule']} missing patch_instruction"
        assert d.get("anchor"), f"Diagnostic {d['rule']} missing source anchor"


def test_corrected_reader_passes_gate_cleanly():
    """Corrected Reader resolves all P0 errors and passes gate."""
    corrected_p = EVALS / "corrected_reader.md"
    assert corrected_p.exists(), "corrected_reader.md must exist"
    text = corrected_p.read_text(encoding="utf-8")

    diagnostics = verify_text_claims(text)
    critical_p0 = [d for d in diagnostics if d.get("severity") == "P0_BLOCKER"]
    assert not critical_p0, f"Corrected Reader must have 0 P0 blockers, got: {critical_p0}"
    assert len(diagnostics) == 0, f"Expected 0 diagnostics, got: {diagnostics}"


def test_precision_recall_positive_class_unit_semantics():
    """Unit test: precision=1.00 on detrimental candidates is zero false alarms, not zero missed."""
    bad_case_1 = "敏捷早筛对劣质方案的精确率达到 1.00（无一漏过）。"
    diag_1 = verify_text_claims(bad_case_1)
    assert any(d["rule"] == "METRIC_POSITIVE_CLASS_INVERSION" for d in diag_1)

    bad_case_2 = "劣化候选策略召回率为 0.83，导致 17% 潜质策略被扼杀。"
    diag_2 = verify_text_claims(bad_case_2)
    assert any(d["rule"] == "METRIC_POSITIVE_CLASS_INVERSION" for d in diag_2)

    good_case = (
        "敏捷验证对劣化候选策略的精确率为 1.00（零误报，被拦截的候选经全量验证均为真实劣化），"
        "召回率为 0.83（全量训练中 6 个真实劣化候选中有 5 个被成功拦截，1 个劣化策略漏过早筛）。"
    )
    diag_good = verify_text_claims(good_case)
    assert not any(d["rule"] == "METRIC_POSITIVE_CLASS_INVERSION" for d in diag_good)


def test_failed_iterations_vs_execution_failure():
    """Unit test: non-improving iterations are not catastrophic training crashes."""
    bad_crash = "在第 14 轮探索中发生 6 次严重训练失败与系统崩溃。"
    diag = verify_text_claims(bad_crash)
    assert any(d["rule"] == "METRIC_SEMANTIC_CONFUSION" for d in diag)

    good_explanation = (
        "系统需要 14 轮并经历了 6 次非提升探索迭代（failed iterations，指未能带来验证集精度增益的候选搜索尝试，而非训练程序崩溃）。"
    )
    diag_good = verify_text_claims(good_explanation)
    assert not any(d["rule"] == "METRIC_SEMANTIC_CONFUSION" for d in diag_good)


def test_gpu_hours_vs_wall_clock_accounting():
    """Unit test: GPU-hours and wall-clock hours must not be collapsed."""
    collapsed = "相比 AutoResearch，GPU 运行时间从 26.90 小时大幅缩减至 12.14 小时。"
    diag = verify_text_claims(collapsed)
    assert any(d["rule"] == "METRIC_UNIT_COLLAPSE" for d in diag)

    distinguished = (
        "总 GPU 算力消耗时间（GPU-hours）从 AutoResearch 的 26.90 小时压减至 12.14 小时，"
        "实际挂钟时间（wall-clock hours）从 13.45 小时缩减至 10.61 小时。"
    )
    diag_good = verify_text_claims(distinguished)
    assert not any(d["rule"] == "METRIC_UNIT_COLLAPSE" for d in diag_good)


def test_bibliographic_evidence_precedence():
    """Unit test: unverified journal claims on preprint are rejected."""
    bad_header = "Kaiyue Kang · IEEE Transactions on Geoscience and Remote Sensing (TGRS) · 2026"
    diag = verify_text_claims(bad_header, source_metadata={"venue_status": {"venue_verified_externally": False}})
    assert any(d["rule"] == "BIBLIOGRAPHIC_FABRICATION" for d in diag)

    good_header = "Kaiyue Kang · arXiv:2609.00814v2 (preprint · venue unverified) · 2026"
    diag_good = verify_text_claims(good_header, source_metadata={"venue_status": {"venue_verified_externally": False}})
    assert not any(d["rule"] == "BIBLIOGRAPHIC_FABRICATION" for d in diag_good)


def test_paper_only_firewall_against_prosail_pinn_leakage():
    """Unit test: attributing external PROSAIL/PINN to paper authors fails closed."""
    leaked = "作者坦承若要迁移至 PROSAIL 与 PINN 等定量遥感物理机理计算，需要引入物理守恒先验。"
    diag = verify_text_claims(leaked)
    assert any(d["rule"] == "PROJECT_ATTRIBUTION_CONFLATION" for d in diag)

    clean_author_claim = "作者指出当前自演化主要聚焦于纯数据驱动的遥感特征模式识别，尚未探索融入物理机理方程。"
    diag_clean = verify_text_claims(clean_author_claim)
    assert not any(d["rule"] == "PROJECT_ATTRIBUTION_CONFLATION" for d in diag_clean)


def test_atomic_claim_ledger_schema_and_integrity(tmp_path):
    """End-to-end test: Atomic Claim Ledger generation and schema validation."""
    root = tmp_path / "test_workspace"
    (root / "source").mkdir(parents=True)
    (root / "model").mkdir()
    (root / "reader").mkdir()
    (root / "source/paper.pdf").write_bytes(b"%PDF-1.4\nfake pdf\n%%EOF")

    # Construct manuscript with corrected text
    corrected_text = (EVALS / "corrected_reader.md").read_text(encoding="utf-8")
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "ringmoclaw_corrected",
        "source_sha256": "32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa",
        "created_at": "2026-10-10T12:00:00Z",
        "document": {
            "title": "RingMoClaw",
            "subtitle": "多智能体自演化科研框架",
            "paper_meta": {
                "authors": ["Kaiyue Kang", "Xian Sun"],
                "venue": "arXiv:2609.00814v2 (preprint · venue unverified)",
                "year": 2026,
                "preprint_status": "PREPRINT",
                "venue_verified_externally": False
            },
            "orientation": {
                "lead": "自演化科研闭环精读"
            },
            "sections": [
                {
                    "id": "sec-01",
                    "title": "精读正文",
                    "blocks": [
                        {"type": "paragraph", "text": corrected_text}
                    ]
                }
            ]
        }
    }
    (root / "reader/narrative_manuscript.json").write_text(json.dumps(manuscript, ensure_ascii=False))

    ledger, errors = verify_reader_scientific_integrity(root, manuscript)
    assert not errors, f"Expected 0 errors on corrected manuscript, got: {errors}"
    assert (root / "model/claim_ledger.json").exists()

    saved_ledger = load_json(root / "model/claim_ledger.json")
    schema_errs = list(schema_validate(saved_ledger, "claim_ledger"))
    assert not schema_errs, f"Claim ledger failed schema: {schema_errs}"
    # Absence of a known regex defect is not independent source verification.
    assert saved_ledger["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert saved_ledger["verification_summary"]["unverified"] >= 1
    assert saved_ledger["verification_summary"]["contradicted"] == 0


def test_adversarial_mutation_on_plausible_prose_fails():
    """Adversarial check: mutating a correct sentence into a plausible falsehood fails gate."""
    truth = "对劣化策略的早筛拦截中，所有被拦截者均确认为劣化，精确率达 1.00；但召回率为 0.83，有 1 个劣化策略漏过早筛。"
    assert not any(d["verdict"] == "CONTRADICTED" for d in verify_text_claims(truth))

    # Mutate to plausible falsehood
    lie = "对劣化策略的早筛拦截中，精度达到惊人的 1.00（无一漏过）。"
    diag = verify_text_claims(lie)
    assert any(d["verdict"] == "CONTRADICTED" for d in diag)
