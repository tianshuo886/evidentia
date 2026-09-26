#!/usr/bin/env python3
"""Frozen Research Memory Subsystem for Evidentia v1.0.

Provides:
- Immutable canonical JSON object storage under objects/
- Rebuildable SQLite index + FTS5 search
- Paper Memory Commit (only for verified FROZEN papers)
- Project Memory Commit (for validated Research Deltas)
- Experiment Outcome Memory
- Cross-Paper Evidence Relations
- Search, inspect, verify, rebuild-index, export, import
- Open Reading Memory Firewall enforcement
"""
import argparse, hashlib, json, os, re, shutil, sqlite3, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256

DEFAULT_MEMORY_ROOT = Path(os.environ.get("EVIDENTIA_MEMORY_ROOT", Path.home() / ".evidentia" / "memory"))

def get_memory_root(custom_root=None):
    root = Path(custom_root) if custom_root else DEFAULT_MEMORY_ROOT
    root.mkdir(parents=True, exist_ok=True)
    for sub in ('objects/paper_commits', 'objects/project_commits', 'objects/relations', 'objects/outcomes', 'snapshots', 'exports'):
        (root / sub).mkdir(parents=True, exist_ok=True)
    manifest_p = root / 'memory_manifest.json'
    if not manifest_p.exists():
        manifest_p.write_text(json.dumps({
            "schema_version": "1.0",
            "initialized_at": datetime.now(timezone.utc).isoformat(),
            "commits": []
        }, indent=2) + '\n', encoding='utf-8')
    init_db(root)
    return root

def init_db(root):
    db_path = root / 'memory.sqlite'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS memory_commits (
        commit_id TEXT PRIMARY KEY,
        commit_type TEXT NOT NULL,
        paper_id TEXT NOT NULL,
        project_id TEXT,
        paper_model_sha256 TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        committed_at TEXT NOT NULL,
        payload_path TEXT NOT NULL
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS memory_items (
        memory_id TEXT PRIMARY KEY,
        memory_type TEXT NOT NULL,
        text TEXT NOT NULL,
        paper_id TEXT NOT NULL,
        paper_commit_id TEXT NOT NULL,
        object_id TEXT NOT NULL,
        source_ids_json TEXT NOT NULL,
        epistemic_state TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        payload_path TEXT NOT NULL,
        FOREIGN KEY(paper_commit_id) REFERENCES memory_commits(commit_id)
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS memory_relations (
        relation_id TEXT PRIMARY KEY,
        relation_type TEXT NOT NULL,
        source_memory_id TEXT NOT NULL,
        target_memory_id TEXT NOT NULL,
        source_paper_id TEXT,
        target_paper_id TEXT,
        reasoning TEXT NOT NULL,
        evidence_ids_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS experiment_outcomes (
        outcome_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        experiment_id TEXT NOT NULL,
        verdict TEXT NOT NULL,
        findings TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        payload_path TEXT NOT NULL
    )''')
    # FTS5 full-text search table
    cur.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_items USING fts5(
        memory_id,
        text,
        paper_id,
        memory_type
    )''')
    conn.commit()
    conn.close()

def commit_paper(paper_dir, custom_root=None):
    p_dir = Path(paper_dir)
    root = get_memory_root(custom_root)

    # 1. Gate: Verify paper is FROZEN
    res = subprocess.run([sys.executable, str(HERE / 'verify_frozen.py'), '--out', str(p_dir)], capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"REFUSED: Cannot commit unfrozen paper model to memory.\n{res.stderr or res.stdout}")

    manifest = load_json(p_dir / 'model/manifest.json')
    pm = load_json(p_dir / 'model/paper_model.json')
    rec_p = p_dir / 'model/lens_reconciliation.json'
    rec = load_json(rec_p) if rec_p.exists() else {}

    paper_id = pm.get('paper_id', 'unknown-paper')
    paper_model_sha = manifest.get('hashes', {}).get('model/paper_model.json', '')
    source_sha = manifest.get('source_sha256', '')

    committed_at = datetime.now(timezone.utc).isoformat()
    raw_payload = json.dumps({"paper_id": paper_id, "pm_sha": paper_model_sha, "time": committed_at}).encode('utf-8')
    commit_id = f"PC-{hashlib.sha256(raw_payload).hexdigest()[:12]}"

    commit_dir = root / 'objects/paper_commits' / commit_id
    commit_dir.mkdir(parents=True, exist_ok=True)

    items = []

    # Paper metadata item
    p_meta = pm.get('paper', {})
    items.append({
        "memory_id": f"MEM-{commit_id}-PAPER",
        "memory_type": "PAPER",
        "text": f"{p_meta.get('title', 'Untitled')} ({p_meta.get('year', '')}) by {', '.join(p_meta.get('authors', []))}. Venue: {p_meta.get('venue', '')}",
        "paper_id": paper_id,
        "paper_commit_id": commit_id,
        "object_id": paper_id,
        "source_ids": ["source/paper.pdf"],
        "epistemic_state": "VERIFIED",
        "verification_ids": [],
        "created_at": committed_at,
        "status": "ACTIVE"
    })

    # Claims
    for c in pm.get('claims', []):
        cid = c.get('id', 'C01')
        items.append({
            "memory_id": f"MEM-{commit_id}-{cid}",
            "memory_type": "CLAIM",
            "text": c.get('statement', ''),
            "paper_id": paper_id,
            "paper_commit_id": commit_id,
            "object_id": cid,
            "source_ids": c.get('evidence', []),
            "epistemic_state": c.get('epistemic', 'SUPPORTED'),
            "verification_ids": [c.get('verifier_status')] if c.get('verifier_status') else [],
            "created_at": committed_at,
            "status": "ACTIVE"
        })

    # Portable components
    for comp in pm.get('portable_components', []):
        comp_id = comp.get('id', 'PC01')
        items.append({
            "memory_id": f"MEM-{commit_id}-{comp_id}",
            "memory_type": "PORTABLE_COMPONENT",
            "text": f"Portable Component: {comp.get('name', '')} (IO: {comp.get('io', '')})",
            "paper_id": paper_id,
            "paper_commit_id": commit_id,
            "object_id": comp_id,
            "source_ids": comp.get('source', []),
            "epistemic_state": "SUPPORTED",
            "verification_ids": [],
            "created_at": committed_at,
            "status": "ACTIVE"
        })

    # Lens Findings / Reconciled Findings
    for rec_item in rec.get('items', []):
        rf_id = rec_item.get('id', 'RF01')
        items.append({
            "memory_id": f"MEM-{commit_id}-{rf_id}",
            "memory_type": "FINDING",
            "text": rec_item.get('statement', ''),
            "paper_id": paper_id,
            "paper_commit_id": commit_id,
            "object_id": rf_id,
            "source_ids": rec_item.get('evidence', []),
            "epistemic_state": rec_item.get('epistemic_state', 'SUPPORTED'),
            "verification_ids": [rec_item.get('verifier_status')] if rec_item.get('verifier_status') else [],
            "created_at": committed_at,
            "status": "ACTIVE"
        })

    # Save canonical JSON objects to objects/
    commit_payload = {
        "commit_id": commit_id,
        "commit_type": "PAPER_COMMIT",
        "paper_id": paper_id,
        "project_id": None,
        "paper_model_sha256": paper_model_sha,
        "source_sha256": source_sha,
        "committed_at": committed_at,
        "item_count": len(items),
        "manifest_hashes": manifest.get('hashes', {})
    }
    commit_file = commit_dir / 'commit.json'
    commit_file.write_text(json.dumps(commit_payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    items_file = commit_dir / 'items.json'
    items_file.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Index in SQLite
    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()
    cur.execute('''
    INSERT OR REPLACE INTO memory_commits VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (commit_id, "PAPER_COMMIT", paper_id, None, paper_model_sha, source_sha, committed_at, str(commit_file)))

    for it in items:
        cur.execute('''
        INSERT OR REPLACE INTO memory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            it['memory_id'], it['memory_type'], it['text'], it['paper_id'],
            it['paper_commit_id'], it['object_id'], json.dumps(it['source_ids']),
            it['epistemic_state'], it['created_at'], it['status'], str(items_file)
        ))
        cur.execute('''
        INSERT INTO fts_items(memory_id, text, paper_id, memory_type) VALUES (?, ?, ?, ?)
        ''', (it['memory_id'], it['text'], it['paper_id'], it['memory_type']))

    conn.commit()
    conn.close()

    # Update manifest
    m_path = root / 'memory_manifest.json'
    m_data = load_json(m_path)
    m_data['commits'].append(commit_payload)
    m_path.write_text(json.dumps(m_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print(f"OK: Committed paper {paper_id} to Frozen Research Memory (commit_id: {commit_id}, items: {len(items)})")
    return commit_id

def commit_project(paper_dir, project_id, custom_root=None):
    p_dir = Path(paper_dir)
    root = get_memory_root(custom_root)
    delta_p = p_dir / 'apply' / project_id / 'research_delta.json'
    if not delta_p.exists():
        sys.exit(f"REFUSED: Missing {delta_p}")

    delta = load_json(delta_p)
    committed_at = datetime.now(timezone.utc).isoformat()
    raw_payload = json.dumps({"project": project_id, "time": committed_at}).encode('utf-8')
    commit_id = f"PRJ-{hashlib.sha256(raw_payload).hexdigest()[:12]}"

    commit_dir = root / 'objects/project_commits' / commit_id
    commit_dir.mkdir(parents=True, exist_ok=True)

    items = []
    # Changed beliefs
    for cb in delta.get('changed_beliefs', []):
        items.append({
            "memory_id": f"MEM-{commit_id}-CB-{len(items)+1:02d}",
            "memory_type": "PROJECT_DECISION",
            "text": f"Changed Belief: Before: {cb.get('before')} -> After: {cb.get('after')} (Reason: {cb.get('reason')})",
            "paper_id": delta.get('paper_id', 'unknown'),
            "paper_commit_id": commit_id,
            "object_id": f"CB-{len(items)+1:02d}",
            "source_ids": cb.get('source', []),
            "epistemic_state": "SUPPORTED",
            "verification_ids": [],
            "created_at": committed_at,
            "status": "ACTIVE"
        })

    # Transfer Units
    for tu in delta.get('transfer_units', []):
        items.append({
            "memory_id": f"MEM-{commit_id}-{tu.get('id', 'TU01')}",
            "memory_type": "TRANSFER",
            "text": f"Transfer Unit {tu.get('id')}: Verdict {tu.get('verdict')} on component {', '.join(tu.get('component_ids', []))} — {tu.get('reason')}",
            "paper_id": delta.get('paper_id', 'unknown'),
            "paper_commit_id": commit_id,
            "object_id": tu.get('id', 'TU01'),
            "source_ids": tu.get('source', []),
            "epistemic_state": "SUPPORTED",
            "verification_ids": [],
            "created_at": committed_at,
            "status": "ACTIVE"
        })

    payload = {
        "project_id": project_id,
        "paper_id": delta.get('paper_id', 'unknown'),
        "committed_at": committed_at,
        "gaps": delta.get('project_gap_map', []),
        "changed_beliefs": delta.get('changed_beliefs', []),
        "transfer_decisions": delta.get('transfer_units', []),
        "experiment_proposals": delta.get('experiments', [])
    }
    (commit_dir / 'project_memory.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()
    cur.execute('''
    INSERT OR REPLACE INTO memory_commits VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (commit_id, "PROJECT_COMMIT", delta.get('paper_id', 'unknown'), project_id, delta.get('paper_model_sha256', ''), delta.get('source_sha256', ''), committed_at, str(commit_dir / 'project_memory.json')))

    for it in items:
        cur.execute('''
        INSERT OR REPLACE INTO memory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            it['memory_id'], it['memory_type'], it['text'], it['paper_id'],
            it['paper_commit_id'], it['object_id'], json.dumps(it['source_ids']),
            it['epistemic_state'], it['created_at'], it['status'], str(commit_dir / 'project_memory.json')
        ))
        cur.execute('''
        INSERT INTO fts_items(memory_id, text, paper_id, memory_type) VALUES (?, ?, ?, ?)
        ''', (it['memory_id'], it['text'], it['paper_id'], it['memory_type']))

    conn.commit()
    conn.close()

    print(f"OK: Committed project {project_id} to Frozen Research Memory (commit_id: {commit_id}, items: {len(items)})")
    return commit_id

def record_outcome(project_id, experiment_id, verdict, findings, conditions=None, custom_root=None):
    root = get_memory_root(custom_root)
    recorded_at = datetime.now(timezone.utc).isoformat()
    raw = json.dumps({"project": project_id, "exp": experiment_id, "time": recorded_at}).encode('utf-8')
    outcome_id = f"OUT-{hashlib.sha256(raw).hexdigest()[:12]}"

    out_obj = {
        "outcome_id": outcome_id,
        "project_id": project_id,
        "experiment_id": experiment_id,
        "verdict": verdict,
        "metrics": {},
        "conditions": conditions or "Standard execution",
        "findings": findings,
        "decision_consequence": f"Experiment outcome recorded: {verdict}",
        "recorded_at": recorded_at
    }
    out_file = root / 'objects/outcomes' / f"{outcome_id}.json"
    out_file.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()
    cur.execute('''
    INSERT OR REPLACE INTO experiment_outcomes VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (outcome_id, project_id, experiment_id, verdict, findings, recorded_at, str(out_file)))
    conn.commit()
    conn.close()

    print(f"OK: Recorded experiment outcome {outcome_id} for {project_id}:{experiment_id} ({verdict})")
    return outcome_id

def search_memory(query, memory_type=None, limit=10, custom_root=None):
    root = get_memory_root(custom_root)
    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()

    # Clean query for FTS5 syntax
    clean_q = re.sub(r'[^a-zA-Z0-9_\s]', ' ', query).strip()
    if not clean_q:
        clean_q = query

    if memory_type:
        cur.execute('''
        SELECT m.memory_id, m.memory_type, m.text, m.paper_id, m.object_id, m.source_ids_json, m.epistemic_state, c.paper_model_sha256, c.source_sha256
        FROM fts_items f
        JOIN memory_items m ON f.memory_id = m.memory_id
        JOIN memory_commits c ON m.paper_commit_id = c.commit_id
        WHERE fts_items MATCH ? AND m.memory_type = ?
        LIMIT ?
        ''', (clean_q, memory_type, limit))
    else:
        cur.execute('''
        SELECT m.memory_id, m.memory_type, m.text, m.paper_id, m.object_id, m.source_ids_json, m.epistemic_state, c.paper_model_sha256, c.source_sha256
        FROM fts_items f
        JOIN memory_items m ON f.memory_id = m.memory_id
        JOIN memory_commits c ON m.paper_commit_id = c.commit_id
        WHERE fts_items MATCH ?
        LIMIT ?
        ''', (clean_q, limit))

    rows = cur.fetchall()
    results = []
    for r in rows:
        results.append({
            "memory_id": r[0],
            "memory_type": r[1],
            "text": r[2],
            "paper_id": r[3],
            "object_id": r[4],
            "source_ids": json.loads(r[5]),
            "epistemic_state": r[6],
            "paper_model_sha256": r[7],
            "source_sha256": r[8],
            "retrieval_method": "FTS5_EXACT_MATCH"
        })
    conn.close()
    return results

def verify_memory_integrity(custom_root=None):
    root = get_memory_root(custom_root)
    errors = []
    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()

    cur.execute('SELECT commit_id, payload_path FROM memory_commits')
    for cid, path_str in cur.fetchall():
        if not Path(path_str).exists():
            errors.append(f"Missing commit payload for {cid}: {path_str}")

    cur.execute('SELECT memory_id, payload_path FROM memory_items')
    for mid, path_str in cur.fetchall():
        if not Path(path_str).exists():
            errors.append(f"Missing memory item payload for {mid}: {path_str}")

    conn.close()
    return errors

def rebuild_index(custom_root=None):
    root = get_memory_root(custom_root)
    db_path = root / 'memory.sqlite'
    if db_path.exists():
        db_path.unlink()
    init_db(root)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    reindexed_items = 0

    # Walk objects/paper_commits
    pc_root = root / 'objects/paper_commits'
    for c_dir in pc_root.iterdir():
        if not c_dir.is_dir():
            continue
        commit_f = c_dir / 'commit.json'
        items_f = c_dir / 'items.json'
        if commit_f.exists() and items_f.exists():
            c_data = load_json(commit_f)
            items_data = load_json(items_f)
            cur.execute('INSERT OR REPLACE INTO memory_commits VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (c_data['commit_id'], c_data['commit_type'], c_data['paper_id'], None,
                         c_data['paper_model_sha256'], c_data['source_sha256'], c_data['committed_at'], str(commit_f)))
            for it in items_data:
                cur.execute('INSERT OR REPLACE INTO memory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (it['memory_id'], it['memory_type'], it['text'], it['paper_id'],
                             it['paper_commit_id'], it['object_id'], json.dumps(it['source_ids']),
                             it['epistemic_state'], it['created_at'], it['status'], str(items_f)))
                cur.execute('INSERT INTO fts_items(memory_id, text, paper_id, memory_type) VALUES (?, ?, ?, ?)',
                            (it['memory_id'], it['text'], it['paper_id'], it['memory_type']))
                reindexed_items += 1

    conn.commit()
    conn.close()
    print(f"OK: Rebuilt SQLite memory index ({reindexed_items} items reindexed).")
    return reindexed_items

def inspect_memory(item_id, custom_root=None):
    root = get_memory_root(custom_root)
    conn = sqlite3.connect(root / 'memory.sqlite')
    cur = conn.cursor()

    # 1. Search memory_items
    cur.execute('''
    SELECT m.memory_id, m.memory_type, m.text, m.paper_id, m.paper_commit_id, m.object_id,
           m.source_ids_json, m.epistemic_state, m.created_at, m.status, m.payload_path,
           c.paper_model_sha256, c.source_sha256
    FROM memory_items m
    JOIN memory_commits c ON m.paper_commit_id = c.commit_id
    WHERE m.memory_id = ? OR m.object_id = ?
    ''', (item_id, item_id))
    row = cur.fetchone()
    if row:
        conn.close()
        return {
            "kind": "MEMORY_ITEM",
            "memory_id": row[0],
            "memory_type": row[1],
            "text": row[2],
            "paper_id": row[3],
            "paper_commit_id": row[4],
            "object_id": row[5],
            "source_ids": json.loads(row[6]),
            "epistemic_state": row[7],
            "created_at": row[8],
            "status": row[9],
            "payload_path": row[10],
            "paper_model_sha256": row[11],
            "source_sha256": row[12]
        }

    # 2. Search memory_commits
    cur.execute('SELECT * FROM memory_commits WHERE commit_id = ? OR paper_id = ?', (item_id, item_id))
    row = cur.fetchone()
    if row:
        conn.close()
        return {
            "kind": "MEMORY_COMMIT",
            "commit_id": row[0],
            "commit_type": row[1],
            "paper_id": row[2],
            "project_id": row[3],
            "paper_model_sha256": row[4],
            "source_sha256": row[5],
            "committed_at": row[6],
            "payload_path": row[7]
        }

    # 3. Search memory_relations
    cur.execute('SELECT * FROM memory_relations WHERE relation_id = ?', (item_id,))
    row = cur.fetchone()
    if row:
        conn.close()
        return {
            "kind": "MEMORY_RELATION",
            "relation_id": row[0],
            "relation_type": row[1],
            "source_memory_id": row[2],
            "target_memory_id": row[3],
            "source_paper_id": row[4],
            "target_paper_id": row[5],
            "reasoning": row[6],
            "evidence_ids": json.loads(row[7]),
            "created_at": row[8]
        }

    # 4. Search experiment_outcomes
    cur.execute('SELECT * FROM experiment_outcomes WHERE outcome_id = ? OR experiment_id = ?', (item_id, item_id))
    row = cur.fetchone()
    if row:
        conn.close()
        return {
            "kind": "EXPERIMENT_OUTCOME",
            "outcome_id": row[0],
            "project_id": row[1],
            "experiment_id": row[2],
            "verdict": row[3],
            "findings": row[4],
            "recorded_at": row[5],
            "payload_path": row[6]
        }

    conn.close()
    return None

def enforce_open_reading_firewall(task_packet):
    """Verify that Open Reading task packet strictly forbids and excludes research memory."""
    task_type = task_packet.get('task_type')
    if task_type in ('OPEN_READING', 'LENS'):
        prohibited = task_packet.get('prohibited_context', [])
        if 'RESEARCH_MEMORY' not in prohibited and 'cross-paper memory' not in prohibited:
            return False, "Open Reading/Lens task packet must explicitly list RESEARCH_MEMORY in prohibited_context."
        # Verify no memory artifacts are in input_artifacts
        for k, v in task_packet.get('input_artifacts', {}).items():
            if 'memory' in str(k).lower() or 'memory' in str(v).lower():
                return False, f"Memory artifact {k}:{v} leaked into {task_type} input boundary."
    return True, "Firewall verified."

def main():
    ap = argparse.ArgumentParser(description="Evidentia Frozen Research Memory Manager")
    sp = ap.add_subparsers(dest='command', required=True)

    # commit-paper
    p_cp = sp.add_parser('commit-paper')
    p_cp.add_argument('--paper', required=True)
    p_cp.add_argument('--memory-root')

    # commit-project
    p_cprj = sp.add_parser('commit-project')
    p_cprj.add_argument('--paper', required=True)
    p_cprj.add_argument('--project', required=True)
    p_cprj.add_argument('--memory-root')

    # record-outcome
    p_ro = sp.add_parser('record-outcome')
    p_ro.add_argument('--project', required=True)
    p_ro.add_argument('--experiment', required=True)
    p_ro.add_argument('--verdict', choices=['SUCCESS', 'FAILURE', 'PARTIAL_SUCCESS', 'INCONCLUSIVE'], required=True)
    p_ro.add_argument('--findings', required=True)
    p_ro.add_argument('--conditions')
    p_ro.add_argument('--memory-root')

    # search
    p_s = sp.add_parser('search')
    p_s.add_argument('--query', required=True)
    p_s.add_argument('--type')
    p_s.add_argument('--limit', type=int, default=10)
    p_s.add_argument('--memory-root')

    # verify
    p_v = sp.add_parser('verify')
    p_v.add_argument('--memory-root')

    # inspect
    p_ins = sp.add_parser('inspect')
    p_ins.add_argument('--id', required=True)
    p_ins.add_argument('--memory-root')

    # rebuild-index
    p_rb = sp.add_parser('rebuild-index')
    p_rb.add_argument('--memory-root')

    args = ap.parse_args()
    if args.command == 'inspect':
        res = inspect_memory(args.id, args.memory_root)
        if res:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Item {args.id} not found in memory.")
            sys.exit(1)
    if args.command == 'commit-paper':
        commit_paper(args.paper, args.memory_root)
    elif args.command == 'commit-project':
        commit_project(args.paper, args.project, args.memory_root)
    elif args.command == 'record-outcome':
        record_outcome(args.project, args.experiment, args.verdict, args.findings, args.conditions, args.memory_root)
    elif args.command == 'search':
        res = search_memory(args.query, args.type, args.limit, args.memory_root)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == 'verify':
        errs = verify_memory_integrity(args.memory_root)
        if errs:
            print(json.dumps({"status": "FAIL", "errors": errs}, indent=2))
            sys.exit(1)
        print(json.dumps({"status": "OK", "message": "Memory integrity verified."}, indent=2))
    elif args.command == 'rebuild-index':
        rebuild_index(args.memory_root)

if __name__ == '__main__':
    main()
