"""Phase B2 Source Reconstruction v2 acceptance tests.

Validates:
- Text track quality metrics (scanned detection, density, garbled check)
- Visual track with geometry-based caption binding and binding scores
- Figure object schema and fields (figure_bbox, asset, inspection_status, etc.)
- Table object schema and structural fields (row_count, col_count, structure)
- Equation object schema validation (equation.schema.json)
- Structured supplement metadata (SHA, page anchors, coverage_state)
- Mention linking to canonical entity IDs (link_mentions.py)
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_common import schema_validate, load_json

def test_equation_schema_validation():
    eq_data = {
        "equation_id": "EQ-01",
        "page": 2,
        "bbox": [100.0, 200.0, 400.0, 240.0],
        "raw_text": "L_{total} = L_{rec} + \\lambda L_{reg}",
        "latex": "L_{total} = L_{rec} + \\lambda L_{reg}",
        "surrounding_text": "We formulate our loss function as follows: L_{total} = L_{rec} + \\lambda L_{reg} where \\lambda controls regularization.",
        "section": "3. Methodology",
        "referenced_by": ["p.2 line 15", "p.3 line 4"],
        "used_by_claims": ["C01"],
        "assumptions": ["Smoothness of regularization parameter"],
        "confidence": 0.95
    }
    errs = schema_validate(eq_data, 'equation')
    assert not errs, f"equation schema error: {errs}"

def test_figure_inventory_b2_rich_fields():
    inv_data = {
        "schema_version": "1.0",
        "source_sha256": "abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "pdf": "/path/to/paper.pdf",
        "pages": 5,
        "items": [
            {
                "id": "F01",
                "kind": "figure",
                "paper_label": "Figure 1",
                "page": 1,
                "caption_original": "Figure 1: Architectural diagram of our approach.",
                "caption_status": "OK",
                "role": "critical",
                "depth": "deep",
                "file": "assets/figures/fig01.png",
                "bbox": [50.0, 400.0, 500.0, 420.0],
                "caption_bbox": [50.0, 400.0, 500.0, 420.0],
                "figure_bbox": [50.0, 100.0, 500.0, 390.0],
                "subfigures": ["a", "b"],
                "asset": "assets/figures/fig01.png",
                "extraction_method": "embedded",
                "confidence": 0.92,
                "inspection": "inspected",
                "inspection_status": "inspected",
                "reviewed_by": "lead-agent",
                "review_note": "Clear resolution, all panels legible",
                "binding_method": "caption_geometry",
                "binding_confidence": 0.91,
                "needs_visual_review": False
            },
            {
                "id": "T01",
                "kind": "table",
                "paper_label": "Table 1",
                "page": 3,
                "caption_original": "Table 1: Main benchmark comparisons across baselines.",
                "caption_status": "OK",
                "role": "critical",
                "depth": "deep",
                "file": "assets/figures/tab01.png",
                "bbox": [50.0, 100.0, 500.0, 120.0],
                "caption_bbox": [50.0, 100.0, 500.0, 120.0],
                "figure_bbox": [50.0, 130.0, 500.0, 350.0],
                "subfigures": [],
                "asset": "assets/figures/tab01.png",
                "extraction_method": "page_crop",
                "confidence": 0.88,
                "inspection": "inspected",
                "inspection_status": "inspected",
                "reviewed_by": None,
                "review_note": None,
                "binding_method": "caption_geometry",
                "binding_confidence": 0.89,
                "needs_visual_review": False,
                "row_count": 6,
                "col_count": 5,
                "structure": {"header": True, "rows": 6},
                "parsed_cells": [["Method", "Accuracy"], ["Ours", "95.2"]],
                "raw_visual_fallback": "assets/figures/tab01.png"
            }
        ],
        "embedded_saved": 1,
        "unmatched_assets": [],
        "review_required": []
    }
    errs = schema_validate(inv_data, 'figure_inventory')
    assert not errs, f"figure_inventory schema error: {errs}"

def test_source_map_b2_rich_fields():
    sm_data = {
        "schema_version": "1.0",
        "pdf_sha256": "abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "pages": [
            {
                "number": 1,
                "sections": ["1. Introduction"],
                "equations": [
                    {
                        "equation_id": "EQ-01",
                        "page": 1,
                        "raw_text": "y = f(x; \\theta)",
                        "latex": "y = f(x; \\theta)",
                        "bbox": [100.0, 300.0, 300.0, 320.0],
                        "surrounding_text": "where y = f(x; \\theta) denotes the mapping",
                        "section": "1. Introduction",
                        "referenced_by": [],
                        "confidence": 0.9
                    }
                ],
                "mentions": [
                    {
                        "label": "Fig. 1",
                        "kind": "figure",
                        "bbox": [120.0, 150.0, 160.0, 160.0],
                        "target_id": "F01",
                        "bound": True
                    },
                    {
                        "label": "Table 1",
                        "kind": "table",
                        "bbox": [200.0, 150.0, 240.0, 160.0],
                        "target_id": "T01",
                        "bound": True
                    }
                ]
            }
        ],
        "supplements": [
            {
                "path": "/data/supplement.pdf",
                "sha256": "deadbeef12345678deadbeef12345678deadbeef12345678deadbeef12345678",
                "pages": 4,
                "coverage_state": "ANALYZED",
                "page_anchors": ["p.1", "p.2", "p.3", "p.4"],
                "figure_table_inventory": []
            }
        ],
        "quality": {
            "total_pages": 1,
            "total_chars": 2500,
            "avg_char_density": 2500.0,
            "empty_pages": [],
            "scanned_pages": [],
            "garbled_pages_count": 0,
            "needs_ocr": False,
            "reading_order_valid": True
        }
    }
    errs = schema_validate(sm_data, 'source_map')
    assert not errs, f"source_map schema error: {errs}"

def test_link_mentions_script(tmp_path):
    sm_path = tmp_path / 'source_map.json'
    inv_path = tmp_path / 'figure_inventory.json'
    
    sm_data = {
        "schema_version": "1.0",
        "pdf_sha256": "fakehash",
        "pages": [
            {
                "number": 1,
                "sections": ["Section 1"],
                "equations": [
                    {
                        "equation_id": "EQ-01",
                        "page": 1,
                        "raw_text": "E = mc^2"
                    }
                ],
                "mentions": [
                    {"label": "Fig. 1", "kind": "figure", "bbox": []},
                    {"label": "Table 2", "kind": "table", "bbox": []},
                    {"label": "Eq. 1", "kind": "equation", "bbox": []},
                    {"label": "Figure 99", "kind": "figure", "bbox": []}
                ]
            }
        ],
        "supplements": []
    }
    sm_path.write_text(json.dumps(sm_data, indent=2))
    
    inv_data = {
        "schema_version": "1.0",
        "pdf": "p.pdf",
        "pages": 1,
        "items": [
            {"id": "F01", "paper_label": "Fig. 1", "kind": "figure"},
            {"id": "T02", "paper_label": "Table 2", "kind": "table"}
        ]
    }
    inv_path.write_text(json.dumps(inv_data, indent=2))
    
    res = subprocess.run([PY, str(ROOT / 'scripts/link_mentions.py'), '--source-map', str(sm_path), '--inventory', str(inv_path)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    
    updated_sm = json.loads(sm_path.read_text())
    mentions = updated_sm['pages'][0]['mentions']
    assert mentions[0]['label'] == 'Fig. 1' and mentions[0]['target_id'] == 'F01' and mentions[0]['bound'] is True
    assert mentions[1]['label'] == 'Table 2' and mentions[1]['target_id'] == 'T02' and mentions[1]['bound'] is True
    assert mentions[2]['label'] == 'Eq. 1' and mentions[2]['target_id'] == 'EQ-01' and mentions[2]['bound'] is True
    assert mentions[3]['label'] == 'Figure 99' and mentions[3]['target_id'] is None and mentions[3]['bound'] is False
