#!/usr/bin/env python3
"""Merge lens findings with provenance preservation (Phase-A fix for provenance loss).

Same (statement, evidence) findings converge into ONE reconciliation item that keeps
ALL supporting_lenses instead of dropping duplicates. Distinct findings are kept as
separate items. Output: model/lens_reconciliation.json + paper_model.lens_synthesis
(back-compat projection) + paper_model.lens_conflicts for TENSION/CONTRADICTION notes.
Never majority-votes: conflicts are recorded, not resolved by count.
"""
import argparse,json
from pathlib import Path
from validate_common import *
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out);pm=load_json(root/'model/paper_model.json'); merged=[];seen={}; conflicts=[]
 order=[]
 for lens in LENSES:
  d=load_json(root/'lens'/f'{lens}.json')
  for f in d.get('findings',[]):
   key=(f.get('statement','').strip().lower(),tuple(sorted(f.get('evidence',[]))))
   if key in seen:
    item=merged[seen[key]]
    if lens not in item['supporting_lenses']:item['supporting_lenses'].append(lens)
    item['supporting_findings'].append(f['id'])
    continue
   seen[key]=len(merged);order.append(key)
   merged.append({'id':f['id'],'statement':f['statement'],'status':'AGREEMENT' if False else 'COMPLEMENTARY','supporting_lenses':[lens],'supporting_findings':[f['id']],'evidence':f.get('evidence',[]),'epistemic':f.get('epistemic'),'conflict_note':''})
 # mark multi-lens convergence explicitly
 for item in merged:
  if len(item['supporting_lenses'])>1:item['status']='AGREEMENT'
 # conflict surface: same evidence, different statements -> record TENSION (fail-closed visibility)
 by_ev={}
 for item in merged:
  for e in item['evidence']:by_ev.setdefault(e,[]).append(item['id'])
 for ev,ids in by_ev.items():
  stmts={next(m['statement'] for m in merged if m['id']==i) for i in ids}
  if len(stmts)>1:conflicts.append({'findings':sorted(ids),'resolution':f'TENSION on {ev}: {len(stmts)} distinct statements share evidence; verify against source before freezing.'})
 # back-compat projection into paper_model.lens_synthesis (id/statement/source/from_lens, now WITH full provenance)
 pm['lens_synthesis']=[{'id':m['id'],'statement':m['statement'],'source':m['evidence'],'from_lens':m['supporting_lenses'],'epistemic':m.get('epistemic')} for m in merged]
 pm['lens_conflicts']=conflicts
 (root/'model/paper_model.json').write_text(json.dumps(pm,indent=2,ensure_ascii=False)+'\n')
 try:src_sha=load_json(root/'model/source_map.json').get('pdf_sha256','')
 except Exception:src_sha=''
 try:base_sha=load_json(root/'model/open_reading_manifest.json').get('base_model_sha256','')
 except Exception:base_sha=''
 recon={'schema_version':'1.0','source_sha256':src_sha,'base_model_sha256':base_sha,
        'items':[{'id':m['id'],'statement':m['statement'],'status':m['status'],'supporting_lenses':m['supporting_lenses'],'evidence':m['evidence'],'conflict_note':m.get('conflict_note','')} for m in merged]}
 (root/'model/lens_reconciliation.json').write_text(json.dumps(recon,indent=2,ensure_ascii=False)+'\n')
 # P0 contract artifact (same source data, alternate shape): model/lens_synthesis.json per schemas/lens_synthesis.schema.json
 agreements=[m for m in merged if len(m['supporting_lenses'])>1];unique=[m for m in merged if len(m['supporting_lenses'])==1]
 synthesis={'schema_version':'1.0','paper_model_sha256':None,
  'agreement':[{'id':m['id'],'statement':m['statement'],'evidence':m['evidence'],'lenses':m['supporting_lenses'],'epistemic':m.get('epistemic'),'support_count':len(m['supporting_lenses'])} for m in agreements],
  'unique_findings':[{'id':m['id'],'statement':m['statement'],'evidence':m['evidence'],'lenses':m['supporting_lenses'],'epistemic':m.get('epistemic'),'support_count':1} for m in unique],
  'complementary_findings':[],
  'conflicts':[{'id':f"LC-{i+1:03d}",'evidence':[],'findings':c['findings'],'status':'UNRESOLVED'} for i,c in enumerate(conflicts)],
  'unresolved_conflicts':[{'id':f"LC-{i+1:03d}",'evidence':[],'findings':c['findings'],'status':'UNRESOLVED'} for i,c in enumerate(conflicts)],
  'cross_lens_support':[{'finding_id':m['id'],'lenses':m['supporting_lenses']} for m in agreements]}
 try:
  import hashlib as _hl
  synthesis['paper_model_sha256']=_hl.sha256((root/'model/paper_model.json').read_bytes()).hexdigest()
 except Exception:pass
 (root/'model/lens_synthesis.json').write_text(json.dumps(synthesis,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'status':'OK','merged':len(merged),'conflicts':len(conflicts)}))
if __name__=='__main__':main()
