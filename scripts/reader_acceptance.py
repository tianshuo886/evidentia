#!/usr/bin/env python3
"""Release gate for the human-facing Paper Reader (Issues #10–#13).

This gate is intentionally deterministic and fail-closed. It checks:
- Semantic story spine and 6 core narrative chapters
- Lens invisibility across the entire document
- Local evidence bindings, image decodability, and per-equation SVG rendering
- Input firewall, intent isolation, and absence of unsolicited transfer prose
- Cross-format semantic parity across HTML, Markdown, and PDF
- Fresh and cryptographically bound Kami visual QA audit
"""
import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path

from render_paper_reader import normalize_latex
from validate_common import load_json, sha256

LENS_TERMS = ("Lens", "透镜", "跨透镜", "六大透镜", "六个 Lens", "六个Lens")
ATLAS_SUBSTITUTES = ("详情见图谱", "图谱详情")
UNSUPPORTED_FILLER = (
    "该公式确立了核心计算关系，约束变量变换与优化目标",
    "建议在目标领域重新验证",
    "假设输入特征分布与训练评测基准保持一致",
)

def _main_body(html_text):
    marker = html_text.find('id="ch-appendix"')
    return html_text if marker < 0 else html_text[:marker]

def _asset_valid(root: Path, asset: str):
    """Check that asset exists, is non-empty, and decodes properly if an image."""
    if not asset:
        return False, "asset path is empty"
    path = root / asset
    if not path.exists():
        return False, f"asset file missing: {asset}"
    ext = path.suffix.lower()
    if ext in ('.png', '.jpg', '.jpeg', '.webp'):
        try:
            from PIL import Image
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                w, h = im.size
                if w <= 0 or h <= 0:
                    return False, f"asset image has invalid dimensions: {w}x{h}"
        except Exception as exc:
            return False, f"asset image cannot be decoded ({exc}): {asset}"
    elif path.stat().st_size == 0:
        return False, f"asset file is empty: {asset}"
    return True, None

def _plain_text(text):
    """Reduce HTML/Markdown/PDF text to a comparable semantic surface."""
    text = html_lib.unescape(str(text or ''))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'!?(?:\[[^\]]*\])\([^)]*\)', ' ', text)
    text = re.sub(r'[`*_>#|$]+', ' ', text)
    return re.sub(r'\s+', '', text)

def _probe(value, limit=24):
    """Return a stable short probe for cross-render semantic parity."""
    compact = _plain_text(value)
    return compact[:limit] if len(compact) >= 8 else compact

def _pdf_text(path):
    try:
        import fitz
        return ''.join(page.get_text() for page in fitz.open(path)), None
    except Exception as fitz_exc:
        try:
            from pypdf import PdfReader
            return '\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages), None
        except Exception as pdf_exc:
            return '', f"cannot extract PDF text ({fitz_exc}; {pdf_exc})"

def evaluate(root: Path):
    errors = []
    manuscript_p = root / "reader/narrative_manuscript.json"
    html_p = root / "reader/paper_reader.html"
    md_p = root / "reader/paper_reader.md"
    pdf_p = root / "reader/paper_reader.pdf"
    for p in (manuscript_p, html_p, md_p, pdf_p):
        if not p.exists():
            errors.append(f"missing reader artifact: {p.relative_to(root)}")
    if errors:
        return _report(errors)

    manuscript = load_json(manuscript_p)
    doc = manuscript.get("document", {})
    chapters = doc.get("chapters", [])
    spine = doc.get("story_spine") or {}

    # 1. Semantic story spine check
    required_spine_text = ("central_question", "motivation", "central_move", "method_logic", "justified_conclusion")
    for field in required_spine_text:
        val = str(spine.get(field, "")).strip()
        if not val or val == "NOT_STATED":
            errors.append(f"story spine missing {field}")
        elif len(val) < 4:
            errors.append(f"story spine {field} is too short or a trivial placeholder: {val!r}")

    required_spine_lists = ("experimental_questions", "major_findings", "scope_and_limits")
    for field in required_spine_lists:
        val = spine.get(field)
        if not isinstance(val, list) or not val:
            errors.append(f"story spine missing non-empty list for {field}")
        elif all(str(x).strip() in ("", "NOT_STATED") or len(str(x).strip()) < 3 for x in val):
            errors.append(f"story spine {field} contains only empty/trivial items")

    chapter_ids = [c.get("id") for c in chapters]
    for cid in ("one_minute", "problem", "method", "experiments", "synthesis", "conclusions"):
        if cid not in chapter_ids:
            errors.append(f"missing paper story chapter: {cid}")

    html_text = html_p.read_text(encoding="utf-8")
    md_text = md_p.read_text(encoding="utf-8")
    pdf_text, pdf_error = _pdf_text(pdf_p)
    if pdf_error:
        errors.append(pdf_error)
    main_html = _main_body(html_text)
    md_appendix = re.search(r'(?m)^##\s+\d+\.\s+证据审计附录', md_text)
    main_md = md_text[:md_appendix.start()] if md_appendix else md_text
    main_views = (main_html, main_md)
    full_views = (html_text, md_text)

    # 2. Lens and Atlas opacity check
    # Main reader must have 0 occurrences of Lens terms or Atlas substitute links
    for term in LENS_TERMS + ATLAS_SUBSTITUTES:
        if any(term in view for view in main_views):
            errors.append(f"main Reader exposes internal/audit vocabulary: {term}")

    # Full document (including appendix) must NOT expose Lens internal machinery terms
    for term in LENS_TERMS:
        if any(term in view for view in full_views):
            errors.append(f"Paper Reader appendix exposes internal Lens vocabulary: {term}")

    # 3. Unsupported prose and generic filler check
    for token in UNSUPPORTED_FILLER:
        if token in html_text or token in md_text:
            errors.append(f"unsupported fallback prose leaked into Reader: {token}")

    # 4. Input firewall and intent isolation check
    state_p = root / "run_state.json"
    if state_p.exists():
        state = load_json(state_p)
        intent = state.get("intent", "PAPER_READING")
        allowed = state.get("allowed_inputs", [])
        forbidden = state.get("forbidden_inputs", ["apply/", "project/", "memory/project/"])
        for item in allowed:
            for f in forbidden:
                if f in str(item) or str(item).startswith(f):
                    errors.append(f"input firewall violated: {item!r} present in allowed_inputs")
    else:
        intent = "PAPER_READING"

    if intent in ("PAPER_READING", "PAPER_TECHNICAL_EXTRACTION"):
        apply_p = root / "apply"
        if apply_p.exists():
            errors.append(f"intent {intent} isolation violated: apply/ directory exists")
        for p in root.glob("project*"):
            errors.append(f"intent {intent} isolation violated: project file {p.name} exists in workspace")

    if intent == "PAPER_READING":
        if any(c.get("id") in ("reusable", "technical_extraction") for c in chapters):
            errors.append("default PAPER_READING contains a technical/reuse chapter")
        transfer_terms = ("可复用技术内容", "迁移复用建议", "迁移到你的项目", "建议用于项目", "项目适配")
        if any(term in view for view in main_views for term in transfer_terms):
            errors.append("default PAPER_READING contains unsolicited transfer prose")
        if (root / "reader/technical_extraction.md").exists() or (root / "reader/technical_extraction.html").exists():
            errors.append("default PAPER_READING contains standalone technical extraction artifact")

    if intent == "PAPER_TECHNICAL_EXTRACTION":
        if not any(c.get("id") == "technical_extraction" for c in chapters):
            errors.append("PAPER_TECHNICAL_EXTRACTION missing technical_extraction chapter")
        transfer_terms = ("迁移到你的项目", "建议用于项目", "项目适配")
        if any(term in view for view in main_views for term in transfer_terms):
            errors.append("PAPER_TECHNICAL_EXTRACTION leaked project-directed transfer prose")

    # 5. Cross-render semantic parity
    views = {"HTML": _plain_text(main_html), "Markdown": _plain_text(main_md), "PDF": _plain_text(pdf_text)}
    for chapter in chapters:
        title = chapter.get("title", "")
        if title:
            for view_name, view in views.items():
                if _plain_text(title) not in view:
                    errors.append(f"chapter missing from {view_name} view: {title}")
    for field in ("central_question", "central_move", "justified_conclusion"):
        probe = _probe(spine.get(field))
        if probe:
            for view_name, view in views.items():
                if probe not in view:
                    errors.append(f"story spine {field} missing from {view_name} view")

    # 6. Local inline evidence bindings and image decodability
    for chapter in chapters:
        for block in chapter.get("blocks", []):
            kind = block.get("type")
            if kind in ("figure", "table"):
                eid = block.get("evidence_id")
                if not eid or not block.get("caption") or not block.get("analysis"):
                    errors.append(f"incomplete inline evidence block: {eid or '<missing id>'}")
                if not block.get("question") or block.get("supports") is None or block.get("limits") is None:
                    errors.append(f"inline evidence binding incomplete: {eid or '<missing id>'}")
                role = block.get("presentation_role", "narrative_support")
                if role in ("narrative_core", "narrative_support"):
                    ok, err = _asset_valid(root, block.get("asset"))
                    if not ok:
                        errors.append(f"inline {kind} {eid} asset invalid: {err}")
                if eid and f'id="{eid}"' not in main_html and f"id='{eid}'" not in main_html:
                    errors.append(f"inline {kind} {eid} is not rendered in main Reader")

            elif kind == "equation":
                eid = block.get("evidence_id")
                if not eid:
                    errors.append("equation block missing equation_id")
                verified_latex = normalize_latex(block.get("latex")) if block.get("source_confidence") == "VERIFIED" else None
                if not verified_latex:
                    fallback = block.get("fallback_asset")
                    ok, err = _asset_valid(root, fallback)
                    if not ok:
                        errors.append(f"equation {eid or '<missing id>'} lacks valid source fallback: {err}")
                else:
                    # Per-equation check: ensure MathJax pre-rendered SVG inside the equation block container
                    eq_pat = rf"(?:id=['\"]{re.escape(eid)}['\"]|<div[^>]*id=['\"]{re.escape(eid)}['\"])[\s\S]*?(?=<div[^>]*class=['\"][^'\"]*equation-block|<section|</section|$)"
                    m_eq = re.search(eq_pat, main_html)
                    if not m_eq:
                        errors.append(f"equation {eid} is not rendered in main Reader")
                    elif 'latex-display-svg' not in m_eq.group(0) or '<svg' not in m_eq.group(0):
                        errors.append(f"equation {eid} verified LaTeX was not pre-rendered to MathJax SVG")

    # 7. Narrative-bearing evidence present in Markdown and PDF
    for chapter in chapters:
        for block in chapter.get("blocks", []):
            if block.get("type") in ("figure", "table", "equation") and block.get("evidence_id"):
                eid = block["evidence_id"]
                if _plain_text(eid) not in views["Markdown"]:
                    errors.append(f"evidence {eid} missing from Markdown view")
                if _plain_text(eid) not in views["PDF"] and block.get("type") != "equation":
                    errors.append(f"evidence {eid} missing from PDF view")

    # 8. Kami visual QA freshness and cryptographic binding
    audit_p = root / "reader/kami_audit.json"
    if not audit_p.exists():
        errors.append("missing Kami visual audit report")
    else:
        audit_data = load_json(audit_p)
        if audit_data.get("status") != "OK":
            errors.append("Kami visual audit failed")
        if pdf_p.exists() and pdf_p.stat().st_mtime > audit_p.stat().st_mtime + 5:
            errors.append("Kami visual audit is stale (PDF modified after audit timestamp)")
        if audit_data.get("pdf_sha256") and pdf_p.exists():
            if audit_data["pdf_sha256"] != sha256(pdf_p):
                errors.append("Kami visual audit pdf_sha256 mismatch")
        if audit_data.get("html_sha256") and html_p.exists():
            if audit_data["html_sha256"] != sha256(html_p):
                errors.append("Kami visual audit html_sha256 mismatch")

    return _report(errors)

def _report(errors):
    parity_errors = ("view", "parity", "PDF", "Markdown", "HTML")
    return {
        "status": "PAPER_COMPLETE" if not errors else "NEEDS_REVIEW",
        "narrative_complete": not any("story spine" in e or "chapter" in e for e in errors),
        "lens_invisible": not any("vocabulary" in e for e in errors),
        "inline_evidence_complete": not any("inline" in e or "evidence" in e for e in errors),
        "equations_valid": not any("equation" in e for e in errors),
        "intent_isolated": not any("Apply" in e or "reuse" in e or "technical" in e or "firewall" in e or "isolation" in e for e in errors),
        "unsupported_prose_free": not any("fallback" in e or "transfer prose" in e for e in errors),
        "html_md_pdf_parity": not any(any(marker in e for marker in parity_errors) for e in errors),
        "visual_review": "PASS" if not errors else "NEEDS_REVIEW",
        "errors": errors,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.out)
    report = evaluate(root)
    out_p = root / "reader/reader_acceptance.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PAPER_COMPLETE" else 1

if __name__ == "__main__":
    sys.exit(main())
