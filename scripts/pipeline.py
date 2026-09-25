#!/usr/bin/env python3
"""Deterministic phase runner for the complete paper-read / paper-apply skill."""
import argparse,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def run(*args):subprocess.check_call([sys.executable,*map(str,args)])
def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 r=sp.add_parser('read');r.add_argument('--pdf',required=True);r.add_argument('--out',required=True);r.add_argument('--supplement',action='append',default=[])
 a=sp.add_parser('apply');a.add_argument('--paper',required=True);a.add_argument('--project',required=True);a.add_argument('--focus')
 n=ap.parse_args()
 if n.cmd=='read':
  run(HERE/'init_run.py','--pdf',n.pdf,'--out',n.out,*sum((['--supplement',s] for s in n.supplement),[]));run(HERE/'ingest.py','--pdf',n.pdf,'--out',n.out,*sum((['--supplement',s] for s in n.supplement),[]));print('Next: populate model/paper_model.json, then run lens_runner.py and the six independent Lens tasks.')
 else:
  run(HERE/'init_apply.py','--paper',n.paper,'--project',n.project,*(['--focus',n.focus] if n.focus else []));print('Next: contextual reread, fill research_delta.json, then validate_delta.py.')
if __name__=='__main__':main()
