#!/usr/bin/env python3
"""Reader v3 stateful orchestration.

This pipeline intentionally coexists with the legacy Reader until real-paper A/B
evaluation passes. It never invokes deterministic scientific synthesis or the
legacy narrative composer.
"""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, schema_validate
from reader_v3_protocol import (
    create_lead_reader_task, create_lens_tasks,
    create_revision_memo_task, create_lead_writer_task,
)


def _status(root: Path) -> dict:
    out = {
        "source_ready": (root / "source/paper.pdf").exists(),
        "lead_reader": (root / "model/paper_understanding_draft.json").exists(),
        "lens_manifest": (root / "model/lens_v3_manifest.json").exists(),
        "revision_memo": (root / "model/revision_memo.json").exists(),
        "lead_writer": (root / "reader/narrative_manuscript.json").exists(),
        "rendered": (root / "reader/paper_reader.html").exists(),
    }
    if out["lens_manifest"]:
        man = load_json(root / "model/lens_v3_manifest.json")
        out["lenses"] = {x["id"]: (root / f"lens_v3/{x['id']}.json").exists() for x in man.get("lenses", [])}
        out["all_lenses"] = bool(out["lenses"]) and all(out["lenses"].values())
    else:
        out["lenses"] = {}
        out["all_lenses"] = False
    return out


def prepare_next(root: Path) -> Path | None:
    st = _status(root)
    if not st["source_ready"]:
        raise FileNotFoundError("Reader v3 requires an initialized workspace with source/paper.pdf")
    if not st["lead_reader"]:
        return create_lead_reader_task(root)
    if not st["lens_manifest"]:
        tasks = create_lens_tasks(root)
        return tasks[0] if tasks else None
    if not st["all_lenses"]:
        return None
    if not st["revision_memo"]:
        return create_revision_memo_task(root)
    if not st["lead_writer"]:
        return create_lead_writer_task(root)
    return None


def render(root: Path):
    manuscript = root / "reader/narrative_manuscript.json"
    if not manuscript.exists():
        raise FileNotFoundError("Lead Writer manuscript is required before rendering")
    errs = schema_validate(load_json(manuscript), "narrative_manuscript")
    if errs:
        raise ValueError("Lead Writer manuscript failed schema validation:\n" + "\n".join(errs))
    # Render directly from the Lead Writer manuscript. Do NOT call render_reader,
    # because the legacy orchestrator would overwrite it with deterministic composition.
    from render_paper_reader import render_paper_reader
    from render_evidence_atlas import render_evidence_atlas
    render_paper_reader(root)
    render_evidence_atlas(root)
    rdir = root / "reader"
    for src, dst in (("paper_reader.html", "reader.html"), ("paper_reader.md", "reader.md"), ("paper_reader.pdf", "reader.pdf")):
        s = rdir / src
        if s.exists():
            shutil.copy2(s, rdir / dst)
    print(f"OK: Reader v3 rendered from strong-model manuscript -> {rdir / 'paper_reader.html'}")


def main():
    ap = argparse.ArgumentParser(description="Evidentia Reader v3")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "status", "render"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.out)

    if args.cmd == "status":
        print(json.dumps(_status(root), indent=2, ensure_ascii=False))
    elif args.cmd == "prepare":
        task = prepare_next(root)
        if task:
            print(f"NEXT_TASK={task}")
        else:
            st = _status(root)
            if st["lens_manifest"] and not st["all_lenses"]:
                missing = [x for x, ok in st["lenses"].items() if not ok]
                print("WAITING_FOR_LENSES=" + ",".join(missing))
            elif st["lead_writer"]:
                print("READY_TO_RENDER")
            else:
                print("NO_ACTION")
    elif args.cmd == "render":
        render(root)


if __name__ == "__main__":
    main()
