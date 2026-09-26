#!/usr/bin/env python3
"""Migrate Evidentia v1.0 paper_model to v2.0 canonical schema without mutating frozen legacy artifacts."""
import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256

def migrate_paper_model(v1_model_path, out_path=None):
    p_in = Path(v1_model_path)
    pm = load_json(p_in)
    
    if pm.get('schema_version') == '2.0':
        print(f"Model at {p_in} is already schema_version 2.0")
        return pm

    # Derive v2 model
    pm_v2 = dict(pm)
    pm_v2['schema_version'] = '2.0'
    pm_v2['derived_from_v1_sha256'] = sha256(p_in)
    pm_v2['migrated_at'] = datetime.now(timezone.utc).isoformat()

    # Populate canonical IDs and origin_type on claims
    for idx, c in enumerate(pm_v2.get('claims', []), 1):
        cid = c.get('id', f'C{idx:02d}')
        c['origin_type'] = c.get('origin_type', 'HOST_AGENT')
        c['observation_ids'] = c.get('observation_ids', [f"O{idx:02d}"])
        c['author_interpretation_ids'] = c.get('author_interpretation_ids', [f"AI{idx:02d}"])
        c['reader_assessment_ids'] = c.get('reader_assessment_ids', [f"RA{idx:02d}"])
        c['evidence_ids'] = c.get('evidence', [])

    out_file = Path(out_path) if out_path else (p_in.parent / 'paper_model_v2.json')
    out_file.write_text(json.dumps(pm_v2, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    
    errs = schema_validate(pm_v2, 'paper_model')
    if errs:
        sys.exit(f"Migrated model failed schema validation:\n{errs}")

    print(f"OK: Migrated paper_model to v2.0 at {out_file}")
    return pm_v2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-model', required=True)
    ap.add_argument('--out')
    a = ap.parse_args()
    migrate_paper_model(a.in_model, a.out)

if __name__ == '__main__':
    main()
