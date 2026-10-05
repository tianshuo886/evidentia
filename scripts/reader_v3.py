#!/usr/bin/env python3
"""Reader v3 stateful orchestration.

This pipeline intentionally coexists with the legacy Reader until real-paper A/B
evaluation passes. It never invokes deterministic scientific synthesis or the
legacy narrative composer.
"""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, schema_validate
from reader_v3_protocol import (
    create_lead_reader_task, create_lens_tasks,
    create_revision_memo_task, create_narrative_plan_task, create_lead_writer_task,
)


INTERNAL_MARKERS = (
    "Author Lens", "Reviewer Lens", "Mechanism Lens", "Builder Lens",
    "Anomaly Lens", "Counterfactual Lens", "Lens Council", "Council Chair",
    "Revision Memo", "TASK-V3", "lens_v3", "schema_version", "source_sha256", "O/I/A"
)


def _allowed_evidence_ids(root: Path):
    allowed = set()
    inv_p = root / "model/figure_inventory.json"
    if inv_p.exists():
        for item in load_json(inv_p).get("items", []):
            if item.get("id"):
                allowed.add(str(item["id"]))
    sm_p = root / "model/source_map.json"
    if sm_p.exists():
        for page in load_json(sm_p).get("pages", []):
            n = page.get("number")
            if n is not None:
                allowed.add(f"p.{n}")
            for eq in page.get("equations", []) if isinstance(page.get("equations", []), list) else []:
                if isinstance(eq, dict) and eq.get("equation_id"):
                    allowed.add(str(eq["equation_id"]))
    return allowed


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_strings(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _walk_strings(value)


def _validate_v3_manuscript(root: Path, data: dict):
    errors = list(schema_validate(data, "narrative_manuscript"))
    plan_ref = data.get("narrative_plan_ref")
    if plan_ref:
        plan_path = root / plan_ref
        if not plan_path.exists():
            errors.append(f"narrative plan is missing: {plan_ref}")
        else:
            plan = load_json(plan_path)
            errors.extend(schema_validate(plan, "narrative_plan"))
            if plan.get("source_sha256") != data.get("source_sha256"):
                errors.append("narrative plan source_sha256 does not match manuscript")
            planned_ids = [str(x.get("id")) for x in plan.get("sections", [])]
            document = data.get("document", {})
            output_sections = document.get("sections") or document.get("chapters", [])
            output_ids = [str(x.get("id")) for x in output_sections]
            if planned_ids and output_ids[:len(planned_ids)] != planned_ids:
                errors.append("Lead Writer section order does not preserve the Dynamic Narrative Plan")
    visible_text = "\n".join(_walk_strings(data.get("document", {})))
    for marker in INTERNAL_MARKERS:
        if marker in visible_text:
            errors.append(f"internal Reader-v3 vocabulary leaked into primary narrative: {marker}")

    allowed = _allowed_evidence_ids(root)
    document = data.get("document", {})
    chapters = document.get("sections") or document.get("chapters", [])
    for chapter in chapters:
        chapter_refs = set()
        for block in chapter.get("blocks", []):
            refs = [str(x) for x in (block.get("evidence_refs") or []) if x]
            if block.get("evidence_id"):
                refs.append(str(block["evidence_id"]))
            chapter_refs.update(refs)
            for ref in refs:
                if ref not in allowed:
                    errors.append(f"unknown source evidence reference {ref!r} in chapter {chapter.get('id')}")
            if block.get("presentation_role") == "audit_only":
                errors.append(f"audit_only evidence leaked into primary Reader: {block.get('evidence_id')}")
            if block.get("type") in ("figure", "table"):
                asset = block.get("asset")
                if block.get("presentation_role") != "uncertain":
                    if not asset:
                        errors.append(f"{block.get('type')} {block.get('evidence_id')} has no bound asset")
                    elif not (root / asset).exists():
                        errors.append(f"{block.get('type')} {block.get('evidence_id')} asset does not exist: {asset}")
        if not chapter_refs:
            errors.append(f"section {chapter.get('id')} contains no source evidence references")
    return errors



def _status(root: Path) -> dict:
    out = {
        "source_ready": (root / "source/paper.pdf").exists(),
        "lead_reader": (root / "model/paper_understanding_draft.json").exists(),
        "lens_manifest": (root / "model/lens_v3_manifest.json").exists(),
        "revision_memo": (root / "model/revision_memo.json").exists(),
        "narrative_plan": (root / "model/narrative_plan.json").exists(),
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


def prepare_next(root: Path) -> Optional[Path]:
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
    if not st["narrative_plan"]:
        return create_narrative_plan_task(root)
    if not st["lead_writer"]:
        return create_lead_writer_task(root)
    return None


def render(root: Path):
    manuscript = root / "reader/narrative_manuscript.json"
    if not manuscript.exists():
        raise FileNotFoundError("Lead Writer manuscript is required before rendering")
    manuscript_data = load_json(manuscript)
    errs = _validate_v3_manuscript(root, manuscript_data)
    if errs:
        raise ValueError("Lead Writer manuscript failed Reader v3 integrity checks:\n" + "\n".join(errs))
    # Render directly from the Lead Writer manuscript. Do NOT call render_reader,
    # because the legacy orchestrator would overwrite it with deterministic composition.
    from render_paper_reader import render_paper_reader
    from render_evidence_atlas_v3 import render as render_evidence_atlas_v3
    render_paper_reader(root)
    render_evidence_atlas_v3(root)
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
