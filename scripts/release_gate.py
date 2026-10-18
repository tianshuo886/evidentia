#!/usr/bin/env python3
"""Authoritative release decision for one paper workspace (Issue #49).

A run may render a Reader, but rendering is not release. This module is the one
place that answers "may this paper be delivered?" and it fails closed:

    NOT_RUN       no independent source/Reader review was executed
    BLOCKED       review ran and found unresolved critical contradictions
    NEEDS_REVIEW  review ran but acceptance gates still fail
    PASS          review ran, gates pass, and the release is bound to this build

The decision is written to `reader/READER_RELEASE_DECISION.md` so a human can
audit why a paper was or was not released. Historical benchmark JSON is never
sufficient: it can only support a cross-paper claim, never certify a new paper.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DECISIONS = ("NOT_RUN", "NEEDS_REVIEW", "BLOCKED", "PASS")
REVIEW_FILES = ("reader/semantic_review.json", "reader/visual_review.json")
SOURCE_REVIEW = "reader/source_review.json"


def _source_review_issues(root: Path) -> list[dict]:
    """Return blocking issues from the independent source review (#46)."""
    path = root / SOURCE_REVIEW
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [
        issue
        for issue in data.get("issues") or []
        if isinstance(issue, dict) and str(issue.get("verdict")) == "CONTRADICTED"
    ]


def _visual_receipt_errors(root: Path) -> list[str]:
    """Return problems with the visual-input receipt, if the Reader has figures."""
    receipt_p = root / "reader/visual_input_receipt.json"
    manuscript_p = root / "reader/narrative_manuscript.json"
    if not manuscript_p.is_file():
        return []
    try:
        manuscript = json.loads(manuscript_p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    has_figures = any(
        block.get("type") in ("figure", "table")
        for chapter in manuscript.get("document", {}).get("chapters", [])
        for block in chapter.get("blocks", [])
    )
    if not has_figures:
        return []
    if not receipt_p.is_file():
        return ["missing reader/visual_input_receipt.json"]
    try:
        receipt = json.loads(receipt_p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"unreadable visual receipt: {exc}"]
    from visual_receipt import receipt_errors

    return receipt_errors(receipt)


def _read_review_findings(root: Path) -> list[dict]:
    """Collect critical findings from whatever review packets exist."""
    findings: list[dict] = []
    for rel in REVIEW_FILES:
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in data.get("critical_findings") or []:
            if isinstance(item, dict):
                findings.append({"review": rel, **item})
            else:
                findings.append({"review": rel, "finding": str(item)})
    return findings


def _missing_reviews(root: Path) -> list[str]:
    return [rel for rel in REVIEW_FILES if not (root / rel).is_file()]


def _source_review_missing(root: Path) -> bool:
    return not (root / SOURCE_REVIEW).is_file()


def evaluate_release(
    root: Path,
    *,
    artifact_only: bool = False,
    regression_report: str | None = None,
) -> dict:
    """Return the release decision for a rendered workspace.

    `artifact_only` is for structural fixtures and can never return PASS.
    """
    from reader_acceptance import evaluate as evaluate_acceptance
    from execution_authenticity import audit_workspace

    root = Path(root)
    acceptance = evaluate_acceptance(
        root, artifact_only=artifact_only, regression_report=regression_report
    )
    missing = _missing_reviews(root)
    findings = _read_review_findings(root)
    source_blocking = _source_review_issues(root)
    source_missing = _source_review_missing(root)

    # A workspace assembled from fixtures or hand-authored envelopes is not a
    # scientific result, however good its artifacts look (Issue #47).
    authenticity = audit_workspace(root)
    fabricated = not authenticity["real_execution_verified"]

    # The Reader must prove it was actually shown the figures it describes (#45).
    visual = _visual_receipt_errors(root)

    if artifact_only:
        decision = "NEEDS_REVIEW"
        reason = "artifact-only evaluation certifies structure, never scientific release"
    elif fabricated:
        decision = "NOT_RUN"
        gaps = authenticity["missing_real_execution"] or ["no agent runs recorded"]
        reason = (
            "no verified real model execution for this workspace: missing "
            + ", ".join(gaps)
        )
    elif visual:
        decision = "BLOCKED"
        reason = "the Reader does not prove it was shown the figures it describes: " + visual[0]
    elif missing or source_missing:
        absent = list(missing) + ([SOURCE_REVIEW] if source_missing else [])
        decision = "NOT_RUN"
        reason = "independent source/Reader review was never executed: missing " + ", ".join(absent)
    elif source_blocking:
        decision = "BLOCKED"
        reason = (
            f"{len(source_blocking)} statement(s) in the Reader contradict the source paper"
        )
    elif findings:
        decision = "BLOCKED"
        reason = (
            f"{len(findings)} unresolved critical finding(s) in the source/Reader review"
        )
    elif acceptance.get("status") == "PAPER_COMPLETE":
        decision = "PASS"
        reason = "independent review executed, acceptance gates pass, release bound to this build"
    else:
        decision = "NEEDS_REVIEW"
        errors = acceptance.get("errors") or []
        reason = (
            f"{len(errors)} acceptance gate error(s) remain"
            if errors
            else "acceptance did not reach PAPER_COMPLETE"
        )

    return {
        "schema_version": "1.0",
        "decision": decision,
        "reason": reason,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_only": artifact_only,
        "real_execution_verified": authenticity["real_execution_verified"],
        "execution_counts": authenticity["counts"],
        "missing_reviews": missing + ([SOURCE_REVIEW] if source_missing else []),
        "critical_findings": findings + [
            {"review": SOURCE_REVIEW, **issue} for issue in source_blocking
        ],
        "acceptance": {
            "status": acceptance.get("status"),
            "errors": acceptance.get("errors") or [],
            "science_verified": acceptance.get("science_verified"),
            "explanation_complete": acceptance.get("explanation_complete"),
            "regression_passed": acceptance.get("regression_passed"),
            "implementation_sha256": acceptance.get("implementation_sha256"),
        },
    }


def _md_cell(value) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def render_decision_markdown(report: dict) -> str:
    """Render the decision as the short human-readable release note."""
    lines = [
        "# Reader Release Decision",
        "",
        f"- Decision: **{report['decision']}**",
        f"- Reason: {report['reason']}",
        f"- Generated: {report['generated_at']}",
        f"- Artifact-only: {report['artifact_only']}",
        f"- Real model execution verified: {report.get('real_execution_verified')}",
        f"- Execution classes: {report.get('execution_counts') or {}}",
        f"- Implementation SHA-256: `{report['acceptance'].get('implementation_sha256') or 'unknown'}`",
        "",
        "## Independent review",
        "",
    ]
    if report["missing_reviews"]:
        lines.append("Review packets were never produced for this paper:")
        lines.extend(f"- missing `{rel}`" for rel in report["missing_reviews"])
        lines.append("")
    else:
        lines.append("Both the semantic and visual review packets are present and hash-bound.")
        lines.append("")

    lines.extend(["## Unresolved critical findings", ""])
    if report["critical_findings"]:
        lines.append("| Review | Finding |")
        lines.append("| --- | --- |")
        for item in report["critical_findings"]:
            summary = (
                item.get("summary")
                or item.get("finding")
                or item.get("reader_quote")
                or item.get("message")
                or json.dumps(item, ensure_ascii=False)
            )
            lines.append(f"| {_md_cell(item.get('review'))} | {_md_cell(summary)} |")
    else:
        lines.append("None recorded.")
    lines.append("")

    lines.extend(["## Acceptance gates", ""])
    errors = report["acceptance"]["errors"]
    if errors:
        lines.extend(f"- {_md_cell(e)}" for e in errors)
    else:
        lines.append("All gates passed.")
    lines.append("")
    lines.extend(
        [
            "## Standing rule",
            "",
            "A rendered Reader is not a released Reader. `PASS` requires an executed,",
            "hash-bound independent review of this specific paper against its own source",
            "PDF. Historical A/B benchmark files document cross-paper regression only and",
            "never certify a newly generated paper.",
            "",
        ]
    )
    return "\n".join(lines)


def write_decision(root: Path, report: dict) -> Path:
    root = Path(root)
    out = root / "reader/READER_RELEASE_DECISION.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_decision_markdown(report), encoding="utf-8")
    json_out = root / "reader/reader_release_decision.json"
    json_out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--artifact-only", action="store_true")
    ap.add_argument("--regression-report")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    report = evaluate_release(
        Path(args.out),
        artifact_only=args.artifact_only,
        regression_report=args.regression_report,
    )
    if not args.no_write:
        write_decision(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
