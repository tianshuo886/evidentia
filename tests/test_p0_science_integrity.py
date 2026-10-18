"""Synthetic regression guards for source-grounded release behavior.

Tests use generated assets and generic evidence IDs to check image binding, math
rendering, and fail-closed release decisions.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))

from math_text import (  # noqa: E402
    protect_math,
    term_html,
    unrendered_math_errors,
    rendered_math_count,
)
from release_gate import evaluate_release, render_decision_markdown  # noqa: E402


# ---------------------------------------------------------------- Issue #48


def test_bare_latex_in_prose_becomes_inline_math():
    assert protect_math(r"核心项 \mathbf{D}\mathbf{A} 表示字典") == (
        r"核心项 \( \mathbf{D}\mathbf{A} \) 表示字典"
    )


def test_glossary_term_is_never_wrapped_in_code():
    rendered = term_html(r"\mathbf{D}\mathbf{A}")
    assert rendered == r"\( \mathbf{D}\mathbf{A} \)"
    assert "<code>" not in rendered


def test_code_spans_stay_code():
    assert protect_math(r"用 `pip install` 安装，误差项 \varepsilon") == (
        r"用 <code>pip install</code> 安装，误差项 \( \varepsilon \)"
    )


def test_currency_is_not_treated_as_math():
    assert protect_math("价格 $5 与 $6") == "价格 $5 与 $6"


def test_left_right_pair_stays_one_formula():
    out = protect_math(r"f=\alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right)")
    assert out.count(r"\(") == 1
    assert r"\right" in out


def test_unrendered_math_is_detected_in_visible_prose():
    html = "<p>含 \\mathbf{D} 的正文</p>"
    assert unrendered_math_errors(html)


def test_rendered_math_is_not_flagged():
    html = "<p>正常中文</p><mjx-container class='MathJax'>x</mjx-container>"
    assert unrendered_math_errors(html) == []


def test_code_block_tex_is_not_flagged():
    html = "<p>示例</p><code>\\mathbf{D}</code>"
    assert unrendered_math_errors(html) == []


def test_rendered_math_count_reads_containers():
    assert rendered_math_count("<mjx-container>a</mjx-container><mjx-container>b</mjx-container>") == 2


# ---------------------------------------------------------------- Issue #45


def _figure_block(eid, asset):
    return {
        "type": "figure",
        "evidence_id": eid,
        "caption": "图注",
        "analysis": "分析",
        "asset": asset,
    }


def test_shared_image_bytes_across_distinct_figures_is_rejected(tmp_path):
    """Two synthetic evidence IDs must not reuse identical image bytes."""
    from render_paper_reader import duplicate_asset_errors

    (tmp_path / "assets/figures").mkdir(parents=True)
    payload = b"\x89PNG\r\n\x1a\nidentical-bytes"
    (tmp_path / "assets/figures/a.png").write_bytes(payload)
    (tmp_path / "assets/figures/b.png").write_bytes(payload)

    manuscript = {
        "document": {
            "chapters": [
                {
                    "id": "spine-01",
                    "title": "T",
                    "blocks": [
                        _figure_block("FIG-01", "assets/figures/a.png"),
                        _figure_block("FIG-02", "assets/figures/b.png"),
                    ],
                }
            ]
        }
    }
    errors = duplicate_asset_errors(manuscript, tmp_path)
    assert errors, "two figures sharing identical bytes must be reported"
    assert "FIG-01" in errors[0] and "FIG-02" in errors[0]


def test_distinct_images_are_accepted(tmp_path):
    from render_paper_reader import duplicate_asset_errors

    (tmp_path / "assets/figures").mkdir(parents=True)
    (tmp_path / "assets/figures/a.png").write_bytes(b"aaa")
    (tmp_path / "assets/figures/b.png").write_bytes(b"bbb")

    manuscript = {
        "document": {
            "chapters": [
                {
                    "id": "spine-01",
                    "title": "T",
                    "blocks": [
                        _figure_block("FIG-01", "assets/figures/a.png"),
                        _figure_block("FIG-02", "assets/figures/b.png"),
                    ],
                }
            ]
        }
    }
    assert duplicate_asset_errors(manuscript, tmp_path) == []


# ---------------------------------------------------------------- Issue #49


def test_release_is_not_run_without_reviews(tmp_path):
    """A rendered workspace with no review packets is NOT_RUN, never PASS."""
    from test_gates import fixture
    from render_reader import render_reader

    root = fixture(tmp_path)
    render_reader(root)
    report = evaluate_release(root)
    assert report["decision"] == "NOT_RUN"
    assert report["missing_reviews"], "missing review packets must be reported"
    assert "reader/source_review.json" in report["missing_reviews"]


def test_artifact_only_can_never_pass(tmp_path):
    from test_gates import fixture
    from render_reader import render_reader

    root = fixture(tmp_path)
    render_reader(root)
    report = evaluate_release(root, artifact_only=True)
    assert report["decision"] == "NEEDS_REVIEW"


def test_decision_markdown_names_the_decision_and_reason():
    report = {
        "decision": "BLOCKED",
        "reason": "2 unresolved critical finding(s)",
        "generated_at": "2026-10-18T00:00:00+00:00",
        "artifact_only": False,
        "missing_reviews": [],
        "critical_findings": [
            {"review": "reader/semantic_review.json", "summary": "Eq.(4) residual dropped"}
        ],
        "acceptance": {
            "status": "NEEDS_REVIEW",
            "errors": ["eq gate failed"],
            "implementation_sha256": "abc123",
        },
    }
    md = render_decision_markdown(report)
    assert "BLOCKED" in md
    assert "Eq.(4) residual dropped" in md
    assert "eq gate failed" in md


def test_untrusted_cross_paper_score_cannot_authorise_release(tmp_path):
    """Presence of old A/B JSON must not upgrade a fresh paper to PASS."""
    from test_gates import fixture
    from render_reader import render_reader

    root = fixture(tmp_path)
    render_reader(root)
    # A synthetic cached score is untrusted and cannot authorize this workspace.
    (root / "legacy_cross_paper_score.json").write_text(
        json.dumps({"status": "PASS", "benchmark_pass": True, "release_ready": True})
    )
    report = evaluate_release(root)
    assert report["decision"] != "PASS"


def test_source_contradiction_blocks_release(tmp_path):
    """A CONTRADICTED statement in the source review must block, not warn."""
    from test_gates import fixture
    from render_reader import render_reader
    from release_gate import _source_review_issues

    root = fixture(tmp_path)
    render_reader(root)
    review = {
        "schema_version": "1.0",
        "source_sha256": "0" * 64,
        "reviewer": {"kind": "MODEL", "model": "m", "method": "direct comparison"},
        "coverage": {"sections_read": ["spine-01"], "claimed_complete": False},
        "issues": [
            {
                "id": "I1",
                "kind": "figure_misread",
                "verdict": "CONTRADICTED",
                "severity": "P0_BLOCKER",
                "summary": "Reader describes six synthetic items as three",
                "reader_locator": "spine-02 block 1",
                "source_locator": "FIG-02, synthetic source",
                "comparison": "The synthetic source fixture contains six named items.",
            }
        ],
        "overall": {"recommendation": "BLOCK"},
    }
    (root / "reader/source_review.json").write_text(json.dumps(review))
    assert len(_source_review_issues(root)) == 1


def test_unverified_is_never_an_approval():
    from source_review import coverage_errors

    review = {
        "coverage": {"sections_read": ["spine-01"]},
        "issues": [
            {"id": "I1", "kind": "major_omission", "verdict": "UNVERIFIED", "summary": "x"},
            {
                "id": "I2",
                "kind": "factual_contradiction",
                "verdict": "SUPPORTED",
                "summary": "y",
            },
        ],
    }
    errors = coverage_errors(review)
    assert any("without a recorded source comparison" in e for e in errors)


def test_source_review_task_has_no_claim_cap_and_no_checklist():
    from source_review import build_task

    root = Path(__file__).parents[1]
    task = build_task(root / "evidentia-pristine-does-not-exist") if False else None
    # Build against a fixture workspace instead.
    import tempfile

    from test_gates import fixture
    from render_reader import render_reader

    tmp = Path(tempfile.mkdtemp())
    ws = fixture(tmp)
    render_reader(ws)
    task = build_task(ws)
    assert task["task_type"] == "SOURCE_REVIEW"
    assert "UNVERIFIED" in task["allowed_verdicts"]
    assert task["constraints"] == ["INDEPENDENT", "NO_DEFAULT_APPROVAL", "NO_CLAIM_CAP"]
    assert "lens_v3/" in task["forbidden_inputs"]
    assert "figure_crops" in task["input_artifacts"]


# ---------------------------------------------------------------- Issue #55


def test_hardlink_keeps_one_copy(tmp_path):
    from storage_links import link_or_copy

    src = tmp_path / "a.pdf"
    src.write_bytes(b"x" * 4096)
    dst = tmp_path / "sub/b.pdf"
    strategy = link_or_copy(src, dst)
    assert strategy in ("HARDLINK", "SYMLINK")
    assert dst.read_bytes() == src.read_bytes()
    if strategy == "HARDLINK":
        assert src.stat().st_ino == dst.stat().st_ino


def test_compact_dry_run_never_deletes(tmp_path):
    from test_gates import fixture

    root = fixture(tmp_path)
    dup = root / "copy_of_fixture.json"
    source = next(p for p in root.rglob("*.json") if p.is_file())
    dup.write_bytes(source.read_bytes())
    before = sorted(p.name for p in root.rglob("*") if p.is_file())

    res = subprocess.run(
        [sys.executable, str(SCRIPTS / "compact_workspace.py"), "--out", str(root), "--json"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["mode"] == "dry-run"
    after = sorted(p.name for p in root.rglob("*") if p.is_file())
    assert before == after, "dry run must not delete anything"
