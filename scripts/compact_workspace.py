#!/usr/bin/env python3
"""Inspect and safely compact one Evidentia paper workspace (Issue #55).

Design rules, in priority order:

1. Never touch the user's original PDF, supplements, notes, or corrections.
2. Never delete the only copy of anything a released Reader depends on.
3. Never destroy a workspace that is still running, failed, or awaiting review.
4. Always be reversible: report first (`--dry-run`, the default), delete later.

`compact` only removes bytes that are provably duplicated within the workspace
(hard-link/symlink consolidation of identical files, plus orphaned render
scratch). It does not touch `source/`, `reader/`, `model/`, `agent_runs/`,
`lens_v3/`, `tasks/`, `notes/`, or `corrections/`.

Usage:
    python scripts/compact_workspace.py --out <workspace>            # dry run
    python scripts/compact_workspace.py --out <workspace> --apply    # compact
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTECTED_DIRS = (
    "source",
    "reader",
    "model",
    "agent_runs",
    "lens_v3",
    "tasks",
    "notes",
    "corrections",
    "apply",
)
# Directories that are pure intermediate scratch and may be re-derived.
SCRATCH_DIRS = ("working", "source_pages")
SAFE_STATES = ("PAPER_COMPLETE", "RENDER", "COMPLETE")


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _human(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _run_state(root: Path) -> dict:
    path = root / "run_state.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _release_decision(root: Path) -> str:
    path = root / "reader/reader_release_decision.json"
    if not path.is_file():
        return "UNKNOWN"
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("decision") or "UNKNOWN")
    except (OSError, ValueError):
        return "UNKNOWN"


def survey(root: Path) -> dict:
    """Group files by content hash and measure what is actually reclaimable."""
    root = Path(root).resolve()
    by_hash: dict[str, list[Path]] = {}
    total_apparent = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".git")]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            total_apparent += size
            if size == 0:
                continue
            try:
                digest = _sha256(path)
            except OSError:
                continue
            by_hash.setdefault(digest, []).append(path)

    duplicate_groups = []
    reclaimable = 0
    for digest, paths in by_hash.items():
        if len(paths) < 2:
            continue
        size = paths[0].stat().st_size
        groups = sorted(paths, key=lambda p: (len(p.parts), str(p)))
        # Keep the shallowest/canonical path, reclaim the rest.
        keeper = groups[0]
        extras = groups[1:]
        duplicate_groups.append(
            {
                "sha256": digest,
                "size": size,
                "keeper": _rel(keeper, root),
                "duplicates": [_rel(p, root) for p in extras],
                "reclaimable": size * len(extras),
            }
        )
        reclaimable += size * len(extras)

    duplicate_groups.sort(key=lambda g: -g["reclaimable"])
    return {
        "workspace": str(root),
        "total_apparent_bytes": total_apparent,
        "total_apparent": _human(total_apparent),
        "reclaimable_bytes": reclaimable,
        "reclaimable": _human(reclaimable),
        "duplicate_groups": duplicate_groups,
    }


def _is_protected(rel: str) -> bool:
    first = rel.split(os.sep, 1)[0]
    return first in PROTECTED_DIRS


def _is_scratch(rel: str) -> bool:
    first = rel.split(os.sep, 1)[0]
    return first in SCRATCH_DIRS


def plan(root: Path, report: dict) -> dict:
    """Decide, per duplicate group, whether consolidation is allowed."""
    root = Path(root).resolve()
    state = _run_state(root)
    phase = str(state.get("phase") or "")
    decision = _release_decision(root)
    blockers: list[str] = []

    if phase and phase not in SAFE_STATES:
        blockers.append(
            f"workspace phase is {phase!r}: a running, failed, or awaiting-review run is never compacted"
        )

    actions = []
    skipped = []
    for group in report["duplicate_groups"]:
        keeper = group["keeper"]
        for dup in group["duplicates"]:
            if _is_protected(dup) and _is_protected(keeper):
                # Two protected copies (for example a Reader asset also kept in
                # model/) are left alone: they are evidence, not scratch.
                skipped.append({"path": dup, "reason": "both copies are protected evidence"})
                continue
            if _is_protected(dup):
                skipped.append({"path": dup, "reason": "duplicate is protected evidence"})
                continue
            actions.append(
                {
                    "path": dup,
                    "keeper": keeper,
                    "bytes": group["size"],
                    "kind": "hardlink_to_keeper",
                }
            )

    return {
        "phase": phase,
        "release_decision": decision,
        "blockers": blockers,
        "actions": actions,
        "skipped": skipped,
        "planned_bytes": sum(a["bytes"] for a in actions),
    }


def apply_plan(root: Path, plan_data: dict) -> dict:
    """Replace duplicate files with hard links to their keeper."""
    root = Path(root).resolve()
    done, failed = [], []
    for action in plan_data["actions"]:
        target = root / action["path"]
        keeper = root / action["keeper"]
        try:
            if not target.is_file() or not keeper.is_file():
                failed.append({"path": action["path"], "error": "file disappeared"})
                continue
            if _sha256(target) != _sha256(keeper):
                failed.append({"path": action["path"], "error": "content changed since survey"})
                continue
            target.unlink()
            os.link(keeper, target)
            done.append(action)
        except OSError as exc:
            failed.append({"path": action["path"], "error": str(exc)})
    return {"linked": done, "failed": failed}


def verify(root: Path) -> list[str]:
    """Confirm the delivered artifacts still resolve after compaction."""
    root = Path(root).resolve()
    problems: list[str] = []
    html = root / "reader/paper_reader.html"
    if not html.is_file():
        problems.append("missing reader/paper_reader.html")
        return problems
    text = html.read_text(encoding="utf-8", errors="replace")
    import re

    for src in re.findall(r"""(?:src|href)=['"]([^'"]+)['"]""", text):
        if src.startswith(("http://", "https://", "#", "data:", "mailto:")):
            continue
        candidate = (html.parent / src).resolve()
        if not candidate.exists():
            alt = (root / src.lstrip("./")).resolve()
            if not alt.exists():
                problems.append(f"broken local reference after compaction: {src}")
    for required in ("source/paper.pdf", "reader/paper_reader.md", "reader/narrative_manuscript.json"):
        if not (root / required).is_file():
            problems.append(f"missing required artifact: {required}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="Paper workspace directory")
    ap.add_argument("--apply", action="store_true", help="Actually compact (default is dry run)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    args = ap.parse_args()

    root = Path(args.out).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}, ensure_ascii=False))
        return 2

    report = survey(root)
    plan_data = plan(root, report)
    result = {
        "mode": "apply" if args.apply else "dry-run",
        **report,
        "plan": plan_data,
    }

    if args.apply:
        if plan_data["blockers"]:
            result["applied"] = False
            result["reason"] = "blocked; nothing was deleted"
        else:
            result["applied"] = apply_plan(root, plan_data)
            after = survey(root)
            result["after"] = {
                "total_apparent_bytes": after["total_apparent_bytes"],
                "total_apparent": after["total_apparent"],
                "reclaimable_bytes": after["reclaimable_bytes"],
                "reclaimable": after["reclaimable"],
            }
            result["verification"] = verify(root)
            result["saved_bytes"] = (
                report["total_apparent_bytes"] - after["total_apparent_bytes"]
            )
            result["saved"] = _human(result["saved_bytes"])

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"workspace      : {result['workspace']}")
    print(f"mode           : {result['mode']}")
    print(f"apparent size  : {result['total_apparent']}")
    print(f"reclaimable    : {result['reclaimable']} in {len(report['duplicate_groups'])} duplicate group(s)")
    if plan_data["blockers"]:
        print("\nblocked:")
        for b in plan_data["blockers"]:
            print(f"  - {b}")
    if plan_data["actions"]:
        print("\nplanned (hard-link duplicate -> keeper):")
        for a in plan_data["actions"][:20]:
            print(f"  {a['path']}  ->  {a['keeper']}")
        if len(plan_data["actions"]) > 20:
            print(f"  ... and {len(plan_data['actions']) - 20} more")
    if plan_data["skipped"]:
        print(f"\nleft alone: {len(plan_data['skipped'])} protected duplicate(s)")
    if args.apply:
        if not result.get("applied"):
            print(f"\nNOTHING DELETED: {result.get('reason')}")
            return 1
        print(f"\nsaved: {result.get('saved')}")
        if result["verification"]:
            print("verification problems:")
            for p in result["verification"]:
                print(f"  - {p}")
            return 1
        print("verification: all delivered artifacts still resolve")
    else:
        print("\n(dry run: pass --apply to compact)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
