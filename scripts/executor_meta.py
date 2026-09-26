#!/usr/bin/env python3
"""Standardized executor metadata builder for Evidentia tasks.

Ensures no required metadata fields are silently omitted.
"""
import os, sys
from datetime import datetime, timezone

REQUIRED_FIELDS = (
    "host",
    "host_version",
    "provider",
    "model",
    "model_version",
    "reasoning_profile",
    "tool_profile",
    "started_at",
    "completed_at"
)

def build_executor_metadata(
    host=None,
    host_version=None,
    provider=None,
    model=None,
    model_version=None,
    reasoning_profile="standard",
    tool_profile="paper-only",
    started_at=None,
    completed_at=None
):
    now_iso = datetime.now(timezone.utc).isoformat()
    meta = {
        "host": host or os.environ.get("PI_HOST") or os.environ.get("AGENT_HOST") or "generic-host",
        "host_version": host_version or os.environ.get("PI_HOST_VERSION") or os.environ.get("AGENT_VERSION") or "UNKNOWN",
        "provider": provider or os.environ.get("PI_PROVIDER") or os.environ.get("LLM_PROVIDER") or "UNKNOWN",
        "model": model or os.environ.get("PI_MODEL") or os.environ.get("LLM_MODEL") or "UNKNOWN",
        "model_version": model_version or os.environ.get("PI_MODEL_VERSION") or "UNKNOWN",
        "reasoning_profile": reasoning_profile or "standard",
        "tool_profile": tool_profile or "paper-only",
        "started_at": started_at or now_iso,
        "completed_at": completed_at or now_iso
    }
    for k in REQUIRED_FIELDS:
        if k not in meta or meta[k] is None:
            meta[k] = "UNKNOWN"
    return meta

if __name__ == '__main__':
    import json
    print(json.dumps(build_executor_metadata(), indent=2))
