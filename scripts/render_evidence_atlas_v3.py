#!/usr/bin/env python3
"""Render a Reader-v3 provenance atlas without depending on the legacy Paper Model.

The atlas is deliberately secondary. It exposes source identity, page/caption,
asset, verification state, and where each evidence item is used in the human
Reader. It does not author scientific conclusions.
"""
from __future__ import annotations
import argparse, html, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from validate_common import load_json


def _esc(x):
    return html.escape(str(x or ""))


def build_atlas(root: Path) -> dict:
    root=Path(root)
    manuscript=load_json(root/"reader/narrative_manuscript.json")
    inv=load_json(root/"model/figure_inventory.json") if (root/"model/figure_inventory.json").exists() else {"items":[]}
    sm=load_json(root/"model/source_map.json") if (root/"model/source_map.json").exists() else {"pages":[]}

    usage={}
    for ch in manuscript.get("document",{}).get("chapters",[]):
        for block in ch.get("blocks",[]):
            refs=list(block.get("evidence_refs",[]) or [])
            if block.get("evidence_id"):
                refs.append(block["evidence_id"])
            for ref in refs:
                usage.setdefault(str(ref),[]).append({
                    "chapter_id":ch.get("id"),
                    "chapter_title":ch.get("title"),
                    "block_type":block.get("type")
                })

    items=[]
    seen=set()
    for item in inv.get("items",[]):
        eid=str(item.get("id") or "")
        if not eid:
            continue
        seen.add(eid)
        items.append({
            "id":eid,
            "kind":item.get("kind","visual"),
            "page":item.get("page"),
            "label":item.get("paper_label"),
            "caption":item.get("caption_original"),
            "asset":item.get("file") or item.get("asset"),
            "verification_status":item.get("vision_verification_status") or item.get("inspection_status"),
            "confidence":item.get("localization_confidence") or item.get("binding_confidence"),
            "used_in":usage.get(eid,[])
        })

    for page in sm.get("pages",[]):
        pno=page.get("number")
        pid=f"p.{pno}"
        if pid not in seen:
            items.append({
                "id":pid,"kind":"page","page":pno,"label":pid,
                "caption":None,"asset":f"source_pages/page-{int(pno):03d}.png" if pno else None,
                "verification_status":"SOURCE_PAGE","confidence":1.0,
                "used_in":usage.get(pid,[])
            })
        for eq in page.get("equations",[]) if isinstance(page.get("equations",[]),list) else []:
            if not isinstance(eq,dict) or not eq.get("equation_id"):
                continue
            eid=str(eq["equation_id"])
            items.append({
                "id":eid,"kind":"equation","page":eq.get("page",pno),"label":eid,
                "caption":eq.get("raw_text") or eq.get("latex"),
                "asset":eq.get("fallback_asset"),
                "verification_status":eq.get("source_confidence","UNCERTAIN"),
                "confidence":None,"used_in":usage.get(eid,[])
            })

    return {
        "schema_version":"3.0",
        "paper_id":manuscript.get("paper_id",root.name),
        "source_sha256":manuscript.get("source_sha256",""),
        "items":items
    }


def render(root: Path):
    root=Path(root)
    atlas=build_atlas(root)
    rdir=root/"reader";rdir.mkdir(parents=True,exist_ok=True)
    (rdir/"evidence_atlas.json").write_text(json.dumps(atlas,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    cards=[]
    for item in atlas["items"]:
        used=item.get("used_in",[])
        usage_html="".join(
            f"<li><a href='paper_reader.html#{_esc(u.get('chapter_id'))}'>{_esc(u.get('chapter_title'))}</a> · {_esc(u.get('block_type'))}</li>"
            for u in used
        ) or "<li>未在主 Reader 中引用</li>"
        asset=item.get("asset")
        media=""
        if asset and (root/asset).exists() and str(asset).lower().endswith((".png",".jpg",".jpeg",".webp")):
            rel="../"+str(asset).replace("\\","/")
            media=f"<img src='{_esc(rel)}' alt='{_esc(item.get('label') or item['id'])}'>"
        cards.append(f"""
<section class='card' id='{_esc(item["id"])}'>
  <div class='meta'>{_esc(item.get("kind"))} · p.{_esc(item.get("page"))} · {_esc(item.get("verification_status"))}</div>
  <h2>{_esc(item.get("label") or item["id"])}</h2>
  {media}
  <p>{_esc(item.get("caption") or "")}</p>
  <details><summary>在主 Reader 中的引用位置</summary><ul>{usage_html}</ul></details>
</section>""")

    html_text=f"""<!doctype html>
<html lang='zh-CN'><head><meta charset='utf-8'>
<title>逐项来源与核验记录</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:980px;margin:0 auto;padding:36px 24px;background:#f7f6f1;color:#1d2733;line-height:1.6}}
a{{color:#1B365D}} .top{{margin-bottom:28px}} .card{{background:white;border:1px solid #ddd9cc;border-radius:8px;padding:18px;margin:18px 0}}
.meta{{font-size:.85rem;color:#69727d}} h2{{margin:.25rem 0 1rem}} img{{max-width:100%;max-height:560px;display:block;margin:12px auto}}
summary{{cursor:pointer;color:#1B365D}}
</style></head><body>
<div class='top'><a href='paper_reader.html'>← 返回论文精读</a>
<h1>逐项来源与核验记录</h1>
<p>这是 Reader v3 的次级来源检查面。正文叙事与审计记录分离；这里仅展示来源定位、视觉核验状态与正文引用位置。</p></div>
{''.join(cards)}
</body></html>"""
    (rdir/"evidence_atlas.html").write_text(html_text,encoding="utf-8")
    print(f"OK: Reader v3 Evidence Atlas -> {rdir/'evidence_atlas.html'}")


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args();render(Path(args.out))


if __name__=="__main__":
    main()
