"""Issue #13 release-gate regression coverage."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reader_acceptance import evaluate
from reader_regression import validate_release_report


def test_real_corpus_report_revalidates_to_pass():
    report = ROOT / "evals/reader_regression/release_report.json"
    assert validate_release_report(report) == []


def test_artifact_acceptance_cannot_promote_without_bound_regression_report():
    run = ROOT / "evals/reader_regression/runs_v2/1706.03762"
    artifact = evaluate(run, artifact_only=True)
    assert artifact["status"] == "READER_ACCEPTED"
    assert artifact["release_ready"] is False
    full = evaluate(run, regression_report=ROOT / "evals/reader_regression/missing-release-report.json")
    assert full["status"] == "NEEDS_REVIEW"
    assert any("release report" in error for error in full["errors"])


def test_release_report_hash_mismatch_is_refused(tmp_path):
    source = ROOT / "evals/reader_regression/release_report.json"
    tampered = tmp_path / "release_report.json"
    payload = json.loads(source.read_text())
    payload["implementation_sha256"] = "0" * 64
    tampered.write_text(json.dumps(payload))
    errors = validate_release_report(tampered)
    assert any("implementation hash mismatch" in error for error in errors)
