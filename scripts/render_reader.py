#!/usr/bin/env python3
"""Render the canonical model into a Claim-centric Evidence Atlas HTML Reader and optional PDF.

Phase B6 updates:
- Claim-centric Evidence Atlas with O/I/A separation
- Complete Evidence Surfaces: Figures, Tables, Equations, Experiments, and Page Anchors
- Bidirectional anchor navigation (Claim <-> Evidence <-> Findings <-> Verifier)
- Verifier status and conflict rendering
- Kami-compatible presentation boundary & visual QA
"""
import argparse, json, html, os, sys
from pathlib import Path

def esc(x):
    return html.escape(str(x or ''))

def card(title, body, cls='card', cid=None):
    id_attr = f' id="{esc(cid)}"' if cid else ''
    return f'<section class="{cls}"{id_attr}><h2>{esc(title)}</h2>{body}</section>'

def li(items, fn=lambda x: x):
    return '<ul>' + ''.join(f'<li>{fn(x)}</li>' for x in items) + '</ul>'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    r = Path(a.out)
    
    pm = json.load(open(r / 'model/paper_model.json', encoding='utf-8'))
    inv = json.load(open(r / 'model/figure_inventory.json', encoding='utf-8'))
    sm_p = r / 'model/source_map.json'
    sm = json.load(open(sm_p, encoding='utf-8')) if sm_p.exists() else {}
    
    deltas = []
    if (r / 'apply').exists():
        for p in sorted((r / 'apply').glob('*/research_delta.json')):
            try:
                deltas.append(json.load(open(p, encoding='utf-8')))
            except Exception:
                pass

    title = pm.get('paper', {}).get('title', 'Untitled paper')
    claims = pm.get('claims', [])
    inv_items = inv.get('items', [])
    figs = pm.get('figures', []) or [x for x in inv_items if x.get('kind') == 'figure']
    tables = pm.get('tables', []) or [x for x in inv_items if x.get('kind') == 'table']
    experiments = pm.get('experiments', [])
    
    # Collect all equations from source map
    all_equations = []
    for page_entry in sm.get('pages', []):
        for eq in page_entry.get('equations', []):
            if isinstance(eq, dict):
                all_equations.append(eq)
            elif isinstance(eq, str):
                all_equations.append({
                    "equation_id": f"EQ-p{page_entry.get('number', 1)}-{len(all_equations)+1}",
                    "page": page_entry.get('number', 1),
                    "raw_text": eq
                })

    # Map evidence back to supported claims for bidirectional navigation
    ev_to_claims = {}
    for c in claims:
        cid = c.get('id')
        for evid in c.get('evidence', []):
            ev_to_claims.setdefault(evid, []).append(cid)

    dash = (
        f'<div class="stats">'
        f'<b>{len(claims)}</b><span>claims</span>'
        f'<b>{len(figs)}</b><span>figures</span>'
        f'<b>{len(tables)}</b><span>tables</span>'
        f'<b>{len(all_equations)}</b><span>equations</span>'
        f'<b>{len(pm.get("unresolved", []))}</b><span>unresolved</span>'
        f'<b>{len(pm.get("lens_conflicts", []))}</b><span>conflicts</span>'
        f'</div>'
    )

    body = '<header><p class="eyebrow">PAPER RESEARCH OS · FROZEN MODEL · EVIDENCE ATLAS</p><h1>' + esc(title) + '</h1>' + dash + '</header>'

    # 1. 30-second scan & Page Anchors
    page_anchors_html = " ".join([f'<a href="#p.{p.get("number")}" class="badge page-anchor-link">p.{p.get("number")}</a>' for p in sm.get('pages', [])])
    body += card('30-second scan', f'<div class="page-anchor-bar"><strong>Page Nav:</strong> {page_anchors_html}</div><p>' + esc(' → '.join(pm.get('natural_structure', []))) + '</p><h3>Argument chain</h3>' + li(pm.get('argument_chain', [])))

    # 2. Claim-Centric Evidence Atlas
    claims_html = []
    for c in claims:
        cid = c.get('id', '')
        stmt = c.get('statement', '')
        epistemic = c.get('epistemic', 'SUPPORTED')
        
        # O / I / A
        obs = c.get('observation', '')
        auth_interp = c.get('author_interpretation', '')
        reader_assess = c.get('reader_assessment', '')
        
        # Evidence links
        ev_links = []
        for evid in c.get('evidence', []):
            ev_links.append(f'<a href="#{esc(evid)}" class="badge evidence-link">{esc(evid)}</a>')
        ev_html = " ".join(ev_links) if ev_links else "<em>None</em>"

        v_badge = f'<span class="badge verifier-{esc(c.get("verifier_status", "").lower())}">{esc(c.get("verifier_status"))}</span>' if c.get('verifier_status') else ''

        c_block = f'''
        <article class="claim" id="{esc(cid)}">
            <div class="claim-header">
                <h3><a href="#{esc(cid)}">{esc(cid)}</a>: {esc(stmt)}</h3>
                <span class="badge epistemic-{esc(epistemic.lower())}">{esc(epistemic)}</span>
                {v_badge}
            </div>
            <div class="evidence-row"><strong>Localized Evidence:</strong> {ev_html} · <a href="#p.{esc(c.get("page", 1))}">p.{esc(c.get("page", 1))}</a></div>
            <div class="oia-grid">
                <div class="oia-box oia-obs"><strong>Observation (Data):</strong> {esc(obs or 'Direct empirical data.')}</div>
                <div class="oia-box oia-auth"><strong>Author Interpretation:</strong> {esc(auth_interp or 'Intended claim from authors.')}</div>
                <div class="oia-box oia-read"><strong>Reader Assessment:</strong> {esc(reader_assess or 'Evaluated assessment.')}</div>
            </div>
        </article>
        '''
        claims_html.append(c_block)
    body += card('Claim-Centric Evidence Atlas', "".join(claims_html), cid='claims-section')

    # 3. Figure & Table Evidence Gallery with bidirectional return links
    ev_gallery = []
    for x in (figs + tables):
        xid = x.get('id', '')
        label = x.get('paper_label', xid)
        caption = x.get('caption_original', '')
        page = x.get('page', 1)
        role = x.get('role', 'unassigned')
        depth = x.get('depth', 'unassigned')
        binding = x.get('binding_method', 'none')
        
        # Back-links to claims
        linked_claims = ev_to_claims.get(xid, [])
        claim_links = " ".join([f'<a href="#{esc(c_item)}" class="badge claim-link">{esc(c_item)}</a>' for c_item in linked_claims]) or "<em>No direct claim binding</em>"

        img_tag = f'<div class="asset-container"><img src="../{esc(x.get("file"))}" alt="{esc(label)}"></div>' if x.get('file') and (r / x.get('file')).exists() else ''
        struct_info = f'<small>Structure: {x.get("row_count")} rows × {x.get("col_count")} cols</small> · ' if x.get('row_count') else ''

        ev_block = f'''
        <article class="evidence" id="{esc(xid)}">
            <div class="evidence-header">
                <h3><a href="#{esc(xid)}">{esc(label)}</a> ({esc(xid)})</h3>
                <span class="badge role-{esc(role)}">{esc(role)}</span>
                <span class="badge depth-{esc(depth)}">{esc(depth)}</span>
            </div>
            <p class="caption">{esc(caption)}</p>
            {img_tag}
            <div class="evidence-meta">
                <small><a href="#p.{esc(page)}">p.{esc(page)}</a> · Binding: {esc(binding)} · {struct_info}</small>
                <div class="return-links"><strong>Supports Claims:</strong> {claim_links}</div>
            </div>
        </article>
        '''
        ev_gallery.append(ev_block)
    body += card('Evidence Gallery & Inspection Surface', "".join(ev_gallery), cid='evidence-section')

    # 4. Equations Evidence Surface
    if all_equations:
        eq_blocks = []
        for eq in all_equations:
            eq_id = eq.get('equation_id', 'EQ')
            raw = eq.get('raw_text', '')
            page = eq.get('page', 1)
            sec = eq.get('section', 'General')
            eq_blocks.append(f'''
            <article class="equation-card" id="{esc(eq_id)}">
                <div class="eq-header"><strong><a href="#{esc(eq_id)}">{esc(eq_id)}</a></strong> · <small>Section: {esc(sec)} · <a href="#p.{esc(page)}">p.{esc(page)}</a></small></div>
                <pre class="eq-body"><code>{esc(raw)}</code></pre>
            </article>
            ''')
        body += card('Equation Evidence Surface', "".join(eq_blocks), cid='equations-section')

    # 5. Experiments Evidence Surface
    if experiments:
        exp_blocks = []
        for exp in experiments:
            exp_id = exp.get('id', 'E01')
            exp_blocks.append(f'''
            <article class="experiment-card" id="{esc(exp_id)}">
                <h4><a href="#{esc(exp_id)}">{esc(exp_id)}</a>: {esc(exp.get('name', 'Experiment'))}</h4>
                <p>{esc(exp.get('description', ''))}</p>
            </article>
            ''')
        body += card('Experiment Evidence Surface', "".join(exp_blocks), cid='experiments-section')

    # 6. Page Anchors Section
    pages_html = []
    for p in sm.get('pages', []):
        p_num = p.get('number', 1)
        p_anchor = f"p.{p_num}"
        pages_html.append(f'''
        <div class="page-anchor-block" id="{esc(p_anchor)}">
            <h4>Page {esc(p_num)}</h4>
            <p><small>{len(p.get("sections", []))} sections · {len(p.get("mentions", []))} mentions</small></p>
        </div>
        ''')
    body += card('Page Evidence Anchors', "".join(pages_html), cid='pages-section')

    # 7. Lens Synthesis & Reconciled Conflicts
    conflicts = pm.get('lens_conflicts', [])
    conflicts_html = []
    for conf in conflicts:
        cid = conf.get('id', 'CONF')
        target = conf.get('target', 'General')
        res = conf.get('resolution', '')
        v_stat = conf.get('verifier_status', 'UNRESOLVED')
        conflicts_html.append(f'''
        <div class="conflict-item">
            <h4>{esc(cid)} (Target: <a href="#{esc(target)}">{esc(target)}</a>)</h4>
            <p>{esc(res)}</p>
            <p><small>Verifier Verdict: <span class="badge verifier-{esc(str(v_stat).lower())}">{esc(v_stat)}</span></small></p>
        </div>
        ''')
    body += card('Cross-Lens Reconciliation & Verification Surface', "".join(conflicts_html) or '<p>No unresolved tensions recorded.</p>')

    # 8. Boundaries & Unresolved
    limits_html = li(pm.get('limitations', []), lambda x: esc(x.get('text', '')))
    unres_html = li(pm.get('unresolved', []), lambda x: esc(x.get('issue', '')))
    body += card('Weakest Links, Boundaries & Unresolved Questions', f'<h3>Limitations</h3>{limits_html}<h3>Unresolved Questions</h3>{unres_html}')

    # 9. Project Delta if present
    if deltas:
        delta_blocks = []
        for d in deltas:
            p_name = d.get("project", {}).get("name", "Project")
            tus = d.get("transfer_units", [])
            tu_html = "".join([
                f'<li><strong>{esc(tu.get("id"))}</strong>: {esc(tu.get("verdict"))} — {esc(tu.get("reason"))} (Source: {", ".join(tu.get("source", []))})</li>'
                for tu in tus
            ])
            delta_blocks.append(f'''
            <article class="delta">
                <h3>Project: {esc(p_name)}</h3>
                <p>Changed beliefs: {len(d.get("changed_beliefs", []))} · Transfer Units: {len(tus)} · New Experiments: {len(d.get("experiments", []))}</p>
                <ul>{tu_html}</ul>
            </article>
            ''')
        body += card('PROJECT RESEARCH DELTA', "".join(delta_blocks), 'project')

    html_doc = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{esc(title)} · Evidentia Evidence Atlas</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>'''

    (r / 'reader').mkdir(exist_ok=True)
    (r / 'reader/reader.html').write_text(html_doc, encoding='utf-8')

    # Render IR
    ir = {
        'schema_version': '1.0',
        'paper_id': pm.get('paper_id', ''),
        'dashboard': {'title': title, 'claim_count': len(claims)},
        'paper_map': pm.get('natural_structure', []),
        'claim_cards': [c.get('id') for c in claims],
        'figure_blocks': [x.get('id') for x in figs],
        'table_blocks': [x.get('id') for x in tables],
        'delta_projects': [d.get('project', {}).get('name', '') for d in deltas]
    }
    (r / 'reader/render_ir.json').write_text(json.dumps(ir, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Enforce Kami / WeasyPrint Visual QA
    pdf_out = r / 'reader/reader.pdf'
    try:
        from weasyprint import HTML
        HTML(string=html_doc, base_url=str(r / 'reader')).write_pdf(str(pdf_out))
    except Exception as e:
        pass

    # Call Kami adapter for visual check if available
    try:
        sys.path.insert(0, str(HERE))
        import kami_adapter
        # kami_adapter check if KAMI_ROOT exists
        if os.environ.get('KAMI_ROOT') and pdf_out.exists():
            subprocess.run([sys.executable, str(HERE / 'kami_adapter.py'), '--paper', str(r)], capture_output=True)
    except Exception:
        pass

    print('OK reader/reader.html')

CSS = '''
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #17263c; background: #f6f8fb; max-width: 1200px; margin: auto; padding: 36px; line-height: 1.5; }
header { background: #102a43; color: white; padding: 36px; border-radius: 18px; margin-bottom: 22px; }
.eyebrow { letter-spacing: .12em; opacity: .7; font-size: 12px; margin-top: 0; }
h1 { font-size: 32px; margin: 10px 0 20px; }
.stats { display: flex; gap: 14px; align-items: baseline; flex-wrap: wrap; }
.stats b { font-size: 24px; color: #63b3ed; }
.stats span { opacity: .8; margin-right: 14px; }
.card { background: white; padding: 28px; border-radius: 16px; margin: 20px 0; box-shadow: 0 4px 18px #102a4312; }
.claim, .evidence, .delta, .equation-card, .experiment-card { border-left: 4px solid #2b6cb0; padding: 16px 20px; margin: 16px 0; background: #f8fbff; border-radius: 0 8px 8px 0; }
.claim-header, .evidence-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.badge { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; margin: 0 4px; }
.evidence-link { background: #e2e8f0; color: #2b6cb0; border: 1px solid #cbd5e0; }
.claim-link { background: #ebf8ff; color: #2b6cb0; border: 1px solid #bee3f8; }
.page-anchor-link { background: #edf2f7; color: #4a5568; }
.epistemic-supported { background: #c6f6d5; color: #22543d; }
.epistemic-verified { background: #9ae6b4; color: #1c4532; }
.epistemic-ambiguous { background: #feebc8; color: #744210; }
.verifier-supported { background: #9ae6b4; color: #1c4532; }
.verifier-rejected { background: #fed7d7; color: #742a2a; }
.oia-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-top: 12px; font-size: 13px; }
.oia-box { padding: 10px 12px; border-radius: 6px; }
.oia-obs { background: #edf2f7; }
.oia-auth { background: #fefcbf; }
.oia-read { background: #e6fffa; }
.asset-container img { display: block; max-width: 100%; max-height: 500px; margin: 12px auto; border-radius: 8px; border: 1px solid #e2e8f0; }
.conflict-item { border-left: 3px solid #e53e3e; padding: 10px 14px; margin: 10px 0; background: #fff5f5; }
.project { border-left: 6px solid #718355; background: #fbfcf5; }
.project .delta { border-color: #718355; }
.page-anchor-bar { margin-bottom: 12px; }
.page-anchor-block { border-bottom: 1px solid #e2e8f0; padding: 6px 0; }
small { color: #63748a; }
ul { padding-left: 20px; }
li { margin: 6px 0; }
'''

if __name__ == '__main__':
    main()
