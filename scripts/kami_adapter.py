#!/usr/bin/env python3
"""Use Kami's rendering/visual checks as Evidentia's presentation backend.

Evidentia owns the Reader information architecture. Kami is invoked only for
PDF visual, density, orphan, placeholder and font checks.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--kami-root',default=os.environ.get('KAMI_ROOT'));a=ap.parse_args();r=Path(a.out)
 if not a.kami_root: raise SystemExit('KAMI_ROOT or --kami-root is required; clone https://github.com/tw93/Kami')
 build=Path(a.kami_root)/'skills/kami/scripts/build.py'
 if not build.exists(): build=Path(a.kami_root)/'scripts/build.py'
 if not build.exists(): raise SystemExit(f'Kami build.py not found under {a.kami_root}')
 pdf=r/'reader/reader.pdf'
 if not pdf.exists(): raise SystemExit(f'missing {pdf}; run render_reader.py first')
 checks=[['--check-visual',str(pdf)],['--check-orphans',str(pdf)],['--check-density',str(pdf)],['--check-fonts',str(pdf)]];results=[]
 for args in checks:
  p=subprocess.run([sys.executable,str(build),*args],capture_output=True,text=True);results.append({'args':args,'returncode':p.returncode,'stdout':p.stdout[-3000:],'stderr':p.stderr[-1000:]})
 report={'status':'OK' if all(x['returncode']==0 for x in results) else 'FAIL','kami_root':str(a.kami_root),'checks':results};(r/'reader/kami_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='OK' else 1
if __name__=='__main__':sys.exit(main())
