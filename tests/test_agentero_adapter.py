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
- Complete 13-step end-to-end flow on synthetic section and chapter manuscripts
"""
from __future__ import annotations
import json
import shutil
import sys
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

sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
from synthetic_workspace import PAPER_ID, SECTION_TITLE, create_synthetic_workspace


@pytest.fixture
def temp_synthetic_vault(tmp_path):
    """Create an isolated Agentero vault using only small synthetic artifacts."""
    paper_dir = tmp_path / "papers" / PAPER_ID
    evidentia_dir = create_synthetic_workspace(paper_dir / "evidentia")
    shutil.copyfile(evidentia_dir / "source/paper.pdf", paper_dir / f"{PAPER_ID}.pdf")
    return paper_dir


@pytest.fixture
def temp_chapter_vault(tmp_path):
    """Exercise chapter manuscripts and alternate anchors with synthetic content."""
    paper_id = "SYNTHETIC-CHAPTER-PAPER"
    paper_dir = tmp_path / "papers" / paper_id
    evidentia_dir = create_synthetic_workspace(
        paper_dir / "evidentia", paper_id=paper_id,
        section_prefix="SEC-", document_key="chapters",
    )
    shutil.copyfile(evidentia_dir / "source/paper.pdf", paper_dir / f"{paper_id}.pdf")
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
def test_vault_layout_mapping(temp_synthetic_vault):
    """Verify AgenteroVaultLayout resolves paths and handles facade correctly."""
    layout = AgenteroVaultLayout(temp_synthetic_vault)
    assert layout.paper_id == "SYNTHETIC-PAPER"
    assert layout.evidentia_dir.exists()
    assert layout.canonical_pdf_path.exists()
    assert layout.notes_md_path == temp_synthetic_vault / "NOTES.md"

    # Direct evidentia_dir target
    layout_direct = AgenteroVaultLayout(temp_synthetic_vault / "evidentia")
    assert layout_direct.paper_id == "SYNTHETIC-PAPER"


# -----------------------------------------------------------------------------
# 3. Reader-First Default Surface
# -----------------------------------------------------------------------------
def test_reader_first_default(temp_synthetic_vault):
    """Verify opening paper defaults to Reader HTML, NOT raw PDF."""
    adapter = AgenteroAdapter(temp_synthetic_vault)

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
def test_anchor_deep_link_mapping(temp_synthetic_vault):
    """Verify Reader anchors resolve to valid URI fragments and target elements."""
    adapter = AgenteroAdapter(temp_synthetic_vault)

    # Valid anchor
    res = adapter.open_reader(anchor="s1")
    assert res["status"] == "SUCCESS"
    assert res["uri"].endswith("#s1")
    assert res["resolved_anchor"]["section_id"] == "s1"
    assert res["resolved_anchor"]["section_title"] == SECTION_TITLE

    # Stale/invalid anchor
    res_stale = adapter.open_reader(anchor="invalid-section-999")
    assert res_stale["status"] == "ERROR"
    assert res_stale["code"] == "STALE_OR_INVALID_ANCHOR"
    assert len(res_stale["available_anchors"]) > 0


# -----------------------------------------------------------------------------
# 5. Evidence & Source Navigation
# -----------------------------------------------------------------------------
def test_evidence_and_source_navigation(temp_synthetic_vault):
    """Verify bidirectional evidence navigation and truthful gap reporting."""
    adapter = AgenteroAdapter(temp_synthetic_vault)

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
    src = adapter.open_source(page=2, region={"x": 10, "y": 20, "w": 100, "h": 50})
    assert src["status"] == "SUCCESS"
    assert src["region_overlay_supported"] is False
    assert src["page"] == 2


# -----------------------------------------------------------------------------
# 6. Selection-Aware Ask Context & Epistemic Attribution
# -----------------------------------------------------------------------------
def test_selection_ask_context(temp_synthetic_vault):
    """Verify Ask receives selection + evidence context, with zero internal lens leakage."""
    adapter = AgenteroAdapter(temp_synthetic_vault)

    # 1. Resolve selection
    sel = adapter.get_reader_selection(anchor="s2")
    assert sel["status"] == "SUCCESS"
    assert "F01" in sel["bound_evidence_ids"]

    # 2. Ask question
    ask = adapter.ask_with_context(
        question="为什么合成测量值随测试条件变化？",
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
def test_notes_bridge_and_isolation(temp_synthetic_vault):
    """Verify notes synchronize to NOTES.md while strictly preserving FPO manuscript SHA."""
    adapter = AgenteroAdapter(temp_synthetic_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Create note
    res = adapter.create_private_note(
        text="这是测试研究笔记：合成测量的变化与测试条件。",
        anchor="s1",
        evidence_id="T01",
        tags=["measurement", "synthetic"],
    )
    assert res["status"] == "SUCCESS"
    assert res["host_action"] == "NOTE_SAVED"
    assert res["mutation_check"] == "PASSED_READER_SHA_UNCHANGED"

    # Verify NOTES.md in Agentero paper folder was synchronized
    notes_md = adapter.layout.notes_md_path
    assert notes_md.exists()
    content = notes_md.read_text(encoding="utf-8")
    assert "合成测量的变化" in content
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
def test_correction_bridge(temp_synthetic_vault):
    """Verify correction proposals: reject preserves state; accept creates version v2."""
    adapter = AgenteroAdapter(temp_synthetic_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Propose correction
    prop = adapter.propose_correction(
        anchor="s2",
        rationale="修正合成测量条件的叙述",
        proposed_text="【经校对】作者提出测试条件变化可以解释合成测量值的变化。",
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
        proposed_text="【正式合入新版本】作者提出测试条件变化可以解释合成测量值的变化。",
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
def test_project_apply_and_memory_boundaries(temp_synthetic_vault, tmp_path, monkeypatch):
    """Verify Apply is explicit and post-freeze only; Research Memory is protected."""
    adapter = AgenteroAdapter(temp_synthetic_vault)
    man_path = adapter.layout.evidentia_dir / "reader" / "narrative_manuscript.json"
    sha_orig = compute_file_sha256(man_path)

    # 1. Apply without explicit context fails
    res_empty = adapter.start_project_apply({})
    assert res_empty["status"] == "ERROR"
    assert res_empty["code"] == "EXPLICIT_PROJECT_CONTEXT_REQUIRED"

    # 2. Apply with explicit context succeeds
    res_ok = adapter.start_project_apply({
        "project_id": "proj-synthetic",
        "objective": "Apply the synthetic measurement procedure to a test project",
    })
    assert res_ok["status"] == "SUCCESS"
    assert res_ok["host_action"] == "OPEN_APPLY_WORKSPACE"
    assert res_ok["project_id"] == "proj-synthetic"

    # Frozen Reader remains immutable
    assert compute_file_sha256(man_path) == sha_orig

    # 3. Memory query uses an isolated empty store, never the real research memory.
    import memory_manager
    monkeypatch.setattr(memory_manager, "DEFAULT_MEMORY_ROOT", tmp_path / "memory")
    mem = adapter.query_research_memory(query="synthetic measurement")
    assert mem["status"] == "SUCCESS"
    assert mem["host_action"] == "SHOW_MEMORY_RESULTS"
    assert mem["results_count"] == 0
    assert compute_file_sha256(man_path) == sha_orig


# -----------------------------------------------------------------------------
# 10. ACP Bridge Tool Definitions & Tool Dispatch
# -----------------------------------------------------------------------------
def test_acp_bridge_tool_definitions_and_dispatch(temp_synthetic_vault):
    """Verify ACP tool definitions and dispatch routing."""
    adapter = AgenteroAdapter(temp_synthetic_vault)
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
# 11. Complete 13-Step Synthetic Workspace End-to-End Validation: synthetic measurements
# -----------------------------------------------------------------------------
def test_synthetic_e2e_sections_complete_sequence(temp_synthetic_vault):
    """Execute complete 13-step sequence on SYNTHETIC-PAPER."""
    adapter = AgenteroAdapter(temp_synthetic_vault)
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
        question="为什么合成测量值随测试条件变化？",
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
        text="E2E test note on synthetic measurement conditions.",
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
        rationale="Test correction proposal for synthetic measurements E2E validation.",
        proposed_text="Proposed replacement text for measurement section.",
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
        proposed_text="Controlled v2 text for synthetic measurements section 1.",
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
        "project_id": "proj-synthetic-e2e",
        "focus": "Transfer the synthetic measurement procedure",
    })
    assert app["status"] == "SUCCESS"
    assert app["project_id"] == "proj-synthetic-e2e"

    # 13. Verify ordinary Reader Q&A did not receive project context
    post_ask = adapter.ask_with_context(
        question="测试条件是如何定义的？",
        anchor="s2",
    )
    assert "proj-synthetic-e2e" not in post_ask["answer"]
    assert compute_file_sha256(man_path) == sha_orig


# -----------------------------------------------------------------------------
# 12. Complete 13-Step Synthetic Workspace End-to-End Validation: chapter workspace
# -----------------------------------------------------------------------------
def test_synthetic_e2e_chapters_complete_sequence(temp_chapter_vault):
    """Execute complete 13-step sequence on SYNTHETIC-CHAPTER-PAPER."""
    adapter = AgenteroAdapter(temp_chapter_vault)
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
        question="为什么合成测量值随测试条件变化？",
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
        text="E2E note on synthetic observations and test conditions.",
        anchor="SEC-01",
    )
    assert note["status"] == "SUCCESS"

    # 8. Verify FPO hash unchanged
    assert compute_file_sha256(man_path) == sha_orig

    # 9. Propose correction
    prop = adapter.propose_correction(
        anchor="SEC-01",
        rationale="chapter workspace correction test.",
        proposed_text="Updated wording on synthetic test conditions.",
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
        rationale="Accepted correction for chapter workspace.",
        proposed_text="New text for chapter workspace section 1.",
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
        "project_id": "proj-synthetic-chapters",
        "focus": "Inspect synthetic measurement conditions",
    })
    assert app["status"] == "SUCCESS"

    # 13. Verify Q&A isolation
    post_ask = adapter.ask_with_context(
        question="合成测量实验得出的结论是什么？",
        anchor="SEC-02",
    )
    assert "proj-synthetic-chapters" not in post_ask["answer"]
    assert compute_file_sha256(man_path) == sha_orig
