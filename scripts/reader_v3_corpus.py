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

from paper_acquire_bridge import acquire_paper, validate_full_pdf
from reader_v3_protocol import create_lead_reader_task
from reader_v3_benchmark import create_direct_task
from validate_common import load_json, sha256
from visual_localization_protocol import create_visual_tasks

ACTIVE_DEVELOPMENT_PAPER = "BENCH-01-VASWANI-ATTENTION"
# The registry DOI for BENCH-03 resolves to an unrelated Remote Sensing of
# Environment article. This explicit, documented identifier correction keeps
# the registry entry authoritative without silently swapping the paper.
IDENTIFIER_OVERRIDES = {
    "BENCH-03-REMOTE-SENSING-FOREST": {
        "identifier": "10.48550/arXiv.2204.08322",
        "reason": "registry DOI 10.1016/j.rse.2022.113070 resolves to an unrelated land-surface-temperature paper; arXiv preprint title/authors match the registered canopy-height work"
    }
}


def _run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


def _write_benchmark_manifest(workspace: Path, paper: dict, source_pdf: Path, acquisition: dict) -> dict:
    """Persist the registry identity and immutable source/contract boundary."""
    source_sha = sha256(source_pdf)
    sha_path = workspace / "source/source_sha256.txt"
    if sha_path.exists() and sha_path.read_text(encoding="utf-8").strip() != source_sha:
        raise ValueError(f"Immutable source SHA changed for {paper['id']}")
    sha_path.write_text(source_sha + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "benchmark_id": paper["id"],
        "registry_version": "1.0",
        "registry_entry": paper,
        "identifier": paper.get("open_access_doi"),
        "resolved_identifier": (acquisition or {}).get("identifier") or paper.get("open_access_doi"),
        "identifier_discrepancy": (acquisition or {}).get("identifier_discrepancy"),
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "source_url": (acquisition or {}).get("source_url"),
        "acquisition_provenance": acquisition or {},
        "source_sha256": source_sha,
        "current_benchmark_contract": {
            "condition": "DIRECT_AI",
            "contract_version": "3.0",
            "prompt_version": "3.0",
            "source_policy": "REAL_PUBLIC_FULL_PDF_ONLY",
            "allowed_inputs": ["source/paper.pdf"],
            "forbidden_inputs": ["model/", "lens/", "lens_v3/", "reader/", "apply/", "project/", "memory/"],
            "output_schema": "direct_reading_baseline",
            "envelope_schema": "agent_result_envelope"
        }
    }
    manifest_path = workspace / "model/benchmark_manifest.json"
    if manifest_path.exists():
        old = load_json(manifest_path)
        if old.get("source_sha256") != source_sha:
            raise ValueError(f"Benchmark manifest source SHA mismatch for {paper['id']}")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (workspace / "acquisition_metadata.json").write_text(
        json.dumps(acquisition or {}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


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
    correction = IDENTIFIER_OVERRIDES.get(pid)
    identifier = correction["identifier"] if correction else paper.get("open_access_doi")
    if source_pdf.exists():
        validate_full_pdf(source_pdf)
        meta = load_json(workspace / "acquisition_metadata.json") if (workspace / "acquisition_metadata.json").exists() else {
            "identifier": identifier,
            "source_type": "EXISTING_WORKSPACE"
        }
    else:
        if not identifier:
            return {"id": pid, "status": "BLOCKED_NO_IDENTIFIER", "workspace": str(workspace)}
        acquired, meta = acquire_paper(
            identifier, out_dir=workspace, target_pdf_path=source_pdf, require_full_pdf=True
        )
        if correction:
            meta["registry_identifier"] = paper.get("open_access_doi")
            meta["identifier_discrepancy"] = correction["reason"]
        if Path(acquired) != source_pdf and Path(acquired).exists():
            source_pdf.write_bytes(Path(acquired).read_bytes())
        validate_full_pdf(source_pdf)

    manifest = _write_benchmark_manifest(workspace, paper, source_pdf, meta)
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

    # Keep equations explicit as a source-side inventory without starting any
    # semantic Reader work.
    source_data = load_json(source_map)
    equation_inventory = {
        "schema_version": "1.0",
        "source_sha256": manifest["source_sha256"],
        "equations": [eq for page in source_data.get("pages", []) for eq in page.get("equations", [])]
    }
    (model_dir / "equation_inventory.json").write_text(
        json.dumps(equation_inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    visual_tasks = create_visual_tasks(workspace)
    lead_task = create_lead_reader_task(workspace)
    direct_task = create_direct_task(workspace)

    return {
        "id": pid,
        "title": paper.get("title"),
        "category": paper.get("category"),
        "workspace": str(workspace),
        "status": "TASKS_READY",
        "source_sha256": manifest["source_sha256"],
        "source_pages": len(list((workspace / "source_pages").glob("page-*.png"))),
        "visual_tasks": len(visual_tasks),
        "equations": len(equation_inventory["equations"]),
        "lead_reader_task": str(lead_task.relative_to(workspace)),
        "direct_task": str(direct_task.relative_to(workspace)),
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
    if selected:
        papers = [p for p in corpus.get("papers", []) if p.get("id") in selected]
    else:
        # Never accidentally prepare the already-active smoke paper through the
        # four-paper development-corpus command.
        papers = [p for p in corpus.get("papers", []) if p.get("id") != ACTIVE_DEVELOPMENT_PAPER]
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
