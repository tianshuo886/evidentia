#!/usr/bin/env python3
"""Generate structured evidence bundles for Host Agent consumption (Section 12).

Creates a clean, consistent evidence surface:
evidence_bundles/
  page-001.json
  figure-F01.json
  table-T02.json
  equation-EQ-01.json
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json

def generate_evidence_bundles(out_dir):
    root = Path(out_dir)
    sm_p = root / 'model/source_map.json'
    fi_p = root / 'model/figure_inventory.json'
    if not sm_p.exists() or not fi_p.exists():
        sys.exit(f"Error: Missing {sm_p} or {fi_p}")

    bundles_dir = root / 'evidence_bundles'
    bundles_dir.mkdir(parents=True, exist_ok=True)

    sm = load_json(sm_p)
    inv = load_json(fi_p)

    generated = 0

    # 1. Page bundles
    for p in sm.get('pages', []):
        p_num = p.get('number', 1)
        p_bundle = {
            "bundle_type": "PAGE",
            "page_number": p_num,
            "text": p.get('text', ''),
            "sections": p.get('sections', []),
            "mentions": p.get('mentions', []),
            "equations": p.get('equations', [])
        }
        (bundles_dir / f"page-{p_num:03d}.json").write_text(json.dumps(p_bundle, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        generated += 1

    # 2. Figure and Table bundles
    for item in inv.get('items', []):
        iid = item.get('id', 'ITEM')
        kind = item.get('kind', 'figure')
        p_num = item.get('page', 1)
        
        # Find mentions on this page or referencing this item
        matching_mentions = []
        for p in sm.get('pages', []):
            for m in p.get('mentions', []):
                if m.get('target_id') == iid or m.get('label') == item.get('paper_label'):
                    matching_mentions.append({"page": p.get('number'), "mention": m})

        if kind == 'figure':
            f_bundle = {
                "bundle_type": "FIGURE",
                "id": iid,
                "paper_label": item.get('paper_label', iid),
                "page": p_num,
                "asset_path": item.get('file'),
                "caption": item.get('caption_original', ''),
                "bbox": item.get('bbox', []),
                "caption_bbox": item.get('caption_bbox', []),
                "figure_bbox": item.get('figure_bbox', []),
                "subfigures": item.get('subfigures', []),
                "mentions": matching_mentions,
                "binding_method": item.get('binding_method'),
                "binding_confidence": item.get('binding_confidence')
            }
            (bundles_dir / f"figure-{iid}.json").write_text(json.dumps(f_bundle, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            generated += 1
        elif kind == 'table':
            t_bundle = {
                "bundle_type": "TABLE",
                "id": iid,
                "paper_label": item.get('paper_label', iid),
                "page": p_num,
                "asset_path": item.get('file'),
                "caption": item.get('caption_original', ''),
                "structure": item.get('structure'),
                "row_count": item.get('row_count'),
                "col_count": item.get('col_count'),
                "parsed_cells": item.get('parsed_cells'),
                "mentions": matching_mentions,
                "raw_visual_fallback": item.get('raw_visual_fallback')
            }
            (bundles_dir / f"table-{iid}.json").write_text(json.dumps(t_bundle, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            generated += 1

    # 3. Equation bundles
    for p in sm.get('pages', []):
        for eq in p.get('equations', []):
            if isinstance(eq, dict):
                eq_id = eq.get('equation_id', 'EQ')
                eq_bundle = {
                    "bundle_type": "EQUATION",
                    "equation_id": eq_id,
                    "page": p.get('number', 1),
                    "raw_text": eq.get('raw_text', ''),
                    "latex": eq.get('latex'),
                    "section": eq.get('section', 'General'),
                    "surrounding_text": eq.get('surrounding_text', '')
                }
                (bundles_dir / f"equation-{eq_id}.json").write_text(json.dumps(eq_bundle, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
                generated += 1

    print(f"OK: Generated {generated} evidence bundles in {bundles_dir}")
    return generated

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    generate_evidence_bundles(a.out)

if __name__ == '__main__':
    main()
