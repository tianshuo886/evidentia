#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from validate_common import *
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out);pm=load_json(root/'model/paper_model.json'); merged=[];seen=set(); conflicts=[]
 for lens in LENSES:
  d=load_json(root/'lens'/f'{lens}.json')
  for f in d.get('findings',[]):
   key=(f.get('statement','').strip().lower(),tuple(sorted(f.get('evidence',[]))))
   if key in seen: continue
   seen.add(key);merged.append({'id':f['id'],'statement':f['statement'],'source':f.get('evidence',[]),'from_lens':[lens],'epistemic':f.get('epistemic')})
 pm['lens_synthesis']=merged
 (root/'model/paper_model.json').write_text(json.dumps(pm,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'status':'OK','merged':len(merged),'conflicts':len(conflicts)}))
if __name__=='__main__':main()
