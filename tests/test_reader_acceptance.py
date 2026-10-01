"""End-to-end acceptance coverage for the Issue #10–#13 Reader contract."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
from reader_acceptance import evaluate
from render_reader import render_reader
from test_gates import fixture


def _render(root, intent=None):
    render_reader(root, intent=intent)
    # Unit tests exercise the artifact contract. Human semantic/visual review
    # and the real-paper regression report are covered by
    # test_reader_release_gate.py and the release corpus.
    return evaluate(root, artifact_only=True)


def test_default_reader_is_complete_and_transfer_free(tmp_path):
    root = fixture(tmp_path)
    report = _render(root)
    assert report["status"] == "READER_ACCEPTED", report
    manuscript = json.loads((root / "reader/narrative_manuscript.json").read_text())
    assert "technical_extraction" not in [c["id"] for c in manuscript["document"]["chapters"]]
    main = (root / "reader/paper_reader.html").read_text()
    assert "可复用技术内容" not in main
    assert "迁移复用建议" not in main


def test_technical_extraction_is_explicit_and_paper_scoped(tmp_path):
    root = fixture(tmp_path)
    (root / "run_state.json").write_text(json.dumps({"intent": "PAPER_TECHNICAL_EXTRACTION"}))
    report = _render(root)
    assert report["status"] == "READER_ACCEPTED", report
    manuscript = json.loads((root / "reader/narrative_manuscript.json").read_text())
    chapters = manuscript["document"]["chapters"]
    extraction = next(c for c in chapters if c["id"] == "technical_extraction")
    assert "项目" not in extraction["lead"]
    assert not (root / "apply").exists()


def test_verified_equation_is_bound_in_all_views(tmp_path):
    root = fixture(tmp_path)
    source_map = json.loads((root / "model/source_map.json").read_text())
    source_map["pages"][0]["equations"] = [{
        "equation_id": "EQ-01",
        "page": 1,
        "raw_text": "L = x + y",
        "latex": "L = x + y",
        "display_mode": True,
        "source_confidence": "VERIFIED",
        "role_zh": "verified objective",
    }]
    (root / "model/source_map.json").write_text(json.dumps(source_map))
    report = _render(root)
    assert report["status"] == "READER_ACCEPTED", report
    html = (root / "reader/paper_reader.html").read_text()
    markdown = (root / "reader/paper_reader.md").read_text()
    assert "latex-display-svg" in html
    assert "EQ-01" in html and "EQ-01" in markdown


def test_all_promoted_evidence_is_local_and_atlas_substitute_is_rejected(tmp_path):
    root = fixture(tmp_path)
    pm_path = root / "model/paper_model.json"
    pm = json.loads(pm_path.read_text())
    pm["figures"] = [
        {"id": "F01", "paper_label": "Fig. 1", "page": 1,
         "caption_original": "第一项结果", "file": "assets/figures/f.png",
         "supports_claims": ["C01"], "observation": "曲线接近",
         "author_interpretation": "作者认为方法有效", "reader_assessment": "在给定条件下得到支持"},
        {"id": "F02", "paper_label": "Fig. 2", "page": 1,
         "caption_original": "第二项结果", "file": "assets/figures/f.png",
         "supports_claims": ["C01"], "observation": "误差下降",
         "author_interpretation": "作者认为训练稳定", "reader_assessment": "在给定条件下得到支持"},
    ]
    pm["claims"] = [{"id": "C01", "statement": "核心方法在实验中得到支持",
                     "evidence": ["F01", "F02"], "epistemic": "SUPPORTED"}]
    pm_path.write_text(json.dumps(pm, ensure_ascii=False))
    (root / "model/argument_reconstruction.json").unlink(missing_ok=True)
    report = _render(root)
    assert report["status"] == "READER_ACCEPTED", report
    manuscript = json.loads((root / "reader/narrative_manuscript.json").read_text())
    ids = {b.get("evidence_id") for c in manuscript["document"]["chapters"]
           for b in c.get("blocks", []) if b.get("type") == "figure"}
    assert {"F01", "F02"}.issubset(ids)
    assert "详情见图谱" not in (root / "reader/paper_reader.html").read_text()


def test_unrenderable_source_equation_fails_closed(tmp_path):
    root = fixture(tmp_path)
    source_map = json.loads((root / "model/source_map.json").read_text())
    source_map["pages"][0]["equations"] = [{
        "equation_id": "EQ-BAD", "page": 1, "raw_text": "x = y",
        "latex": None, "source_confidence": "UNCERTAIN", "fallback_asset": None,
    }]
    (root / "model/source_map.json").write_text(json.dumps(source_map))
    report = _render(root)
    assert report["status"] == "NEEDS_REVIEW"
    assert any("EQ-BAD" in e and "fallback" in e for e in report["errors"])


def test_figure_table_equation_heavy_reader_keeps_local_bindings(tmp_path):
    root = fixture(tmp_path)
    pm_path = root / "model/paper_model.json"
    pm = json.loads(pm_path.read_text())
    pm["figures"] = [{"id": "F01", "paper_label": "Fig. 1", "page": 1,
                      "caption_original": "主结果图", "file": "assets/figures/f.png",
                      "supports_claims": ["C01"], "observation": "曲线重合",
                      "author_interpretation": "作者认为结果稳定", "reader_assessment": "当前条件下得到支持"}]
    pm["tables"] = [{"id": "T01", "paper_label": "Table 1", "page": 1,
                     "caption_original": "主结果表", "file": "assets/figures/f.png",
                     "supports_claims": ["C01"]}]
    pm["claims"] = [{"id": "C01", "statement": "方法在实验中得到支持",
                     "evidence": ["F01", "T01"], "epistemic": "SUPPORTED"}]
    pm_path.write_text(json.dumps(pm, ensure_ascii=False))
    source_map = json.loads((root / "model/source_map.json").read_text())
    source_map["pages"][0]["equations"] = [
        {"equation_id": "EQ-01", "page": 1, "raw_text": "L = x + y",
         "latex": "L = x + y", "source_confidence": "VERIFIED"},
        {"equation_id": "EQ-02", "page": 1, "raw_text": "x = y",
         "latex": None, "source_confidence": "UNCERTAIN",
         "fallback_asset": "assets/figures/f.png"},
    ]
    (root / "model/source_map.json").write_text(json.dumps(source_map))
    (root / "model/argument_reconstruction.json").unlink(missing_ok=True)
    report = _render(root)
    assert report["status"] == "READER_ACCEPTED", report
    html = (root / "reader/paper_reader.html").read_text()
    assert all(f"evidence-{eid}" in html for eid in ("F01", "T01", "EQ-01", "EQ-02"))
    import fitz
    pdf_text = "".join(page.get_text() for page in fitz.open(root / "reader/paper_reader.pdf"))
    assert "EQ-01" in pdf_text and "EQ-02" in pdf_text


def test_acceptance_fails_without_visual_audit(tmp_path):
    root = fixture(tmp_path)
    _render(root)
    (root / "reader/kami_audit.json").unlink()
    report = evaluate(root)
    assert report["status"] == "NEEDS_REVIEW"
    assert "missing Kami visual audit report" in report["errors"]


def test_corrupt_asset_fails_acceptance(tmp_path):
    root = fixture(tmp_path)
    _render(root)
    (root / "assets/figures/f.png").write_bytes(b"not-an-image-data")
    report = evaluate(root)
    assert report["status"] == "NEEDS_REVIEW"
    assert any("asset invalid" in e for e in report["errors"])


def test_stale_kami_audit_fails_acceptance(tmp_path):
    root = fixture(tmp_path)
    _render(root)
    audit_p = root / "reader/kami_audit.json"
    audit = json.loads(audit_p.read_text())
    audit["pdf_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    audit_p.write_text(json.dumps(audit))
    report = evaluate(root)
    assert report["status"] == "NEEDS_REVIEW"
    assert any("mismatch" in e for e in report["errors"])


def test_input_firewall_fails_on_forbidden_inputs(tmp_path):
    root = fixture(tmp_path)
    state = json.loads((root / "run_state.json").read_text()) if (root / "run_state.json").exists() else {}
    state["intent"] = "PAPER_READING"
    state["allowed_inputs"] = ["working/paper.pdf", "project/secret_notes.md"]
    (root / "run_state.json").write_text(json.dumps(state))
    _render(root)
    report = evaluate(root)
    assert report["status"] == "NEEDS_REVIEW"
    assert any("input firewall violated" in e for e in report["errors"])
