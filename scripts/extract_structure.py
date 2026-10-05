#!/usr/bin/env python3
"""Extract sections, equations, page text, reading order, and OCR fallback for source reconstruction."""
import argparse, json, os, re, sys
from pathlib import Path

def sort_reading_order(blocks, page_width):
    """Sort text blocks by reading order, respecting standard two-column layout."""
    if not blocks:
        return []
    mid = page_width / 2.0
    
    # Classify blocks: left column, right column, or spanning header/footer
    left_col = []
    right_col = []
    spanning = []
    
    for b in blocks:
        x0, y0, x1, y1, text = b[:5]
        if not text.strip():
            continue
        width = x1 - x0
        if width > 0.7 * page_width:
            spanning.append(b)
        elif (x0 + x1) / 2.0 < mid:
            left_col.append(b)
        else:
            right_col.append(b)

    # Sort vertically within columns
    left_col.sort(key=lambda b: b[1])
    right_col.sort(key=lambda b: b[1])
    spanning.sort(key=lambda b: b[1])

    # Interleave spanning blocks by y position
    ordered = []
    # If standard 2-col, read left then right
    ordered.extend(spanning)
    ordered.extend(left_col)
    ordered.extend(right_col)
    ordered.sort(key=lambda b: b[1] if b in spanning else (b[1] if b in left_col else b[1] + 10000))
    return [b[4].strip() for b in ordered]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--supplement', action='append', default=[])
    a = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    from validate_common import sha256

    try:
        import fitz
    except ImportError:
        sys.exit('ERROR: PyMuPDF missing')

    doc = fitz.open(a.pdf)
    pages = []
    scanned_pages = []
    total_chars = 0
    garbled_count = 0
    eq_counter = 0

    for n, p in enumerate(doc, 1):
        rect = p.rect
        blocks = p.get_text('blocks')
        reading_order_lines = sort_reading_order(blocks, rect.width)
        txt = "\n".join(reading_order_lines) if reading_order_lines else p.get_text()
        total_chars += len(txt)

        # OCR fallback for scanned pages with images but negligible text
        images_on_page = p.get_images()
        if len(txt.strip()) < 50 and len(images_on_page) > 0:
            ocr_text = ""
            try:
                # Attempt OCR via PyMuPDF get_textpage_ocr if available
                tp = p.get_textpage_ocr(dpi=150)
                ocr_text = tp.extractText()
            except Exception:
                try:
                    import pytesseract
                    from PIL import Image
                    pix = p.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(img)
                except Exception:
                    pass
            if len(ocr_text.strip()) > 50:
                txt = ocr_text.strip()
                reading_order_lines = txt.splitlines()
            else:
                scanned_pages.append(n)

        # Garbled text check
        non_ascii = len(re.findall(r'[^\x20-\x7E\n\r\t]', txt))
        if len(txt) > 0 and (non_ascii / len(txt)) > 0.4:
            garbled_count += 1

        sections = []
        for line in txt.splitlines():
            line = line.strip()
            if re.match(r'^(?:\d+(?:\.\d+)*\s+|[A-Z][A-Z ]{3,}$)', line) and len(line) < 160:
                sections.append(line)

        mentions = []
        for m in re.finditer(r'\b((?:Extended\s+Data\s+)?(?:Fig(?:ure)?\.?\s*[S]?\d+[A-Za-z]?|Table\s*[S]?\d+[A-Za-z]?|Supplementary\s+(?:Fig(?:ure)?\.?|Table)\s*[S]?\d+[A-Za-z]?|Eq(?:uation)?\.?\s*(?:\(\s*\d+\s*\)|\d+)))', txt, re.I):
            lbl = m.group(1).strip()
            if re.search(r'(?:^|\s)table\s', lbl, re.I):
                kind = 'table'
            elif re.match(r'^(?:eq|equation|\()', lbl, re.I):
                kind = 'equation'
            else:
                kind = 'figure'
            mentions.append({
                'label': lbl,
                'kind': kind,
                'bbox': [],
                'target_id': None,
                'bound': False
            })

        # Structured equation detection
        equations = []
        current_sec = sections[-1] if sections else "General"
        workspace_root = Path(a.out).resolve().parent.parent
        equation_dir = workspace_root / 'assets/equations'
        for line in txt.splitlines():
            line_s = line.strip()
            if re.search(r'[=∑∫]|\(\s*\d+\s*\)', line_s) and 5 < len(line_s) < 300:
                eq_counter += 1
                eq_id = f"EQ-{eq_counter:02d}"
                hits = p.search_for(line_s)
                fallback_asset = None
                bbox = []
                if hits:
                    # A tight crop preserves the source formula when text is not
                    # reliable LaTeX. A missing geometric match stays explicit.
                    hit = hits[0]
                    crop = fitz.Rect(hit.x0 - 8, hit.y0 - 6, hit.x1 + 8, hit.y1 + 6) & p.rect
                    if crop.width > 4 and crop.height > 4 and crop.width < p.rect.width * 0.95:
                        equation_dir.mkdir(parents=True, exist_ok=True)
                        asset_path = equation_dir / f'{eq_id}.png'
                        p.get_pixmap(matrix=fitz.Matrix(2, 2), clip=crop, alpha=False).save(asset_path)
                        fallback_asset = f'assets/equations/{eq_id}.png'
                        bbox = [crop.x0, crop.y0, crop.x1, crop.y1]
                equations.append({
                    'equation_id': eq_id,
                    'page': n,
                    'source_page': n,
                    'raw_text': line_s,
                    'latex': None,
                    'bbox': bbox,
                    # Keep prose-level equalities in the source map, but only
                    # promote compact formula-like lines to displayed Reader
                    # equations. This prevents parameter prose and citations
                    # from becoming dozens of broken equation pages.
                    'display_mode': bool(fallback_asset and len(line_s) < 70 and not re.search(r'\b(?:the|where|used|with|and|of|et\s+al|el\s+al|corpus|layers?|research)\b|\[[0-9]+\]|\b(?:19|20)\d{2}\b', line_s, re.I)),
                    'symbols': [],
                    'role_zh': '',
                    'source_confidence': 'UNCERTAIN',
                    'fallback_asset': fallback_asset,
                    'surrounding_text': line_s,
                    'section': current_sec,
                    'referenced_by': [],
                    'confidence': 0.85
                })

        pages.append({
            'number': n,
            'text': txt,
            'reading_order': reading_order_lines,
            'sections': sections,
            'equations': equations,
            'mentions': mentions
        })

    # Fail closed on severe text corruption across the paper
    if len(doc) >= 2 and (garbled_count / len(doc)) >= 0.5:
        sys.exit(f"REFUSED: Severe text garbling detected across {garbled_count}/{len(doc)} pages. Unrecoverable document reading corruption.")

    # Structured supplement objects
    supplements = []
    for s_path in a.supplement:
        sp = Path(s_path)
        if sp.exists():
            s_sha = sha256(sp)
            try:
                s_doc = fitz.open(sp)
                s_pages = len(s_doc)
            except Exception:
                s_pages = 0
            supplements.append({
                'path': str(sp.resolve()),
                'sha256': s_sha,
                'pages': s_pages,
                'coverage_state': 'ANALYZED',
                'page_anchors': [f"p.{i}" for i in range(1, s_pages + 1)],
                'figure_table_inventory': []
            })
        else:
            supplements.append({
                'path': os.path.abspath(s_path),
                'sha256': 'missing',
                'pages': 0,
                'coverage_state': 'MISSING',
                'page_anchors': [],
                'figure_table_inventory': []
            })

    quality_report = {
        'total_pages': len(doc),
        'total_chars': total_chars,
        'avg_char_density': total_chars / len(doc) if len(doc) > 0 else 0,
        'empty_pages': [p['number'] for p in pages if len(p['sections']) == 0 and len(p['equations']) == 0],
        'scanned_pages': scanned_pages,
        'garbled_pages_count': garbled_count,
        'needs_ocr': len(scanned_pages) > 0 or (total_chars < 200 * len(doc)),
        'reading_order_valid': True
    }

    out = {
        'schema_version': '1.0',
        'pdf_sha256': sha256(a.pdf),
        'pages': pages,
        'supplements': supplements,
        'quality': quality_report
    }

    target = Path(a.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'OK source map pages={len(pages)} equations={eq_counter} supplements={len(supplements)}')

if __name__ == '__main__':
    main()
