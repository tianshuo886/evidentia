#!/usr/bin/env python3
"""Reader v3 page-first multimodal visual localization protocol.

The legacy PDF geometry extractor remains a candidate generator. These tasks ask
a vision-capable host agent to inspect the rendered full page and decide the
canonical figure/table region semantically.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from validate_common import load_json, sha256
from task_protocol import validate_and_write_task
from executor_meta import build_executor_metadata


def create_visual_tasks(root: Path) -> list[Path]:
    root=Path(root)
    pdf=root/"source/paper.pdf"
    inv_p=root/"model/figure_inventory.json"
    if not pdf.exists() or not inv_p.exists():
        raise FileNotFoundError("source/paper.pdf and model/figure_inventory.json are required")
    inv=load_json(inv_p)
    by_page={}
    for item in inv.get("items",[]):
        if not item.get("id") or not item.get("page"):
            continue
        by_page.setdefault(int(item["page"]),[]).append({
            "evidence_id":item["id"],
            "kind":item.get("kind"),
            "paper_label":item.get("paper_label"),
            "caption_original":item.get("caption_original"),
            "candidate_bbox_pdf":item.get("figure_bbox"),
            "candidate_asset":item.get("file"),
            "candidate_method":item.get("localization_method") or item.get("binding_method"),
            "candidate_confidence":item.get("localization_confidence") or item.get("binding_confidence")
        })
    tasks=[]
    for page, candidates in sorted(by_page.items()):
        page_rel=f"source_pages/page-{page:03d}.png"
        if not (root/page_rel).exists():
            continue
        task={
            "task_id":f"TASK-V3-VISUAL-P{page:03d}",
            "task_type":"VISUAL_LOCALIZATION",
            "required_capability":"VISUAL_EVIDENCE_LOCALIZATION",
            "scientific_contract":"Inspect the full rendered PDF page and semantically bind each requested Figure/Table to its complete visual region.",
            "description":f"Reader v3 semantic visual localization for source page {page}.",
            "input_artifacts":{
                "source_page":page_rel,
                "source_pdf":"source/paper.pdf",
                "page":page,
                "candidates":candidates
            },
            "target_output":f"visual/page-{page:03d}.json",
            "output_schema":"visual_page_verification",
            "source_sha256":sha256(pdf),
            "base_sha256":None,
            "contract_version":"3.0",
            "prompt_version":"3.0",
            "allowed_inputs":["source/paper.pdf",page_rel,"model/figure_inventory.json"],
            "forbidden_inputs":["apply/","project/","memory/project/","lens/","lens_v3/"],
            "prohibited_context":["PROJECT_APPLY","RESEARCH_MEMORY"],
            "constraints":["FULL_PAGE_SEMANTIC_LOCALIZATION","NO_WHOLE_PAGE_FALLBACK","CAPTION_SEMANTIC_MATCH","MULTI_PANEL_AWARE"],
            "instructions":(
                "Inspect the complete page image, not only PDF object geometry. For every candidate evidence_id, "
                "identify the complete visual region corresponding to its caption. Return bbox_norm=[x0,y0,x1,y1] "
                "in normalized page coordinates 0..1. A multi-panel figure should use one bbox covering the complete "
                "figure and panel_bboxes_norm for meaningful panels when identifiable. Mark VERIFIED only when the "
                "crop is complete and the caption semantically matches. Reject caption-only, body-text-heavy, partial "
                "panel, unrelated image, and whole-page regions. If uncertain, return NEEDS_REVIEW rather than guessing."
            ),
            "executor_template":build_executor_metadata()
        }
        tasks.append(validate_and_write_task(task,root/f"tasks/v3/visual/page-{page:03d}.json"))
    manifest={"schema_version":"3.0","source_sha256":sha256(pdf),"tasks":[str(p.relative_to(root)) for p in tasks]}
    (root/"model/visual_v3_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return tasks


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args()
    tasks=create_visual_tasks(Path(args.out))
    print(f"created {len(tasks)} semantic visual-localization tasks")


if __name__=="__main__":
    main()
