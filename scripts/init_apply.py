#!/usr/bin/env python3
"""Open a contextual apply workspace only after frozen-model verification."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from validate_common import sha256
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--paper',required=True);ap.add_argument('--project',required=True);ap.add_argument('--focus');a=ap.parse_args();r=Path(a.paper);subprocess.check_call([sys.executable,str(Path(__file__).with_name('verify_frozen.py')),'--out',str(r)]);run=r/'apply'/Path(a.project).stem;run.mkdir(parents=True,exist_ok=True);shutil.copy2(a.project,run/'project_document');pm=r/'model/paper_model.json';gaps={'schema_version':'1.0','project_id':Path(a.project).stem,'document':str(run/'project_document'),'focus':a.focus,'gaps':[]};(run/'project_context.json').write_text(json.dumps(gaps,indent=2,ensure_ascii=False)+'\n');delta={'schema_version':'1.0','paper_id':json.load(open(pm)).get('paper_id',''),'paper_model_sha256':sha256(pm),'project':{'name':Path(a.project).stem,'document':str(run/'project_document')},'project_gap_map':[],'contextual_reread':[],'changed_beliefs':[],'new_evidence':[],'new_unknowns':[],'transfer_units':[],'invalidated_plans':[],'experiments':[],'no_new_actionable_experiment':False};(run/'research_delta.json').write_text(json.dumps(delta,indent=2,ensure_ascii=False)+'\n');print(run)
if __name__=='__main__':main()
