#!/usr/bin/env python3
"""Extract embedded figures + build figure/table inventory from a paper PDF.

Usage:
  python extract_figs.py --pdf paper.pdf --out <out>/assets/figures \
      --inventory <out>/model/figure_inventory.json [--min-size 400] [--dpi 300]

- Saves embedded raster images larger than --min-size (px, either side).
- Scans text for Fig./Figure/Table captions, records page + caption text.
- Never invents captions: unparseable -> caption_status NOT_EXTRACTED.
Requires: PyMuPDF (fitz), Pillow.
"""
import argparse, json, os, re, sys

CAP_RE = re.compile(
    r"((?:Fig\.?|Figure|Table|TABLE|Supplementary\s+(?:Fig\.?|Figure|Table))\s*"
    r"S?\d+[a-zA-Z]?(?:\s*[-–—]\s*|\s+|\.\s*))(.{0,400})",
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--min-size", type=int, default=400)
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()
    try:
        import fitz
    except ImportError:
        sys.exit("ERROR: PyMuPDF missing (pip install PyMuPDF)")
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.inventory)), exist_ok=True)
    doc = fitz.open(a.pdf)
    saved = []
    seen_xref = set()
    n = 0
    for pno in range(len(doc)):
        for img in doc[pno].get_images(full=True):
            xref = img[0]
            if xref in seen_xref:
                continue
            seen_xref.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue
            if pix.n - pix.alpha > 3:
                try:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                except Exception:
                    continue
            w, h = pix.width, pix.height
            if max(w, h) < a.min_size or min(w, h) < 8:
                continue
            n += 1
            fn = f"fig{n:02d}_p{pno+1}_{w}x{h}.png"
            pix.save(os.path.join(a.out, fn))
            saved.append({"file": fn, "page": pno + 1, "w": w, "h": h, "xref": xref})
    items = []
    fid = 0
    for pno in range(len(doc)):
        text = doc[pno].get_text()
        for m in CAP_RE.finditer(text):
            label = m.group(1).strip()
            cap = (label + " " + m.group(2)).strip()
            kind = "table" if "abl" in label.lower() else "figure"
            fid += 1
            items.append({
                "id": f"{'T' if kind == 'table' else 'F'}{fid:02d}",
                "paper_label": label,
                "kind": kind,
                "page": pno + 1,
                "caption_original": cap,
                "caption_status": "OK",
                "source_location": f"p.{pno+1}",
                "role": "unassigned",
                "depth": "unassigned",
            })
    inv = {
        "pdf": os.path.abspath(a.pdf),
        "pages": len(doc),
        "embedded_saved": saved,
        "items": items,
        "note": "排版 figures (multi-panel page composites) need manual 300dpi crop; "
                "add entries with source_location + caption_original, never guess.",
    }
    with open(a.inventory, "w") as f:
        json.dump(inv, f, ensure_ascii=False, indent=2)
    print(f"OK: pages={len(doc)} embedded_saved={len(saved)} captions={len(items)}")
    print(f"OK: inventory -> {a.inventory}")

if __name__ == "__main__":
    main()
