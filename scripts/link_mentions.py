#!/usr/bin/env python3
"""Bind textual Fig./Table/Eq. mentions in source_map to canonical entity IDs in figure_inventory."""
import argparse, json, re, sys
from pathlib import Path

def resolve_mention(label, kind, inventory_items, equations):
    clean_lbl = label.strip()
    num_m = re.search(r'[S]?\d+[A-Za-z]?', clean_lbl, re.I)
    if not num_m:
        return None
    num_str = num_m.group(0)
    num_int = int(re.sub(r'[^0-9]', '', num_str) or 0)
    
    if kind == 'figure':
        expected_id = f"F{num_int:02d}"
        for item in inventory_items:
            if item.get('id') == expected_id or item.get('paper_label', '').lower() == clean_lbl.lower():
                return item.get('id')
    elif kind == 'table':
        expected_id = f"T{num_int:02d}"
        for item in inventory_items:
            if item.get('id') == expected_id or item.get('paper_label', '').lower() == clean_lbl.lower():
                return item.get('id')
    elif kind == 'equation':
        expected_id = f"EQ-{num_int:02d}"
        for eq in equations:
            if isinstance(eq, dict) and eq.get('equation_id') == expected_id:
                return eq.get('equation_id')
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-map', required=True)
    ap.add_argument('--inventory', required=True)
    ap.add_argument('--out')
    a = ap.parse_args()

    sm_p = Path(a.source_map)
    inv_p = Path(a.inventory)
    out_p = Path(a.out) if a.out else sm_p

    if not sm_p.exists():
        sys.exit(f"Error: {sm_p} not found")
    if not inv_p.exists():
        sys.exit(f"Error: {inv_p} not found")

    sm = json.loads(sm_p.read_text(encoding='utf-8'))
    inv = json.loads(inv_p.read_text(encoding='utf-8'))
    inv_items = inv.get('items', [])

    total_mentions = 0
    bound_mentions = 0

    for page in sm.get('pages', []):
        eqs = page.get('equations', [])
        for mention in page.get('mentions', []):
            total_mentions += 1
            lbl = mention.get('label', '')
            kind = mention.get('kind', 'figure')
            target_id = resolve_mention(lbl, kind, inv_items, eqs)
            if target_id:
                mention['target_id'] = target_id
                mention['bound'] = True
                bound_mentions += 1
            else:
                mention['target_id'] = None
                mention['bound'] = False

    out_p.write_text(json.dumps(sm, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Linked {bound_mentions}/{total_mentions} mentions across {len(sm.get('pages', []))} pages.")

if __name__ == '__main__':
    main()
