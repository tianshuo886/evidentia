import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]; PY=sys.executable
L=('author','reviewer','mechanism','builder','anomaly','counterfactual')
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def fixture(tmp_path):
 r=tmp_path; (r/'source').mkdir();(r/'model').mkdir();(r/'lens').mkdir();(r/'assets/figures').mkdir(parents=True);(r/'source/paper.pdf').write_bytes(b'pdf')
 src_sha=sha_bytes(b'pdf')
 (r/'assets/figures/f.png').write_bytes(b'png')
 pm={'schema_version':'1.0','source_sha256':src_sha,'paper_id':'p1','created_at':'2026-01-01T00:00:00Z','generator_version':'test','paper':{'title':'T','authors':['A'],'venue':'V','year':2026,'doi':'','pdf_sha256':src_sha},'natural_structure':['Problem'],'paper_type':'method','questions':[{'id':'Q01','text':'q','page':1}],'claims':[{'id':'C01','statement':'c','page':1,'evidence':['F01'],'epistemic':'SUPPORTED','evidence_scope':'IN_PAPER_EVIDENCE','observation':'o','author_interpretation':'i','reader_assessment':'r'}],'observations':[],'author_interpretations':[],'reader_assessments':[],'experiments':[],'figures':[{'id':'F01','paper_label':'Fig. 1','page':1,'caption_original':'cap','caption_status':'OK','role':'critical','depth':'deep','file':'assets/figures/f.png','bbox':[],'caption_bbox':[],'subfigures':[],'extraction_method':'embedded','confidence':1,'inspection':'inspected','observation':'o','author_interpretation':'i','reader_assessment':'r','supports_claims':['C01'],'limitations':[],'open_questions':[]}],'tables':[],'methods':[],'data':{'sources':[],'scale':'','preprocessing':'','splits':'','leakage_risk':'','metrics':''},'assumptions':[],'limitations':[],'open_questions':[],'anomalies':[],'side_findings':[],'portable_components':[],'argument_chain':['Problem'],'unresolved':[],'coverage':{'supplement':'NOT_APPLICABLE','methods_appendix':'ABSENT','ablations':'ABSENT','negative_results':'ABSENT'},'lens_synthesis':[],'lens_conflicts':[]}
 pm_raw=json.dumps(pm).encode()
 base_sha=sha_bytes(pm_raw)
 (r/'model/paper_model.json').write_bytes(pm_raw)
 (r/'model/open_reading_model.json').write_bytes(pm_raw)
 (r/'model/open_reading_manifest.json').write_text(json.dumps({'schema_version':'1.0','source_sha256':src_sha,'base_model_sha256':base_sha,'lens_contract_version':'1.0','prompt_version':'1.0','artifacts':{'open_reading_model':'model/open_reading_model.json'}}))
 (r/'model/evidence_graph.json').write_text(json.dumps({'schema_version':'1.0','source_sha256':src_sha,'nodes':[{'id':'C01','kind':'claim'},{'id':'F01','kind':'figure'}],'edges':[{'from':'C01','rel':'supported_by','to':'F01'}]}));(r/'model/figure_inventory.json').write_text(json.dumps({'schema_version':'1.0','source_sha256':src_sha,'pdf':str(r/'source/paper.pdf'),'pages':1,'items':[{'id':'F01','kind':'figure','paper_label':'Fig. 1','page':1,'caption_original':'cap','caption_status':'OK','role':'critical','depth':'deep','file':'assets/figures/f.png','bbox':[],'caption_bbox':[],'subfigures':[],'extraction_method':'embedded','confidence':1,'inspection':'ok','binding_method':'embedded','binding_confidence':0.9,'needs_visual_review':False}],'unmatched_assets':[],'review_required':[]}));(r/'model/source_map.json').write_text(json.dumps({'schema_version':'1.0','pdf_sha256':src_sha,'pages':[{'number':1,'sections':[],'equations':[],'mentions':[]}],'supplements':[]}))
 for l in L:(r/'lens'/f'{l}.json').write_text(json.dumps({'lens':l,'base_sha256':base_sha,'base_model_sha256':base_sha,'source_sha256':src_sha,'lens_contract_version':'1.0','prompt_version':'1.0','executor':{'host':'test','tool_profile':'paper-only'},'findings':[],'notes':''}))
 (r/'model/lens_reconciliation.json').write_text(json.dumps({'schema_version':'1.0','source_sha256':src_sha,'base_model_sha256':base_sha,'items':[]}))
 return r

def run(script,*args):return subprocess.run([PY,str(ROOT/'scripts'/script),*args],capture_output=True,text=True)
def test_valid_freeze(tmp_path):
 r=fixture(tmp_path);x=run('freeze_check.py','--out',str(r));assert x.returncode==0,x.stdout+x.stderr;assert json.loads((r/'model/manifest.json').read_text())['status']=='FROZEN';assert run('verify_frozen.py','--out',str(r)).returncode==0
def test_dangling_claim_fails(tmp_path):
 r=fixture(tmp_path);p=r/'model/paper_model.json';d=json.loads(p.read_text());d['claims'][0]['evidence']=['F99'];p.write_text(json.dumps(d));x=run('freeze_check.py','--out',str(r));assert x.returncode!=0;assert 'dangling' in x.stdout
def test_missing_lens_fails(tmp_path):
 r=fixture(tmp_path);(r/'lens/anomaly.json').unlink();assert run('freeze_check.py','--out',str(r)).returncode!=0
def test_hash_tamper_fails(tmp_path):
 r=fixture(tmp_path);assert run('freeze_check.py','--out',str(r)).returncode==0;(r/'model/paper_model.json').write_text((r/'model/paper_model.json').read_text()+' ');assert run('verify_frozen.py','--out',str(r)).returncode!=0
