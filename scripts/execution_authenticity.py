#!/usr/bin/env python3
"""Distinguish real model execution from replay, fixture and hand-authored data (Issue #47).

The Reader v3 runs committed in this repository contain `run-*.json` envelopes
whose `started_at` and `completed_at` are identical, and six Lens outputs
stamped at the same wall-clock minute. Those artifacts prove that *something*
wrote a file; they do not prove that six isolated Lens passes ran.

This module answers one question honestly: **was this workspace produced by real
model execution?** It classifies every recorded run as one of:

    REAL        a live adapter/model execution with a non-degenerate duration
    FIXTURE     an explicitly simulated or fixture-generated envelope
    REPLAY      a recorded response played back from disk
    NOT_EVIDENCED  a claimed execution with no receipt that could support it

Only `REAL` execution may support a release decision. Everything else is kept
for regression purposes but is never accepted as scientific evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FIXTURE_KINDS = {"SIMULATED_FIXTURE", "FIXTURE", "SYNTHETIC", "SYNTHETIC_REPLAY"}
REPLAY_KINDS = {"REPLAY", "RECORDED_REPLAY"}
REAL_KINDS = {"HOST_AGENT", "LIVE", "MODEL", "ADAPTER"}

# A real multimodal reasoning pass cannot complete in zero seconds. This is a
# lower bound on plausibility, not a performance expectation.
MIN_REAL_SECONDS = 1.0


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def classify_envelope(envelope: dict) -> tuple[str, list[str]]:
    """Return (classification, reasons) for one run envelope."""
    reasons: list[str] = []
    kind = str(envelope.get("execution_kind") or "").upper()
    executor = envelope.get("executor") or {}

    if kind in FIXTURE_KINDS:
        return "FIXTURE", [f"execution_kind={kind}"]
    if kind in REPLAY_KINDS:
        return "REPLAY", [f"execution_kind={kind}"]

    started = _parse(envelope.get("started_at") or executor.get("started_at"))
    completed = _parse(envelope.get("completed_at") or executor.get("completed_at"))
    if started is None or completed is None:
        reasons.append("missing or unparseable execution timestamps")
    else:
        delta = (completed - started).total_seconds()
        if delta < MIN_REAL_SECONDS:
            reasons.append(
                f"execution duration is {delta:g}s (started_at == completed_at is not a real run)"
            )

    model = executor.get("model") or envelope.get("model")
    if not model:
        reasons.append("no model identity recorded")
    if kind and kind not in REAL_KINDS:
        reasons.append(f"unrecognised execution_kind={kind}")

    if reasons:
        return "NOT_EVIDENCED", reasons
    return "REAL", []


def audit_workspace(root: Path) -> dict:
    """Classify every recorded agent run in one paper workspace."""
    root = Path(root).resolve()
    runs_root = root / "agent_runs"
    tasks = []
    if runs_root.is_dir():
        for task_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
            for envelope_p in sorted(task_dir.glob("run-*.json")):
                try:
                    envelope = json.loads(envelope_p.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    tasks.append({
                        "task_id": task_dir.name,
                        "run": envelope_p.name,
                        "classification": "NOT_EVIDENCED",
                        "reasons": [f"unreadable envelope: {exc}"],
                    })
                    continue
                classification, reasons = classify_envelope(envelope)
                tasks.append({
                    "task_id": task_dir.name,
                    "run": envelope_p.name,
                    "classification": classification,
                    "reasons": reasons,
                })

    counts: dict[str, int] = {}
    for item in tasks:
        counts[item["classification"]] = counts.get(item["classification"], 0) + 1

    required = ("TASK-V3-LEAD-READING", "TASK-V3-LEAD-WRITING")
    lens_tasks = sorted({
        t["task_id"] for t in tasks if t["task_id"].startswith("TASK-V3-LENS-")
    })
    real_tasks = {t["task_id"] for t in tasks if t["classification"] == "REAL"}

    gaps = [name for name in required if name not in real_tasks]
    real_lenses = [name for name in lens_tasks if name in real_tasks]

    return {
        "workspace": str(root),
        "runs": tasks,
        "counts": counts,
        "lens_tasks_recorded": lens_tasks,
        "lens_tasks_with_real_execution": real_lenses,
        "missing_real_execution": gaps,
        "real_execution_verified": not gaps and bool(tasks),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="Paper workspace")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = audit_workspace(Path(args.out))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["real_execution_verified"] else 1

    print(f"workspace: {report['workspace']}")
    print(f"runs recorded: {sum(report['counts'].values())}")
    for label in ("REAL", "FIXTURE", "REPLAY", "NOT_EVIDENCED"):
        print(f"  {label:<14}: {report['counts'].get(label, 0)}")
    print(f"lens tasks recorded      : {len(report['lens_tasks_recorded'])}")
    print(f"lens tasks with real run : {len(report['lens_tasks_with_real_execution'])}")
    if report["missing_real_execution"]:
        print("\nmissing real execution for:")
        for name in report["missing_real_execution"]:
            print(f"  - {name}")
    suspect = [r for r in report["runs"] if r["classification"] != "REAL"]
    if suspect:
        print("\nnot accepted as scientific evidence:")
        for item in suspect[:15]:
            print(f"  - {item['task_id']}/{item['run']}: {item['classification']} ({item['reasons'][0] if item['reasons'] else ''})")
        if len(suspect) > 15:
            print(f"  ... and {len(suspect) - 15} more")
    print(f"\nreal execution verified: {report['real_execution_verified']}")
    return 0 if report["real_execution_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
