#!/usr/bin/env python3
"""Reconstruct Figure/Table inventory with conservative caption binding."""
import argparse,json,os,re,sys
CAP_RE=re.compile(r'^\s*((?:Fig(?:ure)?\.?|Table|Supplementary\s+(?:Fig(?:ure)?\.?|Table))\s*[S]?\d+[A-Za-z]?)\s*[:.]?\s*(.*)$',re.I)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pdf',required=True);ap.add_argument('--out',required=True);ap.add_argument('--inventory',required=True);ap.add_argument('--min-size',type=int,default=400);ap.add_argument('--dpi',type=int,default=200);a=ap.parse_args()
 try:import fitz
 except ImportError:sys.exit('ERROR: PyMuPDF missing')
 os.makedirs(a.out,exist_ok=True);os.makedirs(os.path.dirname(os.path.abspath(a.inventory)),exist_ok=True);doc=fitz.open(a.pdf);saved=[];items=[];seen=set();n=0
 for pno,page in enumerate(doc):
  for b in page.get_text('blocks'):
   for line in b[4].splitlines():
    line=line.strip();m=CAP_RE.match(line)
    if not m:continue
    label=m.group(1).strip();kind='table' if label.lower().startswith('table') else 'figure';num=re.search(r'[S]?\d+[A-Za-z]?',label,re.I).group(0);ident=('T' if kind=='table' else 'F')+f'{int(re.sub("[^0-9]","",num) or 0):02d}'
    if ident in seen:ident+=f'-p{pno+1}'
    seen.add(ident);cap=(label+' '+m.group(2)).strip();bbox=list(b[:4]);item={'id':ident,'paper_label':label,'kind':kind,'page':pno+1,'caption_original':cap,'caption_status':'OK','source_location':f'p.{pno+1}','role':'unassigned','depth':'unassigned','file':None,'bbox':bbox,'caption_bbox':bbox,'subfigures':sorted(set(re.findall(r'\(([a-z])\)',cap,re.I))),'extraction_method':'none','confidence':0.75,'inspection':''}
    best=None
    for img in page.get_images(full=True):
     xref=img[0]
     if xref in saved:continue
     try:pix=fitz.Pixmap(doc,xref)
     except Exception:continue
     if max(pix.width,pix.height)>=a.min_size and (best is None or pix.width*pix.height>best[0]):best=(pix.width*pix.height,xref,pix)
    if best:
     _,xref,pix=best
     if pix.n-pix.alpha>3:
      try:pix=fitz.Pixmap(fitz.csRGB,pix)
      except Exception:pass
     n+=1;fn=f'fig{n:02d}_p{pno+1}_{pix.width}x{pix.height}.png';pix.save(os.path.join(a.out,fn));saved.append(xref);item['file']=f'assets/figures/{fn}';item['extraction_method']='embedded';item['confidence']=0.9
    items.append(item)
 for item in items:
  if item['file'] is None and item['kind']=='figure':
   page=doc[item['page']-1];pix=page.get_pixmap(dpi=a.dpi,alpha=False);fn=f"page_p{item['page']}_{pix.width}x{pix.height}.png";pix.save(os.path.join(a.out,fn));item['file']=f'assets/figures/{fn}';item['extraction_method']='page_crop';item['confidence']=0.55
 inv={'schema_version':'1.0','pdf':os.path.abspath(a.pdf),'pages':len(doc),'items':items,'embedded_saved':len(saved),'unmatched_assets':[],'review_required':[i['id'] for i in items if i['confidence']<0.8]}
 with open(a.inventory,'w',encoding='utf-8') as f:json.dump(inv,f,ensure_ascii=False,indent=2)
 print(f'OK: pages={len(doc)} items={len(items)} review_required={len(inv["review_required"])}')
if __name__=='__main__':main()
