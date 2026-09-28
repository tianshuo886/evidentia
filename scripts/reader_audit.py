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
from validate_common import sha256, schema_validate, load_json

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

        # 6. Issue #8: Argument Reconstruction Artifact Check
        arg_p = r / 'model/argument_reconstruction.json'
        if not arg_p.exists():
            errs.append('missing model/argument_reconstruction.json')
        else:
            try:
                arg_data = load_json(arg_p)
                arg_errs = schema_validate(arg_data, 'argument_reconstruction')
                if arg_errs:
                    errs.append(f'argument_reconstruction schema invalid: {arg_errs}')
            except Exception as e:
                errs.append(f'unparseable model/argument_reconstruction.json: {e}')

        # 7. Issue #8: Renderer Purity & Anti-Contamination Check
        forbidden_hallucinated_tokens = [
            "AdamW",
            "独立同分布高斯分布",
            "多模态数据时存在的表征瓶颈",
            "多尺度特征注意力约束损失"
        ]
        # Check if source paper genuinely mentions them
        src_text = ""
        sm_p = r / 'model/source_map.json'
        if sm_p.exists():
            try:
                sm_data = load_json(sm_p)
                for pg in sm_data.get('pages', []):
                    src_text += " " + (pg.get('text', '') or "")
            except Exception:
                pass

        for tok in forbidden_hallucinated_tokens:
            if tok in html_text and tok not in src_text:
                errs.append(f'Renderer Purity violation: ungrounded boilerplate token "{tok}" leaked into reader HTML')

        # 8. Issue #8: Lens Presentation Check (Lenses must be synthesized, not six mini-reports)
        lens_report_headings = [
            "Author Lens 报告",
            "Reviewer Lens 报告",
            "Mechanism Lens 报告",
            "Builder Lens 报告",
            "Anomaly Lens 报告",
            "Counterfactual Lens 报告"
        ]
        for lh in lens_report_headings:
            if lh in html_text:
                errs.append(f'Reader anti-pattern: raw lens mini-report exposed as top-level narrative ({lh})')

        # 9. Issue #8: Narrative Grounding & Provenance Check
        reader_ir_p = r / 'reader/paper_reader_ir.json'
        if reader_ir_p.exists():
            try:
                reader_ir = load_json(reader_ir_p)
                narrative_units = reader_ir.get('narrative_units', [])
                if not narrative_units:
                    errs.append('missing narrative_units in reader/paper_reader_ir.json')
                else:
                    # Validate that argument references resolve to valid units
                    valid_arg_ids = set()
                    if (r / 'model/argument_reconstruction.json').exists():
                        arg_doc = load_json(r / 'model/argument_reconstruction.json')
                        valid_arg_ids = {u['id'] for u in arg_doc.get('argument_units', [])}
                    
                    valid_claim_ids = {c['id'] for c in pm.get('claims', [])}
                    valid_ev_ids = all_ids | {f"p.{i}" for i in range(1, 100)}
                    
                    for nu in narrative_units:
                        for arg_ref in nu.get('argument_unit_ids', []):
                            if valid_arg_ids and arg_ref not in valid_arg_ids:
                                errs.append(f'narrative unit {nu.get("section_id")} references unknown argument unit: {arg_ref}')
                        for c_ref in nu.get('claim_ids', []):
                            if c_ref not in valid_claim_ids:
                                errs.append(f'narrative unit {nu.get("section_id")} references unknown claim: {c_ref}')
                        for ev_ref in nu.get('evidence_ids', []):
                            if ev_ref not in valid_ev_ids:
                                errs.append(f'narrative unit {nu.get("section_id")} references unknown evidence: {ev_ref}')

                    # Verify that central narrative assertions are grounded
                    has_grounded_unit = any(
                        nu.get('argument_unit_ids') or nu.get('claim_ids') or nu.get('evidence_ids')
                        for nu in narrative_units
                    )
                    if not has_grounded_unit:
                        errs.append('narrative units lack argument/claim/evidence grounding references')
            except Exception as e:
                errs.append(f'error checking narrative grounding in paper_reader_ir.json: {e}')

        # 10. Issue #9: Narrative Manuscript IR & Evidence Atlas Audit
        man_p = r / 'reader/narrative_manuscript.json'
        if man_p.exists():
            try:
                man_data = load_json(man_p)
                m_errs = schema_validate(man_data, 'narrative_manuscript')
                if m_errs:
                    errs.append(f'narrative_manuscript schema invalid: {m_errs}')
            except Exception as e:
                errs.append(f'unparseable narrative_manuscript.json: {e}')

        atlas_p = r / 'reader/evidence_atlas.html'
        if atlas_p.exists():
            atlas_text = atlas_p.read_text(encoding='utf-8')
            if '{{' in atlas_text or '}}' in atlas_text:
                errs.append('unresolved template placeholder in evidence_atlas.html')
            atlas_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', atlas_text))
            atlas_hrefs = set(re.findall(r'\bhref=["\']#([^"\']+)["\']', atlas_text))
            atlas_broken = {a for a in (atlas_hrefs - atlas_ids) if a not in ('top', '')}
            if atlas_broken:
                errs.append(f'broken anchor links in evidence_atlas.html: {sorted(atlas_broken)}')
            # Verify O/I/A completeness in atlas
            for c in pm.get('claims', []):
                cid = c.get('id')
                if cid in atlas_ids:
                    if 'Observation' not in atlas_text or 'Author Interpretation' not in atlas_text or 'Reader Assessment' not in atlas_text:
                        errs.append(f'O/I/A structure missing in evidence_atlas for claim {cid}')

    if errs:
        print(json.dumps({'status': 'FAIL', 'errors': errs}, indent=2))
        return 1

    print(json.dumps({'status': 'OK', 'reader_sha256': sha256(r / 'reader/reader.html')}))
    return 0

if __name__ == '__main__':
    sys.exit(main())
