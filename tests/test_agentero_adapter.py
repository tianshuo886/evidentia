"""Deterministic tests for Agentero Reference Adapter (Issue #25).

Validates:
- Adapter imports cleanly when Agentero is not installed
- Host availability detection (AGENTERO_AVAILABLE vs STANDALONE_FALLBACK)
- Vault layout mapping (<vault>/papers/<paper-id>/)
- Reader-first default surface enforcement
- Anchor deep-link mapping
- Evidence & source navigation
- Selection context packaging & Ask handoff
- Notes bridge & zero-mutation isolation
- Correction bridge (reject immutability & accept versioning)
- Project Apply explicitness
- Research Memory boundary
- Host neutrality
- ACP bridge tool definitions & tool dispatch
- Complete 13-step end-to-end flow on real papers (LoRA, UNSEEN-01)
"""
from __future__ import annotations
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from adapters.agentero import (
    AgenteroAdapter,
    AgenteroVaultLayout,
    is_agentero_available,
    get_agentero_tool_definitions,
    handle_acp_tool_call,
)
from frozen_paper_object import compute_file_sha256
from workspace_contract import INTERNAL_LENS_MARKERS

LORA_WS = ROOT / "reader-v3-runs" / "workspaces" / "BENCH-02-LORA-ADAPTATION"
UNSEEN_WS = ROOT / "reader-v3-runs" / "workspaces" / "UNSEEN-01-RETHINKING-GENERALIZATION"


@pytest.fixture
def temp_lora_vault(tmp_path):
    """Create an isolated Agentero-style vault layout with LoRA workspace."""
    paper_dir = tmp_path / "papers" / "BENCH-02-LORA-ADAPTATION"
    evidentia_dir = paper_dir / "evidentia"
    shutil.copytree(LORA_WS, evidentia_dir)
    # Provide synthetic Agentero paper PDF at root of paper folder
    source_pdf = evidentia_dir / "source" / "paper.pdf"
    if source_pdf.exists():
        shutil.copyfile(source_pdf, paper_dir / "BENCH-02-LORA-ADAPTATION.pdf")
    return paper_dir


@pytest.fixture
def temp_unseen_vault(tmp_path):
    """Create an isolated Agentero-style vault layout with UNSEEN-01 workspace."""
    paper_dir = tmp_path / "papers" / "UNSEEN-01-RETHINKING-GENERALIZATION"
    evidentia_dir = paper_dir / "evidentia"
    shutil.copytree(UNSEEN_WS, evidentia_dir)
    source_pdf = evidentia_dir / "source" / "paper.pdf"
    if source_pdf.exists():
        shutil.copyfile(source_pdf, paper_dir / "UNSEEN-01-RETHINKING-GENERALIZATION.pdf")
    return paper_dir


# -----------------------------------------------------------------------------
# 1. Imports and Host Availability Detection
# -----------------------------------------------------------------------------
def test_adapter_imports_and_host_detection(monkeypatch):
    """Verify adapter imports cleanly and detects host availability without error."""
    # Without environment variables or binaries, defaults to STANDALONE_FALLBACK
    monkeypatch.delenv("AGENTERO_AVAILABLE", raising=False)
    monkeypatch.delenv("AGENTERO_VAULT", raising=False)
    monkeypatch.delenv("AGENTERO_HOME", raising=False)
    assert not is_agentero_available()

    # With AGENTERO_AVAILABLE=1
    monkeypatch.setenv("AGENTERO_AVAILABLE", "1")
    assert is_agentero_available()


# -----------------------------------------------------------------------------
# 2. Vault Layout Mapping
# -----------------------------------------------------------------------------
def test_vault_layout_mapping(temp_lora_vault):
    """Verify AgenteroVaultLayout resolves paths and handles facade correctly."""
    layout = AgenteroVaultLayout(temp_lora_vault)
    assert layout.paper_id == "BENCH-02-LORA-ADAPTATION"
    assert layout.evidentia_dir.exists()
    assert layout.canonical_pdf_path.exists()
    assert layout.notes_md_path == temp_lora_vault / "NOTES.md"

    # Direct evidentia_dir target
    layout_direct = AgenteroVaultLayout(temp_lora_vault / "evidentia")
    assert layout_direct.paper_id == "BENCH-02-LORA-ADAPTATION"


# -----------------------------------------------------------------------------
# 3. Reader-First Default Surface
# -----------------------------------------------------------------------------
def test_reader_first_default(temp_lora_vault):
    """Verify opening paper defaults to Reader HTML, NOT raw PDF."""
    adapter = AgenteroAdapter(temp_lora_vault)

    # 1. Open Reader
    r = adapter.open_reader()
    assert r["status"] == "SUCCESS"
    assert r["host_action"] == "SET_ACTIVE_DOCUMENT"
    assert r["document_type"] == "READER_PRIMARY"
    assert r["surface_role"] == "PRIMARY"
    assert r["default_surface"] is True
    assert r["reader_first_enforced"] is True
    assert r["file_path"].endswith("paper_reader.html")
    assert "paper_reader.html" in r["uri"]

    # 2. Open Source is secondary/verification only
    src = adapter.open_source(page=1)
    assert src["status"] == "SUCCESS"
    assert src["host_action"] == "OPEN_PDF_PAGE"
    assert src["surface_role"] == "VERIFICATION_ONLY"
    assert src["default_surface"] is False
    assert "#page=1" in src["pdf_uri"]


# -----------------------------------------------------------------------------
# 4. Anchor Deep-Link Mapping
# -----------------------------------------------------------------------------
def test_anchor_deep_link_mapping(temp_lora_vault):
    """Verify Reader anchors resolve to valid URI fragments and target elements."""
    adapter = AgenteroAdapter(temp_lora_vault)

    # Valid anchor
    res = adapter.open_reader(anchor="s1")
    assert res["status"] == "SUCCESS"
    assert res["uri"].endswith("#s1")
    assert res["resolved_anchor"]["section_id"] == "s1"
    assert "为什么“适配”首先是部署问题" in res["resolved_anchor"]["section_title"]

    # Stale/invalid anchor
    res_stale = adapter.open_reader(anchor="invalid-section-999")
    assert res_stale["status"] == "ERROR"
    assert res_stale["code"] == "STALE_OR_INVALID_ANCHOR"
    assert len(res_stale["available_anchors"]) > 0


# -----------------------------------------------------------------------------
# 5. Evidence & Source Navigation
# -----------------------------------------------------------------------------
def test_evidence_and_source_navigation(temp_lora_vault):
    """Verify bidirectional evidence navigation and truthful gap reporting."""
    adapter = AgenteroAdapter(temp_lora_vault)

    # 1. Open evidence item
    ev = adapter.open_evidence("F01")
    assert ev["status"] == "SUCCESS"
    assert ev["host_action"] == "SHOW_EVIDENCE_CARD"
    assert ev["evidence_id"] == "F01"
    assert ev["label"] == "Figure 1"
    assert ev["asset_uri"] is not None
    assert "crop_F01" in ev["asset_uri"]
    assert len(ev["bidirectional_links"]["to_reader"]) > 0
    assert ev["authority"] == "FROZEN_READER"

    # 2. Open source page (truthful gap acknowledgement: region_overlay_supported is False)
    src = adapter.open_source(page=4, region={"x": 10, "y": 20, "w": 100, "h": 50})
    assert src["status"] == "SUCCESS"
    assert src["region_overlay_supported"] is False
    assert src["page"] == 4


# -----------------------------------------------------------------------------
# 6. Selection-Aware Ask Context & Epistemic Attribution
# -----------------------------------------------------------------------------
def test_selection_ask_context(temp_lora_vault):
    """Verify Ask receives selection + evidence context, with zero internal lens leakage."""
    adapter = AgenteroAdapter(temp_lora_vault)

    # 1. Resolve selection
    sel = adapter.get_reader_selection(anchor="s2")
    assert sel["status"] == "SUCCESS"
    assert "F01" in sel["bound_evidence_ids"]

    # 2. Ask question
    ask = adapter.ask_with_context(
        question="为什么作者采用低秩分解ΔW=BA？",
        selection=sel,
        anchor="s2",
    )
    assert ask["status"] == "SUCCESS"
    assert ask["host_action"] == "APPEND_CHAT_MESSAGE"
    assert ask["epistemic_category"] in ("OBSERVATION", "AUTHOR_INTERPRETATION", "READER_ASSESSMENT")
    assert len(ask["cited_evidence"]) > 0
    assert ask["no_internal_lens_leakage"] is True

    # Strictly assert no internal lens markers in answer text
    for marker in INTERNAL_LENS_MARKERS:
        assert marker not in ask["answer"]


# -----------------------------------------------------------------------------
# 7. Notes Bridge & Immutability Isolation
# -----------------------------------------------------------------------------
def test_notes_bridge_and_isolation(temp_lora_vault):
    """Verify notes synchronize to NOTES.md while strictly preserving FPO manuscript SHA."""
    adapter = AgenteroAdapter(temp_lora_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Create note
    res = adapter.create_private_note(
        text="这是测试研究笔记：LoRA 在部署时的参数量优势与吞吐分析。",
        anchor="s1",
        evidence_id="T01",
        tags=["deployment", "gpt2"],
    )
    assert res["status"] == "SUCCESS"
    assert res["host_action"] == "NOTE_SAVED"
    assert res["mutation_check"] == "PASSED_READER_SHA_UNCHANGED"

    # Verify NOTES.md in Agentero paper folder was synchronized
    notes_md = adapter.layout.notes_md_path
    assert notes_md.exists()
    content = notes_md.read_text(encoding="utf-8")
    assert "LoRA 在部署时的参数量优势" in content
    assert res["note_id"] in content

    # Assert 100% zero mutation of frozen Reader manuscript
    assert compute_file_sha256(man_path) == sha_orig

    # 2. List and update
    notes = adapter.list_notes()
    assert len(notes) == 1
    updated = adapter.update_note(res["note_id"], text="更新后的笔记内容")
    assert updated["status"] == "SUCCESS"
    assert compute_file_sha256(man_path) == sha_orig


# -----------------------------------------------------------------------------
# 8. Correction Bridge (Reject & Accept)
# -----------------------------------------------------------------------------
def test_correction_bridge(temp_lora_vault):
    """Verify correction proposals: reject preserves state; accept creates version v2."""
    adapter = AgenteroAdapter(temp_lora_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Propose correction
    prop = adapter.propose_correction(
        anchor="s2",
        rationale="修正重参数化矩阵维度的叙述",
        proposed_text="【经校对】在条件语言建模目标中，作者提出基于低秩重参数化分解矩阵增量。",
    )
    assert prop["status"] == "SUCCESS"
    assert prop["host_action"] == "SHOW_CORRECTION_DIFF"
    assert prop["proposal_status"] == "PROPOSED"
    assert prop["human_review_required"] is True
    assert "diff_preview" in prop
    # Manuscript file must not be modified
    assert compute_file_sha256(man_path) == sha_orig

    # 2. Reject proposal
    rej = adapter.review_correction(
        proposal_id=prop["proposal_id"],
        decision="REJECT",
        reviewer_rationale="现有表述已足够明确，暂不采纳变更。",
    )
    assert rej["status"] == "SUCCESS"
    assert rej["decision"] == "REJECT"
    assert compute_file_sha256(man_path) == sha_orig

    # 3. Create another proposal and ACCEPT it
    prop2 = adapter.propose_correction(
        anchor="s2",
        rationale="采纳校对文本",
        proposed_text="【正式合入新版本】在条件语言建模目标中，作者提出基于低秩重参数化分解矩阵增量。",
    )
    acc = adapter.review_correction(
        proposal_id=prop2["proposal_id"],
        decision="ACCEPT",
        reviewer_rationale="证据核验确认，批准合入新版本。",
    )
    assert acc["status"] == "SUCCESS"
    assert acc["decision"] == "ACCEPT"
    assert acc["active_version"] == "v2"

    # Original v1 manuscript on disk MUST REMAIN UNTOUCHED
    assert compute_file_sha256(man_path) == sha_orig

    # Version v2 exists
    v2_man_p = adapter.layout.evidentia_dir / "versions" / "v2" / "narrative_manuscript.json"
    assert v2_man_p.exists()
    assert compute_file_sha256(v2_man_p) != sha_orig


# -----------------------------------------------------------------------------
# 9. Project Apply & Research Memory Boundaries
# -----------------------------------------------------------------------------
def test_project_apply_and_memory_boundaries(temp_lora_vault):
    """Verify Apply is explicit and post-freeze only; Research Memory is protected."""
    adapter = AgenteroAdapter(temp_lora_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Apply without explicit context fails
    res_empty = adapter.start_project_apply({})
    assert res_empty["status"] == "ERROR"
    assert res_empty["code"] == "EXPLICIT_PROJECT_CONTEXT_REQUIRED"

    # 2. Apply with explicit context succeeds
    res_ok = adapter.start_project_apply({
        "project_id": "proj-canopy-lora",
        "objective": "Apply low-rank parameter updates to canopy inversion model",
    })
    assert res_ok["status"] == "SUCCESS"
    assert res_ok["host_action"] == "OPEN_APPLY_WORKSPACE"
    assert res_ok["project_id"] == "proj-canopy-lora"

    # Frozen Reader remains immutable
    assert compute_file_sha256(man_path) == sha_orig

    # 3. Memory query post-freeze succeeds without mutating reader
    mem = adapter.query_research_memory(query="low-rank adaptation")
    assert mem["status"] == "SUCCESS"
    assert mem["host_action"] == "SHOW_MEMORY_RESULTS"
    assert compute_file_sha256(man_path) == sha_orig


# -----------------------------------------------------------------------------
# 10. ACP Bridge Tool Definitions & Tool Dispatch
# -----------------------------------------------------------------------------
def test_acp_bridge_tool_definitions_and_dispatch(temp_lora_vault):
    """Verify ACP tool definitions and dispatch routing."""
    adapter = AgenteroAdapter(temp_lora_vault)
    tool_defs = get_agentero_tool_definitions()
    assert len(tool_defs) >= 7

    tool_names = [t["name"] for t in tool_defs]
    assert "open_reader" in tool_names
    assert "ask_with_context" in tool_names
    assert "open_evidence" in tool_names

    # Test tool dispatch via handle_acp_tool_call
    res = handle_acp_tool_call(adapter, "open_reader", {"anchor": "s1"})
    assert res["status"] == "SUCCESS"
    assert res["host_action"] == "SET_ACTIVE_DOCUMENT"


# -----------------------------------------------------------------------------
# 11. Complete 13-Step Real-Paper End-to-End Validation: LoRA
# -----------------------------------------------------------------------------
def test_real_paper_e2e_lora_complete_sequence(temp_lora_vault):
    """Execute complete 13-step sequence on BENCH-02-LORA-ADAPTATION."""
    adapter = AgenteroAdapter(temp_lora_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Open paper through Agentero
    # 2. Verify Reader opens as primary surface
    r = adapter.open_reader(anchor="s1")
    assert r["status"] == "SUCCESS"
    assert r["surface_role"] == "PRIMARY"
    assert r["default_surface"] is True
    assert "paper_reader.html" in r["file_path"]

    # 3. Select Reader text
    sel = adapter.get_reader_selection(anchor="s1")
    assert sel["status"] == "SUCCESS"
    assert len(sel["selection_text"]) > 20
    assert len(sel["bound_evidence_ids"]) > 0

    # 4. Ask an evidence-grounded question
    ask = adapter.ask_with_context(
        question="为什么适配首先是部署问题？",
        selection=sel,
        anchor="s1",
    )
    assert ask["status"] == "SUCCESS"
    assert "AUTHOR_INTERPRETATION" in ask["epistemic_category"]
    assert len(ask["cited_evidence"]) > 0

    # 5. Navigate to bound evidence
    ev = adapter.open_evidence("F01")
    assert ev["status"] == "SUCCESS"
    assert ev["evidence_id"] == "F01"
    assert ev["authority"] == "FROZEN_READER"

    # 6. Inspect source PDF/page
    src = adapter.open_source(page=1)
    assert src["status"] == "SUCCESS"
    assert src["surface_role"] == "VERIFICATION_ONLY"
    assert src["default_surface"] is False

    # 7. Create persistent private note
    note = adapter.create_private_note(
        text="E2E test note on LoRA deployment bottlenecks.",
        anchor="s1",
        evidence_id="T01",
    )
    assert note["status"] == "SUCCESS"
    assert adapter.layout.notes_md_path.exists()

    # 8. Verify FPO hash unchanged
    assert compute_file_sha256(man_path) == sha_orig

    # 9. Create correction proposal
    prop = adapter.propose_correction(
        anchor="s1",
        rationale="Test correction proposal for LoRA E2E validation.",
        proposed_text="Proposed replacement text for deployment section.",
    )
    assert prop["status"] == "SUCCESS"
    assert prop["proposal_status"] == "PROPOSED"

    # 10. Reject once and prove no mutation
    rej = adapter.review_correction(
        proposal_id=prop["proposal_id"],
        decision="REJECT",
        reviewer_rationale="Proved rejection leaves state unchanged.",
    )
    assert rej["decision"] == "REJECT"
    assert compute_file_sha256(man_path) == sha_orig

    # 11. Accept controlled test correction and prove new FPO version/hash
    prop2 = adapter.propose_correction(
        anchor="s1",
        rationale="Controlled correction for v2 release.",
        proposed_text="Controlled v2 text for LoRA section 1.",
    )
    acc = adapter.review_correction(
        proposal_id=prop2["proposal_id"],
        decision="ACCEPT",
        reviewer_rationale="Accepted controlled correction into v2.",
    )
    assert acc["decision"] == "ACCEPT"
    assert acc["active_version"] == "v2"
    # Original v1 remains unchanged
    assert compute_file_sha256(man_path) == sha_orig

    # 12. Invoke explicit Project Apply
    app = adapter.start_project_apply({
        "project_id": "proj-canopy-e2e",
        "focus": "Transfer LoRA rank search to canopy network",
    })
    assert app["status"] == "SUCCESS"
    assert app["project_id"] == "proj-canopy-e2e"

    # 13. Verify ordinary Reader Q&A did not receive project context
    post_ask = adapter.ask_with_context(
        question="矩阵A与B的初始化规则是什么？",
        anchor="s2",
    )
    assert "proj-canopy-e2e" not in post_ask["answer"]
    assert compute_file_sha256(man_path) == sha_orig


# -----------------------------------------------------------------------------
# 12. Complete 13-Step Real-Paper End-to-End Validation: UNSEEN-01
# -----------------------------------------------------------------------------
def test_real_paper_e2e_unseen01_complete_sequence(temp_unseen_vault):
    """Execute complete 13-step sequence on UNSEEN-01-RETHINKING-GENERALIZATION."""
    adapter = AgenteroAdapter(temp_unseen_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Open paper
    # 2. Verify Reader is primary
    r = adapter.open_reader(anchor="SEC-01")
    assert r["status"] == "SUCCESS"
    assert r["surface_role"] == "PRIMARY"

    # 3. Select text
    sel = adapter.get_reader_selection(anchor="SEC-01")
    assert sel["status"] == "SUCCESS"
    assert len(sel["selection_text"]) > 20

    # 4. Ask evidence-grounded question
    ask = adapter.ask_with_context(
        question="经典泛化理论在过参数化深度学习中为何失效？",
        selection=sel,
        anchor="SEC-01",
    )
    assert ask["status"] == "SUCCESS"

    # 5. Navigate to evidence
    ev = adapter.open_evidence("F01")
    assert ev["status"] == "SUCCESS"

    # 6. Inspect source
    src = adapter.open_source(page=1)
    assert src["status"] == "SUCCESS"
    assert src["surface_role"] == "VERIFICATION_ONLY"

    # 7. Create note
    note = adapter.create_private_note(
        text="E2E note on generalization paradox and random label fitting.",
        anchor="SEC-01",
    )
    assert note["status"] == "SUCCESS"

    # 8. Verify FPO hash unchanged
    assert compute_file_sha256(man_path) == sha_orig

    # 9. Propose correction
    prop = adapter.propose_correction(
        anchor="SEC-01",
        rationale="UNSEEN-01 correction test.",
        proposed_text="Updated wording on finite sample expressivity.",
    )
    assert prop["status"] == "SUCCESS"

    # 10. Reject once
    rej = adapter.review_correction(
        proposal_id=prop["proposal_id"],
        decision="REJECT",
        reviewer_rationale="Proved rejection.",
    )
    assert rej["decision"] == "REJECT"
    assert compute_file_sha256(man_path) == sha_orig

    # 11. Accept correction -> v2
    prop2 = adapter.propose_correction(
        anchor="SEC-01",
        rationale="Accepted correction for UNSEEN-01.",
        proposed_text="New text for UNSEEN-01 section 1.",
    )
    acc = adapter.review_correction(
        proposal_id=prop2["proposal_id"],
        decision="ACCEPT",
        reviewer_rationale="Accepted for v2.",
    )
    assert acc["decision"] == "ACCEPT"
    assert acc["active_version"] == "v2"
    assert compute_file_sha256(man_path) == sha_orig

    # 12. Invoke explicit Apply
    app = adapter.start_project_apply({
        "project_id": "proj-theory-generalization",
        "focus": "Inspect implicit regularization",
    })
    assert app["status"] == "SUCCESS"

    # 13. Verify Q&A isolation
    post_ask = adapter.ask_with_context(
        question="随机标签拟合实验得出的结论是什么？",
        anchor="SEC-02",
    )
    assert "proj-theory-generalization" not in post_ask["answer"]
    assert compute_file_sha256(man_path) == sha_orig
