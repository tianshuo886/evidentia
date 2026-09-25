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
 ids=all_ids(pm); graph=load_json(root/'model/evidence_graph.json') if (root/'model/evidence_graph.json').exists() else {}
 nodeids={n.get('id') for n in graph.get('nodes',[])}
 for e in graph.get('edges',[]):
  if e.get('from') not in nodeids or e.get('to') not in nodeids:errs.append(f'dangling graph edge: {e}')
 for i in inv.get('items',[]):
  if i.get('role') in (None,'unassigned') or i.get('depth') in (None,'unassigned'):errs.append(f"uninspected {i.get('id')}")
  if i.get('caption_status')=='OK' and not i.get('caption_original'):errs.append(f"missing caption {i.get('id')}")
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
   try: errs += schema_validate(load_json(lp),'lens')
   except Exception as e: errs.append(f'unparseable lens/{lens}.json: {e}')
 if not pm.get('unresolved') and any(c.get('epistemic') in ('AMBIGUOUS','INSUFFICIENT_EVIDENCE','UNRESOLVED') for c in pm.get('claims',[])):errs.append('unresolved claims must be explicitly listed')
 if not pm.get('coverage'):errs.append('coverage audit missing')
 if (root/'model/source_map.json').exists() and (root/'model/figure_inventory.json').exists():
  inv_ids={x.get('id') for x in inv.get('items',[])};model_ids={x.get('id') for x in pm.get('figures',[])+pm.get('tables',[])}
  for ident in sorted(inv_ids-model_ids): errs.append(f'inventory item absent from model {ident}')
  for ident in sorted(model_ids-inv_ids): errs.append(f'model item absent from inventory {ident}')
 status='FROZEN' if not errs else 'FAIL';man={'schema_version':'1.0','status':status,'hashes':{},'lens_hashes':{},'counts':{'figures':sum(i.get('kind')=='figure' for i in inv.get('items',[])),'tables':sum(i.get('kind')=='table' for i in inv.get('items',[])),'claims':len(pm.get('claims',[]))},'errors':errs}
 for rel in required:
  if (root/rel).exists():man['hashes'][rel]=sha256(root/rel)
 for lens in LENSES:
  p=root/'lens'/f'{lens}.json'
  if p.exists():man['lens_hashes'][lens]=sha256(p)
 (root/'model').mkdir(exist_ok=True);(root/'model/manifest.json').write_text(json.dumps(man,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps(man,ensure_ascii=False,indent=2));return 0 if status=='FROZEN' else 1
if __name__=='__main__':sys.exit(main())
