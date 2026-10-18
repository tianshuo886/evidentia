#!/usr/bin/env python3
"""Shrink committed eval fixtures without breaking the tests that use them (Issue #55).

The repository shipped ~1.5 GB of run artifacts. Almost none of it is needed to
verify the skill: `provenance/` is a per-Lens copy of `source_pages/` + `assets/`,
`source_pages/` is a rasterisation of the PDF, and `assets/` are crops of the same
pages. All three are regenerable from `source/paper.pdf` in seconds.

This script keeps the workspace *shape* (reader/, model/, lens_v3/, tasks/,
agent_runs/, source/) so contract tests still work, and drops the bulk.

Usage:
    python scripts/shrink_fixtures.py --dry-run     # report only
    python scripts/shrink_fixtures.py --apply       # delete
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Directories that are pure derivatives of source/paper.pdf.
REGENERABLE = ("provenance", "source_pages", "assets")
# Whole trees that no test reads and that only exist as a historical run dump.
EXPENDABLE_TREES = (
    "evals/reader_v3/fresh_ringmoclaw_run",
)
# Workspaces kept only for their PDF (equation extraction tests).
PDF_ONLY_WORKSPACES = (
    "reader-v3-runs/workspaces/BENCH-01-VASWANI-ATTENTION",
    "reader-v3-runs/workspaces/BENCH-03-REMOTE-SENSING-FOREST",
    "reader-v3-runs/workspaces/BENCH-05-QUANTUM-SUPREMACY-ABLATION",
)
# Workspaces whose full structure several contract tests copy.
STRUCTURE_WORKSPACES = (
    "reader-v3-runs/workspaces/BENCH-02-LORA-ADAPTATION",
    "reader-v3-runs/workspaces/BENCH-04-ALPHAFOLD2-STRUCTURE",
    "reader-v3-runs/workspaces/UNSEEN-01-RETHINKING-GENERALIZATION",
)
# Per-workspace exceptions: keep a regenerable directory because a test asserts
# on a concrete asset inside it.
KEEP_REGENERABLE = {
    ("reader-v3-runs/workspaces/BENCH-02-LORA-ADAPTATION", "assets"),
}


def _size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def _human(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def build_plan() -> list[tuple[Path, str]]:
    """Return (path, reason) pairs to remove."""
    plan: list[tuple[Path, str]] = []

    for rel in EXPENDABLE_TREES:
        p = ROOT / rel
        if p.exists():
            plan.append((p, "historical run dump, no test reads it"))

    for rel in STRUCTURE_WORKSPACES:
        base = ROOT / rel
        for sub in REGENERABLE:
            p = base / sub
            if not p.exists():
                continue
            if (rel, sub) in KEEP_REGENERABLE:
                continue
            plan.append((p, f"regenerable from source/paper.pdf ({sub})"))

    for rel in PDF_ONLY_WORKSPACES:
        base = ROOT / rel
        if not base.exists():
            continue
        for child in sorted(base.iterdir()):
            if child.name == "source":
                # keep source/paper.pdf, drop any supplements duplicates
                for inner in sorted(child.iterdir()):
                    if inner.name != "paper.pdf":
                        plan.append((inner, "duplicate source artifact"))
                continue
            plan.append((child, "workspace kept only for its source PDF"))

    return plan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Actually delete (default is dry run)")
    args = ap.parse_args()

    plan = build_plan()
    before = _size(ROOT / "reader-v3-runs") + _size(ROOT / "evals")
    total = sum(_size(p) for p, _ in plan)

    print(f"repository fixture size : {_human(before)}")
    print(f"reclaimable             : {_human(total)} in {len(plan)} item(s)")
    print()
    for p, reason in plan:
        print(f"  {_human(_size(p)):>10}  {p.relative_to(ROOT)}  ({reason})")

    if not args.apply:
        print("\n(dry run: pass --apply to delete)")
        return 0

    failed = []
    for p, _ in plan:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
        except OSError as exc:
            failed.append(f"{p.relative_to(ROOT)}: {exc}")

    after = _size(ROOT / "reader-v3-runs") + _size(ROOT / "evals")
    print(f"\nafter                   : {_human(after)}")
    print(f"saved                   : {_human(before - after)}")
    if failed:
        print("\nfailed to remove:")
        for f in failed:
            print(f"  {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
