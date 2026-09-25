#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
from validate_common import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--paper',required=True);ap.add_argument('--delta',required=True);a=ap.parse_args();r=Path(a.paper);d=load_json(a.delta);errs=schema_validate(d,'research_delta');m=load_json(r/'model/manifest.json');pm=load_json(r/'model/paper_model.json');ids=all_ids(pm)
 if d.get('paper_model_sha256')!=m.get('hashes',{}).get('model/paper_model.json'):errs.append('delta paper_model_sha256 does not match frozen manifest')
 for ref in refs(d):
  if ref.startswith('G') or ref.startswith('TU') or ref.startswith('p.'):continue
  if ref not in ids:errs.append('dangling delta reference '+ref)
 print(json.dumps({'status':'OK' if not errs else 'FAIL','errors':errs},ensure_ascii=False,indent=2));return 0 if not errs else 1
if __name__=='__main__':sys.exit(main())
