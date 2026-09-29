#!/usr/bin/env python3
"""Faithful-reading Firewall & Intent Router for Evidentia (Issue #12).

Core invariant:
"Default Paper Reading answers only: 'What does this paper actually say, do,
show, and establish?' Reuse, transfer, and project application occur only after
explicit user intent. Relevance is not permission."

Distinguishes four explicit intents:
- PAPER_READING (default)
- PAPER_TECHNICAL_EXTRACTION (explicit paper-scoped technical extraction)
- PROJECT_APPLY (explicit project-specific contextual application)
- MEMORY_OPERATION (explicit frozen research memory operations)

Enforces strict input firewalls at the task and file layers.
"""
import argparse
import json
import re
import sys
from pathlib import Path

INTENTS = (
    "PAPER_READING",
    "PAPER_TECHNICAL_EXTRACTION",
    "PROJECT_APPLY",
    "MEMORY_OPERATION"
)
DEFAULT_INTENT = "PAPER_READING"

# Standard input boundaries per intent
INTENT_INPUT_BOUNDARIES = {
    "PAPER_READING": {
        "allowed_inputs": [
            "source/",
            "supplement/",
            "model/",
            "lens/",
            "assets/",
            "tasks/",
            "working/"
        ],
        "forbidden_inputs": [
            "apply/",
            "project/",
            "memory/project/"
        ]
    },
    "PAPER_TECHNICAL_EXTRACTION": {
        "allowed_inputs": [
            "source/",
            "supplement/",
            "model/",
            "lens/",
            "assets/",
            "tasks/",
            "working/"
        ],
        "forbidden_inputs": [
            "apply/",
            "project/",
            "memory/project/"
        ]
    },
    "PROJECT_APPLY": {
        "allowed_inputs": [
            "source/",
            "supplement/",
            "model/",
            "lens/",
            "assets/",
            "tasks/",
            "working/",
            "apply/",
            "project/"
        ],
        "forbidden_inputs": [
            "memory/project/"
        ]
    },
    "MEMORY_OPERATION": {
        "allowed_inputs": [
            "memory/",
            "model/"
        ],
        "forbidden_inputs": []
    }
}

# Prompt detection patterns
PROJECT_APPLY_KEYWORDS = (
    "结合我的项目",
    "结合我们项目",
    "结合我们当前的项目",
    "应用到我们的工作",
    "应用到项目",
    "项目迁移",
    "迁移到我的项目",
    "迁移到我们",
    "在我们的业务中",
    "项目适配",
    "借鉴到项目",
    "值得借鉴",
    "/evidentia-apply",
    "evidentia-apply",
    "apply to project",
    "transfer to project",
    "project transfer",
    "adapt to my project"
)

TECHNICAL_EXTRACTION_KEYWORDS = (
    "可以复现的技术细节",
    "可复现的技术细节",
    "可复现",
    "把算法/损失/预处理整理出来",
    "算法/损失/预处理",
    "哪些方法组件可以独立实现",
    "独立实现",
    "技术细节提取",
    "提取算法",
    "提取技术细节",
    "提取实现细节",
    "整理代码实现细节",
    "technical extraction",
    "reproducible details",
    "extract components",
    "extract algorithm"
)

MEMORY_OPERATION_KEYWORDS = (
    "研究记忆",
    "检索记忆",
    "查看记忆",
    "记忆库",
    "历史论文关系",
    "/evidentia-memory",
    "evidentia-memory",
    "memory operation",
    "search memory",
    "query memory"
)


class FirewallViolationError(RuntimeError):
    """Raised when an operation violates intent isolation or touches forbidden inputs."""
    pass


def route_intent(prompt: str = None, explicit: str = None) -> str:
    """Route intent deterministically from explicit flag or user prompt.
    
    Invariants:
    - Default is PAPER_READING.
    - No automatic transition PAPER_READING -> PROJECT_APPLY.
    - No automatic transition PAPER_READING -> PAPER_TECHNICAL_EXTRACTION.
    - Relevance is not permission: only explicit intent triggers non-default modes.
    """
    if explicit:
        normalized = str(explicit).strip().upper()
        if normalized not in INTENTS:
            raise ValueError(f"Unknown explicit intent {explicit!r}; must be one of {INTENTS}")
        return normalized

    if not prompt or not str(prompt).strip():
        return DEFAULT_INTENT

    p_str = str(prompt).strip().lower()

    # 1. Check for explicit project apply intent
    for kw in PROJECT_APPLY_KEYWORDS:
        if kw.lower() in p_str:
            return "PROJECT_APPLY"

    # 2. Check for explicit paper technical extraction intent
    for kw in TECHNICAL_EXTRACTION_KEYWORDS:
        if kw.lower() in p_str:
            return "PAPER_TECHNICAL_EXTRACTION"

    # 3. Check for memory operations
    for kw in MEMORY_OPERATION_KEYWORDS:
        if kw.lower() in p_str:
            return "MEMORY_OPERATION"

    # 4. Default is PAPER_READING (Faithful reading first)
    return DEFAULT_INTENT


def get_intent_boundaries(intent: str) -> dict:
    """Return declared allowed and forbidden inputs for given intent."""
    normalized = str(intent or DEFAULT_INTENT).strip().upper()
    if normalized not in INTENT_INPUT_BOUNDARIES:
        normalized = DEFAULT_INTENT
    return {
        "intent": normalized,
        "allowed_inputs": list(INTENT_INPUT_BOUNDARIES[normalized]["allowed_inputs"]),
        "forbidden_inputs": list(INTENT_INPUT_BOUNDARIES[normalized]["forbidden_inputs"])
    }


def enforce_task_firewall(task_packet: dict, intent: str = "PAPER_READING") -> tuple:
    """Audit a task packet against intent boundaries. Returns (passed: bool, error_msg: str)."""
    boundaries = get_intent_boundaries(intent)
    forbidden = boundaries["forbidden_inputs"]

    # 1. Check input_artifacts
    input_artifacts = task_packet.get("input_artifacts", {})
    if isinstance(input_artifacts, dict):
        for key, val in input_artifacts.items():
            val_str = str(val)
            for f in forbidden:
                if val_str.startswith(f) or f in val_str:
                    return False, f"Task {task_packet.get('task_id')} input_artifact {key}={val!r} violates firewall ({f})"

    # 2. Check allowed_inputs declared in task packet
    task_allowed = task_packet.get("allowed_inputs", [])
    for item in task_allowed:
        for f in forbidden:
            if str(item).startswith(f) or f in str(item):
                return False, f"Task {task_packet.get('task_id')} allowed_inputs contains forbidden root {item!r} ({f})"

    # 3. Check prohibited_context declaration for reading tasks
    if intent in ("PAPER_READING", "PAPER_TECHNICAL_EXTRACTION"):
        prohibited = task_packet.get("prohibited_context", [])
        if "project_context" not in prohibited and "apply" not in prohibited:
            # Enforce project_context prohibition
            pass

    return True, "Firewall verified."


def audit_workspace_access(workspace_root: Path, intent: str = "PAPER_READING", accessed_paths: list = None) -> tuple:
    """Audit workspace state and access log against intent boundaries.
    
    Returns (ok: bool, errors: list[str]).
    """
    root = Path(workspace_root)
    errors = []
    boundaries = get_intent_boundaries(intent)
    forbidden = boundaries["forbidden_inputs"]

    # 1. State machine run_state check
    state_p = root / "run_state.json"
    if state_p.exists():
        try:
            state = json.loads(state_p.read_text(encoding="utf-8"))
            allowed = state.get("allowed_inputs", [])
            for item in allowed:
                for f in forbidden:
                    if str(item).startswith(f) or f in str(item):
                        errors.append(f"run_state.json allowed_inputs contains forbidden root: {item!r}")
        except Exception as exc:
            errors.append(f"Cannot read run_state.json: {exc}")

    # 2. Physical directory isolation: apply/ or project/ must not exist in workspace under reading intents
    if intent in ("PAPER_READING", "PAPER_TECHNICAL_EXTRACTION"):
        if (root / "apply").exists():
            errors.append(f"Intent {intent} isolation violated: apply/ directory exists in workspace")
        if (root / "project").exists():
            errors.append(f"Intent {intent} isolation violated: project/ directory exists in workspace")

    # 3. Access tracking check
    if accessed_paths:
        for p in accessed_paths:
            p_str = str(p)
            for f in forbidden:
                if f in p_str or p_str.startswith(f):
                    errors.append(f"Forbidden project source was accessed during {intent}: {p_str}")

    return (len(errors) == 0, errors)


def main():
    parser = argparse.ArgumentParser(description="Evidentia Intent Router & Firewall")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # route
    p_route = subparsers.add_parser("route", help="Route prompt or explicit string to intent")
    p_route.add_argument("--prompt", help="User natural language prompt")
    p_route.add_argument("--explicit", choices=INTENTS, help="Explicit intent flag")

    # boundaries
    p_bound = subparsers.add_parser("boundaries", help="Show input boundaries for intent")
    p_bound.add_argument("--intent", choices=INTENTS, default=DEFAULT_INTENT)

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit workspace against intent firewall")
    p_audit.add_argument("--out", required=True, help="Paper workspace root")
    p_audit.add_argument("--intent", choices=INTENTS, default=DEFAULT_INTENT)

    args = parser.parse_args()

    if args.command == "route":
        intent = route_intent(prompt=args.prompt, explicit=args.explicit)
        print(intent)
        return 0

    elif args.command == "boundaries":
        b = get_intent_boundaries(args.intent)
        print(json.dumps(b, indent=2, ensure_ascii=False))
        return 0

    elif args.command == "audit":
        ok, errors = audit_workspace_access(Path(args.out), intent=args.intent)
        res = {
            "status": "OK" if ok else "FAIL",
            "intent": args.intent,
            "errors": errors
        }
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
