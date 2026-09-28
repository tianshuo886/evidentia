#!/usr/bin/env python3
"""Render Chinese-first Kami Long-Doc Paper Reader for Evidentia (Issue #9).

Principle: "Evidentia owns truth. AI owns narrative. Kami owns presentation."

Responsibilities:
- Reads semantic narrative manuscript IR: reader/narrative_manuscript.json
  (generates it via narrative_composer_agent if missing).
- Formats narrative manuscript into editorial Kami long-doc HTML: reader/paper_reader.html
- Formats narrative manuscript into editorial Markdown: reader/paper_reader.md
- Renders printable PDF snapshot via Kami presentation backend: reader/paper_reader.pdf
- Strictly separates human reading flow from audit chrome:
  * No dashboard grids, cards-per-field, or badge storms in main chapters.
  * Figures, equations, and takeaways are woven into narrative argument flow.
  * Appendix provides calm summary and links to reader/evidence_atlas.html.
"""
import argparse, html, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from validate_common import load_json, sha256
from narrative_composer_agent import compose_narrative_manuscript
import kami_adapter

def esc(x):
    return html.escape(str(x or ''))

KAMI_LONG_DOC_CSS = """
/* Regular weight */
@font-face {
  font-family: "TsangerJinKai02";
  src: url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/TsangerJinKai02-W04.ttf") format("truetype");
  font-weight: 400;
  font-style: normal;
}
@font-face {
  font-family: "TsangerJinKai02";
  src: url("https://cdn.jsdelivr.net/gh/tw93/Kami@main/assets/fonts/TsangerJinKai02-W05.ttf") format("truetype");
  font-weight: 500;
  font-style: normal;
}

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
    content: counter(page) " · Evidentia Deep Research";
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
.atlas-portal-card {
  background: var(--ivory);
  border: 1pt solid var(--brand);
  border-radius: 4pt;
  padding: 14pt;
  margin: 16pt 0;
  text-align: center;
  break-inside: avoid;
}
.atlas-portal-card a.btn-atlas {
  display: inline-block;
  background: var(--brand);
  color: var(--ivory);
  font-family: var(--sans);
  font-size: 10pt;
  font-weight: 500;
  text-decoration: none;
  padding: 6pt 16pt;
  border-radius: 4pt;
  margin-top: 8pt;
}
.atlas-portal-card a.btn-atlas:hover {
  background: var(--brand);
}
"""

def render_block_html(b: dict, root: Path) -> str:
    b_type = b.get('type')
    ev_refs = b.get('evidence_refs', [])
    cites = "".join([f'<a href="#{esc(e)}" class="evidence-cite">[实证依据: {esc(e)} · 详情见图谱]</a>' for e in ev_refs]) if ev_refs else ""
    
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
        asset = b.get('asset')
        img_html = ""
        if asset and (root / asset).exists():
            img_html = f"<img src='../{esc(asset)}' alt='{cap}' />"
            
        supp_claims = [e for e in b.get('evidence_refs', []) if e.startswith('C')]
        supp_links = " ".join([f'<a href="#{esc(c)}" class="evidence-cite">[对应支撑主张: {esc(c)} · 详情见附录]</a>' for c in supp_claims]) if supp_claims else "<em>None</em>"
        supp_row = f"<div style='font-size:8.5pt; color:var(--stone); margin-top:4pt;'><strong>Supports Claims:</strong> {supp_links}</div>"
        
        return f"""
        <figure class="kami-figure" id="{esc(fid)}">
          {img_html}
          <figcaption>{cap} {cites}</figcaption>
          <div class="figure-analysis">{analysis}</div>
          {supp_row}
        </figure>
        """
        
    elif b_type == 'equation':
        raw = b.get('raw_text', '')
        exp = esc(b.get('explanation', ''))
        eq_id = b.get('evidence_id', 'EQ')
        math_repr = raw if raw.startswith('\\(') or raw.startswith('\\[') else f"\\[ {raw} \\]"
        return f"""
        <div class='equation-block' id='{esc(eq_id)}'>
          <div class='math-display'>{esc(math_repr)}</div>
          <div class='eq-explanation'>{exp} {cites}</div>
        </div>
        """
        
    elif b_type == 'table':
        tid = b.get('evidence_id', 'TAB')
        cap = esc(b.get('caption', ''))
        analysis = esc(b.get('analysis', ''))
        analysis = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', analysis)
        return f"""
        <div class='takeaway' id='{esc(tid)}'>
          <div class='takeaway-label'>定量评测表: {cap} {cites}</div>
          <div style='font-size:9.5pt; margin-top:6pt;'>{analysis}</div>
        </div>
        """
        
    elif b_type == 'list':
        items = b.get('items', [])
        li_html = "".join([f"<li>{esc(it)}</li>" for it in items])
        return f"<ul>{li_html}</ul>"
        
    return ""

def render_paper_reader_html(manuscript: dict, root: Path) -> str:
    doc = manuscript.get('document', {})
    title = doc.get('title', 'Untitled Paper')
    subtitle = doc.get('subtitle', 'Evidentia 深度科学研读与证据重构报告')
    meta = doc.get('paper_meta', {})
    authors = meta.get('authors', [])
    authors_str = ", ".join(authors) if authors else "Paper Authors"
    venue = meta.get('venue') or 'Academic Archive'
    year = meta.get('year') or 2026
    
    exec_summary = doc.get('executive_summary', {})
    chapters = doc.get('chapters', [])
    app_sum = doc.get('appendix_summary', {})
    
    # TOC generation with descriptive subtitles to ensure balanced line length & avoid typographic orphans
    toc_subtitles = {
        "one_minute": "核心突破与实证结论",
        "problem": "背景与科学缺口",
        "method": "算法架构与计算流",
        "experiments": "实证对比与研判",
        "synthesis": "六大透镜合并审视",
        "reusable": "模块与迁移建议",
        "conclusions": "确立事实与开放问题",
        "appendix": "数据溯源与工作台"
    }
    toc_items = []
    for idx, ch in enumerate(chapters, 1):
        cid = ch.get('id', f'ch-{idx}')
        cnum = ch.get('chapter_num', f'{idx:02d}')
        ctitle = ch.get('title', '')
        sub = toc_subtitles.get(cid, "研读与分析")
        toc_items.append(f"""
        <div class="toc-item">
          <a class="toc-title" href="#ch-{esc(cid)}">
            <span class="toc-num">{esc(cnum)}</span> · {esc(ctitle)} · {esc(sub)}
          </a>
        </div>
        """)
        
    # Append appendix to TOC
    toc_items.append(f"""
    <div class="toc-item">
      <a class="toc-title" href="#ch-appendix">
        <span class="toc-num">08</span> · 证据审计附录 · 数据溯源与工作台
      </a>
    </div>
    """)
    
    # Chapters generation with editorial subtitles
    chapter_subtitles = {
        "one_minute": "核心突破与实证结论",
        "problem": "背景动机与科学缺口",
        "method": "算法架构与理论假设",
        "experiments": "实证对比与反常审视",
        "synthesis": "六大透镜汇聚与替代解释",
        "reusable": "模块设计与工程迁移",
        "conclusions": "确立事实与开放问题",
        "appendix": "数据溯源与检验元数据"
    }
    chapters_html = []
    for ch in chapters:
        cid = ch.get('id', '')
        cnum = ch.get('chapter_num', '')
        ctitle = ch.get('title', '')
        csub = chapter_subtitles.get(cid, "科学研读与分析")
        clead = ch.get('lead', '')
        blocks = ch.get('blocks', [])
        
        b_html = "\n".join([render_block_html(b, root) for b in blocks])
        
        chapters_html.append(f"""
        <section class="chapter" id="ch-{esc(cid)}">
          <div class="chapter-num">Chapter {esc(cnum)}</div>
          <h1>{esc(ctitle)}：{esc(csub)}</h1>
          <div class="lead">{esc(clead)}</div>
          <div class="chapter-body">
            {b_html}
          </div>
        </section>
        """)

    # Appendix section
    pm = load_json(root / 'model/paper_model.json') if (root / 'model/paper_model.json').exists() else {}
    pm_claims = pm.get('claims', [])
    pm_conflicts = pm.get('lens_conflicts', [])
    
    claims_appendix_html = []
    for c in pm_claims:
        cid = c.get('id', '')
        c_stmt = c.get('statement', '')
        c_ev = c.get('evidence', [])
        c_ev_links = " ".join([f'<a href="#{esc(e)}" class="evidence-cite">[实证依据: {esc(e)} · 详情见图谱]</a>' for e in c_ev])
        claims_appendix_html.append(f"""
        <article class="claim-card" id="{esc(cid)}" style="background:var(--ivory); border:1pt solid var(--border); border-radius:4pt; padding:10pt; margin-bottom:10pt;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong><a href="#{esc(cid)}">[{esc(cid)}]</a> {esc(c_stmt)}</strong>
            <span class="tag">【状态: {esc(c.get('epistemic', 'SUPPORTED'))} · 证据闭环】</span>
          </div>
          <div style="font-size:8.5pt; color:var(--stone); margin:4pt 0;">
            <strong>Linked Evidence:</strong> {c_ev_links if c_ev_links else '<em>None</em>'} · <a href="#p.{esc(c.get('page', 1))}">p.{esc(c.get('page', 1))}</a>
          </div>
          <div style="font-size:9pt; margin-top:6pt;">
            <p><strong>Observation (客观数据):</strong> {esc(c.get('observation', 'Direct empirical observation.'))}</p>
            <p><strong>Author Interpretation (作者推断):</strong> {esc(c.get('author_interpretation', 'Intended author interpretation.'))}</p>
            <p><strong>Reader Assessment (读者研判):</strong> {esc(c.get('reader_assessment', 'Evaluated reader assessment.'))}</p>
          </div>
        </article>
        """)
        
    conflicts_appendix_html = []
    for conf in pm_conflicts:
        cid = conf.get('id', '')
        conflicts_appendix_html.append(f"""
        <div class="conflict-card" id="{esc(cid)}" style="background:var(--ivory); border-left:2.5pt solid var(--brand); padding:8pt 10pt; margin-bottom:8pt;">
          <strong>{esc(cid)}: {esc(conf.get('statement', ''))}</strong>
          <p style="font-size:9pt; margin-top:4pt;">{esc(conf.get('resolution', ''))}</p>
        </div>
        """)
        
    page_numbers = {1}
    for c in pm_claims:
        if c.get('page'):
            page_numbers.add(c['page'])
        for ev in c.get('evidence', []):
            m = re.match(r'^p\.([0-9]+)$', str(ev))
            if m:
                page_numbers.add(int(m.group(1)))
    page_anchors_html = " ".join([
        f"<a id='p.{p}' href='#p.{p}' style='font-size:8pt; color:var(--stone); margin-right:4pt;'>p.{p}</a>"
        for p in sorted(page_numbers)
    ])

    appendix_html = f"""
    <section class="chapter appendix" id="ch-appendix">
      <div class="chapter-num">Appendix</div>
      <h1>证据审计附录 (Claim-Centric Evidence Atlas)</h1>
      <div class="lead">全景证据溯源与检验元数据概览。完整卡片细节由独立 Evidence Atlas 工作台承载。</div>
      
      <div class="atlas-portal-card">
        <h3>深入证据审计与双向追溯</h3>
        <p style="font-size:9.5pt; color:var(--dark-warm); margin-top:6pt;">
          当前论文模型共沉淀 <strong>{app_sum.get('claims_count', len(pm_claims))}</strong> 项主张、
          <strong>{app_sum.get('figures_count', 0)}</strong> 组图表、
          <strong>{app_sum.get('tables_count', 0)}</strong> 个数据表、
          以及 <strong>{app_sum.get('conflicts_count', len(pm_conflicts))}</strong> 个跨透镜张力焦点。
        </p>
        <a href="evidence_atlas.html" class="btn-atlas">打开完整证据图谱 (Evidence Atlas) →</a>
      </div>

      <details open>
        <summary>点击展开：核心主张与 O/I/A 证据卡片列表 ({len(pm_claims)} 个)</summary>
        <div style="font-size:9.5pt; margin-top:10pt; line-height:1.55;">
          <p>Evidentia 严格执行 <strong>Observation</strong>（客观实证数据）、<strong>Author Interpretation</strong>（作者主观推断）与 <strong>Reader Assessment</strong>（读者中立研判）三权分立原则。所有结论均通过独立透镜与实证网格交叉互审。</p>
          <div style="margin-top:10pt;">
            {''.join(claims_appendix_html)}
          </div>
        </div>
      </details>
      {f"<details open><summary>点击展开：跨透镜争议焦点与验证记录 ({len(pm_conflicts)} 个)</summary><div style='font-size:9.5pt; margin-top:10pt; line-height:1.55;'>{''.join(conflicts_appendix_html)}</div></details>" if pm_conflicts else ""}
      <div style="margin-top:12pt;">
        <strong>Page Anchors:</strong> {page_anchors_html}
      </div>
    </section>
    """

    full_html = f"""<!doctype html>
<!-- ==================================================================
     Evidentia Chinese-first Scientific Reader · Kami Long-Doc System
     Evidentia owns truth. AI owns narrative. Kami owns presentation.
     ================================================================== -->
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} · Evidentia 深度科学精读</title>
<style>{KAMI_LONG_DOC_CSS}</style>
</head>
<body>

<!-- ═════════════ COVER ═════════════ -->
<section class="cover">
  <div>
    <div class="cover-eyebrow">EVIDENTIA DEEP RESEARCH OS · FOCUSED PAPER READING</div>
    <div class="cover-title">{esc(title)}</div>
    <div class="cover-sub">{esc(subtitle)}</div>
  </div>
  <div class="cover-meta">
    <strong>{esc(authors_str)}</strong><br>
    {esc(venue)} · {esc(year)}<br>
    Evidentia Provenance Engine · Kami Presentation Backend
  </div>
</section>

<!-- ═════════════ TOC ═════════════ -->
<section class="toc">
  <h2>目录</h2>
  {''.join(toc_items)}
</section>

<!-- ═════════════ CHAPTERS ═════════════ -->
{''.join(chapters_html)}

<!-- ═════════════ APPENDIX ═════════════ -->
{appendix_html}

</body>
</html>
"""
    return full_html

def render_paper_reader_md(manuscript: dict) -> str:
    doc = manuscript.get('document', {})
    title = doc.get('title', 'Untitled Paper')
    subtitle = doc.get('subtitle', 'Evidentia 深度科学研读与证据重构报告')
    meta = doc.get('paper_meta', {})
    authors = ", ".join(meta.get('authors', [])) if meta.get('authors') else 'Authors'
    venue = meta.get('venue', 'Archive')
    year = meta.get('year', 2026)
    
    lines = [
        f"# {title}",
        f"**{subtitle}**\n",
        f"- **作者**: {authors}",
        f"- **发表/收录**: {venue} ({year})",
        f"- **报告生成**: Evidentia & Kami Presentation Backend\n",
        "---\n",
        "## 目录",
    ]
    
    chapters = doc.get('chapters', [])
    for idx, ch in enumerate(chapters, 1):
        lines.append(f"{idx}. [{ch.get('title', '')}](#{ch.get('id', '')})")
    lines.append(f"{len(chapters)+1}. [证据审计附录](#appendix)\n")
    lines.append("---\n")
    
    for idx, ch in enumerate(chapters, 1):
        ctitle = ch.get('title', '')
        clead = ch.get('lead', '')
        cid = ch.get('id', '')
        
        lines.append(f"## {idx}. {ctitle} <a id='{cid}'></a>\n")
        lines.append(f"> *{clead}*\n")
        
        for b in ch.get('blocks', []):
            b_type = b.get('type')
            text = b.get('text', '')
            ev_refs = b.get('evidence_refs', [])
            cite_str = f" [依据: {', '.join(ev_refs)}]" if ev_refs else ""
            
            if b_type == 'paragraph':
                lines.append(f"{text}{cite_str}\n")
            elif b_type == 'callout':
                lines.append(f"> **关键审视**: {text}{cite_str}\n")
            elif b_type == 'takeaway':
                lines.append(f"> **核心关注**: {text}{cite_str}\n")
            elif b_type == 'figure':
                lines.append(f"### {b.get('caption', '实证图表')}{cite_str}")
                if b.get('asset'):
                    lines.append(f"![{b.get('caption', '')}]({b.get('asset')})\n")
                lines.append(f"{b.get('analysis', '')}\n")
            elif b_type == 'equation':
                lines.append(f"$$\n{b.get('raw_text', '')}\n$$\n*{b.get('explanation', '')}*{cite_str}\n")
            elif b_type == 'table':
                lines.append(f"### {b.get('caption', '实证评测表')}{cite_str}\n{b.get('analysis', '')}\n")
            elif b_type == 'list':
                for it in b.get('items', []):
                    lines.append(f"- {it}")
                lines.append("")
                
    # Appendix
    lines.append(f"## {len(chapters)+1}. 证据审计附录 (Claim-Centric Evidence Atlas) <a id='appendix'></a>\n")
    lines.append("完整的主张列表、O/I/A 证据卡片、跨透镜争议与双向锚点跳转已解耦部署于独立的证据图谱中：\n")
    lines.append("- [进入证据图谱工作台 (evidence_atlas.html)](evidence_atlas.html)\n")
    lines.append("### 核心原则")
    lines.append("- **Observation (客观数据)**: 严守实验与源文本直接观测事实。")
    lines.append("- **Author Interpretation (作者推断)**: 记录作者提出的假说与外推判断。")
    lines.append("- **Reader Assessment (读者研判)**: Evidentia 独立透镜对主张支撑力度的客观审视。\n")
    
    return "\n".join(lines) + "\n"

def render_paper_reader(root: Path, kami_root: Path = None) -> dict:
    """Render the primary Paper Reader HTML, Markdown, and PDF."""
    reader_dir = root / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)
    
    manuscript_p = reader_dir / 'narrative_manuscript.json'
    if manuscript_p.exists():
        manuscript = load_json(manuscript_p)
    else:
        manuscript = compose_narrative_manuscript(root)
        manuscript_p.write_text(json.dumps(manuscript, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        
    html_content = render_paper_reader_html(manuscript, root)
    html_file = reader_dir / 'paper_reader.html'
    html_file.write_text(html_content, encoding='utf-8')
    
    md_content = render_paper_reader_md(manuscript)
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
