#!/usr/bin/env python3
"""Real-paper, evidence-bearing regression gate. Never generates fake papers.

The manifest identifies external source PDFs, completed reading workspaces,
compact human-authored gold checklists, selected direct-AI/Kami comparisons,
and a post-implementation unseen paper. A partial corpus is NEEDS_REVIEW.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from reader_review import ROOT, bindings, implementation_hash, compact
from validate_common import load_json, sha256

DEFAULT_MANIFEST = ROOT / "evals/reader_regression/corpus.json"
DEFAULT_REPORT = ROOT / "evals/reader_regression/release_report.json"
CATEGORIES = {
    "method_heavy", "equation_heavy", "figure_heavy", "table_heavy",
    "empirical_benchmark", "mechanism_causal", "negative_anomaly",
    "ambiguous_weak_evidence", "nonstandard_narrative",
}
GOLD_FIELDS = ("central_question", "central_move", "decisive_evidence", "key_result",
               "justified_conclusion", "major_limit", "must_show_figures", "must_not_invent")
COMPARABLE = ("narrative_comprehension", "method_understanding", "experiment_understanding", "chinese_readability")
BETTER = ("provenance", "uncertainty", "visual_grounding", "auditability", "contradiction_anomaly_preservation")


def relative(base, path):
    if not isinstance(path, str) or not path:
        raise ValueError("manifest artifact path is missing")
    return (base / path).resolve()


def stamp(value):
    date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return date


def _gold_errors(base, entry, run, inputs):
    errors = []
    gold_path = relative(base, entry.get("gold"))
    if not gold_path.exists():
        return [f"missing human-authored gold checklist: {gold_path}"]
    inputs[str(gold_path)] = sha256(gold_path)
    gold = load_json(gold_path)
    author = gold.get("author") or {}
    if gold.get("status") != "APPROVED" or author.get("kind") != "HUMAN" or not author.get("name"):
        errors.append("gold checklist must be explicitly human-authored and approved; agent drafts do not qualify")
    if gold.get("source_sha256") != sha256(run / "source/paper.pdf"):
        errors.append("gold checklist source PDF hash mismatch")
    source = load_json(run / "model/source_map.json")
    valid_pages = {pg.get("number") for pg in source.get("pages", [])}
    for field in GOLD_FIELDS:
        item = (gold.get("checklist") or {}).get(field) or {}
        if not item.get("criterion") or not item.get("source_pages"):
            errors.append(f"gold checklist missing criterion/source_pages: {field}")
        elif any(page not in valid_pages for page in item["source_pages"]):
            errors.append(f"gold checklist has non-source page: {field}")
    review_path = run / "reader/gold_review.json"
    if not review_path.exists():
        errors.append("missing evidence-bearing gold checklist review")
        return errors
    inputs[str(review_path)] = sha256(review_path)
    review = load_json(review_path)
    if review.get("gold_sha256") != sha256(gold_path) or review.get("artifact_hashes") != bindings(run):
        errors.append("gold review is stale or bound to different artifacts")
    reviewer = review.get("reviewer") or {}
    if not reviewer.get("name") or reviewer.get("kind") not in ("HUMAN", "HOST_AGENT"):
        errors.append("gold review lacks identified reviewer")
    manuscript = load_json(run / "reader/narrative_manuscript.json")
    narrative = compact(" ".join(str(b.get(k, "")) for c in manuscript["document"]["chapters"] for b in c["blocks"] for k in ("text", "analysis", "explanation")))
    for field in GOLD_FIELDS:
        check = (review.get("checks") or {}).get(field) or {}
        quote = compact(check.get("reader_quote"))
        if check.get("verdict") != "PASS" or len(str(check.get("reason", ""))) < 20:
            errors.append(f"gold review did not substantiate {field}")
        if len(quote) < 12 or quote not in narrative:
            errors.append(f"gold review passage not recoverable: {field}")
    if review.get("critical_findings") != []:
        errors.append("gold review contains missing or unresolved critical findings")
    return errors


def _comparison_errors(base, entry, run, inputs):
    path = relative(base, entry.get("baseline_comparison"))
    if not path.exists():
        return [f"missing selected direct-AI/Kami baseline comparison: {path}"]
    inputs[str(path)] = sha256(path)
    comparison = load_json(path)
    errors = []
    if comparison.get("artifact_hashes") != bindings(run):
        errors.append("baseline comparison has stale Evidentia bindings")
    baseline = comparison.get("baseline") or {}
    if baseline.get("execution_kind") != "REAL_DIRECT_READ" or baseline.get("source_sha256") != sha256(run / "source/paper.pdf"):
        errors.append("baseline must be an actual direct source read of the same PDF, not a simulated summary")
    if not baseline.get("model") or not baseline.get("prompt"):
        errors.append("baseline lacks actual model and source-only prompt provenance")
    for field in ("html", "md", "pdf"):
        artifact = baseline.get(field) or {}
        file = relative(base, artifact.get("path"))
        if not file.exists() or artifact.get("sha256") != sha256(file):
            errors.append(f"baseline {field} artifact missing or hash mismatch")
        else:
            inputs[str(file)] = sha256(file)
    if not (comparison.get("reviewer") or {}).get("name"):
        errors.append("baseline comparison lacks a named reviewer")
    dimensions = comparison.get("dimensions") or {}
    for dimension in COMPARABLE + BETTER:
        item = dimensions.get(dimension) or {}
        allowed = ("COMPARABLE", "EVIDENTIA_BETTER") if dimension in COMPARABLE else ("EVIDENTIA_BETTER",)
        if item.get("verdict") not in allowed:
            errors.append(f"baseline comparison failed required dimension: {dimension}")
        if len(str(item.get("reason", ""))) < 30 or not item.get("baseline_passage") or not item.get("evidentia_passage"):
            errors.append(f"baseline comparison lacks paired evidence and rationale: {dimension}")
    return errors


def evaluate_corpus(manifest_path=DEFAULT_MANIFEST):
    from reader_acceptance import evaluate
    path = Path(manifest_path).resolve()
    base = path.parent
    errors = []
    inputs = {str(path): sha256(path)}
    manifest = load_json(path)
    entries = manifest.get("papers") or []
    development = [x for x in entries if x.get("split") == "development"]
    unseen = [x for x in entries if x.get("split") == "unseen"]
    if not 5 <= len(development) <= 10:
        errors.append("regression requires 5–10 real development papers")
    if not unseen:
        errors.append("regression requires at least one fresh unseen paper after implementation freeze")
    categories = {category for x in development for category in x.get("categories", [])}
    if not CATEGORIES.issubset(categories):
        errors.append(f"heterogeneous regression categories missing: {sorted(CATEGORIES - categories)}")
    if len({x.get("domain") for x in development if x.get("domain")}) < 3:
        errors.append("heterogeneous corpus must span at least three scientific domains")
    if len({x.get("id") for x in entries}) != len(entries):
        errors.append("regression corpus contains duplicate paper IDs")
    selected = [x for x in development if x.get("baseline_comparison")]
    if len(selected) < 2:
        errors.append("regression requires selected direct-AI/Kami comparisons on at least two papers")
    lock = None
    if manifest.get("implementation_freeze"):
        lock_path = relative(base, manifest["implementation_freeze"])
        if lock_path.exists():
            inputs[str(lock_path)] = sha256(lock_path)
            lock = load_json(lock_path)
    if not lock or lock.get("implementation_sha256") != implementation_hash():
        errors.append("regression requires a current implementation freeze before unseen evaluation")
    records = []
    source_hashes = set()
    for entry in entries:
        pid = entry.get("id", "<missing id>")
        item_errors = []
        record = {"id": pid, "split": entry.get("split"), "status": "NEEDS_REVIEW", "errors": item_errors}
        records.append(record)
        try:
            run = relative(base, entry.get("run"))
            pdf = run / "source/paper.pdf"
            if not pdf.exists():
                raise ValueError(f"missing real reading workspace source PDF: {pdf}")
            import fitz
            with fitz.open(pdf) as source_pdf:
                text = "".join(page.get_text() for page in source_pdf)
                if len(source_pdf) < 2 or len(text) < 3000:
                    item_errors.append("source is not a full scientific paper; synthetic/abstract-only inputs do not qualify")
            if not entry.get("source_url", "").startswith("https://"):
                item_errors.append("real paper lacks authoritative acquisition URL")
            src_hash = sha256(pdf)
            if entry.get("source_sha256") != src_hash:
                item_errors.append("real paper acquisition hash mismatch")
            if src_hash in source_hashes:
                item_errors.append("regression reuses the same source PDF in multiple records")
            source_hashes.add(src_hash)
            if entry.get("split") == "unseen":
                if entry.get("used_during_implementation") is not False:
                    item_errors.append("unseen paper was used during implementation or has no explicit fresh-paper declaration")
                if not lock or stamp(entry.get("first_read_at")) <= stamp(lock.get("frozen_at")):
                    item_errors.append("unseen source read predates implementation freeze")
            # Issue #14 release evidence: every real-paper workspace must
            # retain the six source-bound Round-1 Council records and bind
            # them to its frozen evidence package.
            council_p = run / "model/lens_council.json"
            package_p = run / "model/frozen_evidence_package.json"
            if not council_p.exists() or not package_p.exists():
                item_errors.append("real-paper workspace lacks frozen Lens Council artifacts")
            else:
                council = load_json(council_p)
                package = load_json(package_p)
                round1 = council.get("round1") or []
                lenses = {str(item.get("lens")) for item in round1 if isinstance(item, dict)}
                if lenses != {"author", "reviewer", "mechanism", "builder", "anomaly", "counterfactual"}:
                    item_errors.append("real-paper Lens Council must retain all six independent Round-1 records")
                if council.get("evidence_package_sha256") != sha256(package_p):
                    item_errors.append("real-paper Lens Council is not bound to its frozen evidence package")
            for rel, digest in bindings(run).items():
                inputs[str(run / rel)] = digest
            for name in ("semantic_review.json", "visual_review.json", "kami_audit.json"):
                review = run / "reader" / name
                if review.exists():
                    inputs[str(review)] = sha256(review)
            visual_p = run / "reader/visual_review.json"
            if visual_p.exists():
                for render in load_json(visual_p).get("renders", []):
                    render_path = run / str(render.get("path") or "")
                    if render_path.is_file():
                        inputs[str(render_path)] = sha256(render_path)
            artifact = evaluate(run, artifact_only=True)
            record["reader_acceptance"] = artifact
            item_errors.extend(artifact["errors"])
            item_errors.extend(_gold_errors(base, entry, run, inputs))
            if entry.get("baseline_comparison"):
                item_errors.extend(_comparison_errors(base, entry, run, inputs))
            if not item_errors:
                record["status"] = "PASS"
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            item_errors.append(f"corpus entry cannot be evaluated: {type(exc).__name__}: {exc}")
        errors.extend(f"{pid}: {message}" for message in item_errors)
    return {"schema_version": "2.0", "status": "PASS" if not errors else "NEEDS_REVIEW",
            "implementation_sha256": implementation_hash(), "manifest": str(path),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "development_count": len(development), "unseen_count": len(unseen),
            "categories": sorted(categories), "input_hashes": inputs,
            "papers": records, "errors": errors}


def validate_release_report(report_path=None):
    path = Path(report_path) if report_path else DEFAULT_REPORT
    if not path.exists():
        return [f"missing real-corpus release report: {path}"]
    try:
        report = load_json(path)
        if report.get("schema_version") != "2.0" or report.get("status") != "PASS":
            return ["real-corpus release report is not v2 PASS; PAPER_COMPLETE refused"]
        if report.get("implementation_sha256") != implementation_hash():
            return ["real-corpus release report implementation hash mismatch; rerun regression"]
        inputs = report.get("input_hashes") or {}
        if not inputs:
            return ["real-corpus release report has no artifact bindings"]
        for rel, expected in inputs.items():
            file = Path(rel)
            if not file.is_file() or sha256(file) != expected:
                return [f"real-corpus release report input changed or missing: {rel}"]
        # Do not trust a forged/stale summary or a count of green records:
        # re-evaluate the declared source workspaces and compare exact inputs.
        current = evaluate_corpus(report.get("manifest"))
        if current["status"] != "PASS":
            return ["real-corpus release revalidation failed", *current["errors"]]
        if current["input_hashes"] != inputs or current["papers"] != report.get("papers"):
            return ["real-corpus release report does not match current evaluation"]
        return []
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return [f"real-corpus release report malformed: {type(exc).__name__}: {exc}"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--out", default=str(DEFAULT_REPORT))
    ap.add_argument("--freeze-implementation", action="store_true", help="Record implementation fingerprint before choosing/reading unseen paper")
    args = ap.parse_args()
    if args.freeze_implementation:
        manifest = load_json(Path(args.manifest))
        freeze_rel = manifest.get("implementation_freeze", "implementation_freeze.json")
        path = relative(Path(args.manifest).parent, freeze_rel)
        if path.exists():
            raise SystemExit(f"REFUSED: preserve existing freeze {path}; a new candidate must use a new manifest/freeze")
        report = {"implementation_sha256": implementation_hash(), "frozen_at": datetime.now(timezone.utc).isoformat()}
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 0
    try:
        report = evaluate_corpus(args.manifest)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        report = {"schema_version": "2.0", "status": "NEEDS_REVIEW", "errors": [f"corpus cannot be evaluated: {exc}"]}
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
