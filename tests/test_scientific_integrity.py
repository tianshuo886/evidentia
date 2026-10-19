"""Paper-independent scientific prose checks and unverified dynamic ledgers."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scientific_claim_verifier import verify_text_claims, build_claim_ledger_for_manuscript, verify_reader_scientific_integrity
from validate_common import load_json, schema_validate


BAD_READER = "该方法彻底消除了所有预测错误。消融证明了模块的绝对必要性。准确率增加了2个百分比。【科学核验通过】"
CORRECTED_READER = "固定预算的实验显示准确率由60%提高到62%，即增加2个百分点。该模块在当前任务下有效缓解误差，但并不能证明其绝对必要性。"


def scientific_manuscript(text):
    return {"schema_version": "3.0", "paper_id": "synthetic-science", "source_sha256": "b" * 64,
            "document": {"title": "Synthetic controlled study", "paper_meta": {
                "authors": ["A. Researcher"], "venue": "Synthetic preprint", "venue_verified_externally": False},
                "sections": [{"id": "controlled-results", "title": "Controlled results", "blocks": [
                    {"type": "paragraph", "text": text, "page": 2, "evidence_refs": ["T01"]}]}]}}


def test_defective_reader_fails_gate_with_concrete_reasons(tmp_path):
    diagnostics = verify_text_claims(BAD_READER)
    assert {"UNJUSTIFIED_CERTAINTY_OVERCLAIM", "UNJUSTIFIED_CAUSALITY_OVERCLAIM",
            "PERCENTAGE_VS_POINTS_CONFUSION", "AUDIT_VOCABULARY_LEAKAGE"} <= {d["rule"] for d in diagnostics}
    assert all(d.get("patch_instruction") and d.get("anchor") for d in diagnostics)
    ledger, errors = verify_reader_scientific_integrity(tmp_path, scientific_manuscript(BAD_READER))
    assert errors
    assert ledger["verification_summary"]["diagnostics"]


def test_corrected_reader_passes_prose_checks_without_claiming_source_verification(tmp_path):
    assert verify_text_claims(CORRECTED_READER) == []
    ledger, errors = verify_reader_scientific_integrity(tmp_path, scientific_manuscript(CORRECTED_READER))
    assert errors == []
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert ledger["verification_summary"]["supported"] == 0


@pytest.mark.parametrize("bad,rule", [
    ("该分类器绝对保证预测正确。", "UNJUSTIFIED_CERTAINTY_OVERCLAIM"),
    ("消融证实了模块不可替代性。", "UNJUSTIFIED_CAUSALITY_OVERCLAIM"),
    ("准确率提高了3个百分比。", "PERCENTAGE_VS_POINTS_CONFUSION"),
    ("【门禁检查通过】该实验结果可靠。", "AUDIT_VOCABULARY_LEAKAGE"),
    ("Lead Writer 要求将该结论直接发布。", "AUDIT_VOCABULARY_LEAKAGE"),
])
def test_adversarial_mutations_fail_closed(bad, rule):
    matched = [d for d in verify_text_claims(bad) if d["rule"] == rule]
    assert matched
    assert matched[0]["severity"] == "P0_BLOCKER"
    assert matched[0]["verdict"] == "CONTRADICTED"


@pytest.mark.parametrize("text", [
    "实验并不能绝对保证在新任务上的准确率。",
    "消融不足以证明模块绝对必要性。",
    "准确率从60%提高至63%，即增加3个百分点。",
    "读者独立评估：该设计在其他领域的表现仍待验证。",
])
def test_calibrated_non_failure_controls(text):
    assert verify_text_claims(text) == []


def test_atomic_claim_ledger_schema_and_integrity_without_source_pdf(tmp_path):
    ledger, errors = verify_reader_scientific_integrity(tmp_path, scientific_manuscript(CORRECTED_READER))
    assert errors == []
    saved = load_json(tmp_path / "model/claim_ledger.json")
    assert saved == ledger
    assert list(schema_validate(saved, "claim_ledger")) == []
    assert saved["verification_summary"]["status"] == "NEEDS_REVIEW"
    assert saved["verification_summary"]["contradicted"] == 0
    assert saved["claims"]
    assert all(c["verdict"] == "UNVERIFIED" and not c["attribution"]["source_confirmed"] for c in saved["claims"])
    assert all("p.2" in c["source_anchors"] and "T01" in c["evidence_refs"] for c in saved["claims"])
    assert not (tmp_path / "source/paper.pdf").exists()


def test_unresolved_and_independent_claims_keep_epistemic_categories(tmp_path):
    manuscript = scientific_manuscript("独立评估认为当前实验存在预算权衡，需要在更多任务上验证。评测脚本未公开，因此63%的统计口径仍待验证。")
    manuscript["document"]["sections"][0]["blocks"][0]["type"] = "takeaway"
    ledger = build_claim_ledger_for_manuscript(tmp_path, manuscript)
    categories = {c["epistemic_category"] for c in ledger["claims"]}
    assert {"READER_ASSESSMENT", "UNRESOLVED"} <= categories
    assert any(c["attribution"]["attributed_to"] == "EVIDENTIA_INDEPENDENT" for c in ledger["claims"])
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"


def test_empty_candidate_set_is_not_source_verified(tmp_path):
    ledger = build_claim_ledger_for_manuscript(tmp_path, scientific_manuscript("A short description."))
    assert ledger["verification_summary"]["status"] != "PASS"
    assert ledger["verification_summary"]["supported"] == 0
    assert all(not c["attribution"]["source_confirmed"] for c in ledger["claims"])
