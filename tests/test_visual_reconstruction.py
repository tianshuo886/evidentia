"""Tests for Page-first Multimodal Visual Reconstruction (P0 Workstream A).

Validates:
- Full page rasterization generates source_pages/page-XXX.png
- Zero whole-page screenshots published as figure or table assets
- Low-confidence or unlocalized visuals fail closed to VISUAL_BINDING_UNCERTAIN / NEEDS_REVIEW
- Real structured table reconstruction (headers, rows, cells) or explicit STRUCTURE_UNCERTAIN
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable

def test_source_page_rasterization_and_clean_crops(tmp_path):
    pdf_path = tmp_path / 'multimodal_paper.pdf'
    inv_path = tmp_path / 'model/figure_inventory.json'
    assets_dir = tmp_path / 'assets/figures'
    
    import fitz
    doc = fitz.open()
    # Page 1: Diagram with caption
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 50), "Paper Title\n\nIntroduction text paragraph.", fontsize=12)
    # Visual diagram box
    p1.draw_rect(fitz.Rect(60, 150, 500, 350), color=(0.1, 0.5, 0.8), fill=(0.9, 0.95, 1.0))
    p1.insert_text((60, 370), "Figure 1: Multimodal pipeline architecture overview.", fontsize=10)
    
    # Page 2: Table with caption
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((60, 100), "Table 1: Main experimental results across baselines.", fontsize=10)
    # Table rows
    p2.insert_text((60, 130), "Method         Accuracy     Latency", fontsize=9)
    p2.insert_text((60, 150), "ResNet-50      76.5         12ms", fontsize=9)
    p2.insert_text((60, 170), "Ours           82.1         14ms", fontsize=9)
    p2.draw_rect(fitz.Rect(55, 115, 520, 190), color=(0.2, 0.2, 0.2))
    
    doc.save(str(pdf_path))
    
    # Execute extract_figs.py
    res = subprocess.run([
        PY, str(ROOT / 'scripts/extract_figs.py'),
        '--pdf', str(pdf_path),
        '--out', str(assets_dir),
        '--inventory', str(inv_path)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    
    # 1. Verify source pages generated
    sp_dir = tmp_path / 'source_pages'
    assert sp_dir.exists()
    assert (sp_dir / 'page-001.png').exists()
    assert (sp_dir / 'page-002.png').exists()
    
    # 2. Verify figure inventory structure
    inv = json.loads(inv_path.read_text(encoding='utf-8'))
    assert len(inv['items']) == 2
    
    fig_item = next(i for i in inv['items'] if i['kind'] == 'figure')
    assert fig_item['id'] == 'F01'
    assert fig_item['binding_method'] in ('MULTIMODAL_PAGE_LOCALIZATION', 'caption_geometry')
    # Bbox must NOT be whole page
    if fig_item['file']:
        img_p = tmp_path / fig_item['file']
        assert img_p.exists()
        # Verify asset dimensions are reasonable (not full page 595x842 scaled to 1653x2339)
        pix = fitz.Pixmap(str(img_p))
        assert pix.height < 1500, f"Figure crop appears to be whole-page fallback ({pix.width}x{pix.height})"
        
    table_item = next(i for i in inv['items'] if i['kind'] == 'table')
    assert table_item['id'] == 'T01'
    assert table_item['headers'] is not None or table_item['structure_status'] == 'STRUCTURE_UNCERTAIN'

def test_appendix_figure_and_table_labels_are_inventory_items(tmp_path):
    pdf_path = tmp_path / 'appendix_paper.pdf'
    inv_path = tmp_path / 'model/figure_inventory.json'
    assets_dir = tmp_path / 'assets/figures'

    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(60, 100, 500, 300), color=(0.1, 0.5, 0.8), fill=(0.9, 0.95, 1.0))
    page.insert_text((60, 320), 'Figure A.1: Appendix diagnostic plot.', fontsize=10)
    page.insert_text((60, 400), 'Table A.1: Appendix results.', fontsize=10)
    page.insert_text((60, 430), 'Method     Score', fontsize=9)
    page.insert_text((60, 450), 'Ours       1.0', fontsize=9)
    doc.save(str(pdf_path))

    res = subprocess.run([
        PY, str(ROOT / 'scripts/extract_figs.py'),
        '--pdf', str(pdf_path), '--out', str(assets_dir), '--inventory', str(inv_path)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    inv = json.loads(inv_path.read_text(encoding='utf-8'))
    assert {item['id'] for item in inv['items']} == {'FA1', 'TA1'}

    # In-text mentions are not caption inventory items when they lack an
    # explicit caption separator.
    page2 = fitz.open(pdf_path)
    page2[0].insert_text((60, 500), 'Figure A.9 is discussed below, but is not drawn here.', fontsize=9)
    page2.save(str(pdf_path.with_name('appendix_paper_with_reference.pdf')))
    inv2_path = tmp_path / 'model/figure_inventory_2.json'
    res2 = subprocess.run([
        PY, str(ROOT / 'scripts/extract_figs.py'),
        '--pdf', str(pdf_path.with_name('appendix_paper_with_reference.pdf')),
        '--out', str(assets_dir), '--inventory', str(inv2_path)
    ], capture_output=True, text=True)
    assert res2.returncode == 0, res2.stdout + res2.stderr
    assert {item['id'] for item in json.loads(inv2_path.read_text())['items']} == {'FA1', 'TA1'}


def test_table_and_chart_nearby_do_not_share_visual_asset(tmp_path):
    import fitz
    pdf_path = tmp_path / 'collision_paper.pdf'
    inv_path = tmp_path / 'model/figure_inventory.json'
    assets_dir = tmp_path / 'assets/figures'
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((60, 90), 'Method      Accuracy      Latency', fontsize=9)
    page.insert_text((60, 112), 'Baseline    0.70         20ms', fontsize=9)
    page.insert_text((60, 134), 'Ours        0.82         14ms', fontsize=9)
    page.insert_text((60, 165), 'Table 4: Performance of methods.', fontsize=10)
    page.draw_rect(fitz.Rect(80, 300, 500, 500), color=(0.1, 0.5, 0.8), fill=(0.9, 0.95, 1.0))
    page.insert_text((80, 520), 'Figure 2: Validation accuracy chart.', fontsize=10)
    doc.save(str(pdf_path))
    res = subprocess.run([
        PY, str(ROOT / 'scripts/extract_figs.py'), '--pdf', str(pdf_path),
        '--out', str(assets_dir), '--inventory', str(inv_path)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    items = json.loads(inv_path.read_text(encoding='utf-8'))['items']
    table = next(x for x in items if x['id'] == 'T04')
    figure = next(x for x in items if x['id'] == 'F02')
    assert table['file'] and figure['file']
    assert table['file'] != figure['file']
    assert table['figure_bbox'][3] < figure['figure_bbox'][1]


def test_uncertain_visual_fails_closed_without_whole_page_asset(tmp_path):
    pdf_path = tmp_path / 'elusive_paper.pdf'
    inv_path = tmp_path / 'model/figure_inventory.json'
    assets_dir = tmp_path / 'assets/figures'
    
    import fitz
    doc = fitz.open()
    # A page with a caption mentioned in text, but NO visual rectangle or image anywhere
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 400), "Figure 7: An abstract conceptual schematic not drawn.", fontsize=10)
    doc.save(str(pdf_path))
    
    res = subprocess.run([
        PY, str(ROOT / 'scripts/extract_figs.py'),
        '--pdf', str(pdf_path),
        '--out', str(assets_dir),
        '--inventory', str(inv_path)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    
    inv = json.loads(inv_path.read_text(encoding='utf-8'))
    item = inv['items'][0]
    
    # Must fail closed:
    # 1. No false full-page image asset published!
    assert item['file'] is None or item.get('raw_visual_fallback') is None
    # 2. Must be flagged as uncertain / needs review
    assert item['binding_method'] == 'VISUAL_BINDING_UNCERTAIN'
    assert item['inspection_status'] == 'NEEDS_REVIEW'
    assert item['needs_visual_review'] is True
    assert item['id'] in inv['review_required']


def test_drawing_background_mask_ignored_and_geometry_not_verified(tmp_path):
    import fitz
    pdf_path = tmp_path / 'multipart_vector.pdf'
    inv_path = tmp_path / 'model/figure_inventory.json'
    assets_dir = tmp_path / 'assets/figures'

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # White background mask covering a large area
    page.draw_rect(fitz.Rect(100, 200, 500, 600), fill=(1.0, 1.0, 1.0), color=None)
    # Actual vector figure components
    page.draw_rect(fitz.Rect(200, 300, 260, 380), color=(0.1, 0.2, 0.8), fill=(0.8, 0.9, 1.0))
    page.draw_rect(fitz.Rect(300, 310, 340, 370), color=(0.8, 0.2, 0.1), fill=(1.0, 0.9, 0.8))
    page.insert_text((180, 420), 'Figure 1: LoRA architecture with adaptation branch.', fontsize=10)
    doc.save(str(pdf_path))

    res = subprocess.run([
        PY, str(ROOT / 'scripts/extract_figs.py'), '--pdf', str(pdf_path),
        '--out', str(assets_dir), '--inventory', str(inv_path)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    items = json.loads(inv_path.read_text(encoding='utf-8'))['items']
    fig = next(x for x in items if x['id'] == 'F01')
    assert fig['file'] is not None
    # Figure box should encompass the vector parts (~[200, 300, 340, 380]), NOT the full white mask [100, 200, 500, 600]
    bbox = fig['figure_bbox']
    assert bbox[0] >= 180 and bbox[2] <= 360
    assert bbox[1] >= 280 and bbox[3] <= 400
    # Must NOT prematurely mark inspection_status as VERIFIED
    assert fig.get('inspection_status') != 'VERIFIED'

