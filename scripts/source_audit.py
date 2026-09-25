#!/usr/bin/env python3
"""Cross-check Source Reconstruction inventory, Paper Model and local assets."""
import argparse,json,sys
from pathlib import Path
from validate_common import load_json

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);errs=[]
 inv=load_json(r/'model/figure_inventory.json');pm=load_json(r/'model/paper_model.json');source=load_json(r/'model/source_map.json')
 inv_ids={x.get('id') for x in inv.get('items',[])};model_ids={x.get('id') for x in pm.get('figures',[])+pm.get('tables',[])}
 for ident in sorted(inv_ids-model_ids):errs.append(f'inventory item absent from paper model: {ident}')
 for ident in sorted(model_ids-inv_ids):errs.append(f'paper model item absent from inventory: {ident}')
 pages=len(source.get('pages',[]))
 for item in inv.get('items',[]):
  if not isinstance(item.get('page'),int) or item['page']<1 or item['page']>pages:errs.append(f"invalid page for {item.get('id')}")
  if item.get('file') and not (r/item['file']).exists():errs.append(f"missing asset for {item.get('id')}: {item['file']}")
  if item.get('caption_status')=='OK' and not item.get('caption_original'):errs.append(f"OK caption empty for {item.get('id')}")
 if errs:print(json.dumps({'status':'FAIL','errors':errs},ensure_ascii=False,indent=2));return 1
 print(json.dumps({'status':'OK','items':len(inv.get('items',[]))}));return 0
if __name__=='__main__':sys.exit(main())
