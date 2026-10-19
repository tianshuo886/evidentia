"""Synthetic Workspace Validation for Evidentia (Issue #24).

Exercises the full reader-first workflow on section- and chapter-shaped
manuscripts without requiring named benchmark papers or generated run outputs.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from workspace_contract import WorkspaceSession
from frozen_paper_object import compute_file_sha256

sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
from synthetic_workspace import create_synthetic_workspace

WORKSPACE_SHAPES = [
    {"id": "SYNTHETIC-SECTIONS", "document_key": "sections", "section_prefix": "s",
     "section_anchor": "s1", "evidence_id": "T01", "source_page": 2,
     "question": "为什么合成测量值随测试条件变化？"},
    {"id": "SYNTHETIC-CHAPTERS", "document_key": "chapters", "section_prefix": "SEC-",
     "section_anchor": "SEC-01", "evidence_id": "T01", "source_page": 2,
     "question": "哪项证据支持合成测量的解释？"},
]


@pytest.mark.parametrize("paper_cfg", WORKSPACE_SHAPES, ids=[p["id"] for p in WORKSPACE_SHAPES])
def test_synthetic_workspace_workflow(tmp_path, paper_cfg):
    """Execute the full interaction workflow on a tiny isolated workspace."""
    ws_copy = create_synthetic_workspace(
        tmp_path / paper_cfg["id"], paper_id=paper_cfg["id"],
        document_key=paper_cfg["document_key"], section_prefix=paper_cfg["section_prefix"],
    )

    # 1. Initialize Workspace Session
    session = WorkspaceSession(ws_copy)
    assert session.paper_id == paper_cfg["id"]

    manuscript_p = ws_copy / "reader" / "narrative_manuscript.json"
    html_p = ws_copy / "reader" / "paper_reader.html"
    initial_man_sha = compute_file_sha256(manuscript_p)
    initial_html_sha = compute_file_sha256(html_p)

    # 2. OPEN_READER (Primary Surface)
    reader_envelope = session.dispatch_action("OPEN_READER", {"anchor": paper_cfg["section_anchor"]})
    assert reader_envelope["status"] == "SUCCESS"
    r_res = reader_envelope["result"]
    assert r_res["surface_role"] == "PRIMARY"
    assert r_res["default_surface"] is True
    assert r_res["resolved_anchor"]["section_id"] == paper_cfg["section_anchor"]
    assert len(r_res["sections_outline"]) == 3

    # 3. GET_READER_SELECTION
    sel_envelope = session.dispatch_action("GET_READER_SELECTION", {"anchor": paper_cfg["section_anchor"]})
    assert sel_envelope["status"] == "SUCCESS"
    sel_res = sel_envelope["result"]
    assert sel_res["section_id"] == paper_cfg["section_anchor"]
    assert len(sel_res["selection_text"]) > 20
    assert len(sel_res["bound_evidence_ids"]) > 0

    # 4. ASK_WITH_CONTEXT (Evidence-grounded Ask)
    ask_envelope = session.dispatch_action(
        "ASK_WITH_CONTEXT",
        {
            "question": paper_cfg["question"],
            "anchor": paper_cfg["section_anchor"],
        },
    )
    assert ask_envelope["status"] == "SUCCESS"
    ask_res = ask_envelope["result"]
    assert ask_res["reader_anchor"] == paper_cfg["section_anchor"]
    assert ask_res["epistemic_category"] in ("OBSERVATION", "AUTHOR_INTERPRETATION", "READER_ASSESSMENT")
    assert len(ask_res["answer"]) > 50

    # 5. OPEN_EVIDENCE & OPEN_SOURCE (Supporting Infrastructure & Verification)
    ev_envelope = session.dispatch_action("OPEN_EVIDENCE", {"evidence_id": paper_cfg["evidence_id"]})
    assert ev_envelope["status"] == "SUCCESS"
    ev_res = ev_envelope["result"]
    assert ev_res["evidence"]["id"] == paper_cfg["evidence_id"]
    assert ev_res["bidirectional_links"]["to_source"]["page"] >= 1
    assert ev_res["authority"] == "FROZEN_READER"

    src_envelope = session.dispatch_action("OPEN_SOURCE", {"page": paper_cfg["source_page"]})
    assert src_envelope["status"] == "SUCCESS"
    src_res = src_envelope["result"]
    assert src_res["surface_role"] == "VERIFICATION_ONLY"
    assert src_res["default_surface"] is False

    # 6. CREATE_PRIVATE_NOTE (User annotation without mutating reader)
    note_envelope = session.dispatch_action(
        "CREATE_PRIVATE_NOTE",
        {
            "text": f"User research note on {paper_cfg['id']} for anchor {paper_cfg['section_anchor']}.",
            "anchor": paper_cfg["section_anchor"],
            "evidence_id": paper_cfg["evidence_id"],
        },
    )
    assert note_envelope["status"] == "SUCCESS"
    note_res = note_envelope["result"]
    assert note_res["author_type"] == "USER"
    assert note_res["mutation_check"] == "PASSED_READER_SHA_UNCHANGED"
    # Cryptographic immutability check
    assert compute_file_sha256(manuscript_p) == initial_man_sha
    assert compute_file_sha256(html_p) == initial_html_sha

    # 7. PROPOSE_CORRECTION (Non-mutating proposal)
    prop_envelope = session.dispatch_action(
        "PROPOSE_CORRECTION",
        {
            "anchor": paper_cfg["section_anchor"],
            "rationale": "Clarify notation and wording based on reinspection.",
            "proposed_text": "Updated proposed passage wording.",
        },
    )
    assert prop_envelope["status"] == "SUCCESS"
    prop_res = prop_envelope["result"]
    assert prop_res["status"] == "PROPOSED"
    assert prop_res["base_version"] == "v1"
    # Cryptographic immutability check
    assert compute_file_sha256(manuscript_p) == initial_man_sha

    # 8. START_PROJECT_APPLY (Explicit post-freeze Project Apply)
    apply_envelope = session.dispatch_action(
        "START_PROJECT_APPLY",
        {
            "project_context": {
                "project_id": "proj-synthetic-research",
                "transfer_objective": "Evaluate transferability of findings",
            }
        },
    )
    assert apply_envelope["status"] == "SUCCESS"
    apply_res = apply_envelope["result"]
    assert apply_res["project_id"] == "proj-synthetic-research"
    assert apply_res["apply_envelope"]["triggered_explicitly"] is True
    # Cryptographic immutability check
    assert compute_file_sha256(manuscript_p) == initial_man_sha
