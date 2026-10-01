#!/usr/bin/env python3
"""Evidence-bearing reviews for Reader release v2.

Preparation creates PENDING packets, never approvals. A reviewer must read the
source and rendered Reader, record recoverable passages and source anchors,
and inspect retained renders. Checks bind that judgment to exact artifacts.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from validate_common import load_json, sha256

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_DIMENSIONS = (
    "research_problem", "motivation_gap", "core_idea", "method_logic",
    "decisive_experiments", "observed_results", "justified_conclusion",
    "limitation_boundary", "evidence_transitions", "conclusion_follows_evidence",
    "paragraph_narrative", "unsupported_prose", "uncertainty_preserved",
    "chinese_readability", "renderer_purity",
)
VISUAL_DIMENSIONS = (
    "equations", "figures", "tables", "headings", "density", "narrative_rhythm",
    "evidence_locality", "typography", "symbol_collisions", "overflow",
)
CORE_INPUTS = (
    "source/paper.pdf", "model/paper_model.json", "model/source_map.json",
    "model/figure_inventory.json", "model/argument_reconstruction.json",
    "reader/narrative_manuscript.json", "reader/paper_reader.html",
    "reader/paper_reader.md", "reader/paper_reader.pdf",
)


def compact(value):
    return re.sub(r"[\s`*_]+", "", str(value or "")).rstrip("，。！？；：")


def implementation_hash():
    files = [ROOT / "SKILL.md"]
    for directory, pattern in (("scripts", "*.py"), ("schemas", "*.json"), ("references", "*.md")):
        files.extend((ROOT / directory).rglob(pattern))
    h = hashlib.sha256()
    for path in sorted(files):
        h.update(str(path.relative_to(ROOT)).encode())
        h.update(bytes.fromhex(sha256(path)))
    return h.hexdigest()


def bindings(root):
    """Bind all scientific inputs, displayed assets, and three Reader views."""
    root = Path(root).resolve()
    paths = set(CORE_INPUTS)
    for name in ("lens_council", "frozen_evidence_package", "scientific_synthesis", "evidence_graph", "manifest"):
        if (root / f"model/{name}.json").exists():
            paths.add(f"model/{name}.json")
    manuscript = load_json(root / "reader/narrative_manuscript.json")
    for chapter in manuscript.get("document", {}).get("chapters", []):
        for block in chapter.get("blocks", []):
            for key in ("asset", "fallback_asset"):
                if block.get(key):
                    paths.add(block[key])
    result = {}
    for rel in sorted(paths):
        path = root / rel
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"review input escapes workspace: {rel}")
        result[rel] = sha256(path)
    return result


def review_header(root):
    return {
        "schema_version": "2.0", "implementation_sha256": implementation_hash(),
        "artifact_hashes": bindings(root), "status": "PENDING",
        "reviewer": {"kind": "", "name": "", "method": ""},
        "reviewed_at": None,
    }


def load_bound_review(root, name):
    path = root / "reader" / name
    if not path.exists():
        return None, [f"missing {name}; explicit source/Reader review is required"]
    try:
        review = load_json(path)
        expected = bindings(root)
    except (ValueError, TypeError, OSError) as exc:
        return None, [f"cannot validate {name}: {exc}"]
    errors = []
    if not isinstance(review, dict):
        return None, [f"malformed {name}: expected object"]
    if review.get("schema_version") != "2.0" or review.get("status") != "PASS":
        errors.append(f"{name} is not a v2 PASS review")
    if review.get("implementation_sha256") != implementation_hash():
        errors.append(f"{name} implementation hash mismatch; review is stale")
    if review.get("artifact_hashes") != expected:
        errors.append(f"{name} artifact hash mismatch; review is stale or incomplete")
    reviewer = review.get("reviewer") or {}
    if reviewer.get("kind") not in ("HUMAN", "HOST_AGENT") or not reviewer.get("name") or not reviewer.get("method"):
        errors.append(f"{name} lacks named reviewer and explicit review method")
    try:
        timestamp = datetime.fromisoformat(review.get("reviewed_at", "").replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
            raise ValueError("review timestamp must be past and timezone-aware")
    except (ValueError, TypeError, AttributeError):
        errors.append(f"{name} lacks valid reviewed_at timestamp")
    return review, errors


def semantic_review_errors(root, manuscript):
    review, errors = load_bound_review(root, "semantic_review.json")
    if review is None:
        return errors
    chapters = manuscript.get("document", {}).get("chapters", [])
    narrative = compact(" ".join(
        str(block.get(key, ""))
        for chapter in chapters for block in chapter.get("blocks", [])
        for key in ("text", "analysis", "explanation")
    ))
    source_map = load_json(root / "model/source_map.json")
    pages = {f"p.{pg.get('number')}": compact(pg.get("text", "")) for pg in source_map.get("pages", [])}
    dimensions = review.get("dimensions") or {}
    for dimension in SEMANTIC_DIMENSIONS:
        item = dimensions.get(dimension) or {}
        if item.get("verdict") != "PASS":
            errors.append(f"semantic review {dimension} did not pass")
        quote = compact(item.get("reader_quote"))
        if len(quote) < 12 or quote not in narrative:
            errors.append(f"semantic review {dimension} reader passage is missing or unrecoverable")
        refs = item.get("source_refs") or []
        source_quote = compact(item.get("source_quote"))
        if not refs or any(ref not in pages for ref in refs):
            errors.append(f"semantic review {dimension} source references do not resolve")
        elif len(source_quote) < 12 or not any(source_quote in pages[ref] for ref in refs):
            errors.append(f"semantic review {dimension} lacks a verified source passage")
        if len(str(item.get("reason", "")).strip()) < 20:
            errors.append(f"semantic review {dimension} lacks a substantive rationale")
    covered = review.get("claim_coverage") or []
    pm = load_json(root / "model/paper_model.json")
    required = {c["id"] for c in pm.get("claims", []) if c.get("id")}
    covered_ids = {x.get("claim_id") for x in covered if isinstance(x, dict) and x.get("verdict") == "PASS"}
    if not required.issubset(covered_ids):
        errors.append(f"semantic review major claims not covered: {sorted(required - covered_ids)}")
    for item in covered:
        quote = compact(item.get("reader_quote"))
        if len(quote) < 12 or quote not in narrative or not item.get("reason"):
            errors.append(f"semantic review claim {item.get('claim_id')} lacks recoverable paragraph and rationale")
    if review.get("critical_findings") != []:
        errors.append("semantic review has missing or unresolved critical findings")
    return errors


def visual_review_errors(root):
    review, errors = load_bound_review(root, "visual_review.json")
    if review is None:
        return errors
    import fitz
    with fitz.open(root / "reader/paper_reader.pdf") as pdf:
        total_pages = len(pdf)
    page_ids = set()
    html_inspected = False
    renders = review.get("renders") or []
    for item in renders:
        rel = str(item.get("path") or "")
        path = root / rel
        if not rel or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            errors.append(f"visual review retained render missing or escapes workspace: {rel}")
            continue
        if item.get("sha256") != sha256(path):
            errors.append(f"visual review render hash mismatch: {rel}")
        if item.get("inspected") is not True or not item.get("notes"):
            errors.append(f"visual review render was not explicitly inspected: {rel}")
        if item.get("view") == "HTML":
            if path.suffix.lower() not in (".html", ".htm"):
                errors.append(f"visual review HTML render is not an HTML artifact: {rel}")
            html_inspected = True
            continue
        from PIL import Image
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                if min(im.size) < 500:
                    errors.append(f"visual review retained render resolution too low: {rel}")
        except (OSError, ValueError) as exc:
            errors.append(f"visual review retained render cannot decode: {rel}: {exc}")
        if item.get("view") == "PDF" and isinstance(item.get("page"), int):
            page_ids.add(item["page"])
    if page_ids != set(range(1, total_pages + 1)):
        errors.append("visual review must inspect and retain every PDF page")
    if not html_inspected:
        errors.append("visual review lacks retained HTML browser render")
    for dimension in VISUAL_DIMENSIONS:
        item = (review.get("dimensions") or {}).get(dimension) or {}
        if item.get("verdict") not in ("PASS", "NOT_APPLICABLE") or len(str(item.get("reason", ""))) < 20:
            errors.append(f"visual review {dimension} lacks explicit verdict and rationale")
    if review.get("critical_findings") != []:
        errors.append("visual review has missing or unresolved critical findings")
    return errors


def prepare(root):
    """Prepare pending packets and exact PDF page renders; never overwrite reviews."""
    import fitz
    root = Path(root)
    target = root / "reader/review_pages"
    target.mkdir(parents=True, exist_ok=True)
    renders = []
    with fitz.open(root / "reader/paper_reader.pdf") as pdf:
        for idx, page in enumerate(pdf, 1):
            path = target / f"page-{idx:03d}.png"
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(path)
            renders.append({"view": "PDF", "page": idx, "path": str(path.relative_to(root)),
                            "sha256": sha256(path), "inspected": False, "notes": ""})
    html_snapshot = target / "paper_reader.html"
    html_snapshot.write_text((root / "reader/paper_reader.html").read_text(encoding="utf-8"), encoding="utf-8")
    renders.append({"view": "HTML", "path": str(html_snapshot.relative_to(root)),
                    "sha256": sha256(html_snapshot), "inspected": False, "notes": ""})
    semantic = review_header(root)
    semantic.update({"dimensions": {d: {"verdict": "PENDING", "reader_quote": "", "source_refs": [], "source_quote": "", "reason": ""} for d in SEMANTIC_DIMENSIONS},
                     "claim_coverage": [], "critical_findings": []})
    visual = review_header(root)
    visual.update({"dimensions": {d: {"verdict": "PENDING", "reason": ""} for d in VISUAL_DIMENSIONS},
                   "renders": renders, "critical_findings": []})
    for name, report in (("semantic_review.pending.json", semantic), ("visual_review.pending.json", visual)):
        (root / "reader" / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {"status": "PENDING", "pages_prepared": len(renders), "instructions": "Review source and Reader, inspect PDF pages and HTML in a browser, then submit explicit semantic_review.json and visual_review.json. Pending packets never approve release."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    print(json.dumps(prepare(Path(args.out)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
