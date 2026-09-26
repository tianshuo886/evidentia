#!/usr/bin/env python3
"""Audit that the Reader preserves canonical content and all provenance links."""
import argparse,json,re,sys
from pathlib import Path
from validate_common import sha256
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);errs=[]
 for rel in ('reader/reader.html','reader/render_ir.json','model/paper_model.json'): 
  if not (r/rel).exists(): errs.append('missing '+rel)
 if (r/'reader/reader.html').exists():
  s=(r/'reader/reader.html').read_text()
  if '{{' in s or '}}' in s: errs.append('unresolved template placeholder')
  pm=json.load(open(r/'model/paper_model.json'));ir=json.load(open(r/'reader/render_ir.json'))
  for c in pm.get('claims',[]):
   if c.get('id') not in ir.get('claim_cards',[]):errs.append('claim omitted '+c.get('id',''))
  for f in pm.get('figures',[]):
   if f.get('id') not in ir.get('figure_blocks',[]):errs.append('figure omitted '+f.get('id',''))
  for t in pm.get('tables',[]):
   if t.get('id') not in ir.get('table_blocks',[]):errs.append('table omitted '+t.get('id',''))
  for f in pm.get('figures',[]):
   if f.get('file') and not (r/f['file']).exists():errs.append('missing figure asset '+f['file'])
  if not pm.get('unresolved') and any(c.get('epistemic') in ('AMBIGUOUS','INSUFFICIENT_EVIDENCE','UNRESOLVED') for c in pm.get('claims',[])):
   errs.append('unresolved claim is not visible in unresolved list')
 if errs: print(json.dumps({'status':'FAIL','errors':errs},indent=2));return 1
 print(json.dumps({'status':'OK','reader_sha256':sha256(r/'reader/reader.html')}));return 0
if __name__=='__main__':sys.exit(main())
