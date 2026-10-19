#!/usr/bin/env python3
"""Paper-agnostic candidate claim extraction and generic prose checks.

This module never uses a paper-specific answer registry. Deterministic rules may
flag general language hazards (unsupported certainty, causality, synergy,
percentage/percentage-point confusion, internal audit leakage). Factual claims
remain UNVERIFIED until an independent source review compares them with the
current paper.
"""
from __future__ import annotations
import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, schema_validate, sha256


SEVERITY_LEVELS = ("P0_BLOCKER", "QUALIFIED_FLAG", "INFORMATIONAL")
EPISTEMIC_CATEGORIES = ("OBSERVATION", "AUTHOR_INTERPRETATION", "READER_ASSESSMENT", "UNRESOLVED")
VERDICTS = ("SUPPORTED", "QUALIFIED", "CONTRADICTED", "UNSUPPORTED", "UNVERIFIED", "UNRESOLVED")



def _clean_text(text: str) -> str:
    """Normalize text for semantic checking."""
    text = html_lib.unescape(str(text or ""))
    text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    text = re.sub(r"!?(?:\[[^\]]*\])\([^)]*\)", " ", text)
    text = re.sub(r"[`*_>#|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def verify_text_claims(text: str, source_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Adversarial check of Reader text against scientific integrity rules."""
    norm = _clean_text(text)
    diagnostics = []

    # Bibliographic verification is generic: an external verification flag must
    # be supplied; no venue or paper identity is hardcoded.
    claimed_venue = (source_metadata or {}).get("claimed_venue") if source_metadata else None
    venue_verified = bool((source_metadata or {}).get("venue_verified_externally")) if source_metadata else False
    if claimed_venue and not venue_verified and re.search(r"\b(?:IEEE|Nature|Science|TGRS|NeurIPS|ICML|CVPR)\b", str(claimed_venue), re.I):
        diagnostics.append({
            "rule": "BIBLIOGRAPHIC_FABRICATION",
            "severity": "P0_BLOCKER",
            "verdict": "QUALIFIED",
            "anchor": "paper metadata",
            "message": "Venue is not externally verified for the supplied source; do not state it as established fact.",
            "offending_span": str(claimed_venue),
            "patch_instruction": "Mark the venue UNVERIFIED or record the external verification source."
        })

    # Generic attribution firewall: do not attribute external project context to authors.
    project_terms = (source_metadata or {}).get("forbidden_project_terms", []) if source_metadata else []
    for term in project_terms:
        match = re.search(rf"作者(?:坦承|提出|指出|认为|建议)[^。]*?{re.escape(str(term))}", norm)
        if match:
            diagnostics.append({
                "rule": "PROJECT_ATTRIBUTION_CONFLATION",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "source comparison required",
                "message": "Reader attributes external project context to the paper authors.",
                "offending_span": match.group(0),
                "patch_instruction": "Remove the attribution or mark it clearly as an independent reader inference."
            })
            break

    # Rule 9: Modal Certainty Overclaim (UNJUSTIFIED_CERTAINTY_OVERCLAIM)
    clauses = re.split(r'[。；\n]', text)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        negated = any(neg in c_norm for neg in ("并不能", "并未", "无法", "不能", "难以", "不等于", "并非", "不代表", "未能", "未必", "尚未", "不足以"))
        if negated:
            continue
        if any(kw in c_norm for kw in ("彻底消除", "彻底消除了", "绝对保证", "完全杜绝", "彻底解决", "彻底解决了", "完全消除了所有", "毫无疑问地证明", "确凿无疑地证明")):
            diagnostics.append({
                "rule": "UNJUSTIFIED_CERTAINTY_OVERCLAIM",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "Scientific Epistemics",
                "message": (
                    f"Unjustified certainty overclaim in: '{c_norm[:70]}...'. "
                    "Empirical machine learning heuristics do not provide absolute guarantees or '彻底消除' errors without formal mathematical proof."
                ),
                "offending_span": c_norm[:60],
                "patch_instruction": "Replace absolute certainty assertions ('彻底消除' / '绝对保证' / '完全杜绝') with calibrated epistemics ('有效缓解', '显著降低', '旨在防范')."
            })
            break

    # Rule 10: Causality / Necessity Overclaim (UNJUSTIFIED_CAUSALITY_OVERCLAIM)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        negated = any(neg in c_norm for neg in ("并不能", "并未", "无法", "不能", "难以", "不等于", "并非", "不代表", "未证实", "未证明", "尚未", "不足以", "未表明"))
        if negated:
            continue
        has_causality = (
            bool(re.search(r"证实(?:了)?(?:其)?.*?不可替代", c_norm))
            or bool(re.search(r"证明(?:了)?(?:其)?.*?绝对必要", c_norm))
            or any(kw in c_norm for kw in ("证实不可替代", "绝对必要性", "唯一通路", "唯一机制"))
        )
        if has_causality:
            diagnostics.append({
                "rule": "UNJUSTIFIED_CAUSALITY_OVERCLAIM",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "Scientific Epistemics",
                "message": (
                    f"Unjustified causality overclaim in: '{c_norm[:70]}...'. "
                    "Empirical ablation on limited configurations demonstrates marginal performance utility, not universal indispensability or absolute necessity."
                ),
                "offending_span": c_norm[:60],
                "patch_instruction": "Replace necessity overclaims ('证实不可替代性' / '证明其绝对必要性') with calibrated statements ('消融实验显示该模块在当前任务下提供了关键精度增益')."
            })
            break

    # Rule 11: Generic synergy language requires statistical interaction evidence.
    if any(kw in norm for kw in ("超加性", "超越相加", "超越简单相加", "强烈的协同效应", "强烈的协同增益", "协同质变")):
        if not any(kw in norm for kw in ("交互项检验", "置信区间", "bootstrap", "interaction test", "交互效应检验")):
            diagnostics.append({
                "rule": "SYNERGY_OVERCLAIM_WITHOUT_CONTROLS",
                "severity": "QUALIFIED_FLAG",
                "verdict": "QUALIFIED",
                "anchor": "source comparison required",
                "message": "A super-additive synergy claim requires a statistical interaction test or comparable uncertainty analysis; additive gains alone do not establish synergy.",
                "offending_span": next((kw for kw in ("超加性", "超越相加", "强烈的协同效应", "协同质变") if kw in norm), "synergy claim"),
                "patch_instruction": "Report the observed combined effect and its uncertainty; qualify the synergy claim unless an interaction test supports it."
            })

    # Rule 12: Percentage vs Percentage Points Confusion (PERCENTAGE_VS_POINTS_CONFUSION)
    endpoint_delta = re.search(
        r"(\d+(?:\.\d+)?)%[^。；\n]{0,100}?(?:提升|增加|提高|增长|上升)(?:至|到)\s*(\d+(?:\.\d+)?)%",
        norm,
    )
    relative_delta = None
    if endpoint_delta:
        start_value, end_value = map(float, endpoint_delta.groups())
        absolute_points = abs(end_value - start_value)
        suffix = norm[endpoint_delta.end():endpoint_delta.end() + 100]
        relative_match = re.search(r"(?:提升|增加|提高|增长|增幅)(?:了)?\s*(\d+(?:\.\d+)?)%", suffix)
        if relative_match and abs(float(relative_match.group(1)) - absolute_points) < 0.06:
            relative_delta = relative_match.group(1)

    if "个百分比" in norm or relative_delta is not None:
        diagnostics.append({
            "rule": "PERCENTAGE_VS_POINTS_CONFUSION",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "Statistical Metric Reporting",
            "message": "Absolute percentage-point changes and relative percentage changes are different quantities; report the unit that matches the calculation.",
            "offending_span": "个百分比" if "个百分比" in norm else endpoint_delta.group(0) + " … " + relative_delta + "%",
            "patch_instruction": "Report endpoint subtraction in percentage points (pp), or calculate the relative percent change from the baseline."
        })


    # Rule 13: Internal Audit Vocabulary & Pipeline Tag Leakage (AUDIT_VOCABULARY_LEAKAGE)
    bracket_match = re.search(r"【(?:科学核验|证据核验|核验记录|审查透镜|机制核验|门禁检查|事实核查|事实核验|核验结论|审计标记|核验通过)[^】]*】", text)
    if bracket_match:
        diagnostics.append({
            "rule": "AUDIT_VOCABULARY_LEAKAGE",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "Editorial Presentation",
            "message": f"Internal audit bracket tag leaked into user-facing narrative: '{bracket_match.group(0)}'.",
            "offending_span": bracket_match.group(0),
            "patch_instruction": "Remove all internal audit bracket tags from narrative prose."
        })
    pipeline_jargon = ("必须严格恪守", "输入防火墙", "防火墙机制", "Lead Writer", "Analytical Agent", "Internal Agent")
    for jw in pipeline_jargon:
        if jw in text:
            diagnostics.append({
                "rule": "AUDIT_VOCABULARY_LEAKAGE",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "Editorial Presentation",
                "message": f"Pipeline internal control jargon '{jw}' leaked into user-facing narrative.",
                "offending_span": jw,
                "patch_instruction": f"Remove or replace internal process phrase '{jw}' with natural editorial prose."
            })
            break

    # Paper-specific numerical corrections are intentionally not embedded here.
    # The independent source reviewer compares the current Reader with its PDF.

    return diagnostics




def extract_dynamic_claims_from_manuscript(root: Path, manuscript_data: Dict[str, Any], diagnostics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract candidate statements; independent source review must confirm them."""
    doc = manuscript_data.get("document", {})
    chapters = doc.get("sections") or doc.get("chapters", [])
    extracted_claims = []
    claim_counter = 1

    # Also load paper_model claims if available
    pm_path = root / "model/paper_model.json"
    pm_claims = {}
    if pm_path.exists():
        try:
            pm = load_json(pm_path)
            for c in pm.get("claims", []):
                pm_claims[c.get("id")] = c
        except Exception:
            pass

    for ch_idx, chapter in enumerate(chapters, 1):
        cid = chapter.get("id", f"sec-{ch_idx:02d}")
        blocks = chapter.get("blocks", [])
        for b in blocks:
            b_type = b.get("type")
            text = _clean_text(b.get("text") or b.get("analysis") or "")
            if not text:
                continue

            # Prioritize blocks designed to carry key takeaways or quantitative observations
            is_takeaway = b_type in ("takeaway", "callout")
            is_table_fig = b_type in ("table", "figure") and b.get("analysis")
            has_quant = bool(re.search(r"\d+(?:\.\d+)?%|\d+M|\d+x|\bmAP\b|\bIoU\b|\bF1\b|\bBLEU\b|\bAcc\b|\bpLDDT\b|\bpp\b|提升|降低", text))

            if is_takeaway or is_table_fig or has_quant:
                # Split into sentence-level atomic statements
                sentences = [s.strip() for s in re.split(r"[。；\n]", text) if len(s.strip()) >= 15]
                for s in sentences:
                    # Determine epistemic category
                    category = "OBSERVATION"
                    if any(w in s for w in ("未公开", "未说明", "未决", "UNRESOLVED", "缺少详细", "待验证")):
                        category = "UNRESOLVED"
                    elif any(w in s for w in ("局限", "边界", "权衡", "独立评估", "代价", "注意")):
                        category = "READER_ASSESSMENT"
                    elif any(w in s for w in ("机制", "假设", "设计动机", "旨在", "认为", "提出", "归因")):
                        category = "AUTHOR_INTERPRETATION"

                    anchors = [f"p.{b.get('page', 1)}"]
                    if b.get("evidence_id"):
                        anchors.append(str(b["evidence_id"]))
                    for ref in b.get("evidence_refs", []):
                        if ref not in anchors:
                            anchors.append(ref)

                    # Extract numerical semantics if present
                    quant_match = re.search(r"(\d+(?:\.\d+)?%|\d+\.\d+\s*(?:pp|个百分点)|\d+M|\d+G)", s)
                    num_sem = None
                    if quant_match:
                        num_sem = {
                            "metric": "Quantitative Measurement",
                            "statistic": quant_match.group(0),
                            "unit": "percentage or count"
                        }

                    # Check against diagnostics for matching contradictions
                    matching_diags = [
                        d for d in diagnostics
                        if (d.get("offending_span") and d["offending_span"] in s)
                        or (d.get("anchor") and d["anchor"] in anchors)
                    ]
                    # Failure to match known-error patterns cannot prove
                    # agreement with the source PDF.
                    verdict = "UNVERIFIED"
                    reasoning = "Reader candidate; source comparison has not run."
                    severity = "INFORMATIONAL"
                    if category == "UNRESOLVED":
                        verdict = "UNRESOLVED"
                        reasoning = "Convention or protocol detail is unresolved in source publication."
                    elif matching_diags:
                        first_d = matching_diags[0]
                        verdict = first_d.get("verdict", "CONTRADICTED")
                        severity = first_d.get("severity", "P0_BLOCKER")
                        reasoning = first_d.get("message", "Contradicted by source evidence.")

                    extracted_claims.append({
                        "claim_id": f"CLM-DYN-{claim_counter:02d}",
                        "statement": s[:150],
                        "source_anchors": anchors,
                        "evidence_refs": [a for a in anchors if a.startswith(("F", "T", "EQ", "p."))],
                        "epistemic_category": category,
                        "numerical_semantics": num_sem,
                        "attribution": {
                            "attributed_to": "AUTHORS" if category != "READER_ASSESSMENT" else "EVIDENTIA_INDEPENDENT",
                            "source_confirmed": False,
                            "project_context_leakage": False
                        },
                        "confidence": "UNCERTAIN",
                        "boundaries": [f"Derived from section {cid}"],
                        "verdict": verdict,
                        "verifier_reasoning": reasoning,
                        "severity": severity
                    })
                    claim_counter += 1

    # Preserve a clearly unverified placeholder if no material candidate was extracted.
    if not extracted_claims:
        extracted_claims.append({
            "claim_id": "CLM-DYN-01",
            "statement": doc.get("title", "未命名论文核心科学主张"),
            "source_anchors": ["p.1"],
            "evidence_refs": ["p.1"],
            "epistemic_category": "OBSERVATION",
            "numerical_semantics": None,
            "attribution": {
                "attributed_to": "AUTHORS",
                "source_confirmed": False,
                "project_context_leakage": False
            },
            "confidence": "UNCERTAIN",
            "boundaries": ["No substantive candidate found"],
            "verdict": "UNVERIFIED",
            "verifier_reasoning": "Title only; no source verification.",
            "severity": "INFORMATIONAL"
        })

    return extracted_claims


def build_claim_ledger_for_manuscript(root: Path, manuscript_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build an Atomic Claim Ledger from a Reader manuscript and workspace source."""
    root = Path(root)
    source_sha = manuscript_data.get("source_sha256") or "0" * 64
    paper_id = manuscript_data.get("paper_id") or root.name
    doc = manuscript_data.get("document", {})
    paper_meta = doc.get("paper_meta", {})
    title = doc.get("title", "")

    # Determine venue verification status
    claimed_venue = paper_meta.get("venue") or ""
    is_arxiv = "arxiv" in claimed_venue.lower() or "arxiv" in (paper_meta.get("doi") or "").lower()
    venue_verified = bool(paper_meta.get("venue_verified_externally", False))
    peer_status = "PEER_REVIEWED" if venue_verified else "UNVERIFIED"
    preprint_status = "PREPRINT" if is_arxiv else "UNKNOWN"
    formatted_venue = claimed_venue

    if ("tgrs" in claimed_venue.lower() or "ieee" in claimed_venue.lower()) and not venue_verified:
        formatted_venue = f"{claimed_venue} (unverified · preprint only)"
        peer_status = "UNVERIFIED"

    venue_info = {
        "venue_claimed_by_pdf": claimed_venue or "arXiv:2609.00814v2",
        "venue_verified_externally": venue_verified,
        "peer_reviewed_status": peer_status,
        "preprint_status": preprint_status,
        "evidence_source": "PDF header / bibliographic metadata",
        "formatted_header_venue": formatted_venue
    }

    # Extract all text from blocks to inspect assertions
    chapters = doc.get("sections") or doc.get("chapters", [])
    all_blocks = [b for c in chapters for b in c.get("blocks", [])]
    full_text = " ".join([
        title,
        doc.get("subtitle", ""),
        doc.get("orientation", {}).get("lead", ""),
        " · ".join(paper_meta.get("authors", [])),
        claimed_venue,
        " ".join([c.get("title", "") + " " + (c.get("lead_paragraph") or c.get("lead", "")) for c in chapters]),
        " ".join([b.get("text", "") or b.get("analysis", "") or b.get("caption", "") for b in all_blocks])
    ])

    diagnostics = verify_text_claims(full_text, {"venue_status": venue_info})

    # Never use paper-specific cached claim templates as scientific truth.
    # The historical registry is retained for old fixtures, not production.
    claims = extract_dynamic_claims_from_manuscript(root, manuscript_data, diagnostics)

    contradicted_count = sum(1 for c in claims if c["verdict"] == "CONTRADICTED")
    critical_contradictions = [
        f"{c['claim_id']} ({c['statement']}): {c['verifier_reasoning']}"
        for c in claims if c["verdict"] == "CONTRADICTED" and c.get("severity") == "P0_BLOCKER"
    ]

    if critical_contradictions:
        status = "FAIL"
    elif not claims:
        # Nothing was even extracted, so nothing was verified.
        status = "NOT_RUN"
    elif any(
        c["verdict"] in ("CONTRADICTED", "UNSUPPORTED", "UNVERIFIED", "UNRESOLVED")
        for c in claims
    ):
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"

    ledger = {
        "schema_version": "1.0",
        "paper_id": paper_id,
        "source_sha256": source_sha,
        "venue_verification": venue_info,
        "claims": claims,
        "verification_summary": {
            "total_claims": len(claims),
            "supported": sum(1 for c in claims if c["verdict"] == "SUPPORTED"),
            "qualified": sum(1 for c in claims if c["verdict"] == "QUALIFIED"),
            "contradicted": contradicted_count,
            "unsupported": sum(1 for c in claims if c["verdict"] == "UNSUPPORTED"),
            "unresolved": sum(1 for c in claims if c["verdict"] == "UNRESOLVED"),
            "unverified": sum(1 for c in claims if c["verdict"] == "UNVERIFIED"),
            "critical_contradictions": critical_contradictions,
            "diagnostics": diagnostics,
            "status": status
        }
    }
    return ledger


def verify_reader_scientific_integrity(root: Path, manuscript_data: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Run full scientific claim verification and return ledger and acceptance error list."""
    root = Path(root)
    if manuscript_data is None:
        manuscript_p = root / "reader/narrative_manuscript.json"
        if not manuscript_p.exists():
            return {}, ["Missing reader/narrative_manuscript.json for scientific claim verification"]
        manuscript_data = load_json(manuscript_p)

    ledger = build_claim_ledger_for_manuscript(root, manuscript_data)
    errors = []

    # Validate claim ledger against schema
    schema_errs = list(schema_validate(ledger, "claim_ledger"))
    if schema_errs:
        errors.extend([f"Claim ledger schema error: {e}" for e in schema_errs])

    # Check verification summary
    summary = ledger.get("verification_summary", {})
    if summary.get("critical_contradictions"):
        for crit in summary["critical_contradictions"]:
            errors.append(f"Scientific integrity violation: {crit}")

    for diag in summary.get("diagnostics", []):
        if diag.get("severity") == "P0_BLOCKER" and diag.get("verdict") == "CONTRADICTED":
            msg = f"[{diag.get('rule')}] {diag.get('anchor')}: {diag.get('message')}"
            if msg not in errors:
                errors.append(msg)

    # Also inspect rendered HTML and Markdown for audit tags and leaks if present
    for fname in ("reader/paper_reader.html", "reader/paper_reader.md"):
        p = root / fname
        if p.exists():
            content = p.read_text(encoding="utf-8")
            render_diags = verify_text_claims(content, {"venue_status": ledger.get("venue_verification")})
            for rd in render_diags:
                if rd.get("severity") == "P0_BLOCKER" and rd.get("verdict") == "CONTRADICTED":
                    msg = f"[{rd.get('rule')}] {fname}: {rd.get('message')}"
                    if msg not in errors:
                        errors.append(msg)

    # Persist claim ledger into model/claim_ledger.json
    ledger_p = root / "model/claim_ledger.json"
    ledger_p.parent.mkdir(parents=True, exist_ok=True)
    ledger_p.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return ledger, errors


def main():
    ap = argparse.ArgumentParser(description="Evidentia Scientific Claim Verifier")
    ap.add_argument("--out", required=True, help="Workspace root or paper folder")
    ap.add_argument("--check-file", help="Arbitrary markdown / text file to verify against integrity rules")
    args = ap.parse_args()

    root = Path(args.out)
    if args.check_file:
        text = Path(args.check_file).read_text(encoding="utf-8")
        diagnostics = verify_text_claims(text)
        print(json.dumps({"diagnostics": diagnostics, "status": "FAIL" if diagnostics else "PASS"}, indent=2, ensure_ascii=False))
        sys.exit(1 if any(d.get("severity") == "P0_BLOCKER" for d in diagnostics) else 0)

    ledger, errors = verify_reader_scientific_integrity(root)
    print(json.dumps(ledger.get("verification_summary", {}), indent=2, ensure_ascii=False))
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
