"""Shared JSON Schema and cross-reference validation helpers."""
from pathlib import Path
import hashlib,json,sys
try:
 from jsonschema import Draft202012Validator
except ImportError:
 Draft202012Validator=None
ROOT=Path(__file__).resolve().parents[1]

def load_json(p):
 with open(p,encoding='utf-8') as f:return json.load(f)
def sha256(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def schema_validate(data,name):
 if Draft202012Validator is None:return ["jsonschema is required (pip install jsonschema)"]
 sp=ROOT/'schemas'/f'{name}.schema.json'; schema=load_json(sp)
 return [f'{e.json_path}: {e.message}' for e in Draft202012Validator(schema).iter_errors(data)]
def all_ids(pm):
 ids={}
 for key in ('questions','claims','observations','experiments','figures','tables','methods','assumptions','limitations','open_questions','anomalies','side_findings','portable_components'):
  for x in pm.get(key,[]) if isinstance(pm.get(key,[]),list) else []:
   if isinstance(x,dict) and x.get('id'):ids[x['id']]=key
 return ids
def refs(pm):
 out=set()
 def walk(v):
  if isinstance(v,list):
   for x in v:walk(x)
  elif isinstance(v,dict):
   for k,x in v.items():
    if k in ('evidence','source','supports','supports_claims','limitations','open_questions','assumptions','component_ids','claim','gap_ids'):
     if isinstance(x,str):out.add(x)
     elif isinstance(x,list):out.update(y for y in x if isinstance(y,str))
    else:walk(x)
 walk(pm);return out


def validate_run_state(path):
    from jsonschema import Draft202012Validator
    d=load_json(path)
    sp=ROOT/'schemas'/'run_state.schema.json'; schema=load_json(sp)
    return [f'{e.json_path}: {e.message}' for e in Draft202012Validator(schema).iter_errors(d)]
