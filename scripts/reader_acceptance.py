#!/usr/bin/env python3
"""Release gate for the human-facing Paper Reader (Issues #10–#13).

This gate is intentionally deterministic and fail-closed. It checks:
- Open paper-specific narrative sections and source/evidence bindings
- Lens invisibility across the entire document
- Local evidence bindings, image decodability, and per-equation SVG rendering
- Input firewall, intent isolation, and absence of unsolicited transfer prose
- Cross-format semantic parity across HTML, Markdown, and PDF
- Fresh and cryptographically bound Kami visual QA audit
"""
import argparse
import html as html_lib
import json
import os
import re
import sys
from pathlib import Path

from render_paper_reader import normalize_latex
from validate_common import load_json, schema_validate, sha256
from reader_review import semantic_review_errors, visual_review_errors, bindings, implementation_hash
from reader_integrity import parity_errors, firewall_errors, lens_execution_provenance_errors, ReaderHTML

GATES = ("narrative_complete", "lens_invisible", "inline_evidence_complete", "equations_valid",
         "intent_isolated", "execution_provenance", "unsupported_prose_free", "html_md_pdf_parity", "visual_review")


class GateErrors(list):
    """Keep diagnostics attributed to their gate, rather than guessing from text."""
    def __init__(self):
        super().__init__()
        self.gate = "artifacts"
        self.failed = set()
        self.diagnostics = []

    def append(self, message):
        super().append(message)
        self.failed.add(self.gate)
        self.diagnostics.append({"gate": self.gate, "message": message})

    def extend(self, values):
        for message in values:
            self.append(message)

LENS_TERMS = ("Lens", "透镜", "跨透镜", "六大透镜", "六个 Lens", "六个Lens")
PRIMARY_INTERNAL_TERMS = LENS_TERMS + (
    "Observation", "Author Interpretation", "Reader Assessment", "O/I/A",
    "claim-card", "证据卡片", "Supports Claims", "schema_version",
)
FORBIDDEN_PRIMARY_PHRASES = ("详情见图谱", "图谱详情")
UNSUPPORTED_FILLER = (
    "该公式确立了核心计算关系，约束变量变换与优化目标",
    "建议在目标领域重新验证",
    "假设输入特征分布与训练评测基准保持一致",
)

def _main_body(html_text):
    marker = html_text.find('id="ch-appendix"')
    if marker < 0:
        marker = html_text.find("id='ch-sources'")
    return html_text if marker < 0 else html_text[:marker]

def _asset_valid(root: Path, asset: str):
    """Check that asset exists, is non-empty, and decodes properly if an image."""
    if not asset:
        if os.environ.get("EVIDENTIA_FIXTURE_ACCEPTANCE") == "1":
            return True, None
        return False, "asset path is empty"
    path = root / asset
    if not path.exists():
        if os.environ.get("EVIDENTIA_FIXTURE_ACCEPTANCE") == "1":
            return True, None
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
    # Only remove actual markup tags; PDF/Markdown equations legitimately
    # contain inequality characters such as ``x < y``.
    text = re.sub(r'</?[A-Za-z][^>]*>', ' ', text)
    text = re.sub(r'!?(?:\[[^\]]*\])\([^)]*\)', ' ', text)
    text = re.sub(r'[`*_>#|$]+', ' ', text)
    return re.sub(r'\s+', '', text)

def _probe(value, limit=24):
    """Return a stable short probe for cross-render semantic parity."""
    compact = _plain_text(value).rstrip('，。！？；：')
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

def _evaluate_artifact(root: Path, *, artifact_only=False):
    errors = GateErrors()
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
    errors.extend(schema_validate(manuscript, "narrative_manuscript"))
    for rel in ("source/paper.pdf", "model/paper_model.json", "model/source_map.json", "model/figure_inventory.json", "model/argument_reconstruction.json"):
        if not (root / rel).exists():
            errors.append(f"missing acceptance input: {rel}")
    if errors:
        return _report(errors)
    doc = manuscript.get("document", {})
    chapters = doc.get("sections") or doc.get("chapters", [])
    spine = doc.get("story_spine") or {}  # optional compatibility metadata only

    # 1. Open narrative check. Rigor is attached to sections and evidence
    # bindings, never to a universal scientific story spine.
    errors.gate = "narrative_complete"
    if not isinstance(chapters, list) or not chapters:
        errors.append("paper-specific Reader has no ordered sections")
    chapter_ids = [c.get("id") for c in chapters]
    if len(set(chapter_ids)) != len(chapter_ids):
        errors.append("paper-specific Reader contains duplicate section ids")
    for chapter in chapters:
        if not str(chapter.get("title", "")).strip():
            errors.append(f"section {chapter.get('id')} has no title")
        if not isinstance(chapter.get("blocks"), list) or not chapter.get("blocks"):
            errors.append(f"section {chapter.get('id')} has no typed presentation blocks")
    if all(cid in {"one_minute", "problem", "method", "experiments", "synthesis", "conclusions"} for cid in chapter_ids):
        errors.append("paper story still uses fixed template chapter ids")

    html_text = html_p.read_text(encoding="utf-8")
    md_text = md_p.read_text(encoding="utf-8")
    pdf_text, pdf_error = _pdf_text(pdf_p)
    if pdf_error:
        errors.append(pdf_error)
    main_html = _main_body(html_text)
    md_appendix = re.search(r'(?m)^##\s+\d+\.\s+证据审计附录', md_text)
    main_md = md_text[:md_appendix.start()] if md_appendix else md_text
    main_views = (main_html, main_md)
    full_views = (html_text, md_text, pdf_text)
    # Unit/fixture artifact checks intentionally omit human review packets;
    # the strict release path still requires fresh semantic and visual review.
    if not artifact_only:
        for message in semantic_review_errors(root, manuscript):
            errors.gate = "unsupported_prose_free" if "unsupported_prose" in message or "renderer_purity" in message else "narrative_complete"
            errors.append(message)
    errors.gate = "narrative_complete"
    paragraphs = [b.get("text", "") for ch in chapters for b in ch.get("blocks", []) if b.get("type") == "paragraph"]
    if not paragraphs or not any(str(p).strip() for p in paragraphs):
        errors.append("narrative is empty or contains no explanatory paragraph")

    # 2. Lens and Atlas opacity check
    # Main reader must have 0 occurrences of Lens terms or Atlas substitute links
    errors.gate = "lens_invisible"
    for term in PRIMARY_INTERNAL_TERMS:
        if any(term in view for view in main_views):
            errors.append(f"main Reader exposes internal/audit vocabulary: {term}")

    # Full document (including appendix) must NOT expose Lens internal machinery terms
    for term in PRIMARY_INTERNAL_TERMS:
        if any(term in view for view in full_views):
            errors.append(f"Paper Reader exposes internal/audit vocabulary: {term}")
    errors.gate = "inline_evidence_complete"
    for phrase in FORBIDDEN_PRIMARY_PHRASES:
        if any(phrase in view for view in full_views):
            errors.append(f"Paper Reader uses an atlas substitute instead of local evidence: {phrase}")

    # 3. Unsupported prose and generic filler check
    errors.gate = "unsupported_prose_free"
    for token in UNSUPPORTED_FILLER:
        if token in html_text or token in md_text:
            errors.append(f"unsupported fallback prose leaked into Reader: {token}")

    # 4. Input firewall and intent isolation check
    errors.gate = "intent_isolated"
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
        state = {}
    errors.extend(firewall_errors(root, intent, state))
    errors.gate = "execution_provenance"
    errors.extend(lens_execution_provenance_errors(root))

    if intent in ("PAPER_READING", "PAPER_TECHNICAL_EXTRACTION"):
        apply_p = root / "apply"
        if apply_p.exists():
            errors.append(f"intent {intent} isolation violated: apply/ directory exists")
        for p in root.glob("project*"):
            errors.append(f"intent {intent} isolation violated: project file {p.name} exists in workspace")

    if intent == "PAPER_READING":
        if any(c.get("id") in ("reusable", "technical_extraction", "technical-extraction") for c in chapters):
            errors.append("default PAPER_READING contains a technical/reuse chapter")
        transfer_terms = ("可复用技术内容", "迁移复用建议", "迁移到你的项目", "建议用于项目", "项目适配")
        if any(term in view for view in main_views for term in transfer_terms):
            errors.append("default PAPER_READING contains unsolicited transfer prose")
        if (root / "reader/technical_extraction.md").exists() or (root / "reader/technical_extraction.html").exists():
            errors.append("default PAPER_READING contains standalone technical extraction artifact")

    if intent == "PAPER_TECHNICAL_EXTRACTION":
        if not any(c.get("id") in ("technical_extraction", "technical-extraction") for c in chapters):
            errors.append("PAPER_TECHNICAL_EXTRACTION missing technical_extraction chapter")
        transfer_terms = ("迁移到你的项目", "建议用于项目", "项目适配")
        if any(term in view for view in main_views for term in transfer_terms):
            errors.append("PAPER_TECHNICAL_EXTRACTION leaked project-directed transfer prose")

    # 5. Cross-render semantic parity
    errors.gate = "html_md_pdf_parity"
    errors.extend(parity_errors(root, manuscript, html_text, md_text, pdf_text))
    views = {"HTML": _plain_text(main_html), "Markdown": _plain_text(main_md), "PDF": _plain_text(pdf_text)}
    for chapter in chapters:
        title = chapter.get("title", "")
        if title:
            for view_name, view in views.items():
                if _plain_text(title) not in view:
                    errors.append(f"chapter missing from {view_name} view: {title}")
    orientation = doc.get("orientation") or doc.get("executive_summary") or {}
    for field in ("lead",):
        probe = _probe(orientation.get(field))
        if probe:
            for view_name, view in views.items():
                if probe not in view:
                    errors.append(f"Reader orientation missing from {view_name} view")

    # 6. Local inline evidence bindings and image decodability
    errors.gate = "inline_evidence_complete"
    rendered_evidence = {}
    parsed_html = ReaderHTML(main_html)
    full_ids = ReaderHTML(html_text).ids
    for anchor in parsed_html.anchors:
        # Page anchors live in the quiet appendix.
        if anchor not in full_ids:
            errors.append(f"inline evidence anchor does not resolve: {anchor}")
    for chapter in chapters:
        for block in chapter.get("blocks", []):
            if block.get("type") in ("figure", "table", "equation") and block.get("evidence_id"):
                eid = str(block["evidence_id"])
                rendered_evidence.setdefault(eid, []).append(block)
    for eid, blocks in rendered_evidence.items():
        if len(blocks) > 1:
            errors.append(f"duplicate primary evidence block: {eid}")

    # Promotion is the canonical decision about what belongs in the human
    # Reader. Every promoted figure/table must have a local block and a valid
    # source asset; missing promotion state is an upstream failure.
    arg_p = root / "model/argument_reconstruction.json"
    if arg_p.exists():
        arg_doc = load_json(arg_p)
        roles = (arg_doc.get("evidence_promotion") or {}).get("evidence_roles", {})
        promoted = {str(eid): role for eid, role in roles.items() if role in ("narrative_core", "narrative_support")}
        pm = load_json(root / "model/paper_model.json") if (root / "model/paper_model.json").exists() else {}
        inv = load_json(root / "model/figure_inventory.json") if (root / "model/figure_inventory.json").exists() else {}
        source_items = {str(x.get("id")): x for x in pm.get("figures", []) + pm.get("tables", []) + inv.get("items", []) if x.get("id")}
        for eid, role in promoted.items():
            blocks = rendered_evidence.get(eid, [])
            if not blocks:
                errors.append(f"promoted evidence {eid} ({role}) is missing from the primary narrative")
                continue
            block = blocks[0]
            if block.get("presentation_role") != role:
                errors.append(f"promoted evidence {eid} has inconsistent presentation role")
            if block.get("type") in ("figure", "table"):
                asset = block.get("asset") or source_items.get(eid, {}).get("file") or source_items.get(eid, {}).get("asset")
                ok, err = _asset_valid(root, asset)
                if not ok:
                    errors.append(f"promoted {block.get('type')} {eid} asset invalid: {err}")

    # Every structured source equation is either rendered in the manuscript or
    # rejected explicitly. This prevents truncation and silent OCR loss.
    source_map_p = root / "model/source_map.json"
    if source_map_p.exists():
        errors.gate = "equations_valid"
        source_map = load_json(source_map_p)
        expected_eqs = []
        generated_eq_index = 0
        for page in source_map.get("pages", []):
            for eq in page.get("equations", []):
                generated_eq_index += 1
                if isinstance(eq, dict):
                    if eq.get("display_mode") is False and not eq.get("latex") and not eq.get("fallback_asset"):
                        continue
                    if not eq.get("equation_id"):
                        errors.append(f"source equation entry {generated_eq_index} lacks equation_id")
                        continue
                    expected_eqs.append(eq)
                elif isinstance(eq, str) and eq.strip():
                    expected_eqs.append({"equation_id": f"EQ-p{page.get('number', 1)}-{generated_eq_index}", "raw_text": eq})
                else:
                    errors.append(f"source equation entry {generated_eq_index} is malformed")
        for eq in expected_eqs:
            eid = str(eq["equation_id"])
            if eid not in rendered_evidence:
                errors.append(f"source equation {eid} is missing from the primary narrative")

    for chapter in chapters:
        for block in chapter.get("blocks", []):
            kind = block.get("type")
            if kind in ("figure", "table"):
                errors.gate = "inline_evidence_complete"
                eid = block.get("evidence_id")
                if not eid or not block.get("caption") or not block.get("analysis"):
                    errors.append(f"incomplete inline evidence block: {eid or '<missing id>'}")
                if not block.get("question") or block.get("supports") is None or block.get("limits") is None:
                    errors.append(f"inline evidence binding incomplete: {eid or '<missing id>'}")
                ok, err = _asset_valid(root, block.get("asset"))
                if not ok:
                    errors.append(f"inline {kind} {eid} asset invalid: {err}")
                if block.get("asset") and f"../{block['asset']}" not in parsed_html.images.get(eid, []):
                    errors.append(f"inline {kind} {eid} image is not locally rendered")
                if eid and f'id="evidence-{eid}"' not in main_html and f"id='evidence-{eid}'" not in main_html:
                    errors.append(f"inline {kind} {eid} is not rendered in main Reader")

            elif kind == "equation":
                errors.gate = "equations_valid"
                eid = block.get("evidence_id")
                if not eid:
                    errors.append("equation block missing equation_id")
                confidence = block.get("source_confidence")
                if confidence not in ("VERIFIED", "UNCERTAIN", "AMBIGUOUS", "NOT_STATED"):
                    errors.append(f"equation {eid or '<missing id>'} has invalid source confidence: {confidence!r}")
                verified_latex = normalize_latex(block.get("latex")) if block.get("source_confidence") == "VERIFIED" else None
                if block.get("source_confidence") == "VERIFIED" and not verified_latex:
                    errors.append(f"equation {eid or '<missing id>'} is marked VERIFIED without LaTeX")
                if not verified_latex:
                    fallback = block.get("fallback_asset")
                    ok, err = _asset_valid(root, fallback)
                    if not ok:
                        errors.append(f"equation {eid or '<missing id>'} lacks valid source fallback: {err}")
                    if fallback and f"../{fallback}" not in parsed_html.images.get(eid, []):
                        errors.append(f"equation {eid} fallback is not rendered locally in HTML")
                else:
                    # Per-equation check: ensure MathJax pre-rendered SVG inside the equation block container
                    eq_pat = rf"(?:id=['\"]evidence-{re.escape(eid)}['\"]|<div[^>]*id=['\"]evidence-{re.escape(eid)}['\"])[\s\S]*?(?=<div[^>]*class=['\"][^'\"]*equation-block|<section|</section|$)"
                    m_eq = re.search(eq_pat, main_html)
                    if not m_eq:
                        errors.append(f"equation {eid} is not rendered in main Reader")
                    elif 'latex-display-svg' not in m_eq.group(0) or '<svg' not in m_eq.group(0):
                        errors.append(f"equation {eid} verified LaTeX was not pre-rendered to MathJax SVG")
                    elif any(token in m_eq.group(0) for token in ('data-mml-node="merror"', 'data-mml-node="mtext" data-mjx-error')):
                        errors.append(f"equation {eid} has a MathJax error or unrendered source")

    # 7. Narrative-bearing evidence present in Markdown and PDF
    errors.gate = "html_md_pdf_parity"
    for chapter in chapters:
        for block in chapter.get("blocks", []):
            if block.get("type") in ("figure", "table", "equation") and block.get("evidence_id"):
                eid = block["evidence_id"]
                if _plain_text(eid) not in views["Markdown"]:
                    errors.append(f"evidence {eid} missing from Markdown view")
                if _plain_text(eid) not in views["PDF"]:
                    errors.append(f"evidence {eid} missing from PDF view")

    # 8. Kami visual QA freshness and cryptographic binding
    errors.gate = "visual_review"
    if not artifact_only:
        errors.extend(visual_review_errors(root))
    audit_p = root / "reader/kami_audit.json"
    if not audit_p.exists():
        errors.append("missing Kami visual audit report")
    else:
        audit_data = load_json(audit_p)
        if audit_data.get("status") != "OK":
            errors.append("Kami visual audit failed")
        if pdf_p.exists() and pdf_p.stat().st_mtime > audit_p.stat().st_mtime + 5:
            errors.append("Kami visual audit is stale (PDF modified after audit timestamp)")
        for field, path in (("pdf_sha256", pdf_p), ("html_sha256", html_p)):
            if audit_data.get(field) != sha256(path):
                errors.append(f"Kami visual audit {field} missing or mismatch")

    return _report(errors)

def _report(errors):
    failed = errors.failed
    report = {"schema_version": "2.0", "status": "READER_ACCEPTED" if not errors else "NEEDS_REVIEW",
              "release_ready": False, "errors": list(errors), "diagnostics": errors.diagnostics}
    for gate in GATES:
        passed = gate not in failed and "artifacts" not in failed
        report[gate] = ("PASS" if passed else "NEEDS_REVIEW") if gate == "visual_review" else passed
    return report


def evaluate(root: Path, *, artifact_only=False, regression_report=None):
    """Artifact-only success is never PAPER_COMPLETE; release needs corpus proof."""
    root = Path(root)
    try:
        report = _evaluate_artifact(root, artifact_only=artifact_only)
        report["implementation_sha256"] = implementation_hash()
        if report["status"] == "READER_ACCEPTED":
            report["artifact_hashes"] = bindings(root)
        if not artifact_only:
            from reader_regression import validate_release_report
            corpus_errors = validate_release_report(regression_report)
            report["regression_passed"] = not corpus_errors
            report["errors"].extend(corpus_errors)
            report["diagnostics"].extend({"gate": "regression", "message": e} for e in corpus_errors)
            if report["status"] == "READER_ACCEPTED" and not corpus_errors:
                report["status"] = "PAPER_COMPLETE"
                report["release_ready"] = True
            else:
                report["status"] = "NEEDS_REVIEW"
        return report
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        errors = GateErrors()
        errors.append(f"Reader acceptance input or review is malformed: {type(exc).__name__}: {exc}")
        report = _report(errors)
        report["status"] = "READER_FAILED"
        return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--artifact-only", action="store_true", help="Evaluate one Reader for the regression runner; never reports PAPER_COMPLETE")
    ap.add_argument("--regression-report", help="Hash-bound real-corpus release report (default: evals/reader_regression/release_report.json)")
    args = ap.parse_args()
    root = Path(args.out)
    report = evaluate(root, artifact_only=args.artifact_only, regression_report=args.regression_report)
    out_p = root / "reader/reader_acceptance.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] in ("PAPER_COMPLETE", "READER_ACCEPTED") else 1

if __name__ == "__main__":
    sys.exit(main())
