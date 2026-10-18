#!/usr/bin/env python3
"""Independent source review of the final Reader (Issue #46).

This is the replacement for "extract up to 12 claims and default to SUPPORTED".
It produces a task packet that asks a strong model to compare the *final* Chinese
Reader against the *original* PDF, with the source figures and equations in
front of it, and to report only the issues that actually matter.

Design constraints taken directly from #46:

* No fixed checklist and no per-sentence ledger. The reviewer chooses what to
  examine based on what this particular paper claims.
* No default approval. Every issue starts from UNVERIFIED; only an explicit
  comparison may raise it to SUPPORTED.
* Coverage must not be silently truncated. There is no claim cap and no
  "first two sentences of each block" rule.
* The reviewer may find errors nobody anticipated; the packet must not
  enumerate expected wrong answers, and no paper-specific regex is involved.
* Mechanism sufficiency is a first-class concern: a Reader can be factually
  clean and still explain nothing.

Output contract (`schemas/source_review.schema.json`) is deliberately small:
a verdict, the source locator, the Reader locator, and a revision request.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, sha256  # noqa: E402

TASK_ID = "TASK-V3-SOURCE-REVIEW"
TASK_TYPE = "SOURCE_REVIEW"
TARGET_OUTPUT = "reader/source_review.json"

VERDICTS = ("SUPPORTED", "QUALIFIED", "CONTRADICTED", "UNSUPPORTED", "UNVERIFIED", "UNRESOLVED")
ISSUE_KINDS = (
    "factual_contradiction",
    "unsupported_comparison",
    "dropped_condition",
    "wrong_equation",
    "causal_overreach",
    "misattribution",
    "mechanism_insufficient",
    "evidence_boundary_missing",
    "major_omission",
    "figure_misread",
)

INSTRUCTIONS = """\
You are an independent scientific reviewer. You did not write this Reader.

Your job: decide whether the FINAL Reader's substantive scientific statements are
supported by the ORIGINAL paper, and whether the Reader explains the paper's
mechanisms well enough to be worth reading. You are not a fact-checking script;
you are a sceptical reader of the same paper.

How to work
- Read the source PDF yourself. Use the page images, figure crops and equation
  crops provided; do not accept the Reader's description of a figure as evidence
  about that figure. If a crop is unreadable, say so instead of guessing.
- Choose your own reading path. Spend effort where this paper actually makes its
  case: its core contribution, its decisive figures/tables/equations, results
  with numbers attached, and any claim that changes how a reader would use the
  work. You do not have to cover every sentence, and you are not limited to any
  preset list of checkpoints.
- You may compare Reader against source directly, re-read around a suspicion,
  recompute a table value, put an equation beside its source crop, or look for
  evidence the Reader omitted. Use whichever is appropriate.
- You may find problems nobody anticipated. Report them.

What counts as an issue
- A substantive statement in the Reader that the source does not support, or
  contradicts (invented comparisons, invented numbers, wrong experimental
  groups, wrong method attributions, dropped residual/condition terms, wrong
  equation, causality stronger than the design allows).
- A figure the Reader interprets in a way the figure itself does not show.
- A mechanism the Reader only names. If stripping the adjectives leaves
  "A combined with B performs better" and that hides how the method actually
  works or what the decisive evidence is, that is a real defect.
- A material omission: a negative result, a key condition, an appendix detail
  that changes the interpretation.

What does NOT count
- Stylistic preference, length, section order, or tone.
- Missing detail on a point the paper itself does not discuss.
- Anything you cannot locate in the source. Say UNVERIFIED and say why.

Verdicts
- SUPPORTED    you compared it with the source and the source supports it
- QUALIFIED    the source supports it only with a condition the Reader omits
- CONTRADICTED the source says otherwise; this blocks release
- UNSUPPORTED  the source contains nothing that establishes it
- UNVERIFIED   you did not manage to check it; this is never an approval
- UNRESOLVED   the paper itself is ambiguous; the Reader should say so

Be honest about your own coverage. `coverage` records what you actually read and
what you skipped; a review that claims completeness it did not achieve is worse
than a narrow honest one.
"""


def _source_sha(root: Path) -> str:
    pdf = root / "source/paper.pdf"
    if not pdf.is_file():
        raise FileNotFoundError(f"missing source PDF: {pdf}")
    return sha256(pdf)


def build_task(root: Path) -> dict:
    """Assemble the source-review task packet for one paper workspace."""
    root = Path(root).resolve()
    manuscript_p = root / "reader/narrative_manuscript.json"
    html_p = root / "reader/paper_reader.html"
    if not manuscript_p.is_file():
        raise FileNotFoundError(f"missing final manuscript: {manuscript_p}")
    if not html_p.is_file():
        raise FileNotFoundError(f"missing rendered Reader: {html_p}")

    manifest_p = root / "model/lens_v3_manifest.json"
    memo_p = root / "model/revision_memo.json"
    plan_p = root / "model/narrative_plan.json"

    return {
        "task_id": TASK_ID,
        "task_type": TASK_TYPE,
        "required_capability": "INDEPENDENT_SOURCE_REVIEW",
        "description": (
            "Independent scientific review of the final Reader against the original paper. "
            "Open-ended: the reviewer decides what to examine."
        ),
        "scientific_contract": (
            "Compare the final Reader with the primary source. Report substantive "
            "contradictions, unsupported comparisons, dropped conditions, wrong "
            "equations, overreach, misattribution, insufficient mechanism explanation, "
            "and material omissions. Never mark something SUPPORTED without comparing it."
        ),
        "instructions": INSTRUCTIONS,
        "input_artifacts": {
            "source_pdf": "source/paper.pdf",
            "source_pages": "source_pages/",
            "figure_inventory": "model/figure_inventory.json",
            "figure_crops": "assets/figures/",
            "equation_crops": "assets/equations/",
            "final_manuscript": "reader/narrative_manuscript.json",
            "final_reader_html": "reader/paper_reader.html",
            **({"revision_memo": "model/revision_memo.json"} if memo_p.is_file() else {}),
            **({"narrative_plan": "model/narrative_plan.json"} if plan_p.is_file() else {}),
            **({"lens_manifest": "model/lens_v3_manifest.json"} if manifest_p.is_file() else {}),
        },
        "allowed_inputs": [
            "source/",
            "source_pages/",
            "assets/",
            "reader/narrative_manuscript.json",
            "reader/paper_reader.html",
            "model/figure_inventory.json",
            "model/revision_memo.json",
            "model/narrative_plan.json",
            "model/lens_v3_manifest.json",
        ],
        # The reviewer must not be primed by prior lens conclusions as authority,
        # and must not see the user's project.
        "forbidden_inputs": ["apply/", "project/", "memory/project/", "lens_v3/"],
        "prohibited_context": ["PROJECT_APPLY", "RESEARCH_MEMORY"],
        "constraints": ["INDEPENDENT", "NO_DEFAULT_APPROVAL", "NO_CLAIM_CAP"],
        "target_output": TARGET_OUTPUT,
        "output_schema": "source_review",
        "source_sha256": _source_sha(root),
        "base_sha256": sha256(manuscript_p),
        "contract_version": "3.0",
        "prompt_version": "3.0",
        "allowed_verdicts": list(VERDICTS),
        "allowed_issue_kinds": list(ISSUE_KINDS),
        "isolation_proof_required": True,
    }


def write_task(root: Path) -> Path:
    root = Path(root).resolve()
    task = build_task(root)
    path = root / "tasks/v3/source_review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def coverage_errors(review: dict) -> list[str]:
    """Reject reviews that claim to be complete without evidence of coverage."""
    errors: list[str] = []
    coverage = review.get("coverage") or {}
    sections = coverage.get("sections_read") or []
    if not sections:
        errors.append("source review does not record which Reader sections it read")
    if coverage.get("claimed_complete") and not coverage.get("skipped_sections_justification"):
        if coverage.get("skipped_sections"):
            errors.append(
                "source review claims complete coverage while skipping sections without justification"
            )
    for issue in review.get("issues") or []:
        verdict = str(issue.get("verdict") or "")
        if verdict not in VERDICTS:
            errors.append(f"source review issue has invalid verdict: {verdict!r}")
        if verdict == "SUPPORTED" and not (issue.get("source_locator") and issue.get("comparison")):
            errors.append(
                "source review marked an item SUPPORTED without a recorded source comparison"
            )
        if verdict in ("CONTRADICTED", "UNSUPPORTED") and not issue.get("reader_locator"):
            errors.append("source review reports a defect without locating it in the Reader")
    return errors


def blocking_issues(review: dict) -> list[dict]:
    """Issues that must be fixed before release."""
    return [
        issue
        for issue in review.get("issues") or []
        if str(issue.get("verdict")) == "CONTRADICTED"
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="Paper workspace")
    ap.add_argument("--check", action="store_true", help="Validate an existing review instead of creating a task")
    args = ap.parse_args()

    root = Path(args.out).resolve()
    if args.check:
        path = root / TARGET_OUTPUT
        if not path.is_file():
            print(json.dumps({"status": "NOT_RUN", "reason": f"missing {TARGET_OUTPUT}"}, ensure_ascii=False))
            return 1
        review = load_json(path)
        errors = coverage_errors(review)
        blocking = blocking_issues(review)
        status = "BLOCKED" if blocking else ("NEEDS_REVIEW" if errors else "PASS")
        print(json.dumps(
            {"status": status, "errors": errors, "blocking_issues": len(blocking)},
            indent=2, ensure_ascii=False,
        ))
        return 0 if status == "PASS" else 1

    path = write_task(root)
    print(json.dumps({"task": str(path), "task_id": TASK_ID}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
