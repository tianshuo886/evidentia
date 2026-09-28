#!/usr/bin/env python3
"""Render Evidence Atlas for Evidentia (Issue #9).

Phase B6 / Workstream C: Secondary inspection & audit surface.
Decoupled from primary human reading surface:
- Primary Reader (paper_reader.html): Narrative-first, editorial, Kami presentation.
- Evidence Atlas (evidence_atlas.html): Inspection-first, claim ↔ evidence navigation,
  O/I/A breakdown, verifier status, epistemic states, Lens conflicts, provenance.
"""
import argparse, html, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from validate_common import load_json, sha256

def esc(x):
    return html.escape(str(x or ''))

ATLAS_CSS = """
:root {
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --border: #e2e8f0;
  --border-focus: #cbd5e1;
  --text: #0f172a;
  --text-muted: #64748b;
  --brand: #1e3a8a;
  --accent: #2563eb;
  --tag-bg: #eff6ff;
  --success: #15803d;
  --warning: #b45309;
  --danger: #b91c1c;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.6;
  padding: 24px;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
}
header {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 24px;
}
.eyebrow {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--brand);
  margin-bottom: 6px;
}
h1 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 10px;
}
.meta-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  padding-top: 10px;
  margin-top: 10px;
}
.meta-bar code {
  font-family: var(--mono);
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}
.nav-bar {
  position: sticky;
  top: 12px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 16px;
  margin-bottom: 24px;
  display: flex;
  gap: 12px;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.nav-bar a {
  color: var(--brand);
  text-decoration: none;
  font-weight: 600;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 4px;
}
.nav-bar a:hover {
  background: #f1f5f9;
}
.nav-bar .return-link {
  margin-left: auto;
  color: #fff;
  background: var(--brand);
  padding: 6px 12px;
  border-radius: 6px;
}
.nav-bar .return-link:hover {
  background: var(--accent);
}
.section-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
}
h2 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
  text-decoration: none;
}
.badge-evidence {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}
.badge-epistemic-supported { background: #dcfce7; color: var(--success); }
.badge-epistemic-partial { background: #fef9c3; color: var(--warning); }
.badge-epistemic-ambiguous { background: #fef3c7; color: var(--warning); }
.badge-epistemic-refuted { background: #fee2e2; color: var(--danger); }
.badge-verifier-verified { background: #dcfce7; color: var(--success); }
.badge-verifier-tension { background: #fef3c7; color: var(--warning); }
.badge-verifier-unresolved { background: #f3f4f6; color: var(--text-muted); }
.claim-article {
  background: #fdfdfd;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.claim-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.claim-title {
  font-size: 14px;
  font-weight: 600;
}
.claim-title a {
  color: var(--brand);
  text-decoration: none;
}
.oia-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
@media (max-width: 800px) {
  .oia-grid { grid-template-columns: 1fr; }
}
.oia-box {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  font-size: 12.5px;
}
.oia-box strong {
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.oia-obs strong { color: #0284c7; }
.oia-auth strong { color: #7c3aed; }
.oia-read strong { color: #059669; }
.evidence-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.evidence-card img {
  max-width: 100%;
  max-height: 400px;
  border-radius: 4px;
  border: 1px solid var(--border);
  margin: 10px 0;
  display: block;
}
.page-anchors-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.page-anchor-badge {
  background: #f1f5f9;
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  text-decoration: none;
}
.warning-box {
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  padding: 12px 16px;
  margin-bottom: 12px;
  border-radius: 0 4px 4px 0;
}
"""

def render_evidence_atlas(root: Path) -> dict:
    pm = load_json(root / 'model/paper_model.json')
    inv_p = root / 'model/figure_inventory.json'
    inv = load_json(inv_p) if inv_p.exists() else {}
    sm_p = root / 'model/source_map.json'
    sm = load_json(sm_p) if sm_p.exists() else {}
    rec_p = root / 'model/lens_reconciliation.json'
    rec = load_json(rec_p) if rec_p.exists() else {}

    title = pm.get('paper', {}).get('title', 'Untitled Paper')
    paper_id = pm.get('paper_id', root.name)
    src_sha = pm.get('source_sha256', '')

    claims = pm.get('claims', [])
    inv_items = inv.get('items', [])
    figs = pm.get('figures', []) or [x for x in inv_items if x.get('kind') == 'figure']
    tables = pm.get('tables', []) or [x for x in inv_items if x.get('kind') == 'table']
    conflicts = pm.get('lens_conflicts', []) or rec.get('items', [])
    unresolved = pm.get('unresolved', [])

    # Map evidence to claims
    ev_to_claims = {}
    for c in claims:
        cid = c.get('id')
        for e in c.get('evidence', []):
            ev_to_claims.setdefault(e, []).append(cid)

    # Collect page numbers
    page_numbers = {1}
    for c in claims:
        if c.get('page'):
            page_numbers.add(c['page'])
        for ev in c.get('evidence', []):
            m = re.match(r'^p\.([0-9]+)$', str(ev))
            if m:
                page_numbers.add(int(m.group(1)))
    for f in figs:
        if f.get('page'):
            page_numbers.add(f['page'])
    for t in tables:
        if t.get('page'):
            page_numbers.add(t['page'])
    for pg in sm.get('pages', []):
        if pg.get('number'):
            page_numbers.add(pg['number'])

    # Build Claim Articles HTML
    claims_html = []
    for c in claims:
        cid = c.get('id', '')
        stmt = c.get('statement', '')
        epistemic = c.get('epistemic', 'SUPPORTED')
        obs = c.get('observation', 'Direct empirical observation.')
        auth = c.get('author_interpretation', 'Intended claim from authors.')
        read = c.get('reader_assessment', 'Evaluated reader assessment.')
        v_stat = c.get('verifier_status', '')
        v_badge = f"<span class='badge badge-verifier-{esc(v_stat.lower())}'>{esc(v_stat)}</span>" if v_stat else ""
        
        ev_badges = []
        for e in c.get('evidence', []):
            ev_badges.append(f"<a href='#{esc(e)}' class='badge badge-evidence'>{esc(e)}</a>")
        ev_str = " ".join(ev_badges) if ev_badges else "<em>None</em>"

        claims_html.append(f"""
        <article class="claim-article" id="{esc(cid)}">
          <a id="item-{esc(cid)}"></a>
          <div class="claim-header">
            <div class="claim-title">
              <a href="#{esc(cid)}">[{esc(cid)}]</a> {esc(stmt)}
            </div>
            <div>
              <span class="badge badge-epistemic-{esc(epistemic.lower())}">{esc(epistemic)}</span>
              {v_badge}
            </div>
          </div>
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:8px;">
            <strong>Linked Evidence:</strong> {ev_str} · <a href="#p.{esc(c.get('page', 1))}" class="badge page-anchor-badge">p.{esc(c.get('page', 1))}</a>
            · <a href="paper_reader.html#ch-one-minute" style="color:var(--brand); text-decoration:none; margin-left:8px;">[主阅读器]</a>
          </div>
          <div class="oia-grid">
            <div class="oia-box oia-obs">
              <strong>Observation (客观实证)</strong>
              {esc(obs)}
            </div>
            <div class="oia-box oia-auth">
              <strong>Author Interpretation (作者推断)</strong>
              {esc(auth)}
            </div>
            <div class="oia-box oia-read">
              <strong>Reader Assessment (读者研判)</strong>
              {esc(read)}
            </div>
          </div>
        </article>
        """)

    # Build Figures & Tables HTML
    evidence_items_html = []
    for f in figs:
        fid = f.get('id', '')
        label = f.get('paper_label', fid)
        cap = f.get('caption_original', '')
        supp = ev_to_claims.get(fid, f.get('supports_claims', []))
        supp_badges = " ".join([f"<a href='#{esc(c)}' class='badge' style='background:#f1f5f9; color:var(--brand);'>{esc(c)}</a>" for c in supp])
        asset = f.get('file') or f.get('asset')
        img_tag = f"<img src='../{esc(asset)}' alt='{esc(label)}' />" if asset and (root / asset).exists() else ""
        
        evidence_items_html.append(f"""
        <div class="evidence-card" id="{esc(fid)}">
          <a id="item-{esc(fid)}"></a>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3><a href="#{esc(fid)}">{esc(label)}</a> ({esc(fid)})</h3>
            <span class="badge" style="background:#f1f5f9; color:var(--brand);">Figure · p.{esc(f.get('page', 1))}</span>
          </div>
          <p style="color:var(--text-muted); font-size:13px; margin:6px 0;">{esc(cap)}</p>
          {img_tag}
          <div style="font-size:12px; margin-top:8px;">
            <strong>Supports Claims:</strong> {supp_badges if supp_badges else "<em>None directly mapped</em>"}
          </div>
          {f"<div class='oia-box' style='margin-top:8px;'><strong>Observation:</strong> {esc(f.get('observation'))}</div>" if f.get('observation') else ""}
        </div>
        """)

    for t in tables:
        tid = t.get('id', '')
        label = t.get('paper_label', tid)
        cap = t.get('caption_original', '')
        supp = ev_to_claims.get(tid, [])
        supp_badges = " ".join([f"<a href='#{esc(c)}' class='badge' style='background:#f1f5f9; color:var(--brand);'>{esc(c)}</a>" for c in supp])
        
        evidence_items_html.append(f"""
        <div class="evidence-card" id="{esc(tid)}">
          <a id="item-{esc(tid)}"></a>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3><a href="#{esc(tid)}">{esc(label)}</a> ({esc(tid)})</h3>
            <span class="badge" style="background:#f1f5f9; color:var(--brand);">Table · p.{esc(t.get('page', 1))}</span>
          </div>
          <p style="color:var(--text-muted); font-size:13px; margin:6px 0;">{esc(cap)}</p>
          <div style="font-size:12px; margin-top:8px;">
            <strong>Supports Claims:</strong> {supp_badges if supp_badges else "<em>None directly mapped</em>"}
          </div>
        </div>
        """)

    # Conflicts HTML
    conflicts_html = []
    for conf in conflicts:
        cid = conf.get('id', '')
        stmt = conf.get('statement', '')
        res = conf.get('resolution', '')
        v_stat = conf.get('verifier_status') or 'TENSION'
        v_stat_cls = v_stat.lower() if isinstance(v_stat, str) else 'tension'
        conflicts_html.append(f"""
        <div class="warning-box" id="{esc(cid)}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>{esc(cid)}: {esc(stmt)}</strong>
            <span class="badge badge-verifier-{esc(v_stat_cls)}">{esc(v_stat)}</span>
          </div>
          <p style="margin-top:6px; font-size:13px;">{esc(res)}</p>
        </div>
        """)

    # Page Anchors HTML
    page_anchors_html = [
        f"<a href='#p.{p}' id='p.{p}' class='page-anchor-badge'>p.{p}</a>"
        for p in sorted(page_numbers)
    ]

    full_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} · Evidence Atlas</title>
<style>{ATLAS_CSS}</style>
</head>
<body>
<div class="container">
  <header>
    <div class="eyebrow">Evidentia Scientific Paper Research OS · Secondary Audit Surface</div>
    <h1>{esc(title)} · Evidence Atlas</h1>
    <div class="meta-bar">
      <span>Paper ID: <code>{esc(paper_id)}</code></span>
      <span>Source SHA256: <code>{esc(src_sha[:16])}</code></span>
      <span>Claims: <strong>{len(claims)}</strong></span>
      <span>Figures/Tables: <strong>{len(figs) + len(tables)}</strong></span>
      <span>Conflicts: <strong>{len(conflicts)}</strong></span>
    </div>
  </header>

  <nav class="nav-bar">
    <a href="#claims-section">Claims & O/I/A</a>
    <a href="#evidence-section">Evidence Items</a>
    <a href="#conflicts-section">Conflicts & Tensions</a>
    <a href="#pages-section">Page Anchors</a>
    <a href="paper_reader.html" class="return-link">← 返回主阅读器 (Paper Reader)</a>
  </nav>

  <section class="section-card" id="claims-section">
    <h2>1. Claims & O/I/A Structure ({len(claims)})</h2>
    {''.join(claims_html) if claims_html else "<p>无提取的主张记录。</p>"}
  </section>

  <section class="section-card" id="evidence-section">
    <h2>2. Visual & Tabular Evidence Items ({len(figs) + len(tables)})</h2>
    {''.join(evidence_items_html) if evidence_items_html else "<p>无提取的图表资产。</p>"}
  </section>

  <section class="section-card" id="conflicts-section">
    <h2>3. Cross-Lens Conflicts & Tensions ({len(conflicts)})</h2>
    {''.join(conflicts_html) if conflicts_html else "<p style='color:var(--text-muted);'>无未解争议或跨透镜冲突记录。</p>"}
  </section>

  <section class="section-card" id="pages-section">
    <h2>4. Source Page Anchors</h2>
    <div class="page-anchors-container">
      {''.join(page_anchors_html)}
    </div>
  </section>
</div>
</body>
</html>
"""

    atlas_data = {
        "schema_version": "1.0",
        "paper_id": paper_id,
        "source_sha256": src_sha,
        "claims_count": len(claims),
        "figures_count": len(figs),
        "tables_count": len(tables),
        "conflicts_count": len(conflicts),
        "claim_cards": [c.get('id') for c in claims],
        "figure_blocks": [f.get('id') for f in figs],
        "table_blocks": [t.get('id') for t in tables],
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    reader_dir = root / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)
    (reader_dir / 'evidence_atlas.html').write_text(full_html, encoding='utf-8')
    (reader_dir / 'evidence_atlas.json').write_text(json.dumps(atlas_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Generated evidence atlas -> {reader_dir / 'evidence_atlas.html'}")
    return atlas_data

def main():
    ap = argparse.ArgumentParser(description="Render Evidence Atlas HTML and JSON.")
    ap.add_argument('--out', required=True, help="Workspace run directory")
    args = ap.parse_args()
    render_evidence_atlas(Path(args.out))
    return 0

if __name__ == '__main__':
    sys.exit(main())
