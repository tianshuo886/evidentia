#!/usr/bin/env python3
"""Search the stable local literature index without requiring a database."""
import argparse,json,re,sys
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--query',required=True);a=ap.parse_args();d=json.load(open(a.index));q=a.query.lower();rows=[]
 for p in d.get('papers',[]):
  hay=json.dumps(p,ensure_ascii=False).lower()
  if q in hay:rows.append(p)
 print(json.dumps({'query':a.query,'count':len(rows),'papers':rows},ensure_ascii=False,indent=2));return 0
if __name__=='__main__':sys.exit(main())
