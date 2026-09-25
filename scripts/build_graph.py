#!/usr/bin/env python3
import argparse,json
from pathlib import Path
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);pm=json.load(open(r/'model/paper_model.json'));nodes=[]
 kinds={'claims':'claim','observations':'observation','experiments':'experiment','figures':'figure','tables':'table','assumptions':'assumption','limitations':'boundary','open_questions':'question','methods':'method','portable_components':'portable_component','side_findings':'side_finding','anomalies':'anomaly'}
 for k,kind in kinds.items():nodes.extend({'id':x['id'],'kind':kind} for x in pm.get(k,[]) if x.get('id'))
 ids={n['id'] for n in nodes};edges=[]
 def add(fr,rel,to):
  if fr in ids and to in ids:edges.append({'from':fr,'rel':rel,'to':to})
 for c in pm.get('claims',[]):
  for e in c.get('evidence',[]):add(c['id'],'supported_by',e)
 for o in pm.get('observations',[]):
  for e in o.get('source',[]):add(o['id'],'observed_in',e)
 for e in pm.get('experiments',[]):
  for c in e.get('supports',[]):add(e['id'],'tested_by',c)
 for f in pm.get('figures',[]):
  for c in f.get('supports_claims',[]):add(f['id'],'supports',c)
 (r/'model/evidence_graph.json').write_text(json.dumps({'schema_version':'1.0','nodes':nodes,'edges':edges},indent=2,ensure_ascii=False)+'\n');print(f'OK graph nodes={len(nodes)} edges={len(edges)}')
if __name__=='__main__':main()
