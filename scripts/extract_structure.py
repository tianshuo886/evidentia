#!/usr/bin/env python3
"""Extract sections, equations and explicit figure/table mentions by page."""
import argparse,json,os,re,sys
from pathlib import Path
from validate_common import sha256
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pdf',required=True);ap.add_argument('--out',required=True);ap.add_argument('--supplement',action='append',default=[]);a=ap.parse_args()
 try:import fitz
 except ImportError:sys.exit('ERROR: PyMuPDF missing')
 doc=fitz.open(a.pdf);pages=[]
 for n,p in enumerate(doc,1):
  txt=p.get_text(); sections=[]
  for line in txt.splitlines():
   line=line.strip()
   if re.match(r'^(?:\d+(?:\.\d+)*\s+|[A-Z][A-Z ]{3,}$)',line) and len(line)<160:sections.append(line)
  mentions=[]
  for m in re.finditer(r'\b(Fig(?:ure)?\.?\s*[S]?\d+[A-Za-z]?|Table\s*[S]?\d+[A-Za-z]?)',txt,re.I):mentions.append({'label':m.group(1),'kind':'table' if m.group(1).lower().startswith('table') else 'figure','bbox':[]})
  equations=[x for x in txt.splitlines() if re.search(r'[=∑∫]|\(\s*\d+\s*\)',x) and len(x.strip())<300]
  pages.append({'number':n,'sections':sections,'equations':equations,'mentions':mentions})
 out={'schema_version':'1.0','pdf_sha256':sha256(a.pdf),'pages':pages,'supplements':[os.path.abspath(x) for x in a.supplement]};Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(f'OK source map pages={len(pages)}')
if __name__=='__main__':main()
