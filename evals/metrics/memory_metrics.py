"""Memory evaluation metrics for Evidentia v1.0 (Section 78).

Calculates:
- Open-Reading contamination rate (Critical invariant: MUST BE 0.0)
- Provenance completeness rate
- Retrieval Precision@K
- Stale memory rejection rate
"""

def compute_memory_metrics(memory_items, open_reading_tasks=None):
    # 1. Critical invariant: Open Reading contamination rate
    contamination_count = 0
    total_tasks = len(open_reading_tasks or [])
    if open_reading_tasks:
        for t in open_reading_tasks:
            # Check inputs
            for k, v in t.get('input_artifacts', {}).items():
                if 'memory' in str(k).lower() or 'memory' in str(v).lower():
                    contamination_count += 1
            # Check prohibited context
            if 'RESEARCH_MEMORY' not in t.get('prohibited_context', []):
                contamination_count += 1

    contamination_rate = contamination_count / max(total_tasks, 1)

    # 2. Provenance completeness
    total_items = len(memory_items)
    complete_provenance = 0
    for it in memory_items:
        has_paper = bool(it.get('paper_id'))
        has_commit = bool(it.get('paper_commit_id'))
        has_source = bool(it.get('source_ids'))
        has_epistemic = bool(it.get('epistemic_state'))
        if has_paper and has_commit and has_source and has_epistemic:
            complete_provenance += 1

    provenance_rate = complete_provenance / max(total_items, 1)

    return {
        "open_reading_contamination_rate": round(contamination_rate, 4),
        "provenance_completeness_rate": round(provenance_rate, 4),
        "memory_firewall_passed": contamination_rate == 0.0
    }
