#!/usr/bin/env python3
"""Deterministic phase runner for the complete Evidentia read / apply skill."""
import argparse,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def run(*args):subprocess.check_call([sys.executable,*map(str,args)])
def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 r=sp.add_parser('read');r.add_argument('--pdf',default=None);r.add_argument('--doi',default=None);r.add_argument('--out',default=None);r.add_argument('--supplement',action='append',default=[]);r.add_argument('--intent',choices=['PAPER_READING','PAPER_TECHNICAL_EXTRACTION'],default=None);r.add_argument('--prompt',default=None)
 a=sp.add_parser('apply');a.add_argument('--paper',required=True);a.add_argument('--project',required=True);a.add_argument('--focus')
 n=ap.parse_args()
 if n.cmd=='read':
  extra_args = []
  if n.doi:
   extra_args.extend(['--doi', n.doi])
  if n.pdf:
   extra_args.extend(['--pdf', n.pdf])
  if n.out:
   extra_args.extend(['--out', n.out])
  if n.intent:
   extra_args.extend(['--intent', n.intent])
  if n.prompt:
   extra_args.extend(['--prompt', n.prompt])
  run(HERE/'evidentia.py','run',*extra_args,*sum((['--supplement',s] for s in n.supplement),[]))
 else:
  run(HERE/'init_apply.py','--paper',n.paper,'--project',n.project,*(['--focus',n.focus] if n.focus else []))
  run(HERE/'apply_agent.py','--paper',n.paper,'--project',n.project,*(['--focus',n.focus] if n.focus else []))
  print(f'OK: Completed Contextual Apply for {n.project}.')
if __name__=='__main__':main()
