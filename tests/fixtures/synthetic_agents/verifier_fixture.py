#!/usr/bin/env python3
"""Synthetic Verifier Agent Fixture for Evidentia Tier 1 Testing.

Produces schema-valid verification_result documents wrapped in an
AgentResultEnvelope tagged with execution_kind="SIMULATED_FIXTURE".
"""
import json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_common import load_json, schema_validate

def run_synthetic_verification(task_path):
    tp = Path(task_path)
    task = load_json(tp)
    stmt = task.get('statement', '')
    target_id = task.get('target_id', 'T01')
    loc = task.get('localized_evidence', {})

    text_corpus = " ".join([
        loc.get('surrounding_text', ''),
        " ".join(loc.get('captions', [])),
        str(loc.get('table_cells', ''))
    ]).lower()

    stmt_lower = stmt.lower()
    refute_patterns = [
        r'\bnot\s+supported\b', r'\bcontradicts\b', r'\bfails?\s+to\b',
        r'\bno\s+significant\b', r'\bnegative\s+result\b', r'\bdisproved\b',
        r'\bsevere\s+instability\b', r'\bdegrades?\b'
    ]

    if not text_corpus.strip() and not loc.get('figure_asset'):
        status = "INSUFFICIENT_EVIDENCE"
        reason = "[SIMULATED] Localized evidence is empty."
    elif any(re.search(pat, text_corpus) for pat in refute_patterns):
        status = "REJECTED"
        reason = "[SIMULATED] Contradiction or degradation marker detected in localized evidence."
    else:
        tokens_stmt = set(re.findall(r'\b[a-z]{3,}\b', stmt_lower))
        tokens_ev = set(re.findall(r'\b[a-z]{3,}\b', text_corpus))
        overlap = len(tokens_stmt & tokens_ev)
        if overlap >= 2:
            status = "SUPPORTED"
            reason = f"[SIMULATED] Localized evidence confirms assertion with {overlap} matched terms."
        elif overlap == 1:
            status = "PARTIAL"
            reason = "[SIMULATED] Partial term overlap with localized evidence."
        else:
            status = "AMBIGUOUS"
            reason = "[SIMULATED] Inconclusive semantic overlap."

    now_iso = datetime.now(timezone.utc).isoformat()
    result_doc = {
        "task_id": task.get("task_id", f"TASK-VERIF-{target_id}"),
        "target_id": target_id,
        "status": status,
        "reasoning": reason,
        "grounding_evidence": loc.get('source_ids', ["p.1"]),
        "epistemic_impact": f"[SIMULATED] Status {status} assigned to {target_id}.",
        "executor_metadata": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-verifier-runner",
            "model": "synthetic-verifier-v1"
        }
    }

    envelope = {
        "task_id": task.get("task_id", f"TASK-VERIF-{target_id}"),
        "execution_kind": "SIMULATED_FIXTURE",
        "executor": {
            "kind": "SIMULATED_FIXTURE",
            "host": "synthetic-verifier-runner",
            "provider": "evidentia-test-suite",
            "model": "synthetic-verifier-v1",
            "started_at": now_iso,
            "completed_at": now_iso
        },
        "started_at": now_iso,
        "completed_at": now_iso,
        "result": result_doc
    }
    return envelope

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: verifier_fixture.py <task_path> [<out_path>]")
    res = run_synthetic_verification(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
    else:
        print(json.dumps(res, indent=2))
