#!/usr/bin/env python3
"""Deterministic Reader Delivery Integrity Auditor (Issue #43).

Verifies that delivered HTML/Markdown/PDF outputs meet publication criteria:
1. Zero unresolved internal fragment targets (every <a href="#id"> has a matching id="id" in DOM)
2. Zero self-loop anchors (no <a id="X" href="#X">)
3. Zero literal unparsed backslash+n sequences in rendered text (distinguishing LaTeX math)
4. Clean cover metadata (publication year rendered once, no '2026 · 2026')
5. Clean citation markers (no duplicate [p.1] [p.1] or 〔p.1〕 [p.1] pills)
6. Relative image asset paths exist on disk
"""
from __future__ import annotations
import argparse
import html as html_lib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json


class DeliveryHTMLParser(HTMLParser):
    """Parse HTML DOM to inspect fragment links, IDs, self-loops, and literal escapes."""
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: Set[str] = set()
        self.hrefs: List[Dict[str, Any]] = []
        self.self_links: List[str] = []
        self.images: List[Dict[str, Any]] = []
        self.text_nodes: List[str] = []
        self.current_tag_stack: List[Tuple[str, Dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        elem_id = attr_dict.get("id")
        if elem_id:
            self.ids.add(elem_id)

        href = attr_dict.get("href")
        if tag == "a" and href and href.startswith("#"):
            target = href[1:]
            self.hrefs.append({
                "target": target,
                "href": href,
                "id": elem_id
            })
            if elem_id and elem_id == target:
                self.self_links.append(elem_id)

        if tag == "img":
            src = attr_dict.get("src")
            if src:
                self.images.append({
                    "src": src,
                    "alt": attr_dict.get("alt", "")
                })

        if tag not in self.VOID_TAGS:
            self.current_tag_stack.append((tag, attr_dict))

    def handle_endtag(self, tag: str):
        for idx in range(len(self.current_tag_stack) - 1, -1, -1):
            if self.current_tag_stack[idx][0] == tag:
                del self.current_tag_stack[idx:]
                break

    def handle_data(self, data: str):
        # Exclude style and script contents from text node analysis
        if any(t[0] in ("style", "script") for t in self.current_tag_stack):
            return
        if data.strip():
            self.text_nodes.append(data)


def audit_delivery_integrity(
    html_text: str,
    md_text: Optional[str] = None,
    root: Optional[Path] = None
) -> Dict[str, Any]:
    """Audit delivery integrity of HTML and Markdown artifacts."""
    errors: List[str] = []
    diagnostics: Dict[str, Any] = {}

    parser = DeliveryHTMLParser()
    parser.feed(html_text)

    # 1. Check unresolved internal fragment targets
    unresolved_targets = sorted(list(set(h["target"] for h in parser.hrefs if h["target"] not in parser.ids)))
    if unresolved_targets:
        msg = f"Found {len(unresolved_targets)} unresolved internal fragment targets: {unresolved_targets}"
        errors.append(msg)
        diagnostics["unresolved_targets"] = unresolved_targets
    else:
        diagnostics["unresolved_targets"] = []

    # 2. Check self-loop anchors
    if parser.self_links:
        msg = f"Found {len(parser.self_links)} self-loop anchor links (href points to own element id): {parser.self_links}"
        errors.append(msg)
        diagnostics["self_links"] = parser.self_links
    else:
        diagnostics["self_links"] = []

    # 3. Check literal backslash+n sequences
    # Distinguish legitimate LaTeX math commands: \nabla, \neq, \nu, \notin, \null, \ni, \neg, \ne, \natural
    latex_n_cmds = ("\\nabla", "\\neq", "\\nu", "\\notin", "\\null", "\\ni", "\\neg", "\\ne", "\\natural", "\\nearrow", "\\nwarrow", "\\norm")
    literal_slash_n_matches = []
    for m in re.finditer(r'\\n', html_text):
        idx = m.start()
        surrounding = html_text[idx:idx+15]
        is_latex = any(surrounding.startswith(cmd) for cmd in latex_n_cmds)
        if not is_latex:
            context_snippet = html_text[max(0, idx-20):min(len(html_text), idx+25)]
            literal_slash_n_matches.append(context_snippet.replace("\n", " "))

    if literal_slash_n_matches:
        msg = f"Found {len(literal_slash_n_matches)} literal unparsed '\\n' sequence(s) in HTML content."
        errors.append(msg)
        diagnostics["literal_slash_n"] = literal_slash_n_matches[:10]
    else:
        diagnostics["literal_slash_n"] = []

    # 4. Check cover metadata for duplicate year (e.g. '2026 · 2026')
    dup_year_match = re.search(r'\b(20\d\d)\s*·\s*\1\b', html_text)
    if dup_year_match:
        msg = f"Cover metadata contains duplicated year: '{dup_year_match.group(0)}'."
        errors.append(msg)
        diagnostics["duplicate_year"] = dup_year_match.group(0)
    else:
        diagnostics["duplicate_year"] = None

    # 5. Check duplicate citation pill patterns in prose
    # Pattern a: in-text 〔...〕 directly followed by <span class="evidence-cites">...</span>
    dup_cites = re.findall(r'〔[^〕]*〕\s*<span class=[\'"]evidence-cites', html_text)
    # Pattern b: duplicate markdown brackets 〔...〕 〔...〕
    if md_text:
        md_dup_cites = re.findall(r'〔[^〕]*〕\s*〔[^〕]*〕', md_text)
        dup_cites.extend(md_dup_cites)

    if dup_cites:
        msg = f"Found {len(dup_cites)} duplicate citation pill occurrence(s) in prose."
        errors.append(msg)
        diagnostics["duplicate_citations"] = len(dup_cites)
    else:
        diagnostics["duplicate_citations"] = 0

    # 6. Check relative image asset paths if root is available
    missing_assets = []
    if root:
        root_path = Path(root)
        reader_dir = root_path / "reader"
        for img in parser.images:
            src = img["src"]
            # Ignore absolute URLs or data URIs
            if src.startswith(("http://", "https://", "data:")):
                continue
            # Handle standard ../ relative to reader/
            if src.startswith("../"):
                target_file = root_path / src[3:]
            else:
                target_file = reader_dir / src
                if not target_file.exists():
                    target_file = root_path / src
            if not target_file.exists():
                missing_assets.append(src)

    if missing_assets:
        msg = f"Referenced image asset(s) not found on disk: {missing_assets}"
        errors.append(msg)
        diagnostics["missing_assets"] = missing_assets
    else:
        diagnostics["missing_assets"] = []

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "diagnostics": diagnostics,
        "total_ids": len(parser.ids),
        "total_hrefs": len(parser.hrefs)
    }


def main():
    ap = argparse.ArgumentParser(description="Evidentia Reader Delivery Integrity Auditor")
    ap.add_argument("--html", required=True, help="Path to paper_reader.html")
    ap.add_argument("--md", help="Path to paper_reader.md")
    ap.add_argument("--root", help="Workspace root directory")
    args = ap.parse_args()

    html_p = Path(args.html)
    if not html_p.exists():
        sys.stderr.write(f"HTML file not found: {html_p}\n")
        sys.exit(1)

    html_content = html_p.read_text(encoding="utf-8")
    md_content = Path(args.md).read_text(encoding="utf-8") if args.md and Path(args.md).exists() else None
    root_p = Path(args.root) if args.root else html_p.parent.parent

    result = audit_delivery_integrity(html_content, md_content, root_p)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["status"] != "PASS":
        sys.stderr.write("\n".join(result["errors"]) + "\n")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
