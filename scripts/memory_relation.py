#!/usr/bin/env python3
"""Cross-Paper Memory Relation Manager for Evidentia v1.1.

Implements Sections 29 & 30:
- Explicit typed cross-paper relations:
  SUPPORTS, CONTRADICTS, EXTENDS, REPLICATES, FAILS_TO_REPLICATE,
  USES_SIMILAR_MECHANISM, USES_DIFFERENT_MECHANISM, SAME_FAILURE_MODE,
  DIFFERENT_DATA_REGIME, TRANSFER_SUCCESS, TRANSFER_FAILURE,
  RESOLVES_UNKNOWN, CREATES_NEW_UNKNOWN
- Provenance-linked, append-only JSON objects in objects/relations/
- SQLite indexing in memory.sqlite
"""
import argparse, hashlib, json, os, sqlite3, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate
import memory_manager

VALID_RELATION_TYPES = [
    "AGREES_WITH", "SUPPORTS", "CONTRADICTS", "EXTENDS", "REPLICATES",
    "FAILS_TO_REPLICATE", "USES_SIMILAR_MECHANISM", "SAME_MECHANISM",
    "USES_DIFFERENT_MECHANISM", "SAME_FAILURE_MODE", "DIFFERENT_DATA_REGIME",
    "SAME_DATA_REGIME", "TRANSFER_SUCCESS", "TRANSFER_FAILURE",
    "TRANSFER_ANALOG", "ALTERNATIVE_TO", "RESOLVES_UNKNOWN", "CREATES_NEW_UNKNOWN"
]

def add_relation(source_id, target_id, rel_type, reason, source_paper=None, target_paper=None, evidence_ids=None, custom_root=None):
    if rel_type not in VALID_RELATION_TYPES:
        sys.exit(f"Error: Invalid relation type '{rel_type}'. Allowed: {', '.join(VALID_RELATION_TYPES)}")

    root = memory_manager.get_memory_root(custom_root)
    created_at = datetime.now(timezone.utc).isoformat()
    raw = json.dumps({
        "src": source_id,
        "tgt": target_id,
        "type": rel_type,
        "time": created_at
    }).encode('utf-8')
    rel_id = f"REL-{hashlib.sha256(raw).hexdigest()[:12]}"

    relation_obj = {
        "relation_id": rel_id,
        "relation_type": rel_type,
        "source_memory_id": source_id,
        "target_memory_id": target_id,
        "source_paper_id": source_paper,
        "target_paper_id": target_paper,
        "reasoning": reason,
        "evidence_ids": evidence_ids or [],
        "created_at": created_at
    }

    # Validate against schema
    errs = schema_validate(relation_obj, 'memory_relation')
    if errs:
        sys.exit(f"Relation failed schema validation:\n{errs}")

    rel_file = root / 'objects/relations' / f"{rel_id}.json"
    rel_file.write_text(json.dumps(relation_obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()
    cur.execute('''
    INSERT OR REPLACE INTO memory_relations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        rel_id, rel_type, source_id, target_id,
        source_paper, target_paper, reason,
        json.dumps(evidence_ids or []), created_at
    ))
    conn.commit()
    conn.close()

    print(f"OK: Added cross-paper relation {rel_id}: {source_id} --[{rel_type}]--> {target_id}")
    return rel_id

def list_relations(custom_root=None):
    root = memory_manager.get_memory_root(custom_root)
    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()
    cur.execute('SELECT relation_id, relation_type, source_memory_id, target_memory_id, reasoning, created_at FROM memory_relations')
    rows = cur.fetchall()
    conn.close()
    relations = []
    for r in rows:
        relations.append({
            "relation_id": r[0],
            "relation_type": r[1],
            "source_memory_id": r[2],
            "target_memory_id": r[3],
            "reasoning": r[4],
            "created_at": r[5]
        })
    return relations

def main():
    ap = argparse.ArgumentParser(description="Evidentia Memory Relation Manager")
    sp = ap.add_subparsers(dest='cmd', required=True)

    p_add = sp.add_parser('add')
    p_add.add_argument('--source', required=True, help="Source memory ID")
    p_add.add_argument('--target', required=True, help="Target memory ID")
    p_add.add_argument('--type', required=True, choices=VALID_RELATION_TYPES)
    p_add.add_argument('--reason', required=True)
    p_add.add_argument('--source-paper')
    p_add.add_argument('--target-paper')
    p_add.add_argument('--evidence', nargs='*', default=[])
    p_add.add_argument('--memory-root')

    p_list = sp.add_parser('list')
    p_list.add_argument('--memory-root')

    args = ap.parse_args()
    if args.cmd == 'add':
        add_relation(
            args.source,
            args.target,
            args.type,
            args.reason,
            source_paper=args.source_paper,
            target_paper=args.target_paper,
            evidence_ids=args.evidence,
            custom_root=args.memory_root
        )
    elif args.cmd == 'list':
        rels = list_relations(custom_root=args.memory_root)
        print(json.dumps(rels, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
