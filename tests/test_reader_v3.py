import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lens_registry import select_lenses
from reader_v3_protocol import (
    create_lead_reader_task,
    create_lens_tasks,
    create_revision_memo_task,
    create_lead_writer_task,
)
from reader_v3_benchmark import create_direct_task
from validate_common import load_json, schema_validate, sha256


def _workspace(tmp_path):
    root = tmp_path / "paper"
    (root / "source").mkdir(parents=True)
    (root / "model").mkdir()
    (root / "reader").mkdir()
    (root / "source/paper.pdf").write_bytes(b"%PDF-1.4\nreader-v3-test\n%%EOF\n")
    (root / "model/source_map.json").write_text(json.dumps({"pages": []}))
    (root / "model/figure_inventory.json").write_text(json.dumps({"items": []}))
    return root


def _draft(root, paper_type="remote_sensing"):
    payload = {
        "schema_version": "1.0",
        "paper_id": "PAPER-V3",
        "source_sha256": sha256(root / "source/paper.pdf"),
        "paper_type": paper_type,
        "story_spine": {
            "central_question": "What problem is being solved?",
            "motivation": "Existing methods leave an unresolved scientific gap.",
            "prior_gap": "Prior evidence is incomplete.",
            "central_move": "The paper proposes a physically informed method.",
            "method_logic": "input -> mechanism -> prediction",
            "major_findings": ["The reported experiment supports the main claim."],
            "justified_conclusion": "The claim is supported within the tested setting.",
            "scope_and_limits": ["External validity remains open."]
        },
        "narrative": "This is a deliberately long scientific draft. " * 12,
        "decisive_evidence": [],
        "uncertainties": ["External validity remains open."],
        "open_questions": []
    }
    errs = schema_validate(payload, "paper_understanding_draft")
    assert not errs
    (root / "model/paper_understanding_draft.json").write_text(json.dumps(payload))
    return payload


def test_lens_registry_is_four_core_plus_two_adaptive():
    theory = select_lenses("theory")
    remote = select_lenses("remote_sensing")
    assert len(theory) == 6 and len(remote) == 6
    assert sum(x["kind"] == "core" for x in theory) == 4
    assert sum(x["kind"] == "specialist" for x in theory) == 2
    assert {x["id"] for x in theory if x["kind"] == "specialist"} == {
        "proof_integrity", "assumption_sensitivity"
    }
    assert {x["id"] for x in remote if x["kind"] == "specialist"} == {
        "mechanism_causality", "reproducibility_implementation"
    }
    assert "anomaly" not in {x["id"] for x in remote}
    assert "counterfactual" not in {x["id"] for x in remote}


def test_reader_v3_task_chain_is_host_neutral_and_context_isolated(tmp_path):
    root = _workspace(tmp_path)

    lead = create_lead_reader_task(root)
    lead_task = load_json(lead)
    assert lead_task["task_type"] == "LEAD_READING"
    assert lead_task["required_capability"] == "DEEP_SCIENTIFIC_READING"
    assert "model" not in lead_task
    assert "provider" not in lead_task
    assert not schema_validate(lead_task, "agent_task")

    _draft(root)
    lens_tasks = create_lens_tasks(root)
    assert len(lens_tasks) == 6
    manifest = load_json(root / "model/lens_v3_manifest.json")
    assert manifest["same_model_default"] is True
    assert manifest["context_isolated"] is True

    for p in lens_tasks:
        t = load_json(p)
        assert t["task_type"] == "LENS_V3"
        assert "lens_v3/" in t["forbidden_inputs"]
        assert "RESEARCH_MEMORY" in t["prohibited_context"]
        assert t["base_sha256"] == manifest["base_sha256"]
        assert not schema_validate(t, "agent_task")
        target = root / t["target_output"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}")

    memo_task = create_revision_memo_task(root)
    memo = load_json(memo_task)
    assert memo["task_type"] == "REVISION_MEMO"
    assert "NO_MAJORITY_VOTING" in memo["constraints"]
    assert not schema_validate(memo, "agent_task")

    (root / "model/revision_memo.json").write_text(json.dumps({
        "schema_version": "1.0",
        "paper_id": "PAPER-V3",
        "source_sha256": sha256(root / "source/paper.pdf"),
        "summary": "No critical changes.",
        "revisions": [],
        "unresolved": []
    }))

    writer_task = create_lead_writer_task(root)
    writer = load_json(writer_task)
    assert writer["task_type"] == "LEAD_WRITING"
    assert writer["target_output"] == "reader/narrative_manuscript.json"
    assert "NO_INTERNAL_PIPELINE_VOCABULARY" in writer["constraints"]
    assert not schema_validate(writer, "agent_task")


def test_direct_baseline_task_is_real_model_contract_not_synthetic_fixture(tmp_path):
    root = _workspace(tmp_path)
    p = create_direct_task(root)
    task = load_json(p)
    assert task["task_type"] == "DIRECT_READING_BASELINE"
    assert task["required_capability"] == "DEEP_SCIENTIFIC_READING"
    assert task["input_artifacts"] == {"source_pdf": "source/paper.pdf"}
    assert "model/" in task["forbidden_inputs"]
    assert "RESEARCH_MEMORY" in task["prohibited_context"]
    assert not schema_validate(task, "agent_task")


def _valid_manuscript(root):
    return {
        "schema_version": "2.0",
        "paper_id": "PAPER-V3",
        "source_sha256": sha256(root / "source/paper.pdf"),
        "created_at": "2026-10-01T00:00:00Z",
        "document": {
            "title": "Reader v3 test paper",
            "subtitle": "中文科学精读稿",
            "paper_meta": {
                "authors": ["A. Researcher"], "venue": "Test", "year": 2026,
                "doi": "", "pdf_sha256": sha256(root / "source/paper.pdf")
            },
            "executive_summary": {
                "lead": "这篇论文回答一个清晰的科学问题。",
                "takeaways": ["方法与结论均在测试范围内得到证据支持。"],
                "key_question": "核心问题是什么？",
                "core_finding": "结果支持核心主张。",
                "core_boundary": "外推仍需验证。"
            },
            "story_spine": {
                "central_question": "核心问题是什么？",
                "motivation": "现有方法存在缺口。",
                "prior_gap": "证据不完整。",
                "central_move": "提出新方法。",
                "method_logic": "输入到输出",
                "experimental_questions": ["主要实验是否支持主张？"],
                "major_findings": ["主要实验支持主张。"],
                "justified_conclusion": "在测试范围内成立。",
                "scope_and_limits": ["外推仍需验证。"]
            },
            "chapters": [{
                "id": "c1", "chapter_num": "01", "title": "论文解决了什么问题",
                "lead": "先建立研究问题与证据。",
                "blocks": [{
                    "type": "paragraph",
                    "text": "论文在来源页中明确提出研究问题，并给出相应实验。",
                    "evidence_refs": ["p.1"]
                }]
            }],
            "appendix_summary": {
                "claims_count": 0, "figures_count": 0, "tables_count": 0,
                "conflicts_count": 0, "unresolved_count": 0,
                "evidence_atlas_ref": "evidence_atlas.html"
            }
        }
    }


def test_v3_manuscript_integrity_rejects_phantom_evidence(tmp_path):
    from reader_v3 import _validate_v3_manuscript
    root = _workspace(tmp_path)
    (root / "model/source_map.json").write_text(json.dumps({
        "pages": [{"number": 1, "equations": []}]
    }))
    manuscript = _valid_manuscript(root)
    assert _validate_v3_manuscript(root, manuscript) == []
    manuscript["document"]["chapters"][0]["blocks"][0]["evidence_refs"] = ["F99"]
    errors = _validate_v3_manuscript(root, manuscript)
    assert any("unknown source evidence reference" in e for e in errors)


def test_v3_evidence_atlas_does_not_require_legacy_paper_model(tmp_path):
    from render_evidence_atlas_v3 import build_atlas
    root = _workspace(tmp_path)
    (root / "model/source_map.json").write_text(json.dumps({
        "pages": [{"number": 1, "equations": []}]
    }))
    manuscript = _valid_manuscript(root)
    (root / "reader/narrative_manuscript.json").write_text(json.dumps(manuscript))
    atlas = build_atlas(root)
    assert atlas["paper_id"] == "PAPER-V3"
    assert any(x["id"] == "p.1" for x in atlas["items"])
    assert not (root / "model/paper_model.json").exists()
