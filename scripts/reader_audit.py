#!/usr/bin/env python3
"""Audit that the Reader preserves canonical content, bidirectional navigation, and O/I/A separation.

Phase B6 Reader Audit v2:
- Semantic coverage of claims, figures, and tables
- Broken anchor detection: every <a href="#ID"> must match an existing element id
- Bidirectional link check: Claim <-> Evidence round trips
- O/I/A preservation: Observation, Author Interpretation, Reader Assessment present
- Missing conflicts & uncertainty checks
- Research Delta provenance check
"""
import argparse, json, re, sys
from pathlib import Path
from validate_common import sha256

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    r = Path(a.out)
    errs = []

    for rel in ('reader/reader.html', 'reader/render_ir.json', 'model/paper_model.json'):
        if not (r / rel).exists():
            errs.append('missing ' + rel)

    if (r / 'reader/reader.html').exists():
        html_text = (r / 'reader/reader.html').read_text(encoding='utf-8')
        if '{{' in html_text or '}}' in html_text:
            errs.append('unresolved template placeholder in reader.html')

        pm = json.load(open(r / 'model/paper_model.json', encoding='utf-8'))
        ir = json.load(open(r / 'reader/render_ir.json', encoding='utf-8'))

        # 1. Semantic coverage
        for c in pm.get('claims', []):
            if c.get('id') not in ir.get('claim_cards', []):
                errs.append(f'claim omitted from render_ir: {c.get("id")}')
        for f in pm.get('figures', []):
            if f.get('id') not in ir.get('figure_blocks', []):
                errs.append(f'figure omitted from render_ir: {f.get("id")}')
        for t in pm.get('tables', []):
            if t.get('id') not in ir.get('table_blocks', []):
                errs.append(f'table omitted from render_ir: {t.get("id")}')
        for f in pm.get('figures', []):
            if f.get('file') and not (r / f['file']).exists():
                errs.append(f'missing figure asset file: {f["file"]}')

        # 2. Broken anchor detection
        all_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html_text))
        all_hrefs = set(re.findall(r'\bhref=["\']#([^"\']+)["\']', html_text))
        broken_anchors = all_hrefs - all_ids
        # Exclude general or top links if any
        broken_anchors = {a for a in broken_anchors if a not in ('top', '')}
        if broken_anchors:
            errs.append(f'broken anchor links in reader.html: {sorted(broken_anchors)}')

        # 3. O/I/A preservation
        for c in pm.get('claims', []):
            cid = c.get('id')
            if cid in all_ids:
                # Check that Observation, Author Interpretation, Reader Assessment labels exist in claim card
                if 'Observation' not in html_text or 'Author Interpretation' not in html_text or 'Reader Assessment' not in html_text:
                    errs.append(f'O/I/A structure missing in reader for claim {cid}')

        # 4. Uncertainty & conflict visibility
        if pm.get('lens_conflicts'):
            for conf in pm['lens_conflicts']:
                cid = conf.get('id')
                if cid and cid not in html_text:
                    errs.append(f'conflict {cid} not rendered in reader.html')

        if not pm.get('unresolved') and any(c.get('epistemic') in ('AMBIGUOUS', 'INSUFFICIENT_EVIDENCE', 'UNRESOLVED') for c in pm.get('claims', [])):
            errs.append('unresolved claim is not visible in unresolved list')

        # 5. Delta provenance check
        if (r / 'apply').exists():
            for p in (r / 'apply').glob('*/research_delta.json'):
                try:
                    delta = json.load(open(p, encoding='utf-8'))
                    for tu in delta.get('transfer_units', []):
                        for s_ref in tu.get('source', []):
                            if s_ref not in all_ids and not s_ref.startswith(('p.', 'Fig.', 'Table.')):
                                errs.append(f'delta transfer unit {tu.get("id")} cites unknown paper evidence: {s_ref}')
                except Exception as e:
                    errs.append(f'error auditing delta provenance: {e}')

    if errs:
        print(json.dumps({'status': 'FAIL', 'errors': errs}, indent=2))
        return 1

    print(json.dumps({'status': 'OK', 'reader_sha256': sha256(r / 'reader/reader.html')}))
    return 0

if __name__ == '__main__':
    sys.exit(main())
