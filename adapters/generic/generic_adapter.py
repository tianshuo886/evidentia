#!/usr/bin/env python3
"""Generic host adapter for standard single-model environments (Codex, Claude Code, CLI)."""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from executor_meta import build_executor_metadata

class GenericAdapter:
    def __init__(self, host=None, model=None):
        self.host = host or "generic-host"
        self.model = model or "default-model"

    def dispatch_task(self, task_packet_path):
        tp = Path(task_packet_path)
        task = json.loads(tp.read_text(encoding='utf-8'))
        return {
            "task_id": task.get('task_id'),
            "host_adapter": self.host,
            "executor_metadata": build_executor_metadata(host=self.host, model=self.model),
            "payload": task
        }

    def collect_result(self, result_path):
        rp = Path(result_path)
        if not rp.exists():
            return None
        return json.loads(rp.read_text(encoding='utf-8'))

if __name__ == '__main__':
    adapter = GenericAdapter()
    print(f"GenericAdapter initialized for host={adapter.host}")
