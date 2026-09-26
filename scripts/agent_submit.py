#!/usr/bin/env python3
"""Scientific Trust Boundary & Result Submission Gateway for Evidentia v1.1.1.

Implements P0-3 Hardening:
- Resolves canonical AgentTask from run workspace (fails closed if 0 or >1 matches)
- Prohibits raw JSON in production without --allow-legacy-raw
- Validates AgentResultEnvelope schema and exact task_id match
- Validates provenance bindings against canonical task (source SHA, baseline SHA, contract, prompt)
- Validates input artifact hashes to reject mid-execution tampering
- Validates cited evidence IDs against reconstructed source inventory (rejects phantom IDs like F99)
- Promotes result payload strictly to task.target_output and records immutable AgentRun
"""
import argparse, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_common import load_json, schema_validate, sha256, all_ids

def resolve_task(run_dir, task_id):
    """Find the exact canonical AgentTask packet matching task_id in workspace."""
    tasks_dir = Path(run_dir) / 'tasks'
    if not tasks_dir.exists():
        sys.exit(f"REFUSED: No tasks directory found at {tasks_dir}")

    matches = []
    task_id_clean = task_id.strip().upper()

    for p in tasks_dir.glob('**/*.json'):
        try:
            data = load_json(p)
            tid = str(data.get('task_id', '')).strip().upper()
            if tid == task_id_clean:
                matches.append((p, data))
        except Exception:
            continue

    if len(matches) == 0:
        # Fallback: check if task_id matches filename stem
        for p in tasks_dir.glob('**/*.json'):
            if p.stem.upper() == task_id_clean or f"TASK-{p.stem.upper()}" == task_id_clean or f"TASK-LENS-{p.stem.upper()}" == task_id_clean:
                try:
                    data = load_json(p)
                    matches.append((p, data))
                except Exception:
                    pass

    if len(matches) == 0:
        sys.exit(f"REFUSED: Task ID '{task_id}' does not match any generated AgentTask in {tasks_dir}")
    if len(matches) > 1:
        paths = [str(m[0].relative_to(run_dir)) for m in matches]
        sys.exit(f"REFUSED: Ambiguous task ID '{task_id}' matched multiple tasks: {paths}")

    return matches[0]

def build_allowed_source_ids(run_dir):
    """Compile exhaustive set of authentic source entity IDs from reconstructed inventory."""
    r_dir = Path(run_dir)
    allowed = set()

    # 1. Source map pages
    sm_p = r_dir / 'model/source_map.json'
    if sm_p.exists():
        sm = load_json(sm_p)
        for pg in sm.get('pages', []):
            allowed.add(f"p.{pg.get('number', 1)}")

    # 2. Figure and Table inventory
    inv_p = r_dir / 'model/figure_inventory.json'
    if inv_p.exists():
        inv = load_json(inv_p)
        for it in inv.get('items', []):
            if it.get('id'):
                allowed.add(it['id'])

    # 3. Model entities (claims, methods, components, experiments)
    for model_name in ('open_reading_model.json', 'paper_model.json'):
        mp = r_dir / 'model' / model_name
        if mp.exists():
            m_data = load_json(mp)
            for k, v in all_ids(m_data).items():
                allowed.add(k)

    return allowed

def validate_evidence_ids(payload, allowed_ids):
    """Verify that every cited evidence/source ID exists in authentic paper inventory."""
    def extract_evidence_ids(obj):
        found = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ('evidence', 'source', 'grounding_evidence', 'evidence_ids') and isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            found.append(item)
                else:
                    found.extend(extract_evidence_ids(v))
        elif isinstance(obj, list):
            for item in obj:
                found.extend(extract_evidence_ids(item))
        return found

    cited = extract_evidence_ids(payload)
    for eid in cited:
        # Check page syntax p.N or presence in allowed_ids
        if re.match(r'^p\.[0-9]+$', eid):
            continue
        if eid not in allowed_ids:
            sys.exit(f"REFUSED: Unknown evidence ID '{eid}' not present in paper source inventory or model.")

def submit_agent_result(run_dir, task_id, result_path, allow_legacy_raw=False):
    r_dir = Path(run_dir)
    res_p = Path(result_path)
    if not res_p.exists():
        sys.exit(f"REFUSED: Result file not found at {res_p}")

    # 1. Resolve canonical AgentTask
    task_path, task = resolve_task(r_dir, task_id)

    raw_data = load_json(res_p)

    # 2. Production gate: prohibit raw JSON without explicit development flag
    if 'result' in raw_data and 'executor' in raw_data:
        envelope = raw_data
        payload = envelope['result']
    else:
        if not allow_legacy_raw and os.environ.get("EVIDENTIA_ALLOW_LEGACY_RAW") != "1":
            sys.exit("REFUSED: Submitted result must be wrapped in an AgentResultEnvelope. Raw JSON is prohibited in production without --allow-legacy-raw.")
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = raw_data
        envelope = {
            "task_id": task.get('task_id', task_id),
            "execution_kind": "SIMULATED_FIXTURE",
            "executor": {
                "kind": "SIMULATED_FIXTURE",
                "host": "legacy-adapter",
                "model": "legacy-raw-submit",
                "started_at": now_iso,
                "completed_at": now_iso
            },
            "started_at": now_iso,
            "completed_at": now_iso,
            "result": payload
        }

    # 3. Envelope schema validation
    errs = schema_validate(envelope, 'agent_result_envelope')
    if errs:
        sys.exit(f"REFUSED: Submitted result failed agent_result_envelope schema validation:\n{errs}")

    # 4. Task ID validation
    env_tid = str(envelope.get('task_id', '')).strip().upper()
    can_tid = str(task.get('task_id', '')).strip().upper()
    if env_tid != can_tid:
        sys.exit(f"REFUSED: Envelope task_id '{envelope.get('task_id')}' does not match canonical AgentTask ID '{task.get('task_id')}'.")

    # 5. Provenance hash and version binding validation
    task_src_sha = task.get('source_sha256')
    if task_src_sha:
        if payload.get('source_sha256') and payload['source_sha256'] != task_src_sha:
            sys.exit(f"REFUSED: Payload source_sha256 '{payload['source_sha256']}' does not match task source_sha256 '{task_src_sha}'.")
        paper_sha = payload.get('paper', {}).get('pdf_sha256')
        if paper_sha and paper_sha != task_src_sha:
            sys.exit(f"REFUSED: Paper pdf_sha256 '{paper_sha}' does not match task source_sha256 '{task_src_sha}'.")

    task_base_sha = task.get('base_sha256')
    if task_base_sha:
        res_base = payload.get('base_sha256') or payload.get('base_model_sha256')
        if res_base and res_base != task_base_sha:
            sys.exit(f"REFUSED: Payload base_sha256 '{res_base}' does not match task base_sha256 '{task_base_sha}'.")

    task_cv = task.get('contract_version')
    if task_cv:
        res_cv = payload.get('contract_version') or payload.get('lens_contract_version') or envelope.get('contract_version')
        if res_cv and str(res_cv) != str(task_cv):
            sys.exit(f"REFUSED: Contract version mismatch: '{res_cv}' != '{task_cv}'.")

    task_pv = task.get('prompt_version')
    if task_pv:
        res_pv = payload.get('prompt_version') or envelope.get('prompt_version')
        if res_pv and str(res_pv) != str(task_pv):
            sys.exit(f"REFUSED: Prompt version mismatch: '{res_pv}' != '{task_pv}'.")

    task_delta_sha = task.get('local_delta_sha256')
    if task_delta_sha:
        res_delta_sha = payload.get('based_on_local_delta_sha256') or payload.get('local_delta_sha256')
        if res_delta_sha and res_delta_sha != task_delta_sha:
            sys.exit(f"REFUSED: Memory synthesis local delta SHA mismatch: '{res_delta_sha}' != '{task_delta_sha}'.")

    # 6. Input artifact hash validation (detect frozen input tampering)
    input_hashes = envelope.get('input_hashes')
    if isinstance(input_hashes, dict):
        for rel_path, expected_hash in input_hashes.items():
            f_path = r_dir / rel_path
            if f_path.exists():
                actual_hash = sha256(f_path)
                if actual_hash != expected_hash:
                    sys.exit(f"REFUSED: Input artifact '{rel_path}' changed during execution (SHA mismatch: {actual_hash} != {expected_hash}).")

    # 7. Evidence ID grounding validation
    allowed_ids = build_allowed_source_ids(r_dir)
    if allowed_ids:
        validate_evidence_ids(payload, allowed_ids)

    # 8. Output path and schema strictly from canonical task
    target_rel = task.get('target_output') or task.get('output')
    if not target_rel:
        sys.exit(f"REFUSED: AgentTask {task_id} does not declare a target_output.")

    output_schema = task.get('output_schema')
    if output_schema:
        schema_errs = schema_validate(payload, output_schema)
        if schema_errs:
            sys.exit(f"REFUSED: Submitted payload failed {output_schema} schema validation:\n{schema_errs}")

    target_output = r_dir / target_rel
    target_output.parent.mkdir(parents=True, exist_ok=True)
    target_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Accepted trusted Host Agent result for {task_id} -> {target_output}")

    # 9. Record immutable AgentRun
    runs_dir = r_dir / 'agent_runs' / task.get('task_id', task_id)
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_idx = len(list(runs_dir.glob('run-*.json'))) + 1
    (runs_dir / f"run-{run_idx:03d}.json").write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    return 0

def main():
    ap = argparse.ArgumentParser(description="Evidentia Scientific Trust Boundary & Submitter")
    ap.add_argument('--run-dir', '--out', required=True, dest='run_dir')
    ap.add_argument('--task', required=True)
    ap.add_argument('--result', required=True)
    ap.add_argument('--allow-legacy-raw', action='store_true', help="Allow unwrapped raw JSON (tests and development only)")
    args = ap.parse_args()
    submit_agent_result(args.run_dir, args.task, args.result, allow_legacy_raw=args.allow_legacy_raw)

if __name__ == '__main__':
    main()
