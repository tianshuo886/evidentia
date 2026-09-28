"""Evidence Promotion and Selectivity Tests for Evidentia (Issue #8).

Verifies the core product invariant:
"Extraction does not imply presentation. Evidence objects are the substrate,
not the final reading experience."

Tests that figures and tables designated as `audit_only` are not dumped into
the main narrative's decisive experiments chapter, while remaining fully
accessible in the audit appendix.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from validate_common import load_json

def test_evidence_selectivity_in_main_reader(tmp_path):
    r = fixture(tmp_path)
    pm_path = r / 'model/paper_model.json'
    pm = load_json(pm_path)
    
    # Simulate a paper with 8 figures and 4 tables (12 evidence items total)
    all_figs = []
    for idx in range(1, 9):
        fid = f"F{idx:02d}"
        role = "critical" if idx in (1, 2) else "supporting" if idx == 3 else "catalog"
        depth = "deep" if idx in (1, 2) else "shallow"
        all_figs.append({
            "id": fid,
            "paper_label": f"Fig. {idx}",
            "page": idx,
            "caption_original": f"Figure {idx} caption description",
            "role": role,
            "depth": depth,
            "file": "assets/figures/f.png",
            "supports_claims": ["C01"] if idx in (1, 2) else []
        })
    
    all_tables = []
    for idx in range(1, 5):
        tid = f"T{idx:02d}"
        all_tables.append({
            "id": tid,
            "paper_label": f"Table {idx}",
            "page": idx + 8,
            "caption_original": f"Table {idx} caption description",
            "supports_claims": ["C01"] if idx == 1 else []
        })
        
    pm['figures'] = all_figs
    pm['tables'] = all_tables
    pm['claims'] = [{
        "id": "C01",
        "statement": "核心方法在基准上表现优异",
        "evidence": ["F01", "T01"],
        "epistemic": "SUPPORTED"
    }]
    pm_path.write_text(json.dumps(pm, indent=2, ensure_ascii=False), encoding='utf-8')

    # Remove cached argument reconstruction to force fresh promotion analysis
    arg_p = r / 'model/argument_reconstruction.json'
    if arg_p.exists():
        arg_p.unlink()

    # Run render_reader.py
    res = subprocess.run([PY, str(ROOT / 'scripts/render_reader.py'), '--out', str(r)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    ir = load_json(r / 'reader/paper_reader_ir.json')
    
    # Decisive experiments in main narrative
    decisive_ids = [exp['id'] for exp in ir['decisive_experiments']]
    
    # Audit appendix items
    appendix_fig_ids = [f['id'] for f in ir['audit_appendix']['figures']]
    appendix_tab_ids = [t['id'] for t in ir['audit_appendix']['tables']]

    # 1. Verification of promotion selectivity:
    # Main narrative must ONLY contain decisive/promoted evidence, NOT all 12 items!
    assert len(decisive_ids) < 12, f"Reader dumped all evidence ({len(decisive_ids)}) into decisive experiments!"
    assert "F01" in decisive_ids, "F01 is core evidence and must be promoted to decisive experiments"
    assert "T01" in decisive_ids, "T01 is core evidence and must be promoted to decisive experiments"
    
    # Catalog figures (F04, F05, F06, F07, F08) and secondary tables (T02, T03, T04) must NOT be in main decisive experiments
    assert "F05" not in decisive_ids, "Catalog figure F05 should not be in decisive experiments"
    assert "T03" not in decisive_ids, "Secondary table T03 should not be in decisive experiments"

    # 2. Verification of audit completeness:
    # All 12 items MUST still be preserved in the audit appendix
    assert len(appendix_fig_ids) == 8, "Audit appendix must preserve all 8 figures"
    assert len(appendix_tab_ids) == 4, "Audit appendix must preserve all 4 tables"
    assert "F05" in appendix_fig_ids
    assert "T03" in appendix_tab_ids
