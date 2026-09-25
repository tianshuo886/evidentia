#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
from validate_common import *
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out);errs=[];pm=load_json(root/'model/paper_model.json'); valid=set(all_ids(pm))
 for lens in LENSES:
  p=root/'lens'/f'{lens}.json'
  if not p.exists():errs.append(f'missing lens/{lens}.json');continue
  try:d=load_json(p);errs+=schema_validate(d,'lens')
  except Exception as e:errs.append(f'lens/{lens}: {e}');continue
  if d.get('lens')!=lens:errs.append(f'lens name mismatch: {lens}')
  for f in d.get('findings',[]):
   for e in f.get('evidence',[]):
    if e not in valid and not e.startswith('p.'):errs.append(f'{f.get("id")} dangling evidence {e}')
   if f.get('id') in valid:errs.append(f'finding ID collision {f.get("id")}')
 if errs:print(json.dumps({'status':'FAIL','errors':errs},ensure_ascii=False,indent=2));return 1
 print(json.dumps({'status':'OK','lenses':list(LENSES)}));return 0
if __name__=='__main__':sys.exit(main())
