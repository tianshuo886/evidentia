#!/usr/bin/env python3
"""Strict freeze gate. Refuses missing provenance, dangling references, files and lens passes."""
import argparse,json,sys
from pathlib import Path
from validate_common import *
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out);errs=[]
 required=['source/paper.pdf','model/paper_model.json','model/evidence_graph.json','model/figure_inventory.json','model/source_map.json']
 for rel in required:
  if not (root/rel).exists():errs.append(f'missing {rel}')
 for rel in ('model/paper_model.json','model/evidence_graph.json','model/figure_inventory.json','model/source_map.json'):
  p=root/rel
  if p.exists():
   try:
    d=load_json(p);errs+=schema_validate(d,p.stem)
   except Exception as e:errs.append(f'unparseable {rel}: {e}')
 pm=load_json(root/'model/paper_model.json') if (root/'model/paper_model.json').exists() else {}
 inv=load_json(root/'model/figure_inventory.json') if (root/'model/figure_inventory.json').exists() else {}
 # --- Phase-A source-SHA content-address chain (fail closed) ---
 actual_src=sha256(root/'source/paper.pdf') if (root/'source/paper.pdf').exists() else None
 if actual_src is None:errs.append('missing source/paper.pdf for SHA chain')
 else:
  sm=root/'model/source_map.json'
  if sm.exists():
   try:
    v=load_json(sm).get('pdf_sha256')
    if v!=actual_src:errs.append('source_map.pdf_sha256 mismatch actual source/paper.pdf (wrong or changed PDF)')
   except Exception as e:errs.append(f'unparseable model/source_map.json SHA: {e}')
  if inv:
   v=inv.get('source_sha256')
   if v and v!=actual_src:errs.append('figure_inventory.source_sha256 mismatch actual source/paper.pdf')
   elif not v:errs.append('figure_inventory.source_sha256 missing (re-run extract_figs.py)')
  if pm:
   for field in ('source_sha256',):
    v=pm.get(field)
    if v and v!=actual_src:errs.append(f'paper_model.{field} mismatch actual source/paper.pdf')
    elif not v:errs.append(f'paper_model.{field} missing')
   if pm.get('paper',{}).get('pdf_sha256') and pm['paper']['pdf_sha256']!=actual_src:errs.append('paper_model.paper.pdf_sha256 mismatch actual source/paper.pdf')
  graph=load_json(root/'model/evidence_graph.json') if (root/'model/evidence_graph.json').exists() else {}
  if graph:
   v=graph.get('source_sha256')
   if v and v!=actual_src:errs.append('evidence_graph.source_sha256 mismatch actual source/paper.pdf')
   elif not v:errs.append('evidence_graph.source_sha256 missing (re-run build_graph.py)')
  base_expected=None
  orman=root/'model/open_reading_manifest.json'
  contract_expected=None;prompt_expected=None
  if orman.exists():
   try:
    om=load_json(orman)
    errs+=['open_reading_manifest: '+e for e in schema_validate(om,'open_reading_manifest')]
    if om.get('source_sha256')!=actual_src:errs.append('open_reading_manifest.source_sha256 mismatch actual source/paper.pdf')
    base_expected=om.get('base_model_sha256');contract_expected=om.get('lens_contract_version');prompt_expected=om.get('prompt_version')
   except Exception as e:errs.append(f'unparseable model/open_reading_manifest.json: {e}')
  else:errs.append('missing model/open_reading_manifest.json (run snapshot_baseline.py)')
  if base_expected and (root/'model/open_reading_model.json').exists():
   import hashlib as _hl
   if _hl.sha256((root/'model/open_reading_model.json').read_bytes()).hexdigest()!=base_expected:errs.append('open_reading_model.json hash mismatch manifest (changed baseline)')
  elif not (root/'model/open_reading_model.json').exists():errs.append('missing model/open_reading_model.json')
 ids=all_ids(pm); graph=load_json(root/'model/evidence_graph.json') if (root/'model/evidence_graph.json').exists() else {}
 nodeids={n.get('id') for n in graph.get('nodes',[])}
 for e in graph.get('edges',[]):
  if e.get('from') not in nodeids or e.get('to') not in nodeids:errs.append(f'dangling graph edge: {e}')
 for i in inv.get('items',[]):
  if i.get('role') in (None,'unassigned') or i.get('depth') in (None,'unassigned'):errs.append(f"uninspected {i.get('id')}")
  if i.get('caption_status')=='OK' and not i.get('caption_original'):errs.append(f"missing caption {i.get('id')}")
  if i.get('binding_method') not in ('embedded','page_crop','manual','caption_geometry','none',None):errs.append(f"invalid binding_method {i.get('id')}")
  if i.get('role')=='critical':
   f=i.get('file');
   if not f or not (root/f).exists():errs.append(f"critical asset missing for {i.get('id')}: {f}")
 for c in pm.get('claims',[]):
  if not c.get('evidence') and c.get('epistemic') not in ('NOT_STATED','UNRESOLVED'):errs.append(f"claim without evidence {c.get('id')}")
 for r in sorted(refs(pm)):
  if r.startswith(('p.','Fig.','Table.')):continue
  if r not in ids:errs.append(f'dangling reference {r}')
 for lens in LENSES:
  lp=root/'lens'/f'{lens}.json'
  if not lp.exists():errs.append(f'missing lens/{lens}.json')
  else:
   try:
    ld=load_json(lp); errs += schema_validate(ld,'lens')
    if actual_src and ld.get('source_sha256')!=actual_src:errs.append(f'lens/{lens}.json source_sha256 mismatch (wrong-paper lens or changed PDF)')
    if base_expected and ld.get('base_sha256')!=base_expected:errs.append(f'lens/{lens}.json base_sha256 mismatch open_reading_manifest (stale baseline)')
    if base_expected and ld.get('base_model_sha256')!=base_expected:errs.append(f'lens/{lens}.json base_model_sha256 mismatch open_reading_manifest (stale baseline)')
    if contract_expected and ld.get('lens_contract_version')!=contract_expected:errs.append(f'lens/{lens}.json lens_contract_version mismatch open_reading_manifest')
    if prompt_expected and ld.get('prompt_version')!=prompt_expected:errs.append(f'lens/{lens}.json prompt_version mismatch open_reading_manifest')
   except Exception as e: errs.append(f'unparseable lens/{lens}.json: {e}')
 lr=root/'model/lens_reconciliation.json'
 if not lr.exists():errs.append('missing model/lens_reconciliation.json (run merge_lenses.py)')
 else:
  try:
   lrd=load_json(lr);errs+=['lens_reconciliation: '+e for e in schema_validate(lrd,'lens_reconciliation')]
   if actual_src and lrd.get('source_sha256')!=actual_src:errs.append('lens_reconciliation.source_sha256 mismatch actual source/paper.pdf')
   if base_expected and lrd.get('base_model_sha256')!=base_expected:errs.append('lens_reconciliation.base_model_sha256 mismatch open_reading_manifest (stale baseline)')
   # erased-conflict detection: every TENSION group merge_lenses would emit must still be recorded
   rec_ids={i.get('id') for i in lrd.get('items',[])}
   for c in pm.get('lens_conflicts',[]) or []:
    for fid in c.get('findings',[]):
     if fid not in rec_ids and fid not in ids:errs.append(f'lens_conflicts references unknown finding {fid} (conflict erased from reconciliation)')
   # lens_synthesis/conflict cross-check: merged items sharing evidence with distinct statements must appear in lens_conflicts
   syn=pm.get('lens_synthesis',[]) or []
   by_ev={}
   for m in syn:
    for e in m.get('source',[]):by_ev.setdefault(e,[]).append(m.get('id'))
   for ev,mids in by_ev.items():
    stmts={next((x.get('statement') for x in syn if x.get('id')==i),None) for i in mids}
    if len(stmts)>1:
     covered=any(set(mids)<=set(c.get('findings',[])) for c in (pm.get('lens_conflicts',[]) or []))
     if not covered:errs.append(f'conflict on {ev} not recorded in lens_conflicts (conflict erased)')
  except Exception as e:errs.append(f'unparseable model/lens_reconciliation.json: {e}')
 if not pm.get('unresolved') and any(c.get('epistemic') in ('AMBIGUOUS','INSUFFICIENT_EVIDENCE','UNRESOLVED') for c in pm.get('claims',[])):errs.append('unresolved claims must be explicitly listed')
 if not pm.get('coverage'):errs.append('coverage audit missing')
 if (root/'model/source_map.json').exists() and (root/'model/figure_inventory.json').exists():
  inv_ids={x.get('id') for x in inv.get('items',[])};model_ids={x.get('id') for x in pm.get('figures',[])+pm.get('tables',[])}
  for ident in sorted(inv_ids-model_ids): errs.append(f'inventory item absent from model {ident}')
  for ident in sorted(model_ids-inv_ids): errs.append(f'model item absent from inventory {ident}')
 status='FROZEN' if not errs else 'FAIL';man={'schema_version':'1.0','status':status,'hashes':{},'lens_hashes':{},'counts':{'figures':sum(i.get('kind')=='figure' for i in inv.get('items',[])),'tables':sum(i.get('kind')=='table' for i in inv.get('items',[])),'claims':len(pm.get('claims',[]))},'errors':errs}
 man['source_sha256']=actual_src
 if base_expected:man['base_model_sha256']=base_expected
 for rel in required:
  if (root/rel).exists():man['hashes'][rel]=sha256(root/rel)
 for rel in ('model/open_reading_model.json','model/open_reading_manifest.json','model/lens_reconciliation.json'):
  if (root/rel).exists():man['hashes'][rel]=sha256(root/rel)
 for lens in LENSES:
  p=root/'lens'/f'{lens}.json'
  if p.exists():man['lens_hashes'][lens]=sha256(p)
 (root/'model').mkdir(exist_ok=True);(root/'model/manifest.json').write_text(json.dumps(man,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps(man,ensure_ascii=False,indent=2));return 0 if status=='FROZEN' else 1
if __name__=='__main__':sys.exit(main())
