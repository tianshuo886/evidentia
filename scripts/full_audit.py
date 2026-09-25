#!/usr/bin/env python3
"""Run all available Evidentia gates and return one machine-readable audit."""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def call(script,*args):
 p=subprocess.run([sys.executable,str(HERE/script),*args],capture_output=True,text=True);return {'script':script,'returncode':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-2000:]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);results=[]
 for script in ('validate_model.py','check_lenses.py','source_audit.py','verify_frozen.py','reader_audit.py'):
  results.append(call(script,'--out',str(r)))
 ok=all(x['returncode']==0 for x in results);report={'status':'OK' if ok else 'FAIL','checks':results};(r/'audit_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
