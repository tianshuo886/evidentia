#!/usr/bin/env python3
"""Pi Host Bridge for Evidentia Multi-Model Execution.

External Host Bridge (Section P0-4 Architecture A):
Pi operates as the external Host Agent executing Evidentia.
Python Core prepares AgentTask dispatch packets and metadata under agent_runs/,
pauses workflow in WAITING_FOR_AGENT, and awaits Host Agent submission via
evidentia submit.

Does NOT own lens definitions, scientific schemas, truth resolution, or freeze logic.
All scientific rules remain in Evidentia Core.
"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from executor_meta import build_executor_metadata

class PiHostBridge:
    def __init__(self, default_model=None, available_models=None):
        self.host = "pi"
        self.default_model = default_model or os.environ.get("PI_MODEL", "claude-3-7-sonnet")
        self.available_models = available_models or [
            "claude-3-7-sonnet",
            "gemini-2.5-pro",
            "gpt-4o"
        ]

    def route_model(self, task_type, lens=None, escalation=False):
        """Route task to appropriate model based on diversity requirements."""
        if escalation:
            candidates = [m for m in self.available_models if m != self.default_model]
            return candidates[0] if candidates else self.default_model
        return self.default_model

    def prepare_dispatch(self, task_packet_path, model=None, out_dir=None):
        """Prepare Host-Agent dispatch packet and persist dispatch metadata."""
        tp = Path(task_packet_path)
        if not tp.exists():
            raise FileNotFoundError(f"Task packet not found at {tp}")

        task = json.loads(tp.read_text(encoding='utf-8'))
        task_id = task.get('task_id', 'TASK-UNKNOWN')
        target_model = model or self.route_model(task.get('task_type'), task.get('lens'))

        dispatch_packet = {
            "task_id": task_id,
            "target_model": target_model,
            "host_adapter": "pi",
            "bridge_mode": "EXTERNAL_HOST_AGENT",
            "executor_metadata": build_executor_metadata(
                host="pi",
                provider="anthropic",
                model=target_model
            ),
            "payload": task
        }

        # Persist dispatch metadata under agent_runs/<task_id>/dispatch.json if out_dir given
        if out_dir:
            runs_dir = Path(out_dir) / 'agent_runs' / task_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            (runs_dir / 'dispatch.json').write_text(json.dumps(dispatch_packet, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        return dispatch_packet

    def dispatch_task(self, task_packet_path, model=None, out_dir=None):
        """Alias for prepare_dispatch for backward compatibility."""
        return self.prepare_dispatch(task_packet_path, model=model, out_dir=out_dir)

    def collect_result(self, result_path, model=None):
        """Read and validate collected task result."""
        rp = Path(result_path)
        if not rp.exists():
            return None
        return json.loads(rp.read_text(encoding='utf-8'))

# Compatibility alias
PiAdapter = PiHostBridge

if __name__ == '__main__':
    bridge = PiHostBridge()
    print(f"PiHostBridge initialized with default_model={bridge.default_model}, available={bridge.available_models}")
