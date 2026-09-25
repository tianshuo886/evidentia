#!/usr/bin/env python3
import argparse,json,hashlib
from pathlib import Path
LENSES=('author','reviewer','mechanism','builder','anomaly','counterfactual')
PROMPTS={'author':"Reconstruct the authors' narrative: problem, hypothesis, design, evidence, conclusion. Mark rhetorical jumps.",'reviewer':'Audit controls, confounds, evaluation, external validation, causal overclaim, ablations and weakest evidence.','mechanism':'Separate correlation, mechanism and causality. State the minimal A→B→C chain and what would falsify it.','builder':'Extract detachable methods, losses, protocols, diagnostics, preprocessing and evaluation components. No project relevance.','anomaly':'Find real downplayed anomalies, subgroup flips, failures and negative results. Empty is valid; never invent one.','counterfactual':'Give serious alternative explanations if the author interpretation is wrong and reuse only cited evidence.'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=Path(a.out);pdf=r/'source/paper.pdf';base=r/'model/paper_model.json';(r/'lens_tasks').mkdir(exist_ok=True)
 if not pdf.exists() or not base.exists():raise SystemExit('source/paper.pdf and model/paper_model.json are required')
 for lens in LENSES:
  task={'lens':lens,'source_pdf':str(pdf),'base_model':str(base),'source_sha256':sha(pdf),'base_sha256':sha(base),'instructions':PROMPTS[lens],'output':str(r/f'lens/{lens}.json')};(r/'lens_tasks'/f'{lens}.json').write_text(json.dumps(task,indent=2,ensure_ascii=False)+'\n')
 print('created 6 independent lens task packets')
if __name__=='__main__':main()
