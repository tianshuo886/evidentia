"""Issue #23: Kami Boundary & Presentation Contract Test Suite.

Verifies:
1. Two papers with different scientific structures render cleanly without forcing identical chapter layouts.
2. Renderer round-trip strictly preserves semantic manuscript ordering, section titles, and lead paragraphs.
3. Evidence references (figures, tables, equations, page anchors) survive rendering without loss.
4. Material prose text is not scientifically rewritten, summarized, or substituted by the renderer.
5. Missing or invalid visual assets fail closed as BLOCKING defects.
6. Absence or failure of Kami presentation does NOT mutate the frozen scientific manuscript.
"""
import copy, hashlib, json, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))
from render_paper_reader import render_paper_reader_html, render_paper_reader_md, render_paper_reader
from validate_common import load_json, sha256
from kami_adapter import collect_kami_report

MANUSCRIPT_PAPER_A = {
    "schema_version": "3.0",
    "paper_id": "PAPER-A-THEORY",
    "source_sha256": "a" * 64,
    "created_at": "2026-10-06T00:00:00Z",
    "document": {
        "title": "有限样本表达力与泛化证伪",
        "subtitle": "数学构造理论论文",
        "paper_meta": {"authors": ["Theorist A"], "year": 2026, "venue": "COLT"},
        "sections": [
            {
                "id": "SEC-01",
                "title": "泛化悖论与容量控制危机",
                "lead_paragraph": "经典最坏情况复杂度界在过参数化网络上失效。",
                "blocks": [{"id": "B01-01", "type": "paragraph", "text": "过参数化网络轻松记忆纯噪声标签 [p.1, F01].", "evidence_refs": ["p.1", "F01"]}]
            },
            {
                "id": "SEC-02",
                "title": "定理 1 构造性证明",
                "lead_paragraph": "双层 ReLU 网络对任意离散标记的插值构造。",
                "blocks": [{"id": "B02-01", "type": "paragraph", "text": "通过标量投影与下三角求逆确立有限样本容量 [p.8].", "evidence_refs": ["p.8"]}]
            },
            {
                "id": "SEC-03",
                "title": "隐式正则化未决前沿",
                "lead_paragraph": "诚实标定科学边界。",
                "blocks": [{"id": "B03-01", "type": "paragraph", "text": "当前理论尚未给出隐式正则化算子的闭式解析表达 [p.11].", "evidence_refs": ["p.11"]}]
            }
        ]
    }
}

MANUSCRIPT_PAPER_B = {
    "schema_version": "3.0",
    "paper_id": "PAPER-B-SYSTEM",
    "source_sha256": "b" * 64,
    "created_at": "2026-10-06T00:00:00Z",
    "document": {
        "title": "低秩重参数化与生产推理服务",
        "subtitle": "系统工程论文",
        "paper_meta": {"authors": ["Engineer B"], "year": 2026, "venue": "OSDI"},
        "sections": [
            {
                "id": "SEC-01",
                "title": "部署显存墙与多租户服务开销",
                "lead_paragraph": "千亿大模型全量权重独立存储的系统瓶颈。",
                "blocks": [{"id": "B01-01", "type": "paragraph", "text": "全量独立微调导致显存与存储爆炸 [p.1].", "evidence_refs": ["p.1"]}]
            },
            {
                "id": "SEC-02",
                "title": "旁路低秩矩阵分解机制",
                "lead_paragraph": "冻结主干权重注入 BA 旁路。",
                "blocks": [{"id": "B02-01", "type": "paragraph", "text": "通过 alpha/r 缩放保证推理时无延迟合并 [p.3, F01].", "evidence_refs": ["p.3", "F01"]}]
            },
            {
                "id": "SEC-03",
                "title": "跨规模吞吐与显存实测",
                "lead_paragraph": "多机多卡测试表现。",
                "blocks": [{"id": "B03-01", "type": "paragraph", "text": "显存占用降低 3 倍而精度持平 [p.8, T04].", "evidence_refs": ["p.8", "T04"]}]
            },
            {
                "id": "SEC-04",
                "title": "Grassmann 子空间相似度投影",
                "lead_paragraph": "奇异方向主成分分析。",
                "blocks": [{"id": "B04-01", "type": "paragraph", "text": "不同秩之间的主奇异向量高度重叠 [p.9].", "evidence_refs": ["p.9"]}]
            },
            {
                "id": "SEC-05",
                "title": "服务批处理与多任务切换边界",
                "lead_paragraph": "工程实践中的限制。",
                "blocks": [{"id": "B05-01", "type": "paragraph", "text": "合并权重后同一批次中切换任务将受限 [p.12].", "evidence_refs": ["p.12"]}]
            }
        ]
    }
}

def test_different_structures_render_without_forcing_identical_chapters(tmp_path):
    root_a = tmp_path / "paper_a"
    root_b = tmp_path / "paper_b"
    root_a.mkdir()
    root_b.mkdir()

    html_a = render_paper_reader_html(MANUSCRIPT_PAPER_A, root_a)
    html_b = render_paper_reader_html(MANUSCRIPT_PAPER_B, root_b)

    # Paper A has exactly 3 scientific sections
    assert "泛化悖论与容量控制危机" in html_a
    assert "定理 1 构造性证明" in html_a
    assert "隐式正则化未决前沿" in html_a
    assert "ch-SEC-01" in html_a
    assert "ch-SEC-02" in html_a
    assert "ch-SEC-03" in html_a
    assert "ch-SEC-04" not in html_a

    # Paper B has exactly 5 scientific sections
    assert "部署显存墙与多租户服务开销" in html_b
    assert "旁路低秩矩阵分解机制" in html_b
    assert "跨规模吞吐与显存实测" in html_b
    assert "Grassmann 子空间相似度投影" in html_b
    assert "服务批处理与多任务切换边界" in html_b
    assert "ch-SEC-05" in html_b

    # Verify no template imposition (e.g. neither forced into Introduction/Related Work/Method/Experiment)
    for forced in ["Introduction", "Related Work", "Methodology", "Experiments"]:
        assert f"<h1>{forced}</h1>" not in html_a
        assert f"<h1>{forced}</h1>" not in html_b

def test_renderer_preserves_manuscript_section_order(tmp_path):
    root = tmp_path / "order_test"
    root.mkdir()
    html_out = render_paper_reader_html(MANUSCRIPT_PAPER_B, root)
    md_out = render_paper_reader_md(MANUSCRIPT_PAPER_B, root)

    # Check that sections appear in the exact planned order 1 -> 2 -> 3 -> 4 -> 5
    pos_sec1 = html_out.find("部署显存墙与多租户服务开销")
    pos_sec2 = html_out.find("旁路低秩矩阵分解机制")
    pos_sec3 = html_out.find("跨规模吞吐与显存实测")
    pos_sec4 = html_out.find("Grassmann 子空间相似度投影")
    pos_sec5 = html_out.find("服务批处理与多任务切换边界")

    assert 0 < pos_sec1 < pos_sec2 < pos_sec3 < pos_sec4 < pos_sec5

    # Check Markdown ordering as well
    m_pos1 = md_out.find("部署显存墙与多租户服务开销")
    m_pos2 = md_out.find("旁路低秩矩阵分解机制")
    m_pos3 = md_out.find("跨规模吞吐与显存实测")
    m_pos4 = md_out.find("Grassmann 子空间相似度投影")
    m_pos5 = md_out.find("服务批处理与多任务切换边界")

    assert 0 < m_pos1 < m_pos2 < m_pos3 < m_pos4 < m_pos5

def test_evidence_citations_survive_rendering(tmp_path):
    root = tmp_path / "cites_test"
    root.mkdir()
    html_out = render_paper_reader_html(MANUSCRIPT_PAPER_A, root)
    md_out = render_paper_reader_md(MANUSCRIPT_PAPER_A, root)

    # HTML must preserve local evidence links
    assert 'evidence-F01' in html_out
    assert 'p.1' in html_out
    assert 'p.8' in html_out
    assert 'p.11' in html_out

    # Markdown must preserve cites in brackets
    assert '〔p.1, F01〕' in md_out or '[p.1, F01]' in md_out

def test_prose_not_rewritten_by_renderer(tmp_path):
    root = tmp_path / "prose_test"
    root.mkdir()
    html_out = render_paper_reader_html(MANUSCRIPT_PAPER_A, root)
    
    # Exact technical phrasing authored by Lead Writer must survive intact
    assert "过参数化网络轻松记忆纯噪声标签" in html_out
    assert "双层 ReLU 网络对任意离散标记的插值构造" in html_out
    assert "通过标量投影与下三角求逆确立有限样本容量" in html_out
    assert "当前理论尚未给出隐式正则化算子的闭式解析表达" in html_out

def test_absence_of_kami_does_not_mutate_scientific_manuscript(tmp_path):
    ws = tmp_path / "immutable_test"
    ws.mkdir()
    (ws / "reader").mkdir(parents=True, exist_ok=True)
    (ws / "source").mkdir(parents=True, exist_ok=True)
    (ws / "assets/figures").mkdir(parents=True, exist_ok=True)
    (ws / "model").mkdir(parents=True, exist_ok=True)
    (ws / "source/paper.pdf").write_bytes(b"%PDF-1.4 test")

    manu_p = ws / "reader/narrative_manuscript.json"
    initial_bytes = json.dumps(MANUSCRIPT_PAPER_A, indent=2, ensure_ascii=False).encode('utf-8') + b'\n'
    manu_p.write_bytes(initial_bytes)
    initial_sha = hashlib.sha256(initial_bytes).hexdigest()

    # Render through paper_reader
    render_paper_reader(ws, kami_root=Path("/non_existent_kami_path"))

    # Manuscript content must be 100% byte-for-byte identical
    final_bytes = manu_p.read_bytes()
    final_sha = hashlib.sha256(final_bytes).hexdigest()
    assert initial_sha == final_sha, "Rendering presentation must NEVER mutate the scientific manuscript!"

def test_kami_audit_warning_classification(tmp_path):
    fake_pdf = tmp_path / "test.pdf"
    fake_html = tmp_path / "test.html"
    fake_pdf.write_bytes(b"%PDF-1.4 test")
    fake_html.write_text("<html><body>Test</body></html>", encoding="utf-8")

    report = collect_kami_report(fake_pdf, html_path=fake_html, out_dir=tmp_path)
    assert report["presentation_contract"]["presentation_only"] is True
    assert "BLOCKING / NON_BLOCKING / HUMAN_REVIEW_REQUIRED" in report["presentation_contract"]["warning_classification_policy"]
    # Broken PDF or font errors are correctly detected as BLOCKING defects
    assert report["blocking_defects_count"] > 0
    assert report["status"] == "FAIL"

def test_kami_audit_when_kami_unavailable_does_not_crash(tmp_path):
    fake_pdf = tmp_path / "test.pdf"
    fake_html = tmp_path / "test.html"
    fake_pdf.write_bytes(b"%PDF-1.4 test")
    fake_html.write_text("<html><body>Test</body></html>", encoding="utf-8")

    # Explicitly test unavailable Kami backend (clean Linux runner without Kami installed)
    report = collect_kami_report(fake_pdf, html_path=fake_html, kami_root=Path("/non_existent_kami_root"), out_dir=tmp_path)
    assert report["presentation_contract"]["presentation_only"] is True
    assert report["blocking_defects_count"] == 0
    assert report["status"] == "OK"
    checks_list = report.get("checks", report.get("results", []))
    assert any(x.get("check") == "KAMI_AVAILABILITY" for x in checks_list)

