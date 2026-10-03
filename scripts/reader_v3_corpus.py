#!/usr/bin/env python3
"""Prepare the real-paper Reader v3 development corpus.

This runner uses evals/real_corpus/benchmark_papers.json as the development set.
It prepares source reconstruction, visual-localization tasks, and the Lead Reader
task. It does not fabricate model outputs or claim empirical completion.

A separate unseen paper must still be added after architecture freeze.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from paper_acquire_bridge import acquire_paper
from reader_v3_protocol import create_lead_reader_task
from visual_localization_protocol import create_visual_tasks


def _run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


def prepare_one(paper: dict, work_root: Path) -> dict:
    pid = paper["id"]
    workspace = work_root / pid
    source_dir = workspace / "source"
    model_dir = workspace / "model"
    assets_dir = workspace / "assets/figures"
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    source_pdf = source_dir / "paper.pdf"
    if not source_pdf.exists():
        identifier = paper.get("open_access_doi")
        if not identifier:
            return {"id": pid, "status": "BLOCKED_NO_IDENTIFIER", "workspace": str(workspace)}
        acquired, meta = acquire_paper(identifier, out_dir=workspace, target_pdf_path=source_pdf)
        if Path(acquired) != source_pdf and Path(acquired).exists():
            source_pdf.write_bytes(Path(acquired).read_bytes())
        (workspace / "acquisition_metadata.json").write_text(
            json.dumps(meta or {}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    source_map = model_dir / "source_map.json"
    inventory = model_dir / "figure_inventory.json"
    if not source_map.exists():
        _run(HERE / "extract_structure.py", "--pdf", source_pdf, "--out", source_map)
    if not inventory.exists():
        _run(
            HERE / "extract_figs.py",
            "--pdf", source_pdf,
            "--out", assets_dir,
            "--inventory", inventory,
        )
    _run(HERE / "link_mentions.py", "--source-map", source_map, "--inventory", inventory)

    visual_tasks = create_visual_tasks(workspace)
    lead_task = create_lead_reader_task(workspace)

    return {
        "id": pid,
        "title": paper.get("title"),
        "category": paper.get("category"),
        "workspace": str(workspace),
        "status": "TASKS_READY",
        "visual_tasks": len(visual_tasks),
        "lead_reader_task": str(lead_task.relative_to(workspace)),
    }


def main():
    ap = argparse.ArgumentParser(description="Prepare Reader v3 real-paper development corpus")
    ap.add_argument(
        "--corpus",
        default=str(ROOT / "evals/real_corpus/benchmark_papers.json"),
        help="Corpus metadata JSON",
    )
    ap.add_argument(
        "--work-root",
        default=str(ROOT / "evals/reader_v3/workspaces"),
        help="Workspace root",
    )
    ap.add_argument("--id", action="append", dest="ids", help="Prepare only selected benchmark ID(s)")
    args = ap.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    selected = set(args.ids or [])
    papers = [p for p in corpus.get("papers", []) if not selected or p.get("id") in selected]
    work_root = Path(args.work_root)
    work_root.mkdir(parents=True, exist_ok=True)

    results = []
    for paper in papers:
        try:
            results.append(prepare_one(paper, work_root))
        except Exception as exc:
            results.append({
                "id": paper.get("id"),
                "title": paper.get("title"),
                "status": "PREPARE_FAILED",
                "error": str(exc),
            })

    manifest = {
        "schema_version": "3.0",
        "purpose": "Reader v3 real-paper development corpus",
        "truth_level": "REAL_PAPERS_TASKS_PREPARED",
        "unseen_paper_required": True,
        "papers": results,
    }
    out = work_root.parent / "corpus_prepare_report.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))

    if any(x.get("status") == "PREPARE_FAILED" for x in results):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
