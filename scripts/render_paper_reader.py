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
from narrative_composer_agent import compose_narrative_manuscript, clean_visible_narrative
import kami_adapter

def esc(x):
    return html.escape(str(x or ''))

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

def _inline_evidence_cites(ev_refs):
    if not ev_refs:
        return ''
    # Only source assets and page anchors have destinations in the human
    # surface; claim IDs remain in the semantic IR and Atlas.
    visible = [e for e in ev_refs if str(e).startswith(('F', 'T', 'EQ', 'p.'))]
    cites = ' '.join(f'<a href="#{esc(e) if str(e).startswith("p.") else "evidence-" + esc(e)}" class="evidence-cite" aria-label="证据 {esc(e)}">[{esc(e)}]</a>' for e in visible)
    if not cites:
        return ''
    return f' <span class="evidence-cites">{cites}</span>'

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
  max-height: 380px;
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
  color: var(--stone);
  margin-top: 4pt;
  text-align: left;
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
@media print {
  .evidence-cite { display: none; }
}
.evidence-binding { font-family: var(--sans); font-size: 8pt; color: var(--brand); margin-right: 5pt; }

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


def render_block_html(b: dict, root: Path) -> str:
    b_type = b.get('type')
    ev_refs = b.get('evidence_refs', [])
    cites = _inline_evidence_cites(ev_refs) if ev_refs else ""
    
    if b_type == 'paragraph':
        text = esc(b.get('text', ''))
        # support basic markdown bold in text
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\n- ', r'<br>• ', text)
        text = text.replace('\n\n', '</p><p>')
        return f"<p>{text}{cites}</p>"
        
    elif b_type == 'callout':
        text = esc(b.get('text', ''))
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\n- ', r'<br>• ', text)
        text = text.replace('\n\n', '</p><p>')
        return f"<div class='callout'><p>{text}{cites}</p></div>"
        
    elif b_type == 'takeaway':
        text = esc(b.get('text', ''))
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return f"<div class='takeaway'><div class='takeaway-label'>核心关注</div><p>{text}{cites}</p></div>"
        
    elif b_type == 'figure':
        fid = b.get('evidence_id', 'FIG')
        cap = esc(b.get('caption', ''))
        analysis = esc(b.get('analysis', ''))
        analysis = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', analysis)
        analysis = analysis.replace('\n\n', '<br>')
        asset = resolve_visual_asset(b, root)
        img_html = ""
        if asset and (root / asset).exists():
            img_html = f"<img src='../{esc(asset)}' alt='{cap}' />"
            
        return f"""
        <figure class="kami-figure" id="evidence-{esc(fid)}">
          {img_html}
          <figcaption>{cap} <span class="evidence-binding">〔{esc(fid)}〕</span></figcaption>
          <div class="figure-analysis">{analysis}{cites}</div>
        </figure>
        """
        
    elif b_type == 'equation':
        raw = normalize_latex(b.get('latex')) if b.get('source_confidence') == 'VERIFIED' else None
        exp = esc(b.get('explanation', ''))
        eq_id = b.get('evidence_id', 'EQ')
        fallback = b.get('fallback_asset')
        if raw:
            math_html = f"<span class='math-source'>\\[ {esc(raw)} \\]</span>"
        elif fallback and (root / fallback).exists():
            math_html = f"<img class='equation-fallback' src='../{esc(fallback)}' alt='公式源图 {esc(eq_id)}' />"
        else:
            math_html = "<span class='equation-uncertain'>公式无法可靠重建；已保留源证据状态。</span>"
        return f"""
        <div class='equation-block' id='evidence-{esc(eq_id)}'>
          <div class='eq-label'>公式 {esc(eq_id)}</div>
          <div class='math-display'>{math_html}</div>
          <div class='eq-explanation'>{exp}</div>
        </div>
        """
        
    elif b_type == 'table':
        tid = b.get('evidence_id', 'TAB')
        cap = esc(b.get('caption', ''))
        analysis = esc(b.get('analysis', ''))
        analysis = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', analysis)
        img_html = ''
        asset = resolve_visual_asset(b, root)
        if asset and (root / asset).exists():
            img_html = f"<img src='../{esc(asset)}' alt='{cap}' class='table-asset' />"
        return f"""
        <div class="takeaway" id="evidence-{esc(tid)}">
          <div class="takeaway-label">{cap} <span class="evidence-binding">〔{esc(tid)}〕</span></div>
          {img_html}
          <div style="font-size:9.5pt; margin-top:6pt;">{analysis}{cites}</div>
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
    year = meta.get('year') or ''
    # Dynamic sections are the canonical presentation sequence. `chapters` is
    # accepted only as a compatibility alias for older manuscripts.
    chapters = doc.get('sections') or doc.get('chapters', [])
    toc_items = []
    for idx, chapter in enumerate(chapters, 1):
        cid = chapter.get('id', f'spine-{idx:02d}')
        toc_items.append(f"<div class='toc-item'><a class='toc-title' href='#ch-{esc(cid)}'><span class='toc-num'>{idx:02d}</span> · {esc(chapter.get('title', ''))}</a></div>")
    toc_items.append(f"<div class='toc-item'><a class='toc-title' href='#ch-sources'><span class='toc-num'>{len(chapters)+1:02d}</span> · 证据来源与页面锚点</a></div>")
    chapters_html = []
    for idx, chapter in enumerate(chapters, 1):
        cid = chapter.get('id', f'spine-{idx:02d}')
        blocks = '\n'.join(render_block_html(block, root) for block in chapter.get('blocks', []))
        chapters_html.append(f"<section class='chapter' id='ch-{esc(cid)}'><h1>{esc(chapter.get('title', ''))}</h1><div class='lead'>{esc(chapter.get('lead', ''))}</div><div class='chapter-body'>{blocks}</div></section>")
    app = doc.get('appendix_summary', {})
    refs = []
    pm = load_json(root / 'model/paper_model.json') if (root / 'model/paper_model.json').exists() else {}
    page_nums = {1}
    for item in pm.get('claims', []) + pm.get('figures', []) + pm.get('tables', []):
        if item.get('page'): page_nums.add(item['page'])
        for ref in item.get('evidence', []):
            if str(ref).startswith('p.'):
                try: page_nums.add(int(str(ref)[2:]))
                except ValueError: pass
    refs_html = '、'.join(f"<a id='p.{n}' href='#p.{n}'>p.{n}</a>" for n in sorted(page_nums))
    appendix = f"""
    <section class='chapter appendix' id='ch-sources'>
      <h1>证据来源与页面锚点</h1>
      <div class='lead'>正文中的图表、公式和引文都保留了返回源材料的线索；需要逐项核对时可打开独立的审计视图。</div>
      <p>当前稿件引用了 {app.get('claims_count', len(pm.get('claims', [])))} 条主张、{app.get('figures_count', len(pm.get('figures', [])))} 组图表和 {app.get('tables_count', len(pm.get('tables', [])))} 张数据表。</p>
      <p>页面锚点：{refs_html}</p>
      <p><a href='evidence_atlas.html'>查看逐项来源与核验记录</a></p>
    </section>
    """
    meta_line = ' · '.join(x for x in (authors_str, venue, str(year)) if x)
    return f"""<!doctype html>
<html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>{esc(title)}</title><style>{KAMI_LONG_DOC_CSS}</style></head>
<body>
<section class='cover'><div><div class='cover-title'>{esc(title)}</div><div class='cover-sub'>{esc(subtitle)}</div></div><div class='cover-meta'>{esc(meta_line)}</div>{('<div class="cover-orientation">' + esc(orientation.get('lead')) + '</div>') if orientation.get('lead') else ''}</section>
<section class='toc'><h2>目录</h2>{''.join(toc_items)}</section>
{''.join(chapters_html)}
{appendix}
</body></html>"""

def render_paper_reader_md(manuscript: dict, root=None) -> str:
    doc = manuscript.get('document', {})
    title = doc.get('title', '未命名论文')
    subtitle = doc.get('subtitle', '中文科学精读稿')
    orientation = doc.get('orientation') or doc.get('executive_summary') or {}
    meta = doc.get('paper_meta', {})
    authors = '、'.join(meta.get('authors', [])) if meta.get('authors') else ''
    meta_line = ' · '.join(x for x in (authors, meta.get('venue', ''), str(meta.get('year') or '')) if x)
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
        lines.extend([f"## {idx}. {chapter.get('title', '')} <a id='{cid}'></a>", '', f"> *{chapter.get('lead', '')}*", ''])
        for block in chapter.get('blocks', []):
            kind = block.get('type'); text = block.get('text', ''); refs = block.get('evidence_refs', [])
            cite = f" 〔{', '.join(refs)}〕" if refs else ''
            if kind in ('paragraph', 'callout', 'takeaway'):
                lines.append(f"{text}{cite}\n")
            elif kind in ('figure', 'table'):
                lines.append(f"### {block.get('caption', '图表')}\n")
                asset = resolve_visual_asset(block, root) if root else block.get('asset')
                if asset: lines.append(f"![{block.get('caption', '')}]({asset})\n")
                lines.append(f"{block.get('analysis', '')}{cite}\n")
            elif kind == 'equation':
                lines.append(f"（{block.get('evidence_id', 'EQ')}）\n")
                latex = normalize_latex(block.get('latex')) if block.get('source_confidence') == 'VERIFIED' else None
                if latex:
                    lines.append(f"$$\n{latex}\n$$\n")
                elif block.get('fallback_asset'):
                    lines.append(f"![公式源图 {block.get('evidence_id', 'EQ')}]({block['fallback_asset']})\n")
                else:
                    lines.append("公式无法可靠重建；已保留源证据状态。\n")
                lines.append(f"{block.get('explanation', '')}{cite}\n")
            elif kind == 'list':
                lines.extend([f'- {item}' for item in block.get('items', [])]); lines.append('')
    lines.extend(['## 证据来源与页面锚点 <a id=\'sources\'></a>', '', '需要逐项核对来源时，请打开 [来源与核验记录](evidence_atlas.html)。', ''])
    return '\n'.join(lines) + '\n'

def render_paper_reader(root: Path, kami_root: Path = None) -> dict:
    """Render the primary Paper Reader HTML, Markdown, and PDF."""
    reader_dir = root / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)
    
    manuscript_p = reader_dir / 'narrative_manuscript.json'
    if manuscript_p.exists():
        manuscript = load_json(manuscript_p)
    else:
        manuscript = compose_narrative_manuscript(root)
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
