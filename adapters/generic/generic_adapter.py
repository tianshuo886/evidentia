#!/usr/bin/env python3
"""Generic host adapter and bridge for Evidentia execution (Codex, Claude Code, CLI)."""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from executor_meta import build_executor_metadata

class GenericAdapter:
    def __init__(self, host=None, model=None):
        self.host = host or "generic-host"
        self.model = model or "default-model"

    def prepare_dispatch(self, task_packet_path, model=None, out_dir=None):
        tp = Path(task_packet_path)
        if not tp.exists():
            raise FileNotFoundError(f"Task packet not found at {tp}")

        task = json.loads(tp.read_text(encoding='utf-8'))
        task_id = task.get('task_id', 'TASK-UNKNOWN')
        target_model = model or self.model

        dispatch_packet = {
            "task_id": task_id,
            "target_model": target_model,
            "host_adapter": self.host,
            "bridge_mode": "EXTERNAL_HOST_AGENT",
            "executor_metadata": build_executor_metadata(host=self.host, model=target_model),
            "payload": task
        }

        if out_dir:
            runs_dir = Path(out_dir) / 'agent_runs' / task_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            (runs_dir / 'dispatch.json').write_text(json.dumps(dispatch_packet, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        return dispatch_packet

    def dispatch_task(self, task_packet_path, model=None, out_dir=None):
        return self.prepare_dispatch(task_packet_path, model=model, out_dir=out_dir)

    def collect_result(self, result_path):
        rp = Path(result_path)
        if not rp.exists():
            return None
        return json.loads(rp.read_text(encoding='utf-8'))

if __name__ == '__main__':
    adapter = GenericAdapter()
    print(f"GenericAdapter initialized for host={adapter.host}")
