#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
from validate_common import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out);errs=[]
 files={'paper_model':'model/paper_model.json','evidence_graph':'model/evidence_graph.json','figure_inventory':'model/figure_inventory.json','source_map':'model/source_map.json'};data={}
 for n,rel in files.items():
  p=root/rel
  if not p.exists():errs.append(f'missing {rel}');continue
  try:data[n]=load_json(p);errs+=schema_validate(data[n],n)
  except Exception as e:errs.append(f'{rel}: {e}')
 pm=data.get('paper_model',{}); ids=all_ids(pm)
 seen=[]
 for key in ('questions','claims','observations','experiments','figures','tables','methods','assumptions','limitations','open_questions','anomalies','side_findings','portable_components'):
  for x in pm.get(key,[]) if isinstance(pm.get(key,[]),list) else []:
   if isinstance(x,dict) and x.get('id'): seen.append(x['id'])
 if len(ids)!=len(seen): errs.append('duplicate IDs')
 eg=data.get('evidence_graph',{}); node_ids={n.get('id') for n in eg.get('nodes',[])}
 if len(node_ids)!=len(eg.get('nodes',[])):errs.append('duplicate evidence graph node IDs')
 for edge in eg.get('edges',[]):
  if edge.get('from') not in node_ids or edge.get('to') not in node_ids:errs.append(f"dangling graph edge {edge}")
 for r in sorted(refs(pm)):
  if r.startswith(('p.','Fig.','Table.')):continue
  if r not in ids: errs.append(f'dangling model reference: {r}')
 for c in pm.get('claims',[]):
  if not c.get('evidence') and c.get('epistemic') not in ('NOT_STATED','UNRESOLVED'):errs.append(f"claim {c.get('id')} has no evidence")
 if errs:
  print(json.dumps({'status':'FAIL','errors':errs},ensure_ascii=False,indent=2));return 1
 print(json.dumps({'status':'OK','ids':len(ids),'graph_nodes':len(node_ids)}));return 0
if __name__=='__main__':sys.exit(main())
