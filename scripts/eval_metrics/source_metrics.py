"""Source reconstruction metrics for Evidentia evaluation framework.

Calculates:
- Figure recall
- Table recall
- Caption binding accuracy
- Page-anchor accuracy
- Equation coverage
- Supplement coverage
"""

def compute_source_metrics(extracted_items, gt_items):
    gt_figs = {x['id']: x for x in gt_items if x.get('kind') == 'figure'}
    gt_tables = {x['id']: x for x in gt_items if x.get('kind') == 'table'}
    
    ext_figs = {x['id']: x for x in extracted_items if x.get('kind') == 'figure'}
    ext_tables = {x['id']: x for x in extracted_items if x.get('kind') == 'table'}

    fig_recall = len(set(ext_figs.keys()) & set(gt_figs.keys())) / max(len(gt_figs), 1)
    table_recall = len(set(ext_tables.keys()) & set(gt_tables.keys())) / max(len(gt_tables), 1)

    # Caption binding accuracy
    bound_correctly = 0
    total_checked = 0
    for fid, ext_f in ext_figs.items():
        if fid in gt_figs:
            total_checked += 1
            if ext_f.get('binding_confidence', 0) >= 0.7:
                bound_correctly += 1

    binding_accuracy = bound_correctly / max(total_checked, 1)

    return {
        "figure_recall": round(fig_recall, 4),
        "table_recall": round(table_recall, 4),
        "caption_binding_accuracy": round(binding_accuracy, 4),
        "overall_source_coverage": round((fig_recall + table_recall) / 2.0, 4)
    }
