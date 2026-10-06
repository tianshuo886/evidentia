#!/usr/bin/env python3
"""Agentero Reference Adapter for Evidentia (Issue #25).

Bridges the host-neutral Evidentia Workspace Contract to Agentero:
- Vault & filesystem layout integration (<vault>/papers/<paper-id>/)
- Reader-first default surface enforcement (paper_reader.html)
- Selection-aware Ask context handoff
- Bidirectional evidence navigation
- Dual-layer private notes (structured notes.json + human NOTES.md)
- Non-mutating correction proposal & diff review bridge
- Opt-in explicit Project Apply boundary
- Optional host degradation (AGENTERO_AVAILABLE vs STANDALONE_FALLBACK)
"""
from __future__ import annotations
import difflib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from workspace_contract import WorkspaceSession, INTERNAL_LENS_MARKERS
from frozen_paper_object import compute_file_sha256
from adapters.agentero.vault_layout import AgenteroVaultLayout


def is_agentero_available() -> bool:
    """Detect whether Agentero host runtime, environment, or CLI is present."""
    if os.environ.get("AGENTERO_AVAILABLE") == "1":
        return True
    if os.environ.get("AGENTERO_VAULT") or os.environ.get("AGENTERO_HOME"):
        return True
    if shutil.which("agentero") is not None or shutil.which("agentero-cli") is not None:
        return True
    return False


class AgenteroAdapter:
    """Reference implementation of the Reader-first Workspace Contract for Agentero."""

    def __init__(
        self,
        target_path: Union[str, Path],
        version: str = "v1",
        paper_id: Optional[str] = None,
    ):
        self.layout = AgenteroVaultLayout(target_path, paper_id=paper_id)
        self.paper_id = self.layout.paper_id
        self.version = version

        # Optional host detection
        self.host_available = is_agentero_available()
        self.host_mode = "AGENTERO_AVAILABLE" if self.host_available else "STANDALONE_FALLBACK"

        # Initialize canonical Evidentia WorkspaceSession on the evidentia workspace directory
        self.session = WorkspaceSession(self.layout.evidentia_dir, version=self.version)

        # Initialize Agentero paper facade if running in or alongside an Agentero paper directory
        self.layout.ensure_agentero_facade()

    # -------------------------------------------------------------------------
    # 1. OPEN_READER (Reader-First Default)
    # -------------------------------------------------------------------------
    def open_reader(self, anchor: Optional[str] = None, format: str = "html") -> Dict[str, Any]:
        """Open the Chinese Reader as the primary reading surface in Agentero."""
        canonical_res = self.session.open_reader(anchor=anchor, format=format)
        if canonical_res.get("status") == "ERROR":
            return {
                "status": "ERROR",
                "code": canonical_res.get("code"),
                "message": canonical_res.get("message"),
                "available_anchors": canonical_res.get("available_anchors", []),
                "host_mode": self.host_mode,
            }

        content_path = canonical_res["content_path"]
        uri = Path(content_path).as_uri()
        if anchor:
            norm_anchor = anchor.lstrip("#")
            uri = f"{uri}#{norm_anchor}"

        return {
            "status": "SUCCESS",
            "host_action": "SET_ACTIVE_DOCUMENT",
            "document_type": "READER_PRIMARY",
            "surface_role": "PRIMARY",
            "default_surface": True,
            "reader_first_enforced": True,
            "paper_id": self.paper_id,
            "version": self.version,
            "title": canonical_res.get("title"),
            "format": format,
            "file_path": content_path,
            "uri": uri,
            "target_anchor": anchor,
            "resolved_anchor": canonical_res.get("resolved_anchor"),
            "sections_outline": canonical_res.get("sections_outline", []),
            "reader_manuscript_sha256": canonical_res.get("reader_manuscript_sha256"),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 2. GET_READER_SELECTION
    # -------------------------------------------------------------------------
    def get_reader_selection(
        self,
        selection_text: Optional[str] = None,
        anchor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract selected text in Reader and enrich with Evidentia bound evidence context."""
        canonical_res = self.session.get_reader_selection(
            selection_text=selection_text, anchor=anchor
        )

        return {
            "status": "SUCCESS",
            "host_action": "READER_SELECTION_RESOLVED",
            "paper_id": self.paper_id,
            "version": self.version,
            "selection_text": canonical_res.get("selection_text"),
            "anchor": canonical_res.get("anchor"),
            "section_id": canonical_res.get("section_id"),
            "section_title": canonical_res.get("section_title"),
            "bound_evidence_ids": canonical_res.get("bound_evidence_ids", []),
            "bound_source_anchors": canonical_res.get("bound_source_anchors", []),
            "bound_source_pages": canonical_res.get("bound_source_pages", []),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 3. OPEN_EVIDENCE
    # -------------------------------------------------------------------------
    def open_evidence(self, evidence_id: str) -> Dict[str, Any]:
        """Navigate to an evidence item, returning card preview and bidirectional links."""
        canonical_res = self.session.open_evidence(evidence_id)
        if canonical_res.get("status") == "ERROR":
            return {
                "status": "ERROR",
                "code": canonical_res.get("code"),
                "message": canonical_res.get("message"),
                "host_mode": self.host_mode,
            }

        ev = canonical_res["evidence"]
        asset_rel = ev.get("asset_path")
        asset_uri = (
            Path(self.layout.evidentia_dir / asset_rel).as_uri()
            if asset_rel and (self.layout.evidentia_dir / asset_rel).exists()
            else None
        )

        return {
            "status": "SUCCESS",
            "host_action": "SHOW_EVIDENCE_CARD",
            "evidence_id": evidence_id,
            "kind": ev.get("kind"),
            "label": ev.get("label"),
            "caption": ev.get("caption"),
            "page": ev.get("page"),
            "asset_uri": asset_uri,
            "verification_status": ev.get("verification_status"),
            "bidirectional_links": canonical_res.get("bidirectional_links", {}),
            "supporting_infrastructure_only": True,
            "authority": "FROZEN_READER",
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 4. OPEN_SOURCE
    # -------------------------------------------------------------------------
    def open_source(self, page: int, region: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Open source PDF in Agentero viewer strictly for verification."""
        canonical_res = self.session.open_source(page=page, region=region)
        source_pdf_p = Path(canonical_res["source_pdf"])
        uri = f"{source_pdf_p.as_uri()}#page={page}"

        return {
            "status": "SUCCESS",
            "host_action": "OPEN_PDF_PAGE",
            "surface_role": "VERIFICATION_ONLY",
            "default_surface": False,
            "reader_first_guidance": canonical_res.get("reader_first_guidance"),
            "pdf_uri": uri,
            "source_pdf": canonical_res["source_pdf"],
            "source_sha256": canonical_res["source_sha256"],
            "page": page,
            "region": region,
            "region_overlay_supported": False,  # Gap 1 documented in ISSUE25_AGENTERO_GAPS.md
            "evidence_on_page": canonical_res.get("evidence_on_page", []),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 5. ASK_WITH_CONTEXT
    # -------------------------------------------------------------------------
    def ask_with_context(
        self,
        question: str,
        selection: Optional[Dict[str, Any]] = None,
        anchor: Optional[str] = None,
        selection_text: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        debug_mode: bool = False,
    ) -> Dict[str, Any]:
        """Bridge companion agent chat with selection and bound evidence context."""
        canonical_res = self.session.ask_with_context(
            question=question,
            selection=selection,
            anchor=anchor,
            selection_text=selection_text,
            evidence_refs=evidence_refs,
            debug_mode=debug_mode,
        )

        return {
            "status": "SUCCESS",
            "host_action": "APPEND_CHAT_MESSAGE",
            "role": "assistant",
            "question": question,
            "answer": canonical_res["answer"],
            "reader_anchor": canonical_res.get("reader_anchor"),
            "section_title": canonical_res.get("section_title"),
            "epistemic_category": canonical_res.get("epistemic_category"),
            "cited_evidence": canonical_res.get("cited_evidence", []),
            "source_pages": canonical_res.get("source_pages", []),
            "debug_trace": canonical_res.get("debug_trace"),
            "no_internal_lens_leakage": not bool(
                any(m in canonical_res["answer"] for m in INTERNAL_LENS_MARKERS)
            ),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 6. PRIVATE NOTES BRIDGE
    # -------------------------------------------------------------------------
    def create_private_note(
        self,
        text: str,
        anchor: Optional[str] = None,
        evidence_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a private note, synchronizing structured record and Agentero NOTES.md."""
        note = self.session.create_private_note(
            text=text,
            anchor=anchor,
            evidence_id=evidence_id,
            tags=tags,
        )
        # Sync human-readable representation into Agentero's native NOTES.md
        self.layout.sync_note_to_markdown(note)

        return {
            "status": "SUCCESS",
            "host_action": "NOTE_SAVED",
            "note_id": note["note_id"],
            "markdown_notes_path": str(self.layout.notes_md_path),
            "structured_note": note,
            "mutation_check": note["mutation_check"],
            "host_mode": self.host_mode,
        }

    def list_notes(
        self, anchor: Optional[str] = None, evidence_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List private notes."""
        return self.session.list_notes(anchor=anchor, evidence_id=evidence_id)

    def update_note(
        self, note_id: str, text: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update a note while ensuring Reader immutability."""
        updated = self.session.update_note(note_id=note_id, text=text, tags=tags)
        return {
            "status": "SUCCESS",
            "host_action": "NOTE_UPDATED",
            "note": updated,
            "host_mode": self.host_mode,
        }

    def delete_note(self, note_id: str) -> bool:
        """Delete a note while ensuring Reader immutability."""
        deleted = self.session.delete_note(note_id=note_id)
        return deleted

    # -------------------------------------------------------------------------
    # 7. CORRECTION WORKFLOW BRIDGE
    # -------------------------------------------------------------------------
    def propose_correction(
        self,
        anchor: str,
        rationale: str,
        proposed_text: str,
        source_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Propose a correction and generate diff preview for Agentero review UI."""
        prop = self.session.propose_correction(
            anchor=anchor,
            rationale=rationale,
            proposed_text=proposed_text,
            source_evidence=source_evidence,
        )

        orig_text = prop.get("original_text", "")
        diff_lines = list(
            difflib.unified_diff(
                orig_text.splitlines(keepends=True),
                proposed_text.splitlines(keepends=True),
                fromfile=f"Reader/{anchor} (v1)",
                tofile=f"Reader/{anchor} (Proposed)",
            )
        )
        diff_preview = "".join(diff_lines) or f"- {orig_text}\n+ {proposed_text}\n"

        return {
            "status": "SUCCESS",
            "host_action": "SHOW_CORRECTION_DIFF",
            "proposal_id": prop["proposal_id"],
            "proposal_status": prop["status"],
            "anchor": prop["anchor"],
            "rationale": prop["rationale"],
            "diff_preview": diff_preview,
            "base_version": prop["base_version"],
            "human_review_required": True,
            "host_mode": self.host_mode,
        }

    def review_correction(
        self,
        proposal_id: str,
        decision: str,
        reviewer_rationale: str,
    ) -> Dict[str, Any]:
        """Review correction proposal through Agentero review actions (ACCEPT/REJECT)."""
        rev_res = self.session.review_correction(
            proposal_id=proposal_id,
            decision=decision,
            reviewer_rationale=reviewer_rationale,
        )

        return {
            "status": "SUCCESS",
            "host_action": "CORRECTION_REVIEW_RECORDED",
            "decision": rev_res.get("decision"),
            "proposal_id": proposal_id,
            "active_version": rev_res.get("new_version") or rev_res.get("active_version"),
            "original_version": rev_res.get("original_version") or self.version,
            "message": rev_res.get("message"),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 8. PROJECT APPLY BRIDGE
    # -------------------------------------------------------------------------
    def start_project_apply(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Explicitly trigger Project Apply post-freeze."""
        apply_res = self.session.start_project_apply(project_context=project_context)
        if apply_res.get("status") == "ERROR":
            return {
                "status": "ERROR",
                "code": apply_res.get("code"),
                "message": apply_res.get("message"),
                "host_mode": self.host_mode,
            }

        return {
            "status": "SUCCESS",
            "host_action": "OPEN_APPLY_WORKSPACE",
            "project_id": apply_res.get("project_id"),
            "apply_envelope": apply_res.get("apply_envelope"),
            "message": apply_res.get("message"),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # 9. RESEARCH MEMORY BRIDGE
    # -------------------------------------------------------------------------
    def query_research_memory(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query persistent cross-paper research memory."""
        mem_res = self.session.query_research_memory(query=query, filters=filters)
        return {
            "status": "SUCCESS",
            "host_action": "SHOW_MEMORY_RESULTS",
            "query": query,
            "results_count": mem_res.get("results_count", 0),
            "results": mem_res.get("results", []),
            "host_mode": self.host_mode,
        }

    # -------------------------------------------------------------------------
    # UNIVERSAL ACTION DISPATCHER
    # -------------------------------------------------------------------------
    def dispatch_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Universal entry point for ACP / MCP tool invocation."""
        p = payload or {}
        act = action.upper()

        if act == "OPEN_READER":
            return self.open_reader(anchor=p.get("anchor"), format=p.get("format", "html"))
        elif act == "GET_READER_SELECTION":
            return self.get_reader_selection(
                selection_text=p.get("selection_text"), anchor=p.get("anchor")
            )
        elif act == "OPEN_EVIDENCE":
            return self.open_evidence(p.get("evidence_id", ""))
        elif act == "OPEN_SOURCE":
            return self.open_source(page=p.get("page", 1), region=p.get("region"))
        elif act == "ASK_WITH_CONTEXT":
            return self.ask_with_context(
                question=p.get("question", ""),
                selection=p.get("selection"),
                anchor=p.get("anchor"),
                selection_text=p.get("selection_text"),
                evidence_refs=p.get("evidence_refs"),
                debug_mode=p.get("debug_mode", False),
            )
        elif act == "CREATE_PRIVATE_NOTE":
            return self.create_private_note(
                text=p.get("text", ""),
                anchor=p.get("anchor"),
                evidence_id=p.get("evidence_id"),
                tags=p.get("tags"),
            )
        elif act == "LIST_NOTES":
            return {
                "status": "SUCCESS",
                "notes": self.list_notes(anchor=p.get("anchor"), evidence_id=p.get("evidence_id")),
            }
        elif act == "UPDATE_NOTE":
            return self.update_note(note_id=p.get("note_id", ""), text=p.get("text"), tags=p.get("tags"))
        elif act == "DELETE_NOTE":
            return {"status": "SUCCESS", "deleted": self.delete_note(p.get("note_id", ""))}
        elif act == "PROPOSE_CORRECTION":
            return self.propose_correction(
                anchor=p.get("anchor", ""),
                rationale=p.get("rationale", ""),
                proposed_text=p.get("proposed_text", ""),
                source_evidence=p.get("source_evidence"),
            )
        elif act == "REVIEW_CORRECTION":
            return self.review_correction(
                proposal_id=p.get("proposal_id", ""),
                decision=p.get("decision", ""),
                reviewer_rationale=p.get("reviewer_rationale", ""),
            )
        elif act == "START_PROJECT_APPLY":
            return self.start_project_apply(project_context=p.get("project_context", {}))
        elif act == "QUERY_RESEARCH_MEMORY":
            return self.query_research_memory(query=p.get("query", ""), filters=p.get("filters"))
        else:
            return {
                "status": "ERROR",
                "code": "UNKNOWN_ACTION",
                "message": f"Action '{action}' not recognized by AgenteroAdapter.",
            }
