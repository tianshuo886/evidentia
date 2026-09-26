#!/usr/bin/env python3
"""Build a stable, cross-paper searchable literature index from frozen models."""
import argparse,json
from pathlib import Path
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();rows=[]
 for p in Path(a.root).glob('**/model/paper_model.json'):
  try:d=json.load(open(p));m=json.load(open(p.parent/'manifest.json'))
  except Exception:continue
  if m.get('status')!='FROZEN':continue
  paper=d.get('paper',{});rows.append({'paper_id':d.get('paper_id'), 'title':paper.get('title'),'year':paper.get('year'),'paper_type':d.get('paper_type'),'methods':[x.get('id') for x in d.get('methods',[])],'portable_components':[x.get('id') for x in d.get('portable_components',[])],'claims':[x.get('id') for x in d.get('claims',[])],'path':str(p.parent),'model_sha256':m.get('hashes',{}).get('model/paper_model.json')})
 out={'schema_version':'1.0','papers':rows};Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(f'indexed {len(rows)} papers')
if __name__=='__main__':main()
