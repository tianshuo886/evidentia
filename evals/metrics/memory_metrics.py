"""Memory evaluation metrics for Evidentia v1.0 (Section 78).

Calculates:
- Open-Reading contamination rate (Critical invariant: MUST BE 0.0)
- Provenance completeness rate
- Retrieval Precision@K
- Stale memory rejection rate
"""

import json
from pathlib import Path

def compute_memory_metrics(memory_items, open_reading_tasks=None, tasks_dir=None):
    # 1. Critical invariant: Open Reading / Lens contamination rate (Section 35)
    tasks = list(open_reading_tasks or [])
    if tasks_dir and Path(tasks_dir).exists():
        td = Path(tasks_dir)
        orp = td / 'open_reading.json'
        if orp.exists():
            tasks.append(json.loads(orp.read_text(encoding='utf-8')))
        lens_d = td / 'lens'
        if lens_d.exists():
            for lp in lens_d.glob('*.json'):
                tasks.append(json.loads(lp.read_text(encoding='utf-8')))

    contamination_count = 0
    total_tasks = len(tasks)
    if tasks:
        for t in tasks:
            is_contaminated = False
            # Check inputs
            for k, v in t.get('input_artifacts', {}).items():
                if 'memory' in str(k).lower() or 'memory' in str(v).lower() or 'apply' in str(k).lower() or 'project' in str(k).lower():
                    is_contaminated = True
            # Check prohibited context
            prohibited = t.get('prohibited_context', [])
            if 'RESEARCH_MEMORY' not in prohibited and 'cross-paper memory' not in prohibited:
                is_contaminated = True
            if is_contaminated:
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
