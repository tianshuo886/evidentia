#!/usr/bin/env python3
"""Render the canonical model into a standalone Paper Reader HTML and optional PDF."""
import argparse,json,html,sys
from pathlib import Path
from validate_common import schema_validate
def esc(x):return html.escape(str(x or ''))
def card(title,body,cls='card'):return f'<section class="{cls}"><h2>{esc(title)}</h2>{body}</section>'
def li(items,fn=lambda x:x):return '<ul>'+''.join(f'<li>{fn(x)}</li>' for x in items)+'</ul>'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);pm=json.load(open(r/'model/paper_model.json'));inv=json.load(open(r/'model/figure_inventory.json'));deltas=[]
 for p in sorted((r/'apply').glob('*/research_delta.json')) if (r/'apply').exists() else []:deltas.append(json.load(open(p)))
 title=pm.get('paper',{}).get('title','Untitled paper'); claims=pm.get('claims',[]);figs=pm.get('figures',[]) or inv.get('items',[]);tables=pm.get('tables',[])
 dash=f'<div class="stats"><b>{len(claims)}</b><span>claims</span><b>{len(figs)}</b><span>figures</span><b>{len(tables)}</b><span>tables</span><b>{len(pm.get("unresolved",[]))}</b><span>unresolved</span></div>'
 body='<header><p class="eyebrow">PAPER RESEARCH OS · FROZEN MODEL</p><h1>'+esc(title)+'</h1>'+dash+'</header>'
 body+=card('30-second scan','<p>'+esc(' → '.join(pm.get('natural_structure',[])))+'</p><h3>Argument chain</h3>'+li(pm.get('argument_chain',[])))
 body+=card('5-minute read',''.join(f'<article class="claim" id="{esc(c.get("id"))}"><h3>{esc(c.get("id"))}: {esc(c.get("statement"))}</h3><p><strong>Evidence:</strong> {esc(", ".join(c.get("evidence",[])))}</p><p><strong>Epistemic:</strong> {esc(c.get("epistemic"))}</p></article>' for c in claims))
 body+=card('Evidence atlas',''.join(f'<article class="evidence" id="{esc(x.get("id"))}"><h3>{esc(x.get("paper_label",x.get("id")))}</h3><p>{esc(x.get("caption_original"))}</p><p><small>p.{esc(x.get("page"))} · {esc(x.get("role"))} · {esc(x.get("depth"))}</small></p>'+ (f'<img src="../{esc(x.get("file"))}" alt="{esc(x.get("paper_label"))}">' if x.get('file') else '')+'</article>' for x in figs))
 body+=card('Weakest links and boundaries',li(pm.get('limitations',[]),lambda x:esc(x.get('text')))+li(pm.get('unresolved',[]),lambda x:esc(x.get('issue'))))
 if deltas:
  body+=card('PROJECT DELTA',''.join(f'<article class="delta"><h3>{esc(d.get("project",{}).get("name"))}</h3><p>Changed beliefs: {len(d.get("changed_beliefs",[]))}; transfer units: {len(d.get("transfer_units",[]))}; experiments: {len(d.get("experiments",[]))}</p></article>' for d in deltas),'project')
 html_doc='''<!doctype html><html><head><meta charset="utf-8"><title>'''+esc(title)+'''</title><style>'''+CSS+'''</style></head><body>'''+body+'''</body></html>'''
 (r/'reader').mkdir(exist_ok=True);(r/'reader/reader.html').write_text(html_doc,encoding='utf-8')
 ir={'schema_version':'1.0','paper_id':pm.get('paper_id',''),'dashboard':{'title':title,'claim_count':len(claims)},'paper_map':pm.get('natural_structure',[]),'claim_cards':[c.get('id') for c in claims],'figure_blocks':[x.get('id') for x in figs if x.get('kind','figure')=='figure'],'table_blocks':[x.get('id') for x in tables],'delta_projects':[d.get('project',{}).get('name','') for d in deltas]};(r/'reader/render_ir.json').write_text(json.dumps(ir,indent=2,ensure_ascii=False)+'\n')
 try:
  from weasyprint import HTML;HTML(string=html_doc,base_url=str(r/'reader')).write_pdf(str(r/'reader/reader.pdf'))
 except Exception as e:print('PDF skipped:',e,file=sys.stderr)
 print('OK reader/reader.html')
CSS='''*{box-sizing:border-box}body{font-family:Inter,Arial,sans-serif;color:#17263c;background:#f6f8fb;max-width:1100px;margin:auto;padding:36px}header{background:#102a43;color:white;padding:36px;border-radius:18px;margin-bottom:22px}.eyebrow{letter-spacing:.12em;opacity:.7;font-size:12px}h1{font-size:34px;margin:10px 0 20px}.stats{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.stats b{font-size:26px}.stats span{opacity:.7;margin-right:12px}.card{background:white;padding:26px;border-radius:16px;margin:18px 0;box-shadow:0 4px 18px #102a4312}.claim,.evidence,.delta{border-left:4px solid #2b6cb0;padding:14px 18px;margin:12px 0;background:#f8fbff}.evidence img{display:block;max-width:100%;max-height:480px;margin:12px auto;border-radius:8px}.project{border-left:6px solid #718355;background:#fbfcf5}.project .delta{border-color:#718355}small{color:#63748a}li{margin:7px 0}'''
if __name__=='__main__':main()
