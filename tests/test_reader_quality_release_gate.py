"""Synthetic structural checks cannot substitute for a fresh source-bound release."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reader_acceptance
from reader_acceptance import evaluate, validate_corpus_or_release_report
from scientific_claim_verifier import verify_text_claims
from render_paper_reader import render_paper_reader_html, render_paper_reader_md
from validate_common import schema_validate
from test_reader_delivery_integrity import delivery_manuscript
from test_scientific_integrity import BAD_READER, CORRECTED_READER


def synthetic_pair():
    return {"schema_version": "1.0", "paper_id": "synthetic-comparison", "source_sha256": "c" * 64,
            "dimensions": [{"name": name, "direct_ai": 2, "evidentia_v3": 4,
                            "evidence_note": "Synthetic schema example, not an empirical benchmark."}
                           for name in ("narrative_clarity", "scientific_completeness", "method_explanation",
                                        "figure_table_correctness", "provenance_usefulness")],
            "qualitative_notes": "Schema-only fixture; never release evidence.", "release_blockers": []}


def test_layer1_schema_and_receipt_invariants():
    pair = synthetic_pair()
    assert list(schema_validate(pair, "reader_pair_evaluation")) == []
    pair["dimensions"][0]["evidentia_v3"] = 6
    assert list(schema_validate(pair, "reader_pair_evaluation"))


def test_layer1_evidence_reference_truthful_resolution(tmp_path):
    manuscript = delivery_manuscript(tmp_path)
    blocks = manuscript["document"]["sections"][0]["blocks"]
    bound = {b["evidence_id"] for b in blocks if b.get("evidence_id")}
    cited = {ref for b in blocks for ref in b.get("evidence_refs", []) if re.fullmatch(r"[FT]\d{2}", ref)}
    assert cited == bound == {"F01", "T01"}
    html = render_paper_reader_html(manuscript, tmp_path)
    md = render_paper_reader_md(manuscript, tmp_path)
    for eid in cited:
        assert f'id="evidence-{eid}"' in html or f"id='evidence-{eid}'" in html
        assert eid in md


def test_layer2_defective_reader_fails_and_corrected_control_passes():
    assert any(d["severity"] == "P0_BLOCKER" for d in verify_text_claims(BAD_READER))
    assert verify_text_claims(CORRECTED_READER) == []


@pytest.mark.parametrize("cached_status", ["PASS", "BENCHMARK_PASS", "PAPER_COMPLETE"])
def test_layer3_cached_pair_benchmark_cannot_authorize_release(tmp_path, cached_status):
    cached = synthetic_pair()
    cached.update(status=cached_status, benchmark_pass=True, release_ready=True)
    path = tmp_path / "cached_pair.json"
    path.write_text(json.dumps(cached))
    errors = validate_corpus_or_release_report(path)
    assert errors, "A cached schema-only scorecard must never authorize release"


def test_cross_paper_report_is_optional_for_single_paper_release():
    # A cross-paper comparison qualifies a skill change; it is not required for
    # every paper reading. The current paper must still pass source_review in
    # release_gate.
    assert validate_corpus_or_release_report(None) == []


def accepted_structural_report():
    return {"status": "READER_ACCEPTED", "errors": [], "diagnostics": [],
            "science_verified": True, "explanation_complete": True,
            "benchmark_pass": False, "release_ready": False}


def test_layer3_artifact_only_cannot_claim_science_or_release(tmp_path, monkeypatch):
    # Isolate release-policy logic from PDF rendering. The lower gate's synthetic
    # result is deliberately optimistic; artifact-only must still revoke facets.
    monkeypatch.setattr(reader_acceptance, "_evaluate_artifact", lambda *a, **kw: accepted_structural_report())
    monkeypatch.setattr(reader_acceptance, "bindings", lambda root: {})
    report = evaluate(tmp_path, artifact_only=True)
    assert report["status"] == "READER_ACCEPTED"
    assert report["science_verified"] is False
    assert report["explanation_complete"] is False
    assert report["benchmark_pass"] is False
    assert report["release_ready"] is False
    assert report["source_review_executed"] is False
    assert not (tmp_path / "source/paper.pdf").exists()


def test_layer3_cached_benchmark_cannot_promote_structural_acceptance(tmp_path, monkeypatch):
    monkeypatch.setattr(reader_acceptance, "_evaluate_artifact", lambda *a, **kw: accepted_structural_report())
    monkeypatch.setattr(reader_acceptance, "bindings", lambda root: {})
    cached = tmp_path / "cached_pair.json"
    cached.write_text(json.dumps({**synthetic_pair(), "status": "PASS", "benchmark_pass": True}))
    report = evaluate(tmp_path, regression_report=cached)
    assert report["status"] == "NEEDS_REVIEW"
    assert report["release_ready"] is False
    assert report["benchmark_pass"] is False
    assert any(d["gate"] == "regression" for d in report["diagnostics"])
    assert report["errors"]
