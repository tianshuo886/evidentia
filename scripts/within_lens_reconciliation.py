#!/usr/bin/env python3
"""Within-Lens Reconciliation for Multi-Model Ensemble Mode.

Reconciles multiple independent model runs for a single lens (lens_runs/<lens>/run-*.json)
into a canonical lens output (lens/<lens>.json).
Detects:
- MODEL_SINGLETON
- CROSS_MODEL_CONVERGENCE
- MODEL_CONFLICT
- MODEL_PARTIAL_AGREEMENT
Principle 4 preserved: model count does NOT decide truth; it provides provenance and diagnostic signal.
"""
import argparse, glob, json, os, sys
from pathlib import Path

def reconcile_lens_runs(runs):
    """Reconcile a list of lens run objects into one merged finding set."""
    if not runs:
        return []

    merged = []
    seen = {}
    
    for run_idx, r in enumerate(runs, 1):
        run_id = r.get('run_id', f"run-{run_idx:03d}")
        model_id = r.get('executor', {}).get('model', 'UNKNOWN-MODEL')
        for f in r.get('findings', []):
            key = (f.get('statement', '').strip().lower(), tuple(sorted(f.get('evidence', []))))
            if key in seen:
                item = merged[seen[key]]
                if model_id not in item['models']:
                    item['models'].append(model_id)
                if run_id not in item['run_ids']:
                    item['run_ids'].append(run_id)
                continue
            
            seen[key] = len(merged)
            merged.append({
                'id': f['id'],
                'statement': f['statement'],
                'evidence': f.get('evidence', []),
                'epistemic': f.get('epistemic', 'SUPPORTED'),
                'novel_vs_base': f.get('novel_vs_base', True),
                'models': [model_id],
                'run_ids': [run_id],
                'within_lens_status': 'MODEL_SINGLETON'
            })

    # Evaluate within-lens convergence or conflict
    by_ev = {}
    for item in merged:
        if len(item['models']) > 1:
            item['within_lens_status'] = 'CROSS_MODEL_CONVERGENCE'
        for e in item['evidence']:
            by_ev.setdefault(e, []).append(item)

    for ev, group in by_ev.items():
        if len(group) > 1:
            distinct_stmts = {g['statement'].lower().strip() for g in group}
            if len(distinct_stmts) > 1:
                for g in group:
                    if g['within_lens_status'] != 'CROSS_MODEL_CONVERGENCE':
                        g['within_lens_status'] = 'MODEL_CONFLICT'

    return merged

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs-dir', required=True, help="Directory containing run-*.json for the lens")
    ap.add_argument('--lens', required=True)
    ap.add_argument('--out', required=True, help="Canonical lens output file")
    a = ap.parse_args()

    runs_p = Path(a.runs_dir)
    run_files = sorted(runs_p.glob('run-*.json'))
    if not run_files:
        sys.exit(f"No run-*.json found in {runs_p}")

    runs_data = [json.loads(f.read_text(encoding='utf-8')) for f in run_files]
    merged_findings = reconcile_lens_runs(runs_data)

    base = runs_data[0]
    out_obj = {
        "lens": a.lens,
        "source_sha256": base.get("source_sha256", "UNKNOWN"),
        "base_sha256": base.get("base_sha256", "UNKNOWN"),
        "base_model_sha256": base.get("base_model_sha256", "UNKNOWN"),
        "lens_contract_version": base.get("lens_contract_version", "1.0"),
        "prompt_version": base.get("prompt_version", "1.0"),
        "executor": {
            "mode": "ensemble",
            "models": list({m for f in merged_findings for m in f.get('models', [])}),
            "runs_count": len(run_files)
        },
        "findings": merged_findings,
        "notes": f"Reconciled {len(run_files)} independent model runs across {len(merged_findings)} findings."
    }

    out_p = Path(a.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Reconciled {len(run_files)} runs for {a.lens} -> {len(merged_findings)} canonical findings.")

if __name__ == '__main__':
    main()
