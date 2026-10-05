"""Issue #20 Canonicalization & Anti-Regression Test Suite.

Verifies:
1. evidentia.py run defaults to Reader v3 canonical pipeline.
2. evidentia.py status and next natively support Reader v3 workspaces.
3. render_paper_reader fails closed when narrative_manuscript.json is missing (no silent composer fallback).
4. render_reader preserves existing Lead Writer narrative manuscript without overwriting.
5. capability_matrix.json adheres to schema version 3.0 and approved status vocabulary.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))
from validate_common import load_json, sha256
from test_intent_isolation import make_test_pdf

def test_evidentia_run_defaults_to_v3(tmp_path):
    out_dir = tmp_path / "v3_workspace"
    pdf_path = tmp_path / "test.pdf"
    make_test_pdf(pdf_path, "Canonical Architecture Verification Paper")

    res = subprocess.run([
        PY, str(ROOT / "scripts/evidentia.py"),
        "run", "--pdf", str(pdf_path), "--out", str(out_dir), "--fixture"
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Evidentia Reader v3 COMPLETE" in res.stdout
    assert (out_dir / "tasks/v3/lead_reading.json").exists()
    assert (out_dir / "tasks/v3/lens/argument_narrative.json").exists()
    assert (out_dir / "reader/narrative_manuscript.json").exists()
    assert (out_dir / "reader/paper_reader.html").exists()

def test_evidentia_status_and_next_v3(tmp_path):
    out_dir = tmp_path / "v3_workspace"
    pdf_path = tmp_path / "test.pdf"
    make_test_pdf(pdf_path, "Status Next Verification Paper")

    # Run up to completion
    subprocess.run([
        PY, str(ROOT / "scripts/evidentia.py"),
        "run", "--pdf", str(pdf_path), "--out", str(out_dir), "--fixture"
    ], check=True)

    # Check status
    res_status = subprocess.run([
        PY, str(ROOT / "scripts/evidentia.py"),
        "status", "--out", str(out_dir)
    ], capture_output=True, text=True)
    assert res_status.returncode == 0
    status_data = json.loads(res_status.stdout)
    assert status_data["source_ready"] is True
    assert status_data["lead_writer"] is True
    assert status_data["rendered"] is True

    # Check next
    res_next = subprocess.run([
        PY, str(ROOT / "scripts/evidentia.py"),
        "next", "--out", str(out_dir)
    ], capture_output=True, text=True)
    assert res_next.returncode == 0
    assert "Reader v3 stages complete" in res_next.stdout or "Ready to render" in res_next.stdout

def test_render_paper_reader_fails_closed_without_manuscript(tmp_path):
    from render_paper_reader import render_paper_reader
    # Create empty workspace without narrative_manuscript.json
    ws = tmp_path / "empty_ws"
    (ws / "reader").mkdir(parents=True)
    (ws / "source").mkdir(parents=True)
    (ws / "source/paper.pdf").write_bytes(b"%PDF-1.4 test")

    import pytest
    with pytest.raises(FileNotFoundError) as exc_info:
        render_paper_reader(ws)
    assert "Missing canonical Lead Writer manuscript" in str(exc_info.value)

def test_render_reader_preserves_lead_writer_manuscript(tmp_path):
    from render_reader import render_reader
    ws = tmp_path / "preserve_ws"
    (ws / "reader").mkdir(parents=True)
    (ws / "source").mkdir(parents=True)
    (ws / "assets/figures").mkdir(parents=True)
    (ws / "model").mkdir(parents=True)
    (ws / "source/paper.pdf").write_bytes(b"%PDF-1.4 test")
    
    # Pre-populate custom Lead Writer manuscript
    custom_manuscript = {
        "schema_version": "3.0",
        "paper_id": "test-paper",
        "source_sha256": "0" * 64,
        "created_at": "2026-10-06T00:00:00Z",
        "document": {
            "title": "Lead Writer Sacred Manuscript",
            "paper_meta": {"authors": ["Lead Writer"]},
            "sections": [
                {
                    "id": "SEC-01",
                    "title": "Custom Unique Section",
                    "lead_paragraph": "Unique text authored by Lead Writer.",
                    "blocks": [{"id": "B01-01", "type": "paragraph", "text": "Preserved content [p.1].", "evidence_refs": ["p.1"]}]
                }
            ]
        }
    }
    manu_p = ws / "reader/narrative_manuscript.json"
    manu_p.write_text(json.dumps(custom_manuscript, indent=2))
    
    # Run render_reader
    render_reader(ws)
    
    # Verify manuscript was NOT overwritten by legacy composer
    after_data = json.loads(manu_p.read_text())
    assert after_data["document"]["title"] == "Lead Writer Sacred Manuscript"
    assert after_data["document"]["sections"][0]["title"] == "Custom Unique Section"

def test_capability_matrix_statuses_valid():
    cm = load_json(ROOT / "capability_matrix.json")
    assert cm["schema_version"] == "3.0"
    valid_statuses = set(cm["statuses"])
    for cap in cm["capabilities"]:
        assert cap["status"] in valid_statuses, f"Invalid status {cap['status']} in {cap['id']}"
    
    # Check that Reader v3 core capabilities are REAL_PAPER_VALIDATED
    real_caps = [c["id"] for c in cm["capabilities"] if c["status"] == "REAL_PAPER_VALIDATED"]
    assert "lead_reader_v3" in real_caps
    assert "adaptive_lens_orchestration" in real_caps
    assert "lead_writer_v3" in real_caps
    assert "dynamic_narrative_plan" in real_caps
    assert "editorial_revision_memo" in real_caps
