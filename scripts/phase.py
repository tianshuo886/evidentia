#!/usr/bin/env python3
"""Advance the explicit Evidentia state machine without skipping gates (Phase-A hardened).

Phase promotion requires: artifact exists + schema valid + hash recorded +
dependency (source SHA / baseline) valid. run_state.json itself must validate
against schemas/run_state.schema.json. Resume-safe: re-running a completed phase
re-validates instead of blindly skipping.
"""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
ORDER={'INGEST':'SOURCE_RECONSTRUCTION','SOURCE_RECONSTRUCTION':'OPEN_READING','OPEN_READING':'LENS','LENS':'FREEZE','FREEZE':'RENDER','RENDER':'COMPLETE'}
def fail(msg):raise SystemExit(f'REFUSED: {msg}')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--complete',required=True);a=ap.parse_args();r=Path(a.out);p=r/'run_state.json'
 sys.path.insert(0,str(Path(__file__).parent))
 from validate_common import load_json,schema_validate,sha256,validate_run_state
 if not p.exists():fail(f'missing {p}')
 errs=validate_run_state(p)
 if errs:fail(f'run_state.json schema-invalid: {errs}')
 s=load_json(p);current=s['phase'];expected=ORDER.get(current)
 if expected!=a.complete:fail(f'expected next phase {expected}, got {a.complete}')
 gates={'SOURCE_RECONSTRUCTION':r/'model/source_map.json','OPEN_READING':r/'model/paper_model.json','LENS':r/'lens/counterfactual.json','FREEZE':r/'model/manifest.json','RENDER':r/'reader/reader.html'}
 if a.complete in gates and not gates[a.complete].exists():fail(f'missing gate artifact {gates[a.complete]}')
 # source SHA stability: run_state.source_sha256 must still match actual PDF
 if (r/'source/paper.pdf').exists():
  actual=sha256(r/'source/paper.pdf')
  if s.get('source_sha256') and s['source_sha256']!=actual:fail('source/paper.pdf changed since run start (resume with changed source refused)')
 # preexisting artifact hashes: any hash recorded by an earlier phase must still match (tamper refused)
 for _phase,_h in (s.get('artifact_hashes') or {}).items():
  _g={'SOURCE_RECONSTRUCTION':r/'model/source_map.json','OPEN_READING':r/'model/paper_model.json','LENS':r/'lens/counterfactual.json','FREEZE':r/'model/manifest.json','RENDER':r/'reader/reader.html'}.get(_phase)
  if _g is not None and _g.exists() and sha256(_g)!=_h:fail(f'previously completed artifact changed since phase {_phase} ({_g}); resume refused')
 if a.complete=='SOURCE_RECONSTRUCTION':
  errs=schema_validate(load_json(r/'model/source_map.json'),'source_map')+schema_validate(load_json(r/'model/figure_inventory.json'),'figure_inventory')
  if errs:fail(f'source reconstruction schema-invalid: {errs}')
 if a.complete=='OPEN_READING':
  from validate_common import schema_validate as sv
  errs=sv(load_json(r/'model/paper_model.json'),'paper_model')
  if errs:fail(f'open reading model schema-invalid: {errs}')
  if not (r/'model/open_reading_manifest.json').exists():fail('missing model/open_reading_manifest.json (run snapshot_baseline.py)')
  errs=sv(load_json(r/'model/open_reading_manifest.json'),'open_reading_manifest')
  if errs:fail(f'open reading manifest schema-invalid: {errs}')
  s['base_sha256']=load_json(r/'model/open_reading_manifest.json').get('base_model_sha256')
 if a.complete=='LENS':
  import subprocess
  if subprocess.run([sys.executable,str(Path(__file__).with_name('check_lenses.py')),'--out',str(r)]).returncode!=0: fail('Lens gate failed')
  if not (r/'model/lens_reconciliation.json').exists():fail('missing model/lens_reconciliation.json (run merge_lenses.py)')
  errs=schema_validate(load_json(r/'model/lens_reconciliation.json'),'lens_reconciliation')
  if errs:fail(f'lens reconciliation schema-invalid: {errs}')
 if a.complete=='FREEZE':
  manifest=load_json(r/'model/manifest.json')
  errs=schema_validate(manifest,'manifest')
  if errs: fail(f'manifest schema-invalid: {errs}')
  if manifest.get('status')!='FROZEN': fail('manifest is not FROZEN')
  if (r/'source/paper.pdf').exists():
   if manifest.get('source_sha256')!=sha256(r/'source/paper.pdf'): fail('manifest source_sha256 != actual source/paper.pdf')
  if s.get('base_sha256') and manifest.get('base_model_sha256')!=s['base_sha256']: fail('manifest base_model_sha256 != run_state baseline')
  import subprocess
  if subprocess.run([sys.executable,str(Path(__file__).with_name('verify_frozen.py')),'--out',str(r)]).returncode!=0: fail('frozen hash re-verification failed')
 if a.complete=='RENDER':
  import subprocess
  if subprocess.run([sys.executable,str(Path(__file__).with_name('reader_audit.py')),'--out',str(r)]).returncode!=0: fail('Reader audit failed')
 s['history'].append({'phase':current,'status':'completed','at':datetime.now(timezone.utc).isoformat()});s['phase']=a.complete
 if current not in s.get('completed_phases',[]):s.setdefault('completed_phases',[]).append(current)
 s['history'].append({'phase':a.complete,'status':'started','at':datetime.now(timezone.utc).isoformat()});s['artifacts'][a.complete]=str(gates[a.complete]) if a.complete in gates else ''
 # record artifact hash for resume validation
 if a.complete in gates:s.setdefault('artifact_hashes',{})[a.complete]=sha256(gates[a.complete])
 p.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n');print(a.complete)
if __name__=='__main__':main()
