#!/usr/bin/env python3
"""Apply vision-verified page bindings to the canonical figure inventory.

Vision results use normalized full-page coordinates. This deterministic stage
only converts coordinates/crops pixels and updates provenance; it does not make
scientific localization decisions.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from validate_common import load_json, schema_validate, sha256


def _safe_id(value):
    return re.sub(r"[^A-Za-z0-9_.-]+","_",str(value))


def apply(root: Path, dpi: int=220):
    root=Path(root)
    pdf_p=root/"source/paper.pdf"
    inv_p=root/"model/figure_inventory.json"
    if not pdf_p.exists() or not inv_p.exists():
        raise FileNotFoundError("source paper and figure inventory are required")
    try:
        import fitz
    except ImportError:
        raise SystemExit("PyMuPDF is required")
    inv=load_json(inv_p)
    results={}
    for p in sorted((root/"visual").glob("page-*.json")) if (root/"visual").exists() else []:
        payload=load_json(p)
        errs=schema_validate(payload,"visual_page_verification")
        if errs:
            raise ValueError(f"{p} failed schema validation: {errs}")
        if payload.get("source_sha256") != sha256(pdf_p):
            raise ValueError(f"{p} source hash mismatch")
        for b in payload.get("bindings",[]):
            results[b["evidence_id"]] = (int(payload["page"]), b)

    doc=fitz.open(str(pdf_p))
    assets=root/"assets/figures"
    assets.mkdir(parents=True,exist_ok=True)
    applied=0
    for item in inv.get("items",[]):
        eid=item.get("id")
        if eid not in results:
            continue
        page_no,b=results[eid]
        item["vision_verification_status"]=b["status"]
        item["vision_caption_match"]=b["caption_match"]
        item["vision_complete"]=b["complete"]
        item["vision_notes"]=b.get("notes")
        item["panel_bboxes_norm"]=b.get("panel_bboxes_norm",[])
        item["localization_confidence"]=b["confidence"]
        if b["status"]!="VERIFIED" or not b["complete"] or not b["caption_match"]:
            item["inspection_status"]="NEEDS_REVIEW"
            item["needs_visual_review"]=True
            item["needs_review"]=True
            continue

        page=doc[page_no-1]
        x0,y0,x1,y1=b["bbox_norm"]
        rect=fitz.Rect(
            page.rect.x0 + x0*page.rect.width,
            page.rect.y0 + y0*page.rect.height,
            page.rect.x0 + x1*page.rect.width,
            page.rect.y0 + y1*page.rect.height,
        )
        if rect.width < 20 or rect.height < 20:
            item["inspection_status"]="NEEDS_REVIEW"
            item["needs_visual_review"]=True
            item["review_note"]="Vision bbox became degenerate after coordinate conversion."
            continue
        pix=page.get_pixmap(dpi=dpi,alpha=False,clip=rect)
        fn=f"v3_{_safe_id(eid)}_p{page_no}_{pix.width}x{pix.height}.png"
        out=assets/fn
        pix.save(str(out))
        item["figure_bbox"]=[rect.x0,rect.y0,rect.x1,rect.y1]
        item["file"]=f"assets/figures/{fn}"
        item["asset"]=item["file"]
        item["extraction_method"]="vision_verified_crop"
        item["binding_method"]="VISION_VERIFIED_PAGE_LOCALIZATION"
        item["localization_method"]="VISION_VERIFIED_PAGE_LOCALIZATION"
        item["binding_confidence"]=b["confidence"]
        item["inspection_status"]="VERIFIED"
        item["needs_visual_review"]=False
        item["needs_review"]=False
        item["review_note"]="Verified from full-page semantic localization."
        applied+=1

    inv["visual_v3"]={
        "source_sha256":sha256(pdf_p),
        "verified_bindings_applied":applied,
        "semantic_localization":True,
        "geometry_is_candidate_only":True
    }
    inv_p.write_text(json.dumps(inv,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"OK: applied {applied} vision-verified bindings -> {inv_p}")


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--dpi",type=int,default=220);args=ap.parse_args()
    apply(Path(args.out),dpi=args.dpi)


if __name__=="__main__":
    main()
