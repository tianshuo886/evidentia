"""Deterministic tests for Reader-first Human-AI Research Workspace Contract (Issue #24).

Validates:
A. Reader-first default: raw PDF is not the primary default interaction surface.
B. Anchor resolution: valid Reader anchors resolve; stale anchors fail clearly.
C. Evidence navigation: bidirectional (Reader block -> evidence -> source, and evidence -> Reader explanation).
D. Selection-aware Ask context: selection + evidence context passed correctly; no internal lens leakage.
E. Notes isolation: note creation/update/delete does not modify Frozen Reader SHA.
F. Memory firewall: pre-freeze Honest Reading cannot access Research Memory; post-freeze only.
G. Correction immutability: proposal cannot mutate Frozen Reader; accepted creates new version/hash; rejected does not mutate.
H. Project Apply explicitness: Apply cannot start without explicit invocation.
I. Host neutrality: canonical Workspace Contract contains no Agentero-only dependency.
"""
from __future__ import annotations
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from workspace_contract import WorkspaceSession, INTERNAL_LENS_MARKERS
from frozen_paper_object import (
    load_frozen_paper_object,
    build_frozen_paper_object,
    verify_frozen_paper_object_integrity,
    compute_file_sha256,
)
from validate_common import schema_validate
import memory_manager

FIXTURE_WS = ROOT / "reader-v3-runs" / "workspaces" / "BENCH-02-LORA-ADAPTATION"


@pytest.fixture
def temp_workspace(tmp_path):
    """Isolated copy of the LoRA workspace to test mutations, notes, and corrections safely."""
    dest = tmp_path / "lora_workspace"
    shutil.copytree(FIXTURE_WS, dest)
    return dest


# -----------------------------------------------------------------------------
# A. Reader-first default
# -----------------------------------------------------------------------------
def test_a_reader_first_default(temp_workspace):
    """Verify that Reader is the primary default surface and source PDF is verification-only."""
    session = WorkspaceSession(temp_workspace)

    # 1. Opening the Reader establishes primary default surface
    reader_res = session.dispatch_action("OPEN_READER")
    assert reader_res["status"] == "SUCCESS"
    res = reader_res["result"]
    assert res["surface_role"] == "PRIMARY"
    assert res["default_surface"] is True
    assert "content_path" in res
    assert res["content_path"].endswith("paper_reader.html")

    # 2. Opening the source PDF is explicitly secondary / verification-only
    source_res = session.dispatch_action("OPEN_SOURCE", {"page": 1})
    assert source_res["status"] == "SUCCESS"
    s_res = source_res["result"]
    assert s_res["surface_role"] == "VERIFICATION_ONLY"
    assert s_res["default_surface"] is False
    assert "verification" in s_res["reader_first_guidance"].lower()


# -----------------------------------------------------------------------------
# B. Anchor resolution
# -----------------------------------------------------------------------------
def test_b_anchor_resolution(temp_workspace):
    """Verify that valid Reader anchors resolve cleanly and stale/invalid anchors fail clearly."""
    session = WorkspaceSession(temp_workspace)

    # 1. Valid section anchor
    res_s1 = session.open_reader(anchor="s1")
    assert res_s1["status"] == "SUCCESS"
    assert res_s1["resolved_anchor"]["section_id"] == "s1"
    assert "部署问题" in res_s1["resolved_anchor"]["section_title"]
    assert len(res_s1["resolved_anchor"]["evidence_refs"]) > 0

    # 2. Valid URL hash anchor "#s2"
    res_s2 = session.open_reader(anchor="#s2")
    assert res_s2["status"] == "SUCCESS"
    assert res_s2["resolved_anchor"]["section_id"] == "s2"

    # 3. Valid HTML ch- prefix anchor "ch-s3"
    res_s3 = session.open_reader(anchor="ch-s3")
    assert res_s3["status"] == "SUCCESS"
    assert res_s3["resolved_anchor"]["section_id"] == "s3"

    # 4. Stale or invalid anchor fails with STALE_OR_INVALID_ANCHOR
    res_stale = session.open_reader(anchor="unknown-section-999")
    assert res_stale["status"] == "ERROR"
    assert res_stale["code"] == "STALE_OR_INVALID_ANCHOR"
    assert "available_anchors" in res_stale
    assert len(res_stale["available_anchors"]) > 0


# -----------------------------------------------------------------------------
# C. Evidence navigation (Bidirectional)
# -----------------------------------------------------------------------------
def test_c_evidence_navigation_bidirectional(temp_workspace):
    """Verify bidirectional navigation: Reader -> Evidence -> Source and Evidence -> Reader."""
    session = WorkspaceSession(temp_workspace)

    # 1. Reader block / selection -> bound evidence IDs
    sel = session.get_reader_selection(anchor="s2")
    assert sel["status"] == "SUCCESS"
    assert "F01" in sel["bound_evidence_ids"]
    assert 4 in sel["bound_source_pages"] or 2 in sel["bound_source_pages"]

    # 2. Evidence ID -> Source location and related Reader explanation
    ev_res = session.open_evidence("F01")
    assert ev_res["status"] == "SUCCESS"
    ev = ev_res["evidence"]
    assert ev["id"] == "F01"
    assert ev["kind"] == "figure"
    assert ev["page"] == 1
    assert "Figure 1" in ev["label"]

    links = ev_res["bidirectional_links"]
    # Points to source PDF
    assert links["to_source"]["source_pdf"].endswith("paper.pdf")
    assert links["to_source"]["page"] == 1
    # Reverse points back to Reader explanation in section s2
    to_reader = links["to_reader"]
    assert len(to_reader) > 0
    assert any(r["section_id"] == "s2" for r in to_reader)

    # 3. Supporting infrastructure only; authority is Frozen Reader
    assert ev_res["supporting_infrastructure_only"] is True
    assert ev_res["authority"] == "FROZEN_READER"


# -----------------------------------------------------------------------------
# D. Selection-aware Ask context
# -----------------------------------------------------------------------------
def test_d_selection_aware_ask_context(temp_workspace):
    """Verify that selection context & evidence are passed to Ask, with zero internal lens leakage."""
    session = WorkspaceSession(temp_workspace)

    # 1. Ask "为什么" returns causal explanation citing bound evidence
    ask_why = session.ask_with_context(
        question="为什么适配首先是部署问题？",
        anchor="s1",
    )
    assert ask_why["status"] == "SUCCESS"
    assert ask_why["reader_anchor"] == "s1"
    assert len(ask_why["cited_evidence"]) > 0
    assert "T01" in [e["id"] for e in ask_why["cited_evidence"]]
    assert ask_why["epistemic_category"] in ("OBSERVATION", "AUTHOR_INTERPRETATION", "READER_ASSESSMENT")
    assert ask_why["debug_trace"] is None  # no debug leakage by default

    # 2. Verify NO internal lens markers leak in standard mode
    ans = ask_why["answer"]
    for marker in INTERNAL_LENS_MARKERS:
        assert marker not in ans, f"Internal lens marker '{marker}' leaked into user answer!"

    # 3. Ask epistemic attribution question
    ask_epistemic = session.ask_with_context(
        question="这是作者主张还是Evidentia评判？",
        anchor="s1",
    )
    assert ask_epistemic["status"] == "SUCCESS"
    assert "认识论三维界定" in ask_epistemic["answer"]
    assert "Observation" in ask_epistemic["answer"]
    assert "Author Interpretation" in ask_epistemic["answer"]

    # 4. Ask English source wording
    ask_en = session.ask_with_context(
        question="原文对应的英文措辞是什么？",
        anchor="s1",
    )
    assert ask_en["status"] == "SUCCESS"
    assert "英文原文措辞" in ask_en["answer"]

    # 5. Debug mode explicitly requested
    ask_dbg = session.ask_with_context(
        question="为什么适配首先是部署问题？",
        anchor="s1",
        debug_mode=True,
    )
    assert ask_dbg["debug_trace"] is not None
    assert "lenses_executed" in ask_dbg["debug_trace"]


# -----------------------------------------------------------------------------
# E. Notes isolation
# -----------------------------------------------------------------------------
def test_e_notes_isolation(temp_workspace):
    """Verify that private notes creation, update, and deletion never modify Frozen Reader SHA."""
    session = WorkspaceSession(temp_workspace)
    manuscript_p = temp_workspace / "reader" / "narrative_manuscript.json"
    html_p = temp_workspace / "reader" / "paper_reader.html"

    orig_man_sha = compute_file_sha256(manuscript_p)
    orig_html_sha = compute_file_sha256(html_p)

    # 1. Create private note
    note = session.create_private_note(
        text="这是测试笔记：LoRA 的 rank 参数选择与显存节约关系。",
        anchor="s2",
        evidence_id="F01",
        tags=["deployment", "memory"],
    )
    assert note["author_type"] == "USER"
    assert note["mutation_check"] == "PASSED_READER_SHA_UNCHANGED"

    # Assert SHA is 100% identical
    assert compute_file_sha256(manuscript_p) == orig_man_sha
    assert compute_file_sha256(html_p) == orig_html_sha

    # 2. List notes
    notes = session.list_notes()
    assert len(notes) == 1
    assert notes[0]["note_id"] == note["note_id"]

    # 3. Update note
    updated = session.update_note(note["note_id"], text="更新后的测试笔记文本")
    assert updated["content"] == "更新后的测试笔记文本"
    assert compute_file_sha256(manuscript_p) == orig_man_sha

    # 4. Delete note
    deleted = session.delete_note(note["note_id"])
    assert deleted is True
    assert len(session.list_notes()) == 0
    assert compute_file_sha256(manuscript_p) == orig_man_sha


# -----------------------------------------------------------------------------
# F. Memory firewall
# -----------------------------------------------------------------------------
def test_f_memory_firewall():
    """Verify that pre-freeze Honest Reading cannot access Research Memory."""
    # 1. Test memory_manager.enforce_open_reading_firewall fails if memory is in input_artifacts
    bad_task = {
        "task_id": "TASK-TEST-LEAD-READING",
        "task_type": "LEAD_READING",
        "prohibited_context": ["RESEARCH_MEMORY"],
        "input_artifacts": {"memory_db": "memory/memory.sqlite"},
    }
    ok, reason = memory_manager.enforce_open_reading_firewall(bad_task)
    assert not ok
    assert "leaked into LEAD_READING" in reason

    # 2. Test memory_manager.enforce_open_reading_firewall fails if prohibited_context misses RESEARCH_MEMORY
    unprotected_task = {
        "task_id": "TASK-TEST-LEAD-READING",
        "task_type": "LEAD_READING",
        "prohibited_context": [],
        "input_artifacts": {},
    }
    ok, reason = memory_manager.enforce_open_reading_firewall(unprotected_task)
    assert not ok
    assert "must explicitly list RESEARCH_MEMORY" in reason

    # 3. Clean task passes
    clean_task = {
        "task_id": "TASK-TEST-LEAD-READING",
        "task_type": "LEAD_READING",
        "prohibited_context": ["RESEARCH_MEMORY"],
        "input_artifacts": {"source_pdf": "source/paper.pdf"},
    }
    ok, reason = memory_manager.enforce_open_reading_firewall(clean_task)
    assert ok


# -----------------------------------------------------------------------------
# G. Correction immutability
# -----------------------------------------------------------------------------
def test_g_correction_immutability(temp_workspace):
    """Verify that corrections cannot silently mutate Frozen Reader; accepted creates new version/hash."""
    session = WorkspaceSession(temp_workspace)
    manuscript_p = temp_workspace / "reader" / "narrative_manuscript.json"
    orig_man_sha = compute_file_sha256(manuscript_p)

    # 1. Propose correction
    prop = session.propose_correction(
        anchor="s2",
        rationale="细化低秩分解关于矩阵初始化形式的说明",
        proposed_text="A矩阵采用高斯分布初始化，B矩阵置零，以确保训练初始状态增量为零。",
        source_evidence={"source_page": 2, "notes": "Section 4.1 paragraph 1"},
    )
    assert prop["status"] == "PROPOSED"
    assert prop["base_version"] == "v1"
    # Base version file MUST NOT be modified
    assert compute_file_sha256(manuscript_p) == orig_man_sha

    # 2. Reject proposal
    reject_res = session.review_correction(
        proposal_id=prop["proposal_id"],
        decision="REJECT",
        reviewer_rationale="现有表述已足够明确，暂不采纳变更。",
    )
    assert reject_res["status"] == "SUCCESS"
    assert reject_res["decision"] == "REJECT"
    assert reject_res["mutated"] is False
    assert compute_file_sha256(manuscript_p) == orig_man_sha

    # 3. Create another proposal and ACCEPT it
    prop2 = session.propose_correction(
        anchor="s2",
        rationale="修正笔误并更新准确描述",
        proposed_text="【经校对】在条件语言建模目标中，作者提出基于低秩重参数化分解矩阵增量。",
    )
    accept_res = session.review_correction(
        proposal_id=prop2["proposal_id"],
        decision="ACCEPT",
        reviewer_rationale="证据核验无误，批准合入新版本。",
    )
    assert accept_res["status"] == "SUCCESS"
    assert accept_res["decision"] == "ACCEPT"
    assert accept_res["original_version"] == "v1"
    assert accept_res["new_version"] == "v2"

    # CRITICAL: Original v1 file on disk is completely untouched!
    assert compute_file_sha256(manuscript_p) == orig_man_sha

    # New version v2 exists and has distinct hash
    v2_manuscript_p = temp_workspace / "versions" / "v2" / "narrative_manuscript.json"
    assert v2_manuscript_p.exists()
    v2_sha = compute_file_sha256(v2_manuscript_p)
    assert v2_sha != orig_man_sha
    assert accept_res["new_reader_sha256"] == v2_sha

    # Version v2 FPO exists and records correction lineage
    v2_fpo_p = temp_workspace / "reader" / "frozen_paper_object.v2.json"
    assert v2_fpo_p.exists()
    v2_fpo = json.loads(v2_fpo_p.read_text(encoding="utf-8"))
    assert v2_fpo["version"] == "v2"
    assert v2_fpo["parent_version"] == "v1"
    assert len(v2_fpo["correction_lineage"]) == 1
    assert v2_fpo["correction_lineage"][0]["proposal_id"] == prop2["proposal_id"]


# -----------------------------------------------------------------------------
# H. Project Apply explicitness
# -----------------------------------------------------------------------------
def test_h_project_apply_explicitness(temp_workspace):
    """Verify that Project Apply requires explicit invocation and context, without modifying reader."""
    session = WorkspaceSession(temp_workspace)
    manuscript_p = temp_workspace / "reader" / "narrative_manuscript.json"
    orig_man_sha = compute_file_sha256(manuscript_p)

    # 1. Missing project_context fails
    res_empty = session.start_project_apply({})
    assert res_empty["status"] == "ERROR"
    assert res_empty["code"] == "EXPLICIT_PROJECT_CONTEXT_REQUIRED"

    # 2. Explicit project_context succeeds
    proj_ctx = {
        "project_id": "proj-canopy-lora",
        "tech_stack": "PyTorch / PINN",
        "transfer_goal": "Adapt canopy inversion via low-rank layers",
    }
    res_ok = session.start_project_apply(proj_ctx)
    assert res_ok["status"] == "SUCCESS"
    assert res_ok["project_id"] == "proj-canopy-lora"
    assert res_ok["apply_envelope"]["triggered_explicitly"] is True

    # Zero mutation to the frozen reader
    assert compute_file_sha256(manuscript_p) == orig_man_sha


# -----------------------------------------------------------------------------
# I. Host neutrality
# -----------------------------------------------------------------------------
def test_i_host_neutrality(temp_workspace):
    """Verify that canonical Workspace Contract has no Agentero-only dependency and dispatches uniformly."""
    import inspect
    import workspace_contract

    # 1. Ensure workspace_contract.py does not import agentero
    src = inspect.getsource(workspace_contract)
    assert "import agentero" not in src
    assert "from agentero" not in src

    # 2. Ensure all actions validate against schema
    session = WorkspaceSession(temp_workspace)
    actions = [
        ("OPEN_READER", {"anchor": "s1"}),
        ("GET_READER_SELECTION", {"anchor": "s1"}),
        ("OPEN_EVIDENCE", {"evidence_id": "F01"}),
        ("OPEN_SOURCE", {"page": 1}),
        ("ASK_WITH_CONTEXT", {"question": "测试提问", "anchor": "s1"}),
        ("LIST_NOTES", {}),
        ("START_PROJECT_APPLY", {"project_context": {"project_id": "p1"}}),
    ]
    for action, payload in actions:
        envelope = session.dispatch_action(action, payload)
        assert envelope["status"] == "SUCCESS"
        assert not schema_validate(envelope, "workspace_contract")
