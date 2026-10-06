"""Real-Paper Workspace Validation for Evidentia (Issue #24).

Validates host-neutral workspace interaction workflows on three structurally diverse real papers:
1. BENCH-02-LORA-ADAPTATION (Empirical NLP / LLM adaptation)
2. BENCH-04-ALPHAFOLD2-STRUCTURE (Biomolecular / structural prediction breakthrough)
3. UNSEEN-01-RETHINKING-GENERALIZATION (Theoretical / empirical generalization paradox)

Demonstrates on each paper:
- Open Reader (primary surface)
- Select passage & resolve bound evidence
- Ask evidence-grounded question
- Open supporting evidence & source page
- Create private user note (isolated from reader)
- Propose correction without mutating Reader
- Explicit Project Apply entry
"""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from workspace_contract import WorkspaceSession
from frozen_paper_object import compute_file_sha256

PAPERS = [
    {
        "id": "BENCH-02-LORA-ADAPTATION",
        "section_anchor": "s1",
        "evidence_id": "F01",
        "source_page": 1,
        "question": "为什么适配首先是部署问题？",
    },
    {
        "id": "BENCH-04-ALPHAFOLD2-STRUCTURE",
        "section_anchor": "s1",
        "evidence_id": "F01",
        "source_page": 2,
        "question": "AlphaFold在CASP14盲测中展示的核心精度尺度是什么？",
    },
    {
        "id": "UNSEEN-01-RETHINKING-GENERALIZATION",
        "section_anchor": "SEC-01",
        "evidence_id": "F01",
        "source_page": 1,
        "question": "经典泛化理论在过参数化深度学习中为何失效？",
    },
]


@pytest.mark.parametrize("paper_cfg", PAPERS, ids=[p["id"] for p in PAPERS])
def test_real_paper_workspace_workflow(tmp_path, paper_cfg):
    """Execute complete 7-step workspace interaction workflow on a real paper fixture."""
    src_ws = ROOT / "reader-v3-runs" / "workspaces" / paper_cfg["id"]
    assert src_ws.exists(), f"Source workspace missing: {src_ws}"

    # Isolate in temp directory to guarantee zero contamination of source fixtures
    ws_copy = tmp_path / paper_cfg["id"]
    shutil.copytree(src_ws, ws_copy)

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
    assert len(r_res["sections_outline"]) >= 5

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
                "project_id": "proj-canopy-research",
                "transfer_objective": "Evaluate transferability of findings",
            }
        },
    )
    assert apply_envelope["status"] == "SUCCESS"
    apply_res = apply_envelope["result"]
    assert apply_res["project_id"] == "proj-canopy-research"
    assert apply_res["apply_envelope"]["triggered_explicitly"] is True
    # Cryptographic immutability check
    assert compute_file_sha256(manuscript_p) == initial_man_sha
