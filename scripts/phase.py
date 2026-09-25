#!/usr/bin/env python3
"""Advance the explicit Evidentia state machine without skipping gates."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
ORDER={'INGEST':'SOURCE_RECONSTRUCTION','SOURCE_RECONSTRUCTION':'OPEN_READING','OPEN_READING':'LENS','LENS':'FREEZE','FREEZE':'RENDER','RENDER':'COMPLETE'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--complete',required=True);a=ap.parse_args();r=Path(a.out);p=r/'run_state.json';s=json.load(open(p));current=s['phase'];expected=ORDER.get(current)
 if expected!=a.complete:raise SystemExit(f'REFUSED: expected next phase {expected}, got {a.complete}')
 gates={'SOURCE_RECONSTRUCTION':r/'model/source_map.json','OPEN_READING':r/'model/paper_model.json','LENS':r/'lens/counterfactual.json','FREEZE':r/'model/manifest.json','RENDER':r/'reader/reader.html'}
 if a.complete in gates and not gates[a.complete].exists():raise SystemExit(f'REFUSED: missing gate artifact {gates[a.complete]}')
 if a.complete=='LENS':
  import subprocess
  if subprocess.run([sys.executable,str(Path(__file__).with_name('check_lenses.py')),'--out',str(r)]).returncode!=0: raise SystemExit('REFUSED: Lens gate failed')
 if a.complete=='FREEZE':
  manifest=json.load(open(r/'model/manifest.json'))
  if manifest.get('status')!='FROZEN': raise SystemExit('REFUSED: manifest is not FROZEN')
 if a.complete=='RENDER':
  import subprocess
  if subprocess.run([sys.executable,str(Path(__file__).with_name('reader_audit.py')),'--out',str(r)]).returncode!=0: raise SystemExit('REFUSED: Reader audit failed')
 s['history'].append({'phase':current,'status':'completed','at':datetime.now(timezone.utc).isoformat()});s['phase']=a.complete;s['history'].append({'phase':a.complete,'status':'started','at':datetime.now(timezone.utc).isoformat()});s['artifacts'][a.complete]=str(gates[a.complete]) if a.complete in gates else '';p.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n');print(a.complete)
if __name__=='__main__':main()
