#!/usr/bin/env python3
"""Render the human-facing Chinese Paper Reader.

Responsibilities:
- Reads semantic narrative manuscript IR: reader/narrative_manuscript.json
  (generates it via narrative_composer_agent if missing).
- Formats narrative manuscript into editorial Kami long-doc HTML: reader/paper_reader.html
- Formats narrative manuscript into editorial Markdown: reader/paper_reader.md
- Renders a continuous paper narrative; audit detail remains in the separately
  rendered Evidence Atlas and is linked only from a quiet appendix.
"""
import argparse, html, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from validate_common import load_json, sha256
# In Reader v3, narrative_manuscript.json is strictly authored by the Lead Writer.
# Deterministic composition is quarantined for legacy compatibility only.
import kami_adapter
from math_text import protect_math, term_html, unrendered_math_errors

def normalize_text_newlines(text: str) -> str:
    """Convert literal escaped '\\n' sequences into actual newlines, preserving LaTeX math commands."""
    if not text:
        return ""
    latex_n_cmds = ("\\nabla", "\\neq", "\\nu", "\\notin", "\\null", "\\ni", "\\neg", "\\ne", "\\natural", "\\nearrow", "\\nwarrow", "\\norm")
    def _repl(m):
        idx = m.start()
        surrounding = text[idx:idx+15]
        if any(surrounding.startswith(cmd) for cmd in latex_n_cmds):
            return m.group(0)
        return "\n"
    return re.sub(r'\\n', _repl, text)

def sanitize_editorial_text(text: str) -> str:
    """Strip internal audit tags and pipeline process vocabulary before rendering."""
    if not text:
        return ""
    text = normalize_text_newlines(text)
    text = re.sub(r'【(?:科学核验|证据核验|核验记录|审查透镜|机制核验|门禁检查|事实核查|事实核验|核验结论|审计标记|核验通过)[^】]*】', '', text)
    text = text.replace("必须严格恪守", "遵循").replace("输入防火墙", "上下文隔离").replace("防火墙机制", "隔离机制")
    text = text.replace("Lead Writer", "科学编辑").replace("Reviewer Lens", "证据审查").replace("Author Lens", "作者解释")
    return text

def esc(x):
    cleaned = sanitize_editorial_text(str(x or ''))
    return html.escape(cleaned)


def esc_math(x):
    """Escape prose while marking mathematics, after editorial sanitizing."""
    return protect_math(sanitize_editorial_text(str(x or '')))

def format_meta_line(authors: str, venue: str, year: any) -> str:
    """Format publication metadata line, ensuring year is never rendered twice."""
    year_str = str(year or '').strip()
    parts = []
    if authors:
        parts.append(authors)
    if venue:
        parts.append(venue)
    if year_str and (not venue or not re.search(rf'\b{re.escape(year_str)}\b', venue)):
        parts.append(year_str)
    return ' · '.join(parts)

FORBIDDEN_MAIN_READER_PHRASES = ('详情见图谱', '图谱详情', '六大透镜', '跨透镜', '六个 Lens', '六个Lens')

def normalize_latex(raw):
    """Normalize a source equation without inventing missing mathematics."""
    value = str(raw or '').strip()
    if value.startswith('\\[') and value.endswith('\\]'):
        value = value[2:-2].strip()
    if value.startswith('$$') and value.endswith('$$'):
        value = value[2:-2].strip()
    depth = 0
    escaped = False
    for ch in value:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0:
                return None
    return value if value and depth == 0 else None

def _render_cites_span(ev_refs, local_ids: set[str] = None) -> str:
    if not ev_refs:
        return ''
    visible = [str(e).strip() for e in ev_refs if str(e).strip().startswith(('F', 'T', 'EQ', 'p.'))]
    if not visible:
        return ''
    links = []
    for e in visible:
        if e.startswith('p.'):
            if local_ids is None or e in local_ids:
                links.append(f'<a href="#{esc(e)}" class="evidence-cite" aria-label="证据 {esc(e)}">[{esc(e)}]</a>')
            else:
                links.append(f'<a href="evidence_atlas.html#{esc(e)}" class="evidence-cite" aria-label="证据 {esc(e)} (图谱)">[{esc(e)}]</a>')
        else:
            target_id = f"evidence-{e}"
            if local_ids is None or target_id in local_ids:
                links.append(f'<a href="#{esc(target_id)}" class="evidence-cite" aria-label="证据 {esc(e)}">[{esc(e)}]</a>')
            else:
                links.append(f'<a href="evidence_atlas.html#{esc(target_id)}" class="evidence-cite" aria-label="证据 {esc(e)} (图谱)">[{esc(e)}]</a>')
    if not links:
        return ''
    return f'<span class="evidence-cites">{" ".join(links)}</span>'

def _inline_evidence_cites(ev_refs, local_ids: set[str] = None):
    span = _render_cites_span(ev_refs, local_ids)
    return f' {span}' if span else ''

def format_cites_in_text_html(text: str, local_ids: set[str] = None) -> tuple[str, set[str]]:
    """Convert in-text Chinese citation brackets 〔...〕 to styled citation spans, tracking cited IDs."""
    cited_refs = set()
    if not text:
        return "", cited_refs
    
    def _repl(match):
        inner = match.group(1)
        raw_items = [x.strip() for x in re.split(r'[,、]', inner) if x.strip()]
        for item in raw_items:
            cited_refs.add(item)
        cites_html = _render_cites_span(raw_items, local_ids)
        return cites_html if cites_html else match.group(0)
    
    formatted = re.sub(r'〔([^〕]+)〕', _repl, text)
    return formatted, cited_refs

KAMI_LONG_DOC_CSS = """
/* Keep release rendering offline and deterministic.  The prior remote font
   fetch could block a release on a CDN/network timeout; installed CJK fonts
   remain the presentation fallback. */

@page {
  size: A4;
  margin: 20mm 22mm 22mm 22mm;
  background: #f5f4ed;

  @top-right {
    content: string(section-title);
    font-family: "TsangerJinKai02", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", Georgia, serif;
    font-size: 8pt;
    color: #6b6a64;
  }

  @bottom-center {
    content: counter(page);
    font-family: "TsangerJinKai02", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", Georgia, serif;
    font-size: 9pt;
    color: #6b6a64;
  }
}

@page:first {
  @top-right { content: ""; }
  @bottom-center { content: ""; }
}

* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --parchment: #f5f4ed;
  --ivory:     #faf9f5;
  --near-black:#141413;
  --dark-warm: #3d3d3a;
  --olive:     #504e49;
  --stone:     #6b6a64;
  --brand:     #1B365D;
  --border:    #e8e6dc;
  --border-soft:#e5e3d8;
  --tag-bg:    #E4ECF5;
  --serif: "TsangerJinKai02", "Source Han Serif SC", "Source Han Serif CN", "Noto Serif CJK SC", "Noto Serif SC", "Songti SC", "STSong", "SimSun", Georgia, serif;
  --sans: var(--serif);
  --rhythm-module: 14pt;
  --rhythm-section: 18pt;
}

html, body {
  background: var(--parchment);
  color: var(--near-black);
  font-family: var(--serif);
  font-size: 10.5pt;
  line-height: 1.55;
  letter-spacing: 0.2pt;
  widows: 3;
  orphans: 3;
}

@media screen {
  body {
    max-width: 210mm;
    margin: 0 auto;
    padding: 20mm 22mm;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  }
}

/* ========== COVER ========== */
.cover {
  min-height: 240mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 36mm 0 0 0;
  break-after: page;
}
.cover-eyebrow {
  font-family: var(--sans);
  font-size: 9.5pt;
  color: var(--brand);
  letter-spacing: 1.5pt;
  text-transform: uppercase;
  font-weight: 500;
  margin-bottom: 18pt;
}
.cover-title {
  font-size: 30pt;
  font-weight: 500;
  color: var(--near-black);
  line-height: 1.25;
  letter-spacing: 0.3pt;
  margin-bottom: 16pt;
}
.cover-sub {
  font-size: 13pt;
  color: var(--olive);
  line-height: 1.5;
  max-width: 90%;
  margin-bottom: 24pt;
}
.cover-meta {
  font-size: 9.5pt;
  color: var(--stone);
  line-height: 1.55;
  border-top: 0.5pt solid var(--border);
  padding-top: 14pt;
}
.cover-meta strong {
  color: var(--dark-warm);
  font-weight: 500;
}

/* ========== TOC ========== */
.toc {
  break-after: page;
  padding-top: 16pt;
}
.toc h2 {
  font-size: 20pt;
  font-weight: 500;
  margin-bottom: var(--rhythm-module);
  color: var(--near-black);
}
.toc-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 7pt 0;
  border-bottom: 0.3pt dotted var(--border);
  font-size: 10.5pt;
}
.toc-num {
  color: var(--brand);
  font-weight: 500;
  min-width: 28pt;
}
.toc-title {
  flex: 1;
  color: var(--near-black);
  text-decoration: none;
  display: block;
}
.toc-title[href]::after {
  content: target-counter(attr(href), page);
  color: var(--stone);
  font-variant-numeric: tabular-nums;
  float: right;
}

/* ========== CHAPTERS ========== */
.chapter {
  break-before: page;
  padding-top: 10pt;
}
.chapter-num {
  font-family: var(--sans);
  font-size: 9.5pt;
  color: var(--brand);
  letter-spacing: 1pt;
  text-transform: uppercase;
  margin-bottom: 6pt;
  font-weight: 500;
}
h1 {
  font-size: 20pt;
  font-weight: 500;
  line-height: 1.25;
  margin: 0 0 10pt 0;
  color: var(--near-black);
  break-after: avoid;
  string-set: section-title content();
}
h2 {
  font-size: 14pt;
  font-weight: 500;
  line-height: 1.3;
  margin: 20pt 0 8pt 0;
  color: var(--near-black);
  break-after: avoid;
}
.lead {
  font-size: 11.5pt;
  line-height: 1.55;
  color: var(--dark-warm);
  margin-bottom: var(--rhythm-module);
  font-style: normal;
  border-left: 2pt solid var(--brand);
  padding-left: 10pt;
}

p {
  margin: 0 0 10pt 0;
  line-height: 1.55;
  color: var(--near-black);
  break-inside: avoid;
}

/* ========== CALLOUTS & TAKEAWAYS ========== */
.callout {
  background: var(--ivory);
  border-left: 2.5pt solid var(--brand);
  padding: 10pt 14pt;
  border-radius: 0 3pt 3pt 0;
  margin: 12pt 0;
  line-height: 1.55;
  break-inside: avoid;
}
.takeaway {
  background: var(--ivory);
  border: 1pt solid var(--border);
  border-radius: 4pt;
  padding: 10pt 14pt;
  margin: 14pt 0;
  break-inside: avoid;
}
.takeaway-label {
  font-family: var(--sans);
  font-size: 8.5pt;
  color: var(--brand);
  letter-spacing: 0.8pt;
  text-transform: uppercase;
  font-weight: 500;
  margin-bottom: 4pt;
}

/* ========== FIGURES & TABLES ========== */
figure.kami-figure {
  margin: 16pt 0;
  break-inside: avoid;
  background: var(--ivory);
  border: 1pt solid var(--border);
  border-radius: 4pt;
  padding: 12pt;
}
figure.kami-figure img {
  max-width: 100%;
  /* Dense multi-panel and architecture figures were unreadable at 520px.
     Full width plus a lightbox gives true 1:1 zoom of the same source file. */
  max-height: 76vh;
  width: auto;
  object-fit: contain;
  cursor: zoom-in;
  display: block;
  margin: 0 auto 8pt auto;
  border-radius: 2pt;
}
figcaption {
  font-family: var(--sans);
  font-size: 9pt;
  color: var(--stone);
  text-align: center;
  margin-bottom: 8pt;
  font-weight: 500;
}
.figure-analysis {
  font-size: 9.5pt;
  color: var(--dark-warm);
  line-height: 1.55;
  border-top: 0.3pt solid var(--border);
  padding-top: 8pt;
}

.equation-block {
  background: var(--ivory);
  border-radius: 4pt;
  padding: 10pt 14pt;
  margin: 12pt 0;
  break-inside: avoid;
  text-align: center;
}
.math-display {
  font-size: 11pt;
  margin: 6pt 0;
}
.math-source { display: inline-block; max-width: 100%; overflow-wrap: anywhere; }
.equation-fallback, .table-asset { max-width: 100%; height: auto; display: block; margin: 6pt auto; }
.equation-uncertain { color: var(--stone); font-style: italic; }
.eq-explanation {
  font-size: 9pt;
  color: var(--ink);
  margin-top: 6pt;
  text-align: left;
  line-height: 1.5;
}
.eq-role {
  font-size: 9pt;
  font-weight: 600;
  color: var(--brand);
  margin-top: 6pt;
  text-align: left;
}
.eq-terms {
  font-size: 8.5pt;
  color: var(--ink);
  margin-top: 6pt;
  text-align: left;
  line-height: 1.5;
}
.eq-terms ul { margin: 3pt 0 3pt 14pt; padding: 0; }
.eq-terms li { margin-bottom: 2pt; }
.eq-proxy {
  font-size: 8.5pt;
  color: var(--stone);
  background: var(--warm-gray, #f8f6f0);
  padding: 4pt 8pt;
  border-radius: 3pt;
  margin-top: 6pt;
  text-align: left;
  border-left: 2pt solid var(--gold, #d97706);
}

/* Quiet evidence anchors */
.evidence-cite {
  display: inline-block;
  white-space: nowrap;
  font-family: var(--sans);
  font-size: 8pt;
  color: var(--brand);
  background: var(--tag-bg);
  padding: 1pt 5pt;
  border-radius: 2pt;
  margin-left: 4pt;
  vertical-align: 1pt;
  text-decoration: none;
}
.evidence-cite:hover {
  text-decoration: underline;
}
.page-anchor {
  display: inline-block;
  margin: 2pt 4pt;
  padding: 1pt 5pt;
  background: var(--ivory);
  border: 1pt solid var(--border);
  border-radius: 3pt;
  font-family: var(--sans);
  font-size: 8.5pt;
}
.page-anchor-link {
  color: var(--brand);
  text-decoration: none;
}
.page-anchor-link:hover {
  text-decoration: underline;
}
@media print {
  body {
    max-width: 100%;
    margin: 0;
    padding: 0;
    box-shadow: none;
    background: transparent;
  }
  .evidence-cite { display: none; }
  .chapter { break-before: page; }
  figure.kami-figure, .takeaway, .callout, .equation-block { break-inside: avoid; }
  figure.kami-figure img, .table-asset, .equation-fallback { max-height: 620px; object-fit: contain; }
}
.evidence-binding { font-family: var(--sans); font-size: 8pt; color: var(--brand); margin-right: 5pt; }

/* ========== SOURCE-IMAGE LIGHTBOX ========== */
/* Scaling the same file the page already shows; never alters the evidence. */
#evidentia-lightbox {
  position: fixed; inset: 0; z-index: 9999; display: none;
  background: rgba(0,0,0,.88); cursor: zoom-out;
  align-items: center; justify-content: center; padding: 2vh 2vw;
}
#evidentia-lightbox.open { display: flex; }
#evidentia-lightbox img { max-width: 96vw; max-height: 96vh; object-fit: contain; background: #fff; }
#evidentia-lightbox .lb-hint {
  position: absolute; top: 10px; left: 0; right: 0; text-align: center;
  color: #ddd; font-family: var(--sans); font-size: 9pt;
}

/* ========== APPENDIX ========== */
.appendix {
  border-top: 0.5pt solid var(--border);
  padding-top: 14pt;
  margin-top: 20pt;
}
.appendix details {
  background: var(--ivory);
  border: 1pt solid var(--border);
  border-radius: 4pt;
  padding: 10pt 14pt;
  margin: 12pt 0;
}
.appendix summary {
  font-weight: 500;
  cursor: pointer;
  color: var(--brand);
}
"""

def _inventory_asset_map(root: Path, kind: str = None) -> dict[str, str]:
    inventory = root / "model" / "figure_inventory.json"
    if not inventory.exists():
        return {}
    data = load_json(inventory)
    asset_map = {}
    for item in data.get("items", []):
        iid = item.get("id")
        if not iid:
            continue
        if kind and item.get("kind") and item.get("kind") != kind:
            continue
        if item.get("needs_visual_review") or item.get("inspection_status") == "NEEDS_REVIEW" or item.get("binding_method") == "VISUAL_BINDING_UNCERTAIN":
            continue
        asset = item.get("file") or item.get("asset")
        if asset:
            asset_map[str(iid)] = str(asset)
    return asset_map


def resolve_visual_asset(block: dict, root: Path):
    """Resolve by canonical evidence identity, never by a stale writer path."""
    eid = block.get("evidence_id")
    block_type = block.get("type")
    inventory_asset = _inventory_asset_map(root, kind=block_type).get(str(eid)) if eid else None
    if inventory_asset and (root / inventory_asset).exists():
        return inventory_asset
    return block.get("asset")


def rebind_visual_assets(manuscript: dict, root: Path) -> list[dict[str, str]]:
    """Repair stale evidence→asset paths through the generic inventory binding."""
    changes = []
    document = manuscript.get("document", {})
    chapters = document.get("sections") or document.get("chapters", [])

    # Pass 1: Collect candidate asset claims across all figure and table blocks.
    candidate_claims: dict[str, set[str]] = {}
    claimants: list[tuple[dict, str, str]] = []
    for chapter in chapters:
        for block in chapter.get("blocks", []):
            if block.get("type") not in ("figure", "table") or not block.get("evidence_id"):
                continue
            eid = str(block["evidence_id"])
            resolved = resolve_visual_asset(block, root)
            if resolved:
                candidate_claims.setdefault(resolved, set()).add(eid)
                claimants.append((block, eid, resolved))

    # Pass 2: Mark any asset claimed by more than one distinct evidence ID as ambiguous.
    ambiguous_assets = {asset for asset, eids in candidate_claims.items() if len(eids) > 1}

    # Pass 3: Leave every claimant of an ambiguous asset unchanged; rebind unambiguous assets.
    for block, eid, resolved in claimants:
        if resolved in ambiguous_assets:
            continue
        if block.get("asset") != resolved:
            changes.append({"evidence_id": eid, "old_asset": block.get("asset"), "new_asset": resolved})
            block["asset"] = resolved
    return changes


def render_block_html(b: dict, root: Path, local_ids: set[str] = None) -> str:
    b_type = b.get('type')
    ev_refs = b.get('evidence_refs', [])
    
    if b_type == 'paragraph':
        text = esc_math(b.get('text', ''))
        text, cited_refs = format_cites_in_text_html(text, local_ids)
        remaining_refs = [r for r in ev_refs if str(r).strip() not in cited_refs]
        trailing_cites = f" {_render_cites_span(remaining_refs, local_ids)}" if remaining_refs else ""
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\n- ', r'<br>• ', text)
        text = re.sub(r'\n(\d+)\. ', r'<br>\1. ', text)
        text = text.replace('\n\n', '</p><p>')
        text = text.replace('\n', '<br>')
        return f"<p>{text}{trailing_cites}</p>"
        
    elif b_type == 'callout':
        text = esc_math(b.get('text', ''))
        text, cited_refs = format_cites_in_text_html(text, local_ids)
        remaining_refs = [r for r in ev_refs if str(r).strip() not in cited_refs]
        trailing_cites = f" {_render_cites_span(remaining_refs, local_ids)}" if remaining_refs else ""
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\n- ', r'<br>• ', text)
        text = re.sub(r'\n(\d+)\. ', r'<br>\1. ', text)
        text = text.replace('\n\n', '</p><p>')
        text = text.replace('\n', '<br>')
        return f"<div class='callout'><p>{text}{trailing_cites}</p></div>"
        
    elif b_type == 'takeaway':
        text = esc_math(b.get('text', ''))
        text, cited_refs = format_cites_in_text_html(text, local_ids)
        remaining_refs = [r for r in ev_refs if str(r).strip() not in cited_refs]
        trailing_cites = f" {_render_cites_span(remaining_refs, local_ids)}" if remaining_refs else ""
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = text.replace('\n', '<br>')
        return f"<div class='takeaway'><div class='takeaway-label'>核心关注</div><p>{text}{trailing_cites}</p></div>"
        
    elif b_type == 'figure':
        fid = b.get('evidence_id', 'FIG')
        cap = esc_math(b.get('caption', ''))
        analysis = esc_math(b.get('analysis', ''))
        analysis, cited_refs = format_cites_in_text_html(analysis, local_ids)
        remaining_refs = [r for r in ev_refs if str(r).strip() not in cited_refs]
        trailing_cites = f" {_render_cites_span(remaining_refs, local_ids)}" if remaining_refs else ""
        analysis = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', analysis)
        analysis = analysis.replace('\n\n', '<br>')
        analysis = analysis.replace('\n', '<br>')
        asset = resolve_visual_asset(b, root)
        img_html = ""
        if asset and (root / asset).exists():
            img_html = f"<img src='../{esc(asset)}' alt='{cap}' onerror=\"this.onerror=null; this.src=this.src.includes('../')?this.src.replace('../',''):('../'+this.src);\" />"
            
        return f"""
        <figure class="kami-figure" id="evidence-{esc(fid)}">
          {img_html}
          <figcaption>{cap} <span class="evidence-binding">〔{esc(fid)}〕</span></figcaption>
          <div class="figure-analysis">{analysis}{trailing_cites}</div>
        </figure>
        """
        
    elif b_type == 'equation':
        raw_latex = b.get('latex')
        raw = normalize_latex(raw_latex) if raw_latex else None
        exp = esc_math(b.get('explanation', ''))
        exp, cited_refs = format_cites_in_text_html(exp, local_ids)
        remaining_refs = [r for r in ev_refs if str(r).strip() not in cited_refs]
        trailing_cites = f" {_render_cites_span(remaining_refs, local_ids)}" if remaining_refs else ""
        eq_id = b.get('evidence_id') or b.get('equation_id') or 'EQ'
        paper_label = b.get('paper_label') or ''
        fallback = b.get('fallback_asset')
        confidence = b.get('source_confidence', 'VERIFIED')

        if raw and confidence == 'VERIFIED':
            math_html = f"<span class='math-source'>\\[ {esc(raw)} \\]</span>"
        elif fallback and (root / fallback).exists():
            math_html = f"<img class='equation-fallback' src='../{esc(fallback)}' alt='公式源图 {esc(eq_id)}' onerror=\"this.onerror=null; this.src=this.src.includes('../')?this.src.replace('../',''):('../'+this.src);\" />"
        elif raw:
            math_html = f"<span class='math-source'>\\[ {esc(raw)} \\]</span>"
        else:
            default_asset = f"assets/equations/{eq_id}.png"
            if (root / default_asset).exists():
                math_html = f"<img class='equation-fallback' src='../{esc(default_asset)}' alt='公式源图 {esc(eq_id)}' onerror=\"this.onerror=null; this.src=this.src.includes('../')?this.src.replace('../',''):('../'+this.src);\" />"
            else:
                math_html = f"<div class='equation-uncertain-trace'>公式源图已锁定于源文档 p.{b.get('page', 1)}。</div>"

        label_display = f"公式 {esc(paper_label)} 〔{esc(eq_id)}〕" if paper_label else f"公式 {esc(eq_id)}"
        ped = b.get('pedagogy') or {}
        role = ped.get('role') or b.get('role_zh') or ''
        term_interps = ped.get('term_interpretations') or b.get('term_interpretations') or []
        proxy = ped.get('implementation_proxy') or b.get('implementation_proxy')

        pedagogy_html = ""
        if role:
            pedagogy_html += f"<div class='eq-role'>角色定位：{esc(role)}</div>"
        if term_interps:
            # A glossary term is mathematics; <code> is skipped by the MathJax
            # pipeline and produced literal \mathbf{D}\mathbf{A} (Issue #48).
            terms_li = "".join(
                f"<li>{term_html(t.get('term', ''))}（{esc(t.get('role', '项'))}）：{protect_math(t.get('intuition', ''))}</li>"
                for t in term_interps if t.get('term')
            )
            pedagogy_html += f"<div class='eq-terms'><strong>核心项解析与数学直觉</strong>：<ul>{terms_li}</ul></div>"
        if proxy:
            pedagogy_html += f"<div class='eq-proxy'><strong>工程实现与代理说明</strong>：{esc(proxy)}</div>"

        return f"""
        <div class='equation-block' id='evidence-{esc(eq_id)}'>
          <div class='eq-label'>{label_display}</div>
          <div class='math-display'>{math_html}</div>
          <div class='eq-explanation'>{exp}{trailing_cites}</div>
          {pedagogy_html}
        </div>
        """
        
    elif b_type == 'table':
        tid = b.get('evidence_id', 'TAB')
        cap = esc_math(b.get('caption', ''))
        analysis = esc_math(b.get('analysis', ''))
        analysis, cited_refs = format_cites_in_text_html(analysis, local_ids)
        remaining_refs = [r for r in ev_refs if str(r).strip() not in cited_refs]
        trailing_cites = f" {_render_cites_span(remaining_refs, local_ids)}" if remaining_refs else ""
        analysis = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', analysis)
        img_html = ''
        asset = resolve_visual_asset(b, root)
        if asset and (root / asset).exists():
            img_html = f"<img src='../{esc(asset)}' alt='{cap}' class='table-asset' onerror=\"this.onerror=null; this.src=this.src.includes('../')?this.src.replace('../',''):('../'+this.src);\" />"
        return f"""
        <div class="takeaway" id="evidence-{esc(tid)}">
          <div class="takeaway-label">{cap} <span class="evidence-binding">〔{esc(tid)}〕</span></div>
          {img_html}
          <div style="font-size:9.5pt; margin-top:6pt;">{analysis}{trailing_cites}</div>
        </div>
        """
        
    elif b_type == 'list':
        items = b.get('items', [])
        li_html = "".join([f"<li>{esc(it)}</li>" for it in items])
        return f"<ul>{li_html}</ul>"
        
    return ""

def render_paper_reader_html(manuscript: dict, root: Path) -> str:
    """Render the story as an editorial document, without audit vocabulary."""
    doc = manuscript.get('document', {})
    title = doc.get('title', '未命名论文')
    subtitle = doc.get('subtitle', '中文科学精读稿')
    orientation = doc.get('orientation') or doc.get('executive_summary') or {}
    meta = doc.get('paper_meta', {})
    authors = meta.get('authors', [])
    authors_str = '、'.join(authors) if authors else ''
    venue = meta.get('venue') or ''
    if (meta.get('preprint_status') == 'PREPRINT' or meta.get('peer_reviewed_status') == 'UNVERIFIED') and not meta.get('venue_verified_externally'):
        if venue and not any(kw in venue.lower() for kw in ('preprint', 'unverified', 'arxiv')):
            venue = f"{venue} (preprint · venue unverified)"
    year = meta.get('year') or ''
    # Dynamic sections are the canonical presentation sequence. `chapters` is
    # accepted only as a compatibility alias for older manuscripts.
    chapters = doc.get('sections') or doc.get('chapters', [])

    pm = load_json(root / 'model/paper_model.json') if (root / 'model/paper_model.json').exists() else {}

    # Pass 1: Collect all page numbers and local element IDs to ensure 100% anchor resolution
    page_nums = {1}
    for item in pm.get('claims', []) + pm.get('figures', []) + pm.get('tables', []):
        if item.get('page'):
            try: page_nums.add(int(item['page']))
            except (ValueError, TypeError): pass
        for ref in item.get('evidence', []):
            if str(ref).startswith('p.'):
                try: page_nums.add(int(str(ref)[2:]))
                except (ValueError, TypeError): pass

    local_ids = {'ch-sources'}
    for idx, chapter in enumerate(chapters, 1):
        cid = chapter.get('id', f'spine-{idx:02d}')
        local_ids.add(f'ch-{cid}')
        for block in chapter.get('blocks', []):
            b_type = block.get('type')
            if b_type == 'figure' and block.get('evidence_id'):
                local_ids.add(f"evidence-{block['evidence_id']}")
            elif b_type == 'equation':
                eq_id = block.get('evidence_id') or block.get('equation_id')
                if eq_id:
                    local_ids.add(f"evidence-{eq_id}")
            elif b_type == 'table' and block.get('evidence_id'):
                local_ids.add(f"evidence-{block['evidence_id']}")

            if block.get('page'):
                try: page_nums.add(int(block['page']))
                except (ValueError, TypeError): pass
            for ref in block.get('evidence_refs', []):
                if str(ref).startswith('p.'):
                    try: page_nums.add(int(str(ref)[2:]))
                    except (ValueError, TypeError): pass
            text_probe = (block.get('text') or '') + ' ' + (block.get('analysis') or '') + ' ' + (block.get('caption') or '')
            for m in re.finditer(r'\bp\.(\d+)\b', text_probe):
                page_nums.add(int(m.group(1)))

    for n in page_nums:
        local_ids.add(f"p.{n}")

    toc_items = []
    for idx, chapter in enumerate(chapters, 1):
        cid = chapter.get('id', f'spine-{idx:02d}')
        toc_items.append(f"<div class='toc-item'><a class='toc-title' href='#ch-{esc(cid)}'><span class='toc-num'>{idx:02d}</span> · {esc(chapter.get('title', ''))}</a></div>")
    toc_items.append(f"<div class='toc-item'><a class='toc-title' href='#ch-sources'><span class='toc-num'>{len(chapters)+1:02d}</span> · 证据来源与页面锚点</a></div>")
    
    chapters_html = []
    for idx, chapter in enumerate(chapters, 1):
        cid = chapter.get('id', f'spine-{idx:02d}')
        blocks = '\n'.join(render_block_html(block, root, local_ids=local_ids) for block in chapter.get('blocks', []))
        lead_text = chapter.get('lead_paragraph') or chapter.get('lead', '')
        chapters_html.append(f"<section class='chapter' id='ch-{esc(cid)}'><h1>{esc(chapter.get('title', ''))}</h1><div class='lead'>{esc(lead_text)}</div><div class='chapter-body'>{blocks}</div></section>")
    
    app = doc.get('appendix_summary', {})
    has_pdf = (root / 'source/paper.pdf').exists()
    pdf_href = '../source/paper.pdf' if has_pdf else None
    anchors = []
    for n in sorted(page_nums):
        if pdf_href:
            anchors.append(f"<span class='page-anchor' id='p.{n}'><a href='{pdf_href}#page={n}' target='_blank' rel='noopener' class='page-anchor-link'>p.{n}</a></span>")
        else:
            anchors.append(f"<span class='page-anchor' id='p.{n}'>p.{n}</span>")
    refs_html = '、'.join(anchors)

    appendix = f"""
    <section class='chapter appendix' id='ch-sources'>
      <h1>证据来源与页面锚点</h1>
      <div class='lead'>正文中的图表、公式和引文都保留了返回源材料的线索；需要逐项核对时可打开独立的审计视图。</div>
      <p>当前稿件引用了 {app.get('claims_count', len(pm.get('claims', [])))} 条主张、{app.get('figures_count', len(pm.get('figures', [])))} 组图表和 {app.get('tables_count', len(pm.get('tables', [])))} 张数据表。</p>
      <p>页面锚点：{refs_html}</p>
      <p><a href='evidence_atlas.html'>查看逐项来源与核验记录</a></p>
    </section>
    """
    meta_line = format_meta_line(authors_str, venue, year)
    return f"""<!doctype html>
<html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>{esc(title)}</title><style>{KAMI_LONG_DOC_CSS}</style></head>
<body>
<section class='cover'><div><div class='cover-title'>{esc(title)}</div><div class='cover-sub'>{esc(subtitle)}</div></div><div class='cover-meta'>{esc(meta_line)}</div>{('<div class="cover-orientation">' + esc(orientation.get('lead')) + '</div>') if orientation.get('lead') else ''}</section>
<section class='toc'><h2>目录</h2>{''.join(toc_items)}</section>
{''.join(chapters_html)}
{appendix}
<div id="evidentia-lightbox" role="dialog" aria-label="查看原始图片">
  <div class="lb-hint">点击任意位置关闭 · 图片为源文件原始像素</div>
  <img alt="" />
</div>
<script>
(function () {{
  var box = document.getElementById('evidentia-lightbox');
  if (!box) return;
  var img = box.querySelector('img');
  document.addEventListener('click', function (event) {{
    var target = event.target;
    if (target === box || target === img) {{ box.classList.remove('open'); img.src = ''; return; }}
    if (target && target.tagName === 'IMG' && target.closest('figure.kami-figure')) {{
      img.src = target.getAttribute('src');
      img.alt = target.getAttribute('alt') || '';
      box.classList.add('open');
    }}
  }});
  document.addEventListener('keydown', function (event) {{
    if (event.key === 'Escape') {{ box.classList.remove('open'); img.src = ''; }}
  }});
}})();
</script>
</body></html>"""

def render_paper_reader_md(manuscript: dict, root=None) -> str:
    doc = manuscript.get('document', {})
    title = doc.get('title', '未命名论文')
    subtitle = doc.get('subtitle', '中文科学精读稿')
    orientation = doc.get('orientation') or doc.get('executive_summary') or {}
    meta = doc.get('paper_meta', {})
    authors = '、'.join(meta.get('authors', [])) if meta.get('authors') else ''
    venue_md = meta.get('venue') or ''
    if (meta.get('preprint_status') == 'PREPRINT' or meta.get('peer_reviewed_status') == 'UNVERIFIED') and not meta.get('venue_verified_externally'):
        if venue_md and not any(kw in venue_md.lower() for kw in ('preprint', 'unverified', 'arxiv')):
            venue_md = f"{venue_md} (preprint · venue unverified)"
    meta_line = format_meta_line(authors, venue_md, meta.get('year'))
    lines = [f'# {title}', f'**{subtitle}**', '', meta_line, '']
    if orientation.get('lead'):
        lines.extend([f'> {orientation.get("lead")}', ''])
    lines.extend(['---', '', '## 目录'])
    chapters = doc.get('sections') or doc.get('chapters', [])
    for idx, chapter in enumerate(chapters, 1):
        lines.append(f"{idx}. [{chapter.get('title', '')}](# {chapter.get('id', '')})".replace('# ', '#'))
    lines.append(f"{len(chapters)+1}. [证据来源与页面锚点](#sources)")
    lines.extend(['', '---', ''])
    for idx, chapter in enumerate(chapters, 1):
        cid = chapter.get('id', f'spine-{idx:02d}')
        lead_text = sanitize_editorial_text(chapter.get('lead_paragraph') or chapter.get('lead', ''))
        lines.extend([f"## {idx}. {chapter.get('title', '')} <a id='{cid}'></a>", '', f"> *{lead_text}*", ''])
        for block in chapter.get('blocks', []):
            kind = block.get('type')
            text = sanitize_editorial_text(block.get('text', ''))
            refs = [str(r).strip() for r in block.get('evidence_refs', []) if str(r).strip()]
            in_text_cites = {r.strip() for m in re.finditer(r'〔([^〕]+)〕', text) for r in re.split(r'[,、]', m.group(1)) if r.strip()}
            remaining_refs = [r for r in refs if r not in in_text_cites]
            cite = f" 〔{', '.join(remaining_refs)}〕" if remaining_refs else ''
            if kind in ('paragraph', 'callout', 'takeaway'):
                lines.append(f"{text}{cite}\n")
            elif kind in ('figure', 'table'):
                caption = sanitize_editorial_text(block.get('caption', '图表'))
                eid = block.get('evidence_id')
                heading = f"### {caption} 〔{eid}〕\n" if eid else f"### {caption}\n"
                lines.append(heading)
                asset = resolve_visual_asset(block, root) if root else block.get('asset')
                if asset: lines.append(f"![{caption}]({asset})\n")
                analysis = sanitize_editorial_text(block.get('analysis', ''))
                in_text_analysis = {r.strip() for m in re.finditer(r'〔([^〕]+)〕', analysis) for r in re.split(r'[,、]', m.group(1)) if r.strip()}
                remaining_analysis_refs = [r for r in refs if r not in in_text_analysis]
                cite_analysis = f" 〔{', '.join(remaining_analysis_refs)}〕" if remaining_analysis_refs else ''
                lines.append(f"{analysis}{cite_analysis}\n")
            elif kind == 'equation':
                eq_id = block.get('evidence_id') or block.get('equation_id') or 'EQ'
                paper_label = block.get('paper_label', '')
                lbl = f"（{paper_label} · {eq_id}）" if paper_label else f"（{eq_id}）"
                lines.append(f"{lbl}\n")
                raw_latex = block.get('latex')
                latex = normalize_latex(raw_latex) if raw_latex else None
                fallback = block.get('fallback_asset') or f"assets/equations/{eq_id}.png"
                if latex:
                    lines.append(f"$$\n{latex}\n$$\n")
                elif fallback and root and (root / fallback).exists():
                    lines.append(f"![公式源图 {eq_id}]({fallback})\n")
                else:
                    lines.append(f"![公式源图 {eq_id}](assets/equations/{eq_id}.png)\n")
                explanation = sanitize_editorial_text(block.get('explanation', ''))
                in_text_exp = {r.strip() for m in re.finditer(r'〔([^〕]+)〕', explanation) for r in re.split(r'[,、]', m.group(1)) if r.strip()}
                remaining_exp_refs = [r for r in refs if r not in in_text_exp]
                cite_exp = f" 〔{', '.join(remaining_exp_refs)}〕" if remaining_exp_refs else ''
                lines.append(f"{explanation}{cite_exp}\n")
                ped = block.get('pedagogy') or {}
                role = ped.get('role') or block.get('role_zh')
                term_interps = ped.get('term_interpretations') or block.get('term_interpretations') or []
                proxy = ped.get('implementation_proxy') or block.get('implementation_proxy')
                if role:
                    lines.append(f"**角色定位**：{role}\n")
                if term_interps:
                    lines.append("**核心项解析与数学直觉**：")
                    for t in term_interps:
                        if t.get('term'):
                            lines.append(f"- `{t.get('term')}`（{t.get('role', '项')}）：{t.get('intuition', '')}")
                    lines.append("")
                if proxy:
                    lines.append(f"**工程实现与代理说明**：{proxy}\n")
            elif kind == 'list':
                lines.extend([f'- {item}' for item in block.get('items', [])]); lines.append('')
    lines.extend(['## 证据来源与页面锚点 <a id=\'sources\'></a>', '', '需要逐项核对来源时，请打开 [来源与核验记录](evidence_atlas.html)。', ''])
    return '\n'.join(lines) + '\n'

def duplicate_asset_errors(manuscript: dict, root: Path) -> list[str]:
    """Detect two different evidence items backed by byte-identical images.

    Fig. 11 showing Fig. 9's bytes is the failure this prevents (#45).
    """
    seen: dict[str, str] = {}
    errors: list[str] = []
    for chapter in manuscript.get('document', {}).get('chapters', []):
        for block in chapter.get('blocks', []):
            if block.get('type') not in ('figure', 'table'):
                continue
            asset = resolve_visual_asset(block, root)
            if not asset:
                continue
            path = root / asset
            if not path.is_file():
                continue
            try:
                digest = sha256(path)
            except OSError:
                continue
            eid = str(block.get('evidence_id') or block.get('id') or '?')
            if digest in seen and seen[digest] != eid:
                errors.append(
                    f"{seen[digest]} and {eid} both resolve to {asset} (sha256 {digest[:12]}); "
                    "one of them is bound to the wrong image"
                )
            else:
                seen[digest] = eid
    return errors


def render_paper_reader(root: Path, kami_root: Path = None) -> dict:
    """Render the primary Paper Reader HTML, Markdown, and PDF."""
    reader_dir = root / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)
    
    manuscript_p = reader_dir / 'narrative_manuscript.json'
    if manuscript_p.exists():
        manuscript = load_json(manuscript_p)
    elif os.environ.get("EVIDENTIA_ALLOW_LEGACY_COMPOSER") == "1":
        from narrative_composer_agent import compose_narrative_manuscript
        manuscript = compose_narrative_manuscript(root)
    else:
        raise FileNotFoundError(
            f"Missing canonical Lead Writer manuscript at {manuscript_p}. "
            "In Reader v3, the narrative manuscript must be produced by the strong-model Lead Writer. "
            "Deterministic composition is deprecated and prohibited in production."
        )
    # Two distinct figures must never share one image file (Issue #45).
    if os.environ.get('EVIDENTIA_ALLOW_SHARED_ASSETS') != '1':
        collisions = duplicate_asset_errors(manuscript, root)
        if collisions:
            raise ValueError(
                "distinct evidence items resolve to identical image bytes; refusing to render:\n  "
                + "\n  ".join(collisions)
            )

    binding_changes = rebind_visual_assets(manuscript, root)
    manuscript_p.write_text(json.dumps(manuscript, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if binding_changes:
        (reader_dir / 'visual_binding_repair.json').write_text(
            json.dumps({
                'schema_version': '1.0',
                'method': 'EVIDENCE_ID_TO_INVENTORY_ASSET',
                'changes': binding_changes,
                'inventory_sha256': sha256(root / 'model/figure_inventory.json'),
            }, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
        )

    html_content = kami_adapter.render_math_html(render_paper_reader_html(manuscript, root), kami_root=kami_root)

    # Deterministic math gate (Issue #48): a rendered Reader must never show raw
    # TeX. Whether a formula is CORRECT is the source review's job (Issue #46).
    math_errors = unrendered_math_errors(html_content)
    if math_errors:
        raise ValueError(
            "Reader HTML still contains unrendered mathematics; refusing to publish:\n  "
            + "\n  ".join(math_errors)
        )

    html_file = reader_dir / 'paper_reader.html'
    html_file.write_text(html_content, encoding='utf-8')
    
    md_content = render_paper_reader_md(manuscript, root)
    md_file = reader_dir / 'paper_reader.md'
    md_file.write_text(md_content, encoding='utf-8')
    
    pdf_file = reader_dir / 'paper_reader.pdf'
    pages = kami_adapter.build_kami_document(html_content, pdf_file, base_url=str(reader_dir), kami_root=kami_root)
    
    print(f"OK: Rendered Paper Reader -> {html_file}, {md_file}, {pdf_file} ({pages} pages)")
    return {
        "html": str(html_file),
        "md": str(md_file),
        "pdf": str(pdf_file),
        "pages": pages
    }

def main():
    ap = argparse.ArgumentParser(description="Render Paper Reader long-document.")
    ap.add_argument('--out', required=True, help="Workspace run directory")
    ap.add_argument('--kami-root', default=None, help="Path to Kami skill/clone")
    args = ap.parse_args()
    render_paper_reader(Path(args.out), kami_root=args.kami_root)
    return 0

if __name__ == '__main__':
    sys.exit(main())
