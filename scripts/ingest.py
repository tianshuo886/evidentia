#!/usr/bin/env python3
"""Create a source-only paper bundle and run conservative source reconstruction."""
import argparse,shutil,subprocess,sys
from pathlib import Path
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pdf',required=True);ap.add_argument('--out',required=True);ap.add_argument('--supplement',action='append',default=[]);a=ap.parse_args();r=Path(a.out);(r/'source').mkdir(parents=True,exist_ok=True);(r/'model').mkdir(exist_ok=True);shutil.copy2(a.pdf,r/'source/paper.pdf')
 for x in a.supplement:shutil.copy2(x,r/'source'/Path(x).name)
 here=Path(__file__).parent
 subprocess.check_call([sys.executable,str(here/'extract_figs.py'),'--pdf',str(r/'source/paper.pdf'),'--out',str(r/'assets/figures'),'--inventory',str(r/'model/figure_inventory.json')])
 subprocess.check_call([sys.executable,str(here/'extract_structure.py'),'--pdf',str(r/'source/paper.pdf'),'--out',str(r/'model/source_map.json'),*sum((['--supplement',x] for x in a.supplement),[])])
 print(f'OK source-only bundle at {r}')
if __name__=='__main__':main()
