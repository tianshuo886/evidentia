#!/usr/bin/env python3
import argparse,json,shutil,uuid
from pathlib import Path
from datetime import datetime,timezone
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pdf',required=True);ap.add_argument('--out',required=True);ap.add_argument('--supplement',action='append',default=[]);a=ap.parse_args();r=Path(a.out);(r/'working').mkdir(parents=True,exist_ok=True);(r/'source').mkdir(exist_ok=True);shutil.copy2(a.pdf,r/'working/paper.pdf');shutil.copy2(a.pdf,r/'source/paper.pdf')
 for s in a.supplement:shutil.copy2(s,r/'working'/Path(s).name);shutil.copy2(s,r/'source'/Path(s).name)
 state={'schema_version':'1.0','run_id':str(uuid.uuid4()),'mode':'paper-read','phase':'INGEST','allowed_inputs':['working/paper.pdf']+[f'working/{Path(s).name}' for s in a.supplement],'artifacts':{},'history':[{'phase':'INGEST','status':'started','at':datetime.now(timezone.utc).isoformat()}]};(r/'run_state.json').write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n');print(f'initialized {r}/run_state.json')
if __name__=='__main__':main()
