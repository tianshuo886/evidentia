#!/usr/bin/env python3
"""Check six lens outputs: schema, naming, evidence refs, and baseline binding (Phase-A).

Fail-closed: every lens must carry source_sha256 == actual source/paper.pdf and
base_sha256 == open_reading_manifest.base_model_sha256 (when a baseline exists).
"""
import argparse,json,sys
from pathlib import Path
from validate_common import *
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out);errs=[];pm=load_json(root/'model/paper_model.json'); valid=set(all_ids(pm))
 actual_src=sha256(root/'source/paper.pdf') if (root/'source/paper.pdf').exists() else None
 base_expected=None; contract_expected=None; prompt_expected=None
 man_path=root/'model/open_reading_manifest.json'
 if man_path.exists():
  try:
   om=load_json(man_path)
   errs+=schema_validate(om,'open_reading_manifest')
   base_expected=om.get('base_model_sha256');contract_expected=om.get('lens_contract_version');prompt_expected=om.get('prompt_version')
  except Exception as e:errs.append(f'unparseable model/open_reading_manifest.json: {e}')
 else:errs.append('missing model/open_reading_manifest.json (run snapshot_baseline.py)')
 for lens in LENSES:
  p=root/'lens'/f'{lens}.json'
  if not p.exists():errs.append(f'missing lens/{lens}.json');continue
  try:d=load_json(p);errs+=schema_validate(d,'lens')
  except Exception as e:errs.append(f'lens/{lens}: {e}');continue
  if d.get('lens')!=lens:errs.append(f'lens name mismatch: {lens}')
  if actual_src and d.get('source_sha256')!=actual_src:errs.append(f'{lens}: source_sha256 mismatch (wrong-paper lens or changed PDF)')
  if base_expected and d.get('base_sha256')!=base_expected:errs.append(f'{lens}: base_sha256 mismatch (stale baseline; re-run snapshot_baseline.py + lens_runner.py)')
  if base_expected and d.get('base_model_sha256')!=base_expected:errs.append(f'{lens}: base_model_sha256 mismatch open_reading_manifest (stale baseline)')
  if contract_expected and d.get('lens_contract_version')!=contract_expected:errs.append(f'{lens}: lens_contract_version mismatch open_reading_manifest')
  if prompt_expected and d.get('prompt_version')!=prompt_expected:errs.append(f'{lens}: prompt_version mismatch open_reading_manifest')
  for f in d.get('findings',[]):
   for e in f.get('evidence',[]):
    if e not in valid and not e.startswith('p.'):errs.append(f'{f.get("id")} dangling evidence {e}')
   if f.get('id') in valid:errs.append(f'finding ID collision {f.get("id")}')
 if errs:print(json.dumps({'status':'FAIL','errors':errs},ensure_ascii=False,indent=2));return 1
 print(json.dumps({'status':'OK','lenses':list(LENSES)}));return 0
if __name__=='__main__':sys.exit(main())
