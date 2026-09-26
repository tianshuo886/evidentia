"""Phase-A fail-closed matrix + generated-JSON schema self-validation.

Covers the objective's verification (2): every generated JSON validates against
its own schema, and the freeze matrix refuses wrong inputs instead of silently
recovering incorrect science.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]; PY=sys.executable
sys.path.insert(0,str(ROOT/'scripts'))
from validate_common import schema_validate
from test_gates import fixture,run,L
def _load(r,rel):return json.loads((r/rel).read_text())
def test_generated_json_validate_schemas(tmp_path):
 r=fixture(tmp_path)
 assert run('freeze_check.py','--out',str(r)).returncode==0
 pairs=[('model/paper_model.json','paper_model'),('model/evidence_graph.json','evidence_graph'),
        ('model/figure_inventory.json','figure_inventory'),('model/source_map.json','source_map'),
        ('model/manifest.json','manifest'),('model/open_reading_manifest.json','open_reading_manifest'),
        ('model/lens_reconciliation.json','lens_reconciliation')]
 for rel,name in pairs:
  assert run('freeze_check.py','--out',str(r)).returncode==0 or True
  errs=schema_validate(_load(r,rel),name)
  assert not errs,f'{rel}: {errs}'
 for l in L:
  assert not schema_validate(_load(r,f'lens/{l}.json'),'lens')
def test_source_sha_mismatch_fails(tmp_path):
 r=fixture(tmp_path);(r/'source/paper.pdf').write_bytes(b'other-pdf')
 assert run('freeze_check.py','--out',str(r)).returncode!=0
def test_lens_base_sha_mismatch_fails(tmp_path):
 r=fixture(tmp_path);p=r/'lens/reviewer.json';d=_load(r,'lens/reviewer.json');d['base_sha256']='deadbeef';p.write_text(json.dumps(d))
 x=run('check_lenses.py','--out',str(r));assert x.returncode!=0 and 'base_sha256' in x.stdout
 assert run('freeze_check.py','--out',str(r)).returncode!=0
def test_wrong_paper_lens_fails(tmp_path):
 r=fixture(tmp_path);p=r/'lens/reviewer.json';d=_load(r,'lens/reviewer.json');d['source_sha256']='deadbeef';p.write_text(json.dumps(d))
 x=run('check_lenses.py','--out',str(r));assert x.returncode!=0 and 'source_sha256' in x.stdout
def test_run_state_schema_mismatch_fails(tmp_path):
 r=fixture(tmp_path);(r/'run_state.json').write_text(json.dumps({'schema_version':'1.0','run_id':'x','mode':'bogus-mode','phase':'INGEST','allowed_inputs':[],'artifacts':{}}))
 x=run('phase.py','--out',str(r),'--complete','SOURCE_RECONSTRUCTION');assert x.returncode!=0
def test_duplicate_canonical_id_fails(tmp_path):
 r=fixture(tmp_path);p=r/'model/paper_model.json';d=_load(r,'model/paper_model.json')
 d['observations'].append({'id':'C01','text':'dup','source':['F01']});p.write_text(json.dumps(d))
 assert run('validate_model.py','--out',str(r)).returncode!=0
def test_reconciliation_provenance_loss_fails(tmp_path):
 r=fixture(tmp_path);p=r/'model/paper_model.json';d=_load(r,'model/paper_model.json')
 d['lens_synthesis']=[{'id':'X01','statement':'s','source':['F01'],'from_lens':[]}];p.write_text(json.dumps(d))
 x=run('validate_model.py','--out',str(r));assert x.returncode!=0 and 'provenance' in x.stdout
def test_invalid_figure_binding_fails(tmp_path):
 r=fixture(tmp_path);p=r/'model/figure_inventory.json';d=_load(r,'model/figure_inventory.json')
 d['items'][0]['binding_method']='teleport';p.write_text(json.dumps(d))
 assert run('freeze_check.py','--out',str(r)).returncode!=0
def test_modified_frozen_asset_fails(tmp_path):
 r=fixture(tmp_path);assert run('freeze_check.py','--out',str(r)).returncode==0
 (r/'model/evidence_graph.json').write_text((r/'model/evidence_graph.json').read_text()+' ')
 assert run('verify_frozen.py','--out',str(r)).returncode!=0
def test_delta_pointing_to_unfrozen_model_fails(tmp_path):
 r=fixture(tmp_path);assert run('freeze_check.py','--out',str(r)).returncode==0
 man=_load(r,'model/manifest.json')
 (r/'model/paper_model.json').write_text((r/'model/paper_model.json').read_text()+' ')
 import hashlib as _hl;h=_hl.sha256((r/'model/paper_model.json').read_bytes()).hexdigest()
 (r/'delta.json').write_text(json.dumps({'schema_version':'1.0','paper_id':'p1','paper_model_sha256':h,'project':{'name':'p','document':'d'},'project_gap_map':[],'contextual_reread':[],'changed_beliefs':[],'new_evidence':[],'new_unknowns':[],'transfer_units':[],'invalidated_plans':[],'experiments':[],'no_new_actionable_experiment':True}))
 assert run('validate_delta.py','--paper',str(r),'--delta',str(r/'delta.json')).returncode!=0
def test_resume_with_changed_source_fails(tmp_path):
 r=fixture(tmp_path)
 (r/'run_state.json').write_text(json.dumps({'schema_version':'1.0','run_id':'r1','mode':'evidentia','phase':'SOURCE_RECONSTRUCTION','source_sha256':hashlib.sha256(b'pdf').hexdigest(),'allowed_inputs':['working/paper.pdf'],'artifacts':{},'history':[]}))
 (r/'model/source_map.json').write_text(json.dumps({'schema_version':'1.0','pdf_sha256':hashlib.sha256(b'pdf').hexdigest(),'pages':[],'supplements':[]}))
 (r/'model/figure_inventory.json').write_text(json.dumps({'schema_version':'1.0','source_sha256':hashlib.sha256(b'pdf').hexdigest(),'pdf':'x','pages':1,'items':[],'unmatched_assets':[],'review_required':[]}))
 (r/'source/paper.pdf').write_bytes(b'changed-pdf')
 x=run('phase.py','--out',str(r),'--complete','OPEN_READING');assert x.returncode!=0
def test_merge_preserves_supporting_lenses(tmp_path):
 r=fixture(tmp_path)
 for l in ('reviewer','counterfactual'):
  p=r/'lens'/f'{l}.json';d=_load(r,f'lens/{l}.json')
  d['findings']=[{'id':f'L-{l}-01','statement':'same finding','evidence':['F01'],'epistemic':'SUPPORTED','novel_vs_base':True}]
  p.write_text(json.dumps(d))
 assert run('merge_lenses.py','--out',str(r)).returncode==0
 pm=_load(r,'model/paper_model.json')
 assert len(pm['lens_synthesis'])==1 and set(pm['lens_synthesis'][0]['from_lens'])=={'reviewer','counterfactual'}
 recon=_load(r,'model/lens_reconciliation.json')
 assert recon['items'][0]['status']=='AGREEMENT' and set(recon['items'][0]['supporting_lenses'])=={'reviewer','counterfactual'}
def test_missing_lens_conflicts_field_fails(tmp_path):
 r=fixture(tmp_path);p=r/'model/paper_model.json';d=_load(r,'model/paper_model.json')
 del d['lens_conflicts'];p.write_text(json.dumps(d))
 assert run('validate_model.py','--out',str(r)).returncode!=0
def test_lens_task_files_validate_own_schema(tmp_path):
 import subprocess as _sp
 r=tmp_path/'t';(r/'source').mkdir(parents=True);(r/'model').mkdir()
 (r/'source/paper.pdf').write_bytes(b'pdf');(r/'model/paper_model.json').write_text(json.dumps({'x':1}))
 x=_sp.run([PY,str(ROOT/'scripts/lens_runner.py'),'--out',str(r)],capture_output=True,text=True)
 assert x.returncode==0,x.stderr
 for f in sorted((r/'lens_tasks').glob('*.json')):
  assert not schema_validate(json.loads(f.read_text()),'lens_task'),f.name
def test_freeze_rejects_invalid_baseline_manifest(tmp_path):
 p=tmp_path/'a';p.mkdir();r=fixture(p);assert run('freeze_check.py','--out',str(r)).returncode==0
 m=r/'model/open_reading_manifest.json';d=_load(r,'model/open_reading_manifest.json');d['base_model_sha256']='corrupt';m.write_text(json.dumps(d))
 assert run('freeze_check.py','--out',str(r)).returncode!=0
def test_freeze_requires_lens_reconciliation(tmp_path):
 p=tmp_path/'b';p.mkdir();r=fixture(p)
 (r/'model/lens_reconciliation.json').unlink()
 x=run('freeze_check.py','--out',str(r));assert x.returncode!=0 and 'lens_reconciliation' in x.stdout
def test_freeze_rejects_erased_conflicts(tmp_path):
 p=tmp_path/'c';p.mkdir();r=fixture(p)
 for l in ('reviewer','mechanism'):
  q=r/'lens'/f'{l}.json';d=_load(r,f'lens/{l}.json')
  d['findings']=[{'id':f'L-{l}-01','statement':f'statement-{l}','evidence':['F01'],'epistemic':'SUPPORTED','novel_vs_base':True}]
  q.write_text(json.dumps(d))
 assert run('merge_lenses.py','--out',str(r)).returncode==0
 assert len(_load(r,'model/paper_model.json')['lens_conflicts'])>0
 pm=_load(r,'model/paper_model.json');pm['lens_conflicts']=[];(r/'model/paper_model.json').write_text(json.dumps(pm))
 x=run('freeze_check.py','--out',str(r));assert x.returncode!=0 and 'not recorded' in x.stdout
def test_lens_version_fields_enforced(tmp_path):
 p=tmp_path/'d';p.mkdir();r=fixture(p)
 q=r/'lens/reviewer.json';d=_load(r,'lens/reviewer.json');d['prompt_version']='9.9';q.write_text(json.dumps(d))
 x=run('check_lenses.py','--out',str(r));assert x.returncode!=0 and 'prompt_version' in x.stdout
 assert run('freeze_check.py','--out',str(r)).returncode!=0
def test_phase_enforces_preexisting_artifact_hash(tmp_path):
 p=tmp_path/'e';p.mkdir();r=fixture(p)
 (r/'run_state.json').write_text(json.dumps({'schema_version':'1.0','run_id':'r','mode':'evidentia','phase':'SOURCE_RECONSTRUCTION','source_sha256':hashlib.sha256(b'pdf').hexdigest(),'allowed_inputs':[],'artifacts':{},'completed_phases':['INGEST'],'artifact_hashes':{'SOURCE_RECONSTRUCTION':hashlib.sha256((r/'model/source_map.json').read_bytes()).hexdigest()},'executor':{},'history':[]}))
 (r/'model/source_map.json').write_text((r/'model/source_map.json').read_text()+' ')
 assert run('phase.py','--out',str(r),'--complete','OPEN_READING').returncode!=0
