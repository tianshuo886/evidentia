"""Targeted regressions for P0 source-review fail-closed fixes (#45–#49).

These fixtures test software contracts only. They do NOT claim a real
multimodal model or independent scientist reviewed a paper.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from reader_acceptance import _evaluate_artifact, evaluate, validate_corpus_or_release_report
from render_reader import render_reader
from scientific_claim_verifier import (
    build_claim_ledger_for_manuscript, extract_dynamic_claims_from_manuscript
)
from test_gates import fixture


def test_missing_source_and_visual_reviews_block_release(tmp_path):
    root = fixture(tmp_path)
    render_reader(root)
    result = _evaluate_artifact(root, artifact_only=False)
    assert result["status"] == "NEEDS_REVIEW"
    assert result["scientific_integrity"] is False
    assert result["visual_review"] == "NEEDS_REVIEW"
    assert any("missing semantic_review.json" in err for err in result["errors"])
    assert any("missing visual_review.json" in err for err in result["errors"])


def test_artifact_fixture_cannot_claim_scientific_review(tmp_path):
    root = fixture(tmp_path)
    render_reader(root)
    result = evaluate(root, artifact_only=True)
    assert result["release_ready"] is False
    assert result["science_verified"] is False
    assert result["source_review_executed"] is False
    assert result["status"] in ("READER_ACCEPTED", "NEEDS_REVIEW")


def test_historical_pair_scores_cannot_replace_fresh_release_evidence():
    errors = validate_corpus_or_release_report()
    assert errors and "fresh real-corpus release report" in errors[0]


def test_unseen_claim_extraction_has_no_twelve_claim_cutoff(tmp_path):
    manuscript = {
        "paper_id": "unknown_case", "source_sha256": "0" * 64,
        "document": {"title": "Unseen empirical paper",
                     "sections": [
                         {"id": f"s{i}", "title": f"Section {i}", "blocks": [
                             {"type": "takeaway",
                              "text": (
                                  "第一种观察指标提升了百分之五但缺少重复实验。"
                                  "第二种条件下的反例显示结论并不稳定。"
                                  "第三种对照在另一个设置中提升了三个百分点。"
                              )}
                         ]} for i in range(1, 8)
                     ]}
    }
    ledger = build_claim_ledger_for_manuscript(tmp_path, manuscript)
    assert len(ledger["claims"]) > 12
    assert any("s7" in c["boundaries"][0] for c in ledger["claims"])
    assert all(c["attribution"]["source_confirmed"] is False for c in ledger["claims"])
    assert all(c["verdict"] != "SUPPORTED" for c in ledger["claims"])
    assert ledger["verification_summary"]["status"] == "NEEDS_REVIEW"


def test_empty_diagnostic_anchor_is_not_automatic_contradiction(tmp_path):
    manuscript = {
        "document": {"title": "Unknown", "sections": [
            {"id": "late", "blocks": [
                {"type": "takeaway",
                 "text": "这一观察与控制变量之间具有明确联系但尚需正式源文核对。"}
            ]}
        ]}
    }
    results = extract_dynamic_claims_from_manuscript(
        tmp_path, manuscript,
        [{"anchor": "", "offending_span": "", "verdict": "CONTRADICTED",
          "severity": "P0_BLOCKER"}]
    )
    assert len(results) == 1
    assert results[0]["verdict"] == "UNVERIFIED"
