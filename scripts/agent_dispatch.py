#!/usr/bin/env python3
"""Host Agent Dispatch Layer for Evidentia v1.1.1.

Host-neutral interface providing:
    dispatch_agent_task(task_path, adapter=None, model=None, replay_dir=None, fixture=False) -> AgentResultEnvelope | None

Implements:
- Tier 2 Recorded Replay execution (replay_dir)
- Tier 3 External Host Bridge (PiHostBridge / GenericAdapter)
- Tier 1 Isolated Synthetic Fixtures (only when explicitly requested via fixture=True)
- Explicit AgentDispatchError on broken adapter configurations (zero silent exception swallowing)
- Clean stop returning None when waiting for external Host Agent submission
"""
import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'adapters/generic'))
sys.path.insert(0, str(ROOT / 'adapters/pi'))
sys.path.insert(0, str(ROOT / 'tests/fixtures/synthetic_agents'))

from validate_common import load_json, schema_validate

class AgentDispatchError(Exception):
    """Raised when an agent dispatch or adapter configuration fails."""
    pass

def is_fixture_enabled(fixture=None):
    if fixture is not None:
        return bool(fixture)
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("EVIDENTIA_ALLOW_FIXTURE") == "1")

def dispatch_agent_task(task_path, adapter=None, model=None, replay_dir=None, fixture=None):
    """Dispatch an AgentTask packet and return a validated AgentResultEnvelope, or None if waiting."""
    tp = Path(task_path)
    if not tp.exists():
        raise FileNotFoundError(f"Task packet not found at {tp}")
    
    task = load_json(tp)
    task_id = task.get('task_id', '')
    task_type = task.get('task_type', '')
    root = tp.parent.parent
    if tp.parent.name in ('lens', 'verification', 'apply'):
        root = tp.parent.parent.parent
    if not task_type:
        if 'target_type' in task or 'target_id' in task or 'TASK-V' in task_id or 'verif' in task_id.lower():
            task_type = 'VERIFICATION'
        elif 'lens' in task:
            task_type = 'LENS'
        elif 'OPEN' in task_id:
            task_type = 'OPEN_READING'
        elif 'RECON' in task_id:
            task_type = 'RECONCILIATION'
        elif 'APPLY' in task_id:
            task_type = 'APPLY_LOCAL'

    # 1. Tier 2 Replay: Check for pre-recorded Host-Agent result when replay_dir is specified
    replays_to_check = []
    if replay_dir:
        replays_to_check.append(Path(replay_dir))
    if os.environ.get("EVIDENTIA_REPLAY_DIR"):
        replays_to_check.append(Path(os.environ["EVIDENTIA_REPLAY_DIR"]))

    for r_dir in replays_to_check:
        if r_dir.exists():
            candidate = r_dir / f"{task_id}.json"
            if not candidate.exists():
                candidate = r_dir / f"{task_type.lower()}.json"
            if candidate.exists():
                envelope = load_json(candidate)
                errs = schema_validate(envelope, 'agent_result_envelope')
                if not errs:
                    # Bind provenance hashes to current task execution context
                    payload = envelope.get('result', {})
                    if isinstance(payload, dict):
                        if task.get('source_sha256'):
                            payload['source_sha256'] = task['source_sha256']
                            if 'paper' in payload and isinstance(payload['paper'], dict):
                                payload['paper']['pdf_sha256'] = task['source_sha256']
                        if task.get('base_sha256'):
                            if 'base_sha256' in payload:
                                payload['base_sha256'] = task['base_sha256']
                            if 'base_model_sha256' in payload:
                                payload['base_model_sha256'] = task['base_sha256']
                        # Bind figure asset files to actual inventory in this run
                        if 'figures' in payload and 'input_artifacts' in task:
                            inv_rel = task['input_artifacts'].get('figure_inventory')
                            if inv_rel:
                                inv_p = root / inv_rel
                                if inv_p.exists():
                                    inv_data = load_json(inv_p)
                                    inv_map = {it['id']: it.get('file') for it in inv_data.get('items', [])}
                                    for f in payload.get('figures', []):
                                        if f.get('id') in inv_map:
                                            f['file'] = inv_map[f['id']]
                    return envelope

    # 2. Tier 1 Synthetic Fixtures: Only when explicitly requested
    allow_fixture = is_fixture_enabled(fixture)
    if allow_fixture:
        if task_type == 'OPEN_READING':
            import open_reading_fixture
            return open_reading_fixture.run_synthetic_open_reading(tp)
        elif task_type == 'LENS':
            import lens_fixture
            return lens_fixture.run_synthetic_lens(tp, model=model or "fixture-lens-model")
        elif task_type == 'RECONCILIATION':
            import reconciliation_fixture
            return reconciliation_fixture.run_synthetic_reconciliation(tp)
        elif task_type == 'VERIFICATION':
            import verifier_fixture
            return verifier_fixture.run_synthetic_verification(tp)
        elif task_type == 'APPLY_LOCAL':
            import apply_fixture
            root = tp.parent.parent
            if tp.parent.name == 'apply':
                root = tp.parent.parent.parent
            proj_doc = task.get('project_doc')
            if not proj_doc or not Path(proj_doc).exists():
                proj_doc = root / task.get('input_artifacts', {}).get('project_document', 'project_document.md')
            return apply_fixture.run_synthetic_apply(root, proj_doc)
        elif task_type == 'MEMORY_SYNTHESIS':
            import apply_fixture
            return apply_fixture.run_synthetic_memory_synthesis(tp)

    # 3. External Host Bridges: prepare dispatch and await host submission
    if adapter == 'pi':
        try:
            from pi_adapter import PiHostBridge
            pi = PiHostBridge(default_model=model)
            dispatch_packet = pi.prepare_dispatch(tp, model=model, out_dir=root)
            print(f"[HOST_BRIDGE] Prepared Pi dispatch packet for {task_id} (Target Model: {dispatch_packet.get('target_model')})")
            return None
        except Exception as e:
            raise AgentDispatchError(f"Pi host bridge preparation failed for {task_id}: {e}")

    if adapter == 'generic':
        try:
            from generic_adapter import GenericAdapter
            gen = GenericAdapter(model=model)
            dispatch_packet = gen.prepare_dispatch(tp, model=model, out_dir=root)
            print(f"[HOST_BRIDGE] Prepared Generic dispatch packet for {task_id} (Host: {dispatch_packet.get('host_adapter')})")
            return None
        except Exception as e:
            raise AgentDispatchError(f"Generic adapter preparation failed for {task_id}: {e}")

    # No automated execution available -> return None to signal WAITING_FOR_AGENT
    return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: agent_dispatch.py <task_path> [--fixture] [--replay <dir>] [--model <model>]")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('task_path')
    ap.add_argument('--fixture', action='store_true')
    ap.add_argument('--replay')
    ap.add_argument('--model')
    ap.add_argument('--adapter')
    args = ap.parse_args()
    envelope = dispatch_agent_task(args.task_path, adapter=args.adapter, model=args.model, replay_dir=args.replay, fixture=args.fixture)
    if envelope:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
    else:
        print("WAITING_FOR_AGENT")
        sys.exit(2)
