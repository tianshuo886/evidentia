#!/usr/bin/env python3
"""Reconcile independent Lens outputs without mutating canonical Paper Model facts."""
import argparse,json
from collections import defaultdict
from pathlib import Path
from validate_common import load_json
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args(); root=Path(a.out)
 groups=defaultdict(list); missing=[]
 for lens in LENSES:
  p=root/'lens'/f'{lens}.json'
  if not p.exists(): missing.append(lens); continue
  for f in load_json(p).get('findings',[]):
   key=(f.get('statement','').strip().lower(),tuple(sorted(f.get('evidence',[]))))
   groups[key].append((lens,f))
 agreements=[]; unique=[]
 for idx,(key,items) in enumerate(groups.items(),1):
  lenses=sorted({x[0] for x in items}); f=items[0][1]
  obj={'id':f'LS-{idx:03d}','statement':f.get('statement',''),'evidence':f.get('evidence',[]),'lenses':lenses,'epistemic':f.get('epistemic'),'support_count':len(lenses)}
  (agreements if len(lenses)>1 else unique).append(obj)
 # Conservative conflict candidate: same evidence, different statements from different lenses.
 by_evidence=defaultdict(list)
 for obj in agreements+unique:
  by_evidence[tuple(sorted(obj['evidence']))].append(obj)
 conflicts=[]
 for ev,items in by_evidence.items():
  statements={i['statement'].strip().lower() for i in items}
  if ev and len(statements)>1:
   conflicts.append({'id':f'LC-{len(conflicts)+1:03d}','evidence':list(ev),'findings':[i['id'] for i in items],'status':'UNRESOLVED'})
 synthesis={'schema_version':'1.0','paper_model_sha256':None,'agreement':agreements,'unique_findings':unique,'complementary_findings':[],'conflicts':conflicts,'unresolved_conflicts':conflicts,'cross_lens_support':[{'finding_id':x['id'],'lenses':x['lenses']} for x in agreements]}
 out=root/'model'/'lens_synthesis.json'; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(synthesis,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'status':'OK' if not missing else 'PARTIAL','agreements':len(agreements),'unique_findings':len(unique),'conflicts':len(conflicts),'missing_lenses':missing,'output':str(out)},ensure_ascii=False,indent=2)); return 0 if not missing else 1
if __name__=='__main__': raise SystemExit(main())
