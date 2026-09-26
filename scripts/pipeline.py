#!/usr/bin/env python3
"""Deterministic phase runner for the complete Evidentia read / apply skill."""
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
  run(HERE/'evidentia.py','run','--pdf',n.pdf,'--out',n.out,*sum((['--supplement',s] for s in n.supplement),[]))
 else:
  run(HERE/'init_apply.py','--paper',n.paper,'--project',n.project,*(['--focus',n.focus] if n.focus else []))
  run(HERE/'apply_agent.py','--paper',n.paper,'--project',n.project,*(['--focus',n.focus] if n.focus else []))
  print(f'OK: Completed Contextual Apply for {n.project}.')
if __name__=='__main__':main()
