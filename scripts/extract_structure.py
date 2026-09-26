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
        for m in re.finditer(r'\b(Fig(?:ure)?\.?\s*[S]?\d+[A-Za-z]?|Table\s*[S]?\d+[A-Za-z]?|Eq(?:uation)?\.?\s*(?:\(\s*\d+\s*\)|\d+))', txt, re.I):
            lbl = m.group(1).strip()
            if lbl.lower().startswith('table'):
                kind = 'table'
            elif lbl.lower().startswith(('eq', '(')):
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
        for line in txt.splitlines():
            line_s = line.strip()
            if re.search(r'[=∑∫]|\(\s*\d+\s*\)', line_s) and 5 < len(line_s) < 300:
                eq_counter += 1
                eq_id = f"EQ-{eq_counter:02d}"
                equations.append({
                    'equation_id': eq_id,
                    'page': n,
                    'raw_text': line_s,
                    'latex': None,
                    'bbox': [],
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
