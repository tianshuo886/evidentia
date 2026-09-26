#!/usr/bin/env python3
"""Create Open Reading baseline snapshot: model/open_reading_model.json + open_reading_manifest.json.

Phase-A baseline/final separation: lens inputs bind to the frozen baseline hash.
The agent populates model/paper_model.json as the Open Reading draft, then runs
this script to snapshot it as the immutable lens baseline. Later lens merge writes
the reconciled final model back to model/paper_model.json without mutating the baseline.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
LENS_CONTRACT_VERSION='1.0'
PROMPT_VERSION='1.0'
def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out)
 src=r/'model/paper_model.json'
 if not src.exists():raise SystemExit('missing model/paper_model.json (populate the Open Reading draft first)')
 raw=src.read_bytes()
 base_sha=sha_bytes(raw)
 dst=r/'model/open_reading_model.json'
 dst.write_bytes(raw)
 try:
    sys.path.insert(0,str(Path(__file__).parent))
    from validate_common import sha256 as fsha
    source_sha=fsha(r/'source/paper.pdf') if (r/'source/paper.pdf').exists() else ''
 except Exception:
    source_sha=''
 man={'schema_version':'1.0','source_sha256':source_sha,'base_model_sha256':base_sha,
      'lens_contract_version':LENS_CONTRACT_VERSION,'prompt_version':PROMPT_VERSION,
      'artifacts':{'open_reading_model':'model/open_reading_model.json'},
      'created_at':datetime.now(timezone.utc).isoformat()}
 (r/'model/open_reading_manifest.json').write_text(json.dumps(man,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'status':'OK','base_model_sha256':base_sha,'source_sha256':source_sha}))
if __name__=='__main__':main()
