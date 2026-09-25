#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
from validate_common import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--paper',required=True);ap.add_argument('--delta',required=True);a=ap.parse_args();r=Path(a.paper);d=load_json(a.delta);errs=schema_validate(d,'research_delta');m=load_json(r/'model/manifest.json');pm=load_json(r/'model/paper_model.json');ids=all_ids(pm)
 if d.get('paper_model_sha256')!=m.get('hashes',{}).get('model/paper_model.json'):errs.append('delta paper_model_sha256 does not match frozen manifest')
 gap_ids={g.get('id') for g in d.get('project_gap_map',[])}; component_ids={x.get('id') for x in pm.get('portable_components',[])}
 for item in d.get('contextual_reread',[])+d.get('changed_beliefs',[])+d.get('new_evidence',[])+d.get('new_unknowns',[]):
  for gap in item.get('gap_ids',[]):
   if gap not in gap_ids: errs.append('delta references unknown gap '+gap)
 for item in d.get('transfer_units',[]):
  for comp in item.get('component_ids',[]):
   if comp not in component_ids: errs.append('transfer unit references unknown component '+comp)
  for gap in item.get('gap_ids',[]):
   if gap not in gap_ids: errs.append('transfer unit references unknown gap '+gap)
 for item in d.get('experiments',[]):
  for gap in item.get('gap_ids',[]):
   if gap not in gap_ids: errs.append('experiment references unknown gap '+gap)
 for ref in refs(d):
  if ref.startswith('G') or ref.startswith('TU') or ref.startswith('p.'):continue
  if ref not in ids:errs.append('dangling delta reference '+ref)
 print(json.dumps({'status':'OK' if not errs else 'FAIL','errors':errs},ensure_ascii=False,indent=2));return 0 if not errs else 1
if __name__=='__main__':sys.exit(main())
