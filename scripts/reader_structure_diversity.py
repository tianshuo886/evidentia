#!/usr/bin/env python3
"""Check paper-specific Reader architectures across real completed workspaces.

This is a structural-freedom gate, not a paper-quality benchmark. It only
asserts that completed source-grounded Readers expose their own ordered section
architectures and do not all collapse to the same fixed outline.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from validate_common import load_json, schema_validate, sha256

FIXED_IDS = {"one_minute", "problem", "method", "experiments", "synthesis", "conclusions"}

def _sections(manuscript):
    doc = manuscript.get("document", {})
    return doc.get("sections") or doc.get("chapters") or []

def _signature(sections):
    def normalize(title):
        text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(title or "").lower()).strip()
        return text[:80]
    return tuple(normalize(section.get("title")) for section in sections)

def inspect_workspace(root: Path):
    root = Path(root)
    errors = []
    source = root / "source/paper.pdf"
    manuscript_path = root / "reader/narrative_manuscript.json"
    if not source.exists():
        errors.append("missing source/paper.pdf")
    if not manuscript_path.exists():
        errors.append("missing reader/narrative_manuscript.json")
        return {"root": str(root), "status": "NEEDS_REVIEW", "errors": errors}
    manuscript = load_json(manuscript_path)
    errors.extend(schema_validate(manuscript, "narrative_manuscript"))
    sections = _sections(manuscript)
    ids = [str(section.get("id")) for section in sections]
    if not sections:
        errors.append("Reader has no dynamic sections")
    if len(ids) != len(set(ids)):
        errors.append("Reader has duplicate section ids")
    if ids and set(ids).issubset(FIXED_IDS):
        errors.append("Reader uses only canonical fixed-slot section ids")
    for section in sections:
        if not section.get("title") or not section.get("blocks"):
            errors.append(f"section {section.get('id')} lacks title or typed blocks")
        if not (section.get("evidence_refs") or section.get("source_anchors") or any(block.get("evidence_refs") for block in section.get("blocks", []))):
            errors.append(f"section {section.get('id')} lacks source/evidence binding")
    if source.exists() and manuscript.get("source_sha256") and manuscript["source_sha256"] != sha256(source):
        errors.append("manuscript source_sha256 does not match source PDF")
    return {
        "root": str(root), "paper_id": manuscript.get("paper_id"),
        "section_ids": ids, "section_titles": [str(x.get("title")) for x in sections],
        "signature": list(_signature(sections)), "status": "PASS" if not errors else "NEEDS_REVIEW", "errors": errors,
    }

def evaluate(roots):
    records = [inspect_workspace(Path(root)) for root in roots]
    errors = [f"{record['root']}: {error}" for record in records for error in record["errors"]]
    passed = [record for record in records if record["status"] == "PASS"]
    if len(passed) < 3:
        errors.append("structural-diversity validation requires at least three passing real-paper Readers")
    signatures = {tuple(record["signature"]) for record in passed}
    if len(passed) >= 3 and len(signatures) < 2:
        errors.append("three real-paper Readers collapse to one section architecture")
    return {"status": "PASS" if not errors else "NEEDS_REVIEW", "errors": errors, "records": records,
            "interpretation": "Does this Reader feel shaped by the paper, or shaped by Evidentia?",
            "materially_different_architectures": len(signatures) >= 2 if passed else False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="Completed real-paper workspace; repeat at least three times")
    parser.add_argument("--report")
    args = parser.parse_args()
    result = evaluate(args.run)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
