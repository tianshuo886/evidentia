#!/usr/bin/env python3
"""Deterministic phase runner for paper-read and paper-apply.

The model-producing steps remain explicit inputs: this runner never invents paper facts.
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(*args): subprocess.check_call([sys.executable,*map(str,args)])
def paper_read(pdf,out,supplements):
 out=Path(out); (out/'working').mkdir(parents=True,exist_ok=True)
 # Source-only workspace: only paper and supplied supplements are copied.
 shutil.copy2(pdf,out/'working/paper.pdf')
 for s in supplements: shutil.copy2(s,out/'working'/Path(s).name)
 run(HERE/'ingest.py','--pdf',pdf,'--out',out,*sum((['--supplement',s] for s in supplements),[]))
 print('NEXT: populate model/paper_model.json and six lens/*.json from the source-only bundle.')
def paper_apply(paper,project,delta):
 paper=Path(paper); manifest=paper/'model/manifest.json'
 if not manifest.exists(): raise SystemExit('REFUSED: paper is not frozen')
 run(HERE/'verify_frozen.py','--out',paper)
 # Apply input is copied into an isolated contextual workspace; paper model stays read-only.
 target=paper/'apply'/Path(project).stem; target.mkdir(parents=True,exist_ok=True)
 shutil.copy2(project,target/'project_document')
 print(f'NEXT: populate {target}/research_delta.json from contextual reread, then validate_delta.py')
 if delta: run(HERE/'validate_delta.py','--paper',paper,'--delta',delta)
def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 r=sp.add_parser('read');r.add_argument('--pdf',required=True);r.add_argument('--out',required=True);r.add_argument('--supplement',action='append',default=[])
 a=sp.add_parser('apply');a.add_argument('--paper',required=True);a.add_argument('--project',required=True);a.add_argument('--delta');
 ns=ap.parse_args(); paper_read(ns.pdf,ns.out,ns.supplement) if ns.cmd=='read' else paper_apply(ns.paper,ns.project,ns.delta)
if __name__=='__main__':main()
