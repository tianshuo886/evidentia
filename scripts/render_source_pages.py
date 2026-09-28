#!/usr/bin/env python3
"""Render complete PDF pages into high-resolution source_pages/page-XXX.png.

Kami visual track / Evidentia page-first visual substrate:
- Render full pages first
- Deterministic page PNG naming: source_pages/page-001.png, page-002.png, ...
- Serves as the substrate for multimodal visual localization and human visual QA
"""
import argparse, os, sys
from pathlib import Path

def render_pages(pdf_path, out_dir, dpi=200):
    pdf = Path(pdf_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    try:
        import fitz
    except ImportError:
        sys.exit("ERROR: PyMuPDF (fitz) is required for page rasterization")
        
    doc = fitz.open(str(pdf))
    rendered = []
    for pno, page in enumerate(doc, start=1):
        fn = f"page-{pno:03d}.png"
        target = out / fn
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        pix.save(str(target))
        rendered.append(str(target))
    print(f"OK: rendered {len(rendered)} source pages to {out}")
    return rendered

def main():
    ap = argparse.ArgumentParser(description="Render PDF pages to PNG")
    ap.add_argument('--pdf', required=True, help="Path to input PDF")
    ap.add_argument('--out', required=True, help="Directory to save source_pages")
    ap.add_argument('--dpi', type=int, default=200, help="Rasterization DPI")
    args = ap.parse_args()
    render_pages(args.pdf, args.out, dpi=args.dpi)

if __name__ == '__main__':
    main()
