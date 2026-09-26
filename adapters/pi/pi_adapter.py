#!/usr/bin/env python3
"""Pi Adapter for Evidentia Multi-Model Ensemble.

Host adapter responsible solely for:
- Model routing
- Task packet dispatch
- Result collection
- Executor metadata injection

Does NOT own lens definitions, scientific schemas, truth resolution, or freeze logic.
All scientific rules remain in Evidentia Core.
"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from executor_meta import build_executor_metadata

class PiAdapter:
    def __init__(self, default_model=None, available_models=None):
        self.host = "pi"
        self.default_model = default_model or os.environ.get("PI_MODEL", "gemini-2.5-pro")
        self.available_models = available_models or [
            "gemini-2.5-pro",
            "claude-3-7-sonnet",
            "gpt-4o"
        ]

    def route_model(self, task_type, lens=None, escalation=False):
        """Route task to appropriate model based on diversity requirements."""
        if escalation:
            # Pick secondary diverse model
            candidates = [m for m in self.available_models if m != self.default_model]
            return candidates[0] if candidates else self.default_model
        return self.default_model

    def dispatch_task(self, task_packet_path, model=None):
        """Dispatch task packet to specified model and prepare execution environment."""
        tp = Path(task_packet_path)
        task = json.loads(tp.read_text(encoding='utf-8'))
        
        target_model = model or self.route_model(task.get('task_type'), task.get('lens'))
        
        dispatch_packet = {
            "task_id": task.get('task_id'),
            "target_model": target_model,
            "host_adapter": "pi",
            "executor_metadata": build_executor_metadata(
                host="pi",
                provider="antigravity",
                model=target_model
            ),
            "payload": task
        }
        return dispatch_packet

    def collect_result(self, result_path, model=None):
        """Read and validate collected task result."""
        rp = Path(result_path)
        if not rp.exists():
            return None
        return json.loads(rp.read_text(encoding='utf-8'))

if __name__ == '__main__':
    adapter = PiAdapter()
    print(f"PiAdapter initialized with default_model={adapter.default_model}, available={adapter.available_models}")
