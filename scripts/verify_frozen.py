#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
from validate_common import sha256
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);m=json.load(open(r/'model/manifest.json'));errs=[]
 if m.get('status')!='FROZEN':errs.append('manifest status is not FROZEN')
 for rel,h in m.get('hashes',{}).items():
  p=r/rel
  if not p.exists():errs.append('missing '+rel)
  elif sha256(p)!=h:errs.append('hash mismatch '+rel)
 for lens,h in m.get('lens_hashes',{}).items():
  p=r/'lens'/f'{lens}.json'
  if not p.exists() or sha256(p)!=h:errs.append('hash mismatch lens/'+lens+'.json')
 print(json.dumps({'status':'OK' if not errs else 'FAIL','errors':errs},indent=2));return 0 if not errs else 1
if __name__=='__main__':sys.exit(main())
