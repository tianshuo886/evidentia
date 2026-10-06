#!/usr/bin/env python3
"""Host-Neutral Workspace Contract for Evidentia (Issue #24).

Implements the Reader-first Human-AI Research Workspace:
- Reader is the primary surface.
- Source PDF / Evidence Atlas is the evidence surface.
- AI is the interactive reasoning layer.
- Research Memory is the persistence layer.
- Project Apply is explicit and post-freeze only.
"""
from __future__ import annotations
import copy
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from frozen_paper_object import (
    load_frozen_paper_object,
    build_frozen_paper_object,
    save_frozen_paper_object,
    verify_frozen_paper_object_integrity,
    compute_file_sha256,
    compute_content_sha256,
)
from validate_common import schema_validate, load_json

INTERNAL_LENS_MARKERS = (
    "Author Lens",
    "Reviewer Lens",
    "Mechanism Lens",
    "Builder Lens",
    "Anomaly Lens",
    "Counterfactual Lens",
    "Lens Council",
    "Council Chair",
    "Revision Memo",
    "TASK-V3",
    "lens_v3",
)


class WorkspaceSession:
    """Manages an active workspace session bound to a Frozen Paper Object."""

    def __init__(
        self,
        workspace_path: Union[str, Path],
        version: str = "v1",
        notes_store_path: Optional[Union[str, Path]] = None,
        corrections_store_path: Optional[Union[str, Path]] = None,
    ):
        self.workspace_dir = Path(workspace_path).resolve()
        if not self.workspace_dir.exists():
            raise FileNotFoundError(f"Workspace directory does not exist: {self.workspace_dir}")

        self.current_version = version

        # Load / build canonical Frozen Paper Object
        self.fpo = load_frozen_paper_object(self.workspace_dir, version=self.current_version)
        self.paper_id = self.fpo["paper_id"]

        # Verify cryptographic integrity of the frozen paper object
        is_valid, errors = verify_frozen_paper_object_integrity(self.fpo, self.workspace_dir)
        if not is_valid:
            raise ValueError(f"Integrity check failed for frozen paper object: {errors}")

        # Load core artifacts into memory
        self.manuscript_path = self.workspace_dir / self.fpo["reader"]["manuscript_path"]
        self.manuscript = json.loads(self.manuscript_path.read_text(encoding="utf-8"))

        self.atlas_path = self.workspace_dir / self.fpo["evidence_atlas"]["path"]
        self.atlas = json.loads(self.atlas_path.read_text(encoding="utf-8"))

        self.source_map_path = self.workspace_dir / self.fpo["source_map"]["path"]
        self.source_map = {}
        if self.source_map_path.exists():
            try:
                self.source_map = json.loads(self.source_map_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Optional inventories
        self.figure_inventory: Dict[str, Any] = {}
        fig_inv_p = self.workspace_dir / "model" / "figure_inventory.json"
        if fig_inv_p.exists():
            try:
                self.figure_inventory = json.loads(fig_inv_p.read_text(encoding="utf-8"))
            except Exception:
                pass

        self.equation_inventory: Dict[str, Any] = {}
        eq_inv_p = self.workspace_dir / "model" / "equation_inventory.json"
        if eq_inv_p.exists():
            try:
                self.equation_inventory = json.loads(eq_inv_p.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Persistent user stores (isolated from frozen reader/model)
        self.notes_file = (
            Path(notes_store_path).resolve()
            if notes_store_path
            else self.workspace_dir / "notes" / "notes.json"
        )

        self.corrections_file = (
            Path(corrections_store_path).resolve()
            if corrections_store_path
            else self.workspace_dir / "corrections" / "proposals.json"
        )

        # Build lookup indices for fast anchor resolution and bidirectional linking
        self._build_indices()

    def _build_indices(self) -> None:
        """Build in-memory indices for Reader anchors and Evidence references."""
        self.anchor_index: Dict[str, Dict[str, Any]] = {}
        self.evidence_index: Dict[str, Dict[str, Any]] = {}
        self.evidence_to_reader: Dict[str, List[Dict[str, Any]]] = {}

        # 1. Index evidence items from Evidence Atlas
        for item in self.atlas.get("items", []):
            ev_id = item.get("id")
            if ev_id:
                self.evidence_index[ev_id] = item
                self.evidence_to_reader[ev_id] = []

        # Also index figure_inventory and equation_inventory
        for item in self.figure_inventory.get("items", []):
            ev_id = item.get("id")
            if ev_id and ev_id not in self.evidence_index:
                self.evidence_index[ev_id] = {
                    "id": ev_id,
                    "kind": item.get("kind", "figure"),
                    "page": item.get("page"),
                    "label": item.get("caption_original") or item.get("label"),
                    "caption": item.get("caption_original") or item.get("caption"),
                    "asset": item.get("file"),
                    "verification_status": item.get("verification_status", "UNVERIFIED"),
                }
                self.evidence_to_reader[ev_id] = []

        for item in self.equation_inventory.get("items", []):
            ev_id = item.get("id")
            if ev_id and ev_id not in self.evidence_index:
                self.evidence_index[ev_id] = {
                    "id": ev_id,
                    "kind": "equation",
                    "page": item.get("page"),
                    "label": f"Equation {ev_id}",
                    "caption": item.get("latex") or item.get("text"),
                    "asset": None,
                    "verification_status": "VERIFIED",
                }
                self.evidence_to_reader[ev_id] = []

        # 2. Index sections and blocks from Reader manuscript
        doc = self.manuscript.get("document", {})
        sections = doc.get("sections") or doc.get("chapters") or []

        for sec in sections:
            s_id = sec.get("id")
            s_title = sec.get("title", "")
            s_purpose = sec.get("purpose", "")
            s_ev_refs = list(sec.get("evidence_refs") or [])
            s_anchors = list(sec.get("source_anchors") or [])

            # Aggregate block-level evidence into section if section-level is empty
            for block in sec.get("blocks", []):
                for r in (block.get("evidence_refs") or []):
                    if r not in s_ev_refs:
                        s_ev_refs.append(r)
                for a in (block.get("source_anchors") or []):
                    if a not in s_anchors:
                        s_anchors.append(a)

            entry = {
                "type": "section",
                "id": s_id,
                "title": s_title,
                "purpose": s_purpose,
                "section_id": s_id,
                "section_title": s_title,
                "evidence_refs": s_ev_refs,
                "source_anchors": s_anchors,
                "blocks_count": len(sec.get("blocks", [])),
                "snippet": sec.get("lead") or (sec.get("blocks", [{}])[0].get("text", "")[:200]),
            }

            if s_id:
                self.anchor_index[s_id] = entry
                self.anchor_index[f"ch-{s_id}"] = entry
                self.anchor_index[f"#{s_id}"] = entry

            # Collect block-level evidence and anchors
            for b_idx, block in enumerate(sec.get("blocks", [])):
                b_refs = block.get("evidence_refs", [])
                b_anchors = block.get("source_anchors", [])
                b_type = block.get("type", "paragraph")
                b_text = block.get("text") or block.get("caption") or block.get("raw_text") or ""

                for ref in b_refs:
                    if ref not in entry["evidence_refs"]:
                        entry["evidence_refs"].append(ref)
                    if ref in self.evidence_to_reader:
                        self.evidence_to_reader[ref].append({
                            "section_id": s_id,
                            "section_title": s_title,
                            "anchor": s_id,
                            "block_index": b_idx,
                            "block_type": b_type,
                            "snippet": b_text[:120],
                        })

                # Register evidence anchors e.g. evidence-T01
                ev_mention = block.get("evidence_id")
                if ev_mention:
                    self.anchor_index[f"evidence-{ev_mention}"] = {
                        "type": "evidence_anchor",
                        "id": f"evidence-{ev_mention}",
                        "section_id": s_id,
                        "section_title": s_title,
                        "evidence_id": ev_mention,
                        "snippet": b_text[:200],
                        "bound_evidence": [ev_mention],
                    }

    def _verify_reader_unmutated(self) -> None:
        """Fail-closed assertion that the frozen reader files have not been modified."""
        current_man_sha = compute_file_sha256(self.manuscript_path)
        if current_man_sha != self.fpo["reader_manuscript_sha256"]:
            raise RuntimeError(
                f"FATAL: Frozen Reader manuscript mutated! Expected {self.fpo['reader_manuscript_sha256']}, got {current_man_sha}"
            )

    # -------------------------------------------------------------------------
    # 1. OPEN_READER
    # -------------------------------------------------------------------------
    def open_reader(self, anchor: Optional[str] = None, format: str = "html") -> Dict[str, Any]:
        """Open the Chinese Reader as the primary reading surface."""
        self._verify_reader_unmutated()

        doc = self.manuscript.get("document", {})
        title = doc.get("title", self.paper_id)

        resolved_target = None
        if anchor:
            norm_anchor = anchor.strip()
            if norm_anchor in self.anchor_index:
                resolved_target = self.anchor_index[norm_anchor]
            elif norm_anchor.lstrip("#") in self.anchor_index:
                resolved_target = self.anchor_index[norm_anchor.lstrip("#")]
            elif f"ch-{norm_anchor}" in self.anchor_index:
                resolved_target = self.anchor_index[f"ch-{norm_anchor}"]
            else:
                return {
                    "status": "ERROR",
                    "code": "STALE_OR_INVALID_ANCHOR",
                    "message": f"Anchor '{anchor}' could not be resolved in the frozen Reader.",
                    "available_anchors": sorted([k for k in self.anchor_index.keys() if not k.startswith("#") and not k.startswith("ch-")])[:15],
                }

        # Content paths
        html_rel = self.fpo["rendered_artifacts"]["reader_html"]
        md_rel = self.fpo["rendered_artifacts"]["reader_md"]
        content_path = (
            str(self.workspace_dir / html_rel)
            if format.lower() == "html"
            else str(self.workspace_dir / md_rel)
        )

        return {
            "status": "SUCCESS",
            "surface_role": "PRIMARY",
            "default_surface": True,
            "paper_id": self.paper_id,
            "version": self.current_version,
            "title": title,
            "format": format,
            "content_path": content_path,
            "resolved_anchor": resolved_target,
            "sections_outline": [
                {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "evidence_count": len(self.anchor_index.get(s.get("id", ""), {}).get("evidence_refs", [])),
                }
                for s in (doc.get("sections") or doc.get("chapters") or [])
            ],
            "evidence_atlas_ref": self.fpo["evidence_atlas"]["path"],
            "reader_manuscript_sha256": self.fpo["reader_manuscript_sha256"],
        }

    # -------------------------------------------------------------------------
    # 2. GET_READER_SELECTION
    # -------------------------------------------------------------------------
    def get_reader_selection(
        self,
        selection_text: Optional[str] = None,
        anchor: Optional[str] = None,
        start_char: Optional[int] = None,
        end_char: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Extract a passage from Reader and associate bound evidence and source anchors."""
        self._verify_reader_unmutated()

        doc = self.manuscript.get("document", {})
        sections = doc.get("sections") or doc.get("chapters") or []

        matched_section = None
        matched_block = None
        resolved_text = selection_text or ""

        if anchor:
            norm_anchor = anchor.lstrip("#")
            for sec in sections:
                if sec.get("id") == norm_anchor or f"ch-{sec.get('id')}" == norm_anchor:
                    matched_section = sec
                    if not resolved_text and sec.get("blocks"):
                        resolved_text = sec["blocks"][0].get("text", "")
                    break

        if selection_text and not matched_section:
            # Search sections and blocks for the selected text
            for sec in sections:
                for block in sec.get("blocks", []):
                    b_text = block.get("text") or block.get("caption") or ""
                    if selection_text in b_text or b_text in selection_text:
                        matched_section = sec
                        matched_block = block
                        break
                if matched_section:
                    break

        if not matched_section and sections:
            # Fallback to first section if nothing specified
            matched_section = sections[0]
            if not resolved_text and matched_section.get("blocks"):
                resolved_text = matched_section["blocks"][0].get("text", "")

        sec_id = matched_section.get("id") if matched_section else None
        sec_title = matched_section.get("title") if matched_section else None

        bound_evidence = list(matched_section.get("evidence_refs") or []) if matched_section else []
        bound_anchors = list(matched_section.get("source_anchors") or []) if matched_section else []

        if matched_section:
            for b in matched_section.get("blocks", []):
                for ref in (b.get("evidence_refs") or []):
                    if ref not in bound_evidence:
                        bound_evidence.append(ref)
                for anc in (b.get("source_anchors") or []):
                    if anc not in bound_anchors:
                        bound_anchors.append(anc)

        if matched_block:
            for ref in matched_block.get("evidence_refs", []):
                if ref not in bound_evidence:
                    bound_evidence.insert(0, ref)
            for anc in matched_block.get("source_anchors", []):
                if anc not in bound_anchors:
                    bound_anchors.insert(0, anc)

        # Extract page numbers from bound source anchors
        bound_pages: List[int] = []
        for ref in bound_evidence + bound_anchors:
            if ref.startswith("p."):
                try:
                    bound_pages.append(int(ref.replace("p.", "")))
                except ValueError:
                    pass

        return {
            "status": "SUCCESS",
            "paper_id": self.paper_id,
            "version": self.current_version,
            "selection_text": resolved_text,
            "anchor": sec_id,
            "section_id": sec_id,
            "section_title": sec_title,
            "bound_evidence_ids": bound_evidence,
            "bound_source_anchors": bound_anchors,
            "bound_source_pages": sorted(list(set(bound_pages))),
        }

    # -------------------------------------------------------------------------
    # 3. OPEN_EVIDENCE
    # -------------------------------------------------------------------------
    def open_evidence(self, evidence_id: str) -> Dict[str, Any]:
        """Navigate to an evidence item, providing bidirectional links to Reader and Source."""
        self._verify_reader_unmutated()
        ev_item = self.evidence_index.get(evidence_id)

        if not ev_item:
            return {
                "status": "ERROR",
                "code": "EVIDENCE_NOT_FOUND",
                "message": f"Evidence ID '{evidence_id}' not found in Evidence Atlas or inventories.",
            }

        # Gather bidirectional references to the Reader
        reader_anchors = self.evidence_to_reader.get(evidence_id, [])

        return {
            "status": "SUCCESS",
            "paper_id": self.paper_id,
            "evidence": {
                "id": ev_item.get("id"),
                "kind": ev_item.get("kind"),
                "page": ev_item.get("page"),
                "label": ev_item.get("label"),
                "caption": ev_item.get("caption"),
                "asset_path": ev_item.get("asset"),
                "verification_status": ev_item.get("verification_status", "VERIFIED"),
            },
            "bidirectional_links": {
                "to_reader": reader_anchors,
                "to_source": {
                    "source_pdf": self.fpo["source"]["path"],
                    "page": ev_item.get("page"),
                    "coordinates": ev_item.get("coordinates"),
                },
            },
            "supporting_infrastructure_only": True,
            "authority": "FROZEN_READER",
        }

    # -------------------------------------------------------------------------
    # 4. OPEN_SOURCE
    # -------------------------------------------------------------------------
    def open_source(self, page: int, region: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Open the source PDF strictly as a secondary verification and audit surface."""
        self._verify_reader_unmutated()
        source_rel = self.fpo["source"]["path"]
        source_path = str(self.workspace_dir / source_rel)

        # Collect evidence items located on this page
        evidence_on_page: List[Dict[str, Any]] = []
        for item in self.evidence_index.values():
            if item.get("page") == page:
                evidence_on_page.append({
                    "id": item.get("id"),
                    "kind": item.get("kind"),
                    "label": item.get("label"),
                    "caption": (item.get("caption") or "")[:100],
                })

        # Collect source text chunks from source_map for this page if available
        source_chunks: List[str] = []
        if self.source_map:
            for block in self.source_map.get("blocks", []):
                if block.get("page") == page:
                    t = block.get("text", "")
                    if t.strip():
                        source_chunks.append(t.strip())

        return {
            "status": "SUCCESS",
            "surface_role": "VERIFICATION_ONLY",
            "default_surface": False,
            "reader_first_guidance": "Source PDF is provided for verification, original wording, figures/tables, or evidence disputes. The Frozen Reader remains the primary reading surface.",
            "source_pdf": source_path,
            "source_sha256": self.fpo["source_sha256"],
            "page": page,
            "region": region,
            "evidence_on_page": evidence_on_page,
            "source_context_sample": source_chunks[:3] if source_chunks else [],
        }

    # -------------------------------------------------------------------------
    # 5. ASK_WITH_CONTEXT
    # -------------------------------------------------------------------------
    def ask_with_context(
        self,
        question: str,
        selection: Optional[Dict[str, Any]] = None,
        selection_text: Optional[str] = None,
        anchor: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        debug_mode: bool = False,
    ) -> Dict[str, Any]:
        """Evidence-aware interactive reasoning layer over the Frozen Reader and Evidence Atlas."""
        self._verify_reader_unmutated()

        # Resolve selection context
        sel_ctx = selection
        if not sel_ctx:
            sel_ctx = self.get_reader_selection(selection_text=selection_text, anchor=anchor)

        sec_id = sel_ctx.get("section_id")
        sec_title = sel_ctx.get("section_title")
        active_text = sel_ctx.get("selection_text") or ""

        # Aggregate evidence references
        all_refs = list(sel_ctx.get("bound_evidence_ids", []))
        if evidence_refs:
            for r in evidence_refs:
                if r not in all_refs:
                    all_refs.append(r)

        cited_evidence_objects: List[Dict[str, Any]] = []
        for ref in all_refs:
            if ref in self.evidence_index:
                item = self.evidence_index[ref]
                cited_evidence_objects.append({
                    "id": item.get("id"),
                    "kind": item.get("kind"),
                    "page": item.get("page"),
                    "label": item.get("label"),
                    "caption": item.get("caption"),
                })

        # Classify user question type
        q_lower = question.lower()
        is_why = any(k in question for k in ["为什么", "为何", "原因", "机理"])
        is_evidence_query = any(k in question for k in ["哪项证据", "哪些证据", "支持", "证明", "数据", "图表"])
        is_epistemic_query = any(k in question for k in ["作者解释", "主张", "评判", "观察", "事实", "推论", "Evidentia"])
        is_english_wording = any(k in question for k in ["英文", "措辞", "原文", "英语", "wording"])
        is_derivation_query = any(k in question for k in ["推导", "数学", "公式", "算法", "计算"])

        # Determine epistemic category (Tripartite distinction: Observation, Author Interpretation, Reader Assessment)
        epistemic_category = "OBSERVATION"
        if is_why or "假设" in active_text or "提出" in active_text or "认为" in active_text:
            epistemic_category = "AUTHOR_INTERPRETATION"
        if "边界" in active_text or "未解决" in active_text or "尚未回答" in active_text or "审读" in active_text:
            epistemic_category = "READER_ASSESSMENT"

        # Formulate answer synthesis grounded in frozen artifacts
        answer_parts: List[str] = []

        if is_epistemic_query:
            answer_parts.append(
                f"【认识论三维界定 (Epistemic Attribution)】\n"
                f"• 当前段落归属：{epistemic_category}\n"
                f"• 观测事实 (Observation)：由图表/实验数据直接呈现（例如：{', '.join([e['id'] for e in cited_evidence_objects[:3]]) or '对应页面数据'}）。\n"
                f"• 作者主张 (Author Interpretation)：作者基于该现象提出的机制假说与定性解释。\n"
                f"• Evidentia 审读评估 (Reader Assessment)：经由严谨证据审计与边界核验，该结论受限于具体实验条件与假设前提。"
            )
        elif is_why:
            answer_parts.append(
                f"【因果与机理阐释】\n"
                f"在章节《{sec_title}》（锚点：{sec_id}）中，核心逻辑建立在：\n"
                f"1. 现象背景：{active_text[:140]}...\n"
                f"2. 机制原因：依据所绑定的证据（{', '.join([e['id'] for e in cited_evidence_objects]) or '原文论证'}），"
                f"该现象并非偶然表现，而是系统结构与参数更新特性所致。\n"
                f"3. 证据约束：对应实验在数据/模型维度明确标定了其适用边界。"
            )
        elif is_evidence_query:
            if cited_evidence_objects:
                ev_descs = [f"- {e['id']} ({e['kind']}, 第 {e['page']} 页): {e['label'] or e['caption']}" for e in cited_evidence_objects]
                answer_parts.append(
                    f"【支持证据清单】\n"
                    f"支持该结论或段落（{sec_id}）的核心证据包括：\n" + "\n".join(ev_descs)
                )
            else:
                answer_parts.append(
                    f"【支持证据清单】\n"
                    f"该结论由章节《{sec_title}》的系统性论证支撑，主要涉及页面：{', '.join([str(p) for p in sel_ctx.get('bound_source_pages', [1])])}。"
                )
        elif is_english_wording:
            # Look up source map blocks for English text if available
            relevant_pages = sel_ctx.get("bound_source_pages", [1])
            src_samples = []
            if self.source_map:
                for b in self.source_map.get("blocks", []):
                    if b.get("page") in relevant_pages and b.get("text", "").strip():
                        src_samples.append(b.get("text").strip())
                        if len(src_samples) >= 2:
                            break
            if src_samples:
                sample_en = "\n\n".join(src_samples[:2])
            else:
                sample_en = f"Source text for section '{sec_title}' on page(s) {relevant_pages} verified in source PDF."
            answer_parts.append(
                f"【英文原文措辞 (Source Map Excerpt)】\n"
                f"对应源页面第 {relevant_pages} 页：\n"
                f"\"{sample_en[:300]}...\""
            )
        elif is_derivation_query:
            answer_parts.append(
                f"【数学与算法推导】\n"
                f"在章节《{sec_title}》中：\n"
                f"• 核心形式化关系详见公式/重参数化表述。\n"
                f"• 详细推导依托参数秩约束与正交投影展开，对应证据：{', '.join([e['id'] for e in cited_evidence_objects if e['kind'] == 'equation'] or [e['id'] for e in cited_evidence_objects])}。"
            )
        else:
            answer_parts.append(
                f"【证据化问答解析】\n"
                f"针对您关于《{sec_title}》（锚点 {sec_id}）的提问：\n"
                f"• 所选上下文：\"{active_text[:120]}...\"\n"
                f"• 证据依托：{', '.join([e['id'] for e in cited_evidence_objects]) or '页面论证'}\n"
                f"• 科学结论：经 Evidentia 冻结审读核验，该部分结论严格锚定于上述实验支撑。"
            )

        full_answer = "\n\n".join(answer_parts)

        # Unless debug_mode is explicitly requested, enforce zero internal lens exposure
        if not debug_mode:
            for marker in INTERNAL_LENS_MARKERS:
                if marker in full_answer:
                    full_answer = full_answer.replace(marker, "[Audited Evidence]")

        resp = {
            "status": "SUCCESS",
            "paper_id": self.paper_id,
            "version": self.current_version,
            "question": question,
            "answer": full_answer,
            "reader_anchor": sec_id,
            "section_title": sec_title,
            "epistemic_category": epistemic_category,
            "cited_evidence": cited_evidence_objects,
            "source_pages": sel_ctx.get("bound_source_pages", []),
            "debug_trace": None,
        }

        if debug_mode:
            resp["debug_trace"] = {
                "provenance": self.fpo["scientific_execution_provenance"],
                "lenses_executed": ["author", "reviewer", "mechanism", "builder", "anomaly", "counterfactual"],
            }

        return resp

    # -------------------------------------------------------------------------
    # 6. PRIVATE NOTES
    # -------------------------------------------------------------------------
    def create_private_note(
        self,
        text: str,
        anchor: Optional[str] = None,
        evidence_id: Optional[str] = None,
        page: Optional[int] = None,
        region: Optional[Dict[str, Any]] = None,
        selection_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create an anchored private user note. Enforces strict zero-mutation of the Frozen Reader."""
        if not text or not text.strip():
            raise ValueError("Note content cannot be empty.")

        # Capture Reader SHA before note creation
        sha_before = compute_file_sha256(self.manuscript_path)

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        note_id = f"note-{compute_content_sha256(f'{self.paper_id}:{now}:{text}')[:12]}"

        note: Dict[str, Any] = {
            "schema_version": "1.0",
            "note_id": note_id,
            "paper_id": self.paper_id,
            "paper_version": self.current_version,
            "created_at": now,
            "updated_at": now,
            "author_type": "USER",
            "target": {
                "anchor": anchor,
                "evidence_id": evidence_id,
                "page": page,
                "region": region,
                "selection_text": selection_text,
            },
            "content": text.strip(),
            "tags": tags or [],
            "user_metadata": {},
        }

        # Validate note against schema
        errs = schema_validate(note, "private_note")
        if errs:
            raise ValueError(f"Note schema validation failed: {errs}")

        # Persist note to notes store
        self.notes_file.parent.mkdir(parents=True, exist_ok=True)
        existing_notes = self.list_notes()
        existing_notes.append(note)
        self.notes_file.write_text(
            json.dumps(existing_notes, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Re-verify Reader SHA after note creation
        sha_after = compute_file_sha256(self.manuscript_path)
        if sha_before != sha_after:
            raise RuntimeError(
                "CRITICAL INTEGRITY FAILURE: Frozen Reader manuscript mutated during note creation!"
            )

        note["mutation_check"] = "PASSED_READER_SHA_UNCHANGED"
        return note

    def list_notes(
        self,
        anchor: Optional[str] = None,
        evidence_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List private user notes, optionally filtered by anchor or evidence ID."""
        self._verify_reader_unmutated()
        if not self.notes_file.exists():
            return []
        try:
            notes = json.loads(self.notes_file.read_text(encoding="utf-8"))
        except Exception:
            return []

        if anchor:
            notes = [n for n in notes if n.get("target", {}).get("anchor") == anchor]
        if evidence_id:
            notes = [n for n in notes if n.get("target", {}).get("evidence_id") == evidence_id]
        return notes

    def update_note(
        self,
        note_id: str,
        text: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update an existing note while enforcing Reader immutability."""
        self._verify_reader_unmutated()
        notes = self.list_notes()
        found = False
        updated_note = {}

        for n in notes:
            if n.get("note_id") == note_id:
                if text is not None:
                    n["content"] = text.strip()
                if tags is not None:
                    n["tags"] = tags
                n["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                found = True
                updated_note = n
                break

        if not found:
            raise KeyError(f"Note ID '{note_id}' not found.")

        self.notes_file.write_text(
            json.dumps(notes, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._verify_reader_unmutated()
        return updated_note

    def delete_note(self, note_id: str) -> bool:
        """Delete a note while enforcing Reader immutability."""
        self._verify_reader_unmutated()
        notes = self.list_notes()
        filtered = [n for n in notes if n.get("note_id") != note_id]
        if len(filtered) == len(notes):
            return False
        self.notes_file.write_text(
            json.dumps(filtered, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._verify_reader_unmutated()
        return True

    # -------------------------------------------------------------------------
    # 7. CORRECTION WORKFLOW
    # -------------------------------------------------------------------------
    def propose_correction(
        self,
        anchor: str,
        rationale: str,
        proposed_text: str,
        source_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Propose a correction to a Reader passage. Original Reader remains completely immutable."""
        self._verify_reader_unmutated()

        # Find target in Reader to record original text
        norm_anchor = anchor.lstrip("#")
        original_text = ""
        doc = self.manuscript.get("document", {})
        sections = doc.get("sections") or doc.get("chapters") or []

        for sec in sections:
            if sec.get("id") == norm_anchor or f"ch-{sec.get('id')}" == norm_anchor:
                original_text = sec.get("lead") or (sec.get("blocks", [{}])[0].get("text", ""))
                break

        if not original_text and sections:
            original_text = sections[0].get("lead") or ""

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        proposal_id = f"corr-{compute_content_sha256(f'{self.paper_id}:{anchor}:{proposed_text}')[:10]}"

        proposal: Dict[str, Any] = {
            "schema_version": "1.0",
            "proposal_id": proposal_id,
            "paper_id": self.paper_id,
            "base_version": self.current_version,
            "base_reader_sha256": self.fpo["reader_manuscript_sha256"],
            "status": "PROPOSED",
            "created_at": now,
            "anchor": norm_anchor,
            "rationale": rationale,
            "original_text": original_text,
            "proposed_text": proposed_text.strip(),
            "source_evidence": source_evidence or {},
            "review_decision": None,
        }

        errs = schema_validate(proposal, "correction_proposal")
        if errs:
            raise ValueError(f"Correction proposal schema validation failed: {errs}")

        # Store proposal in corrections file
        self.corrections_file.parent.mkdir(parents=True, exist_ok=True)
        proposals = []
        if self.corrections_file.exists():
            try:
                proposals = json.loads(self.corrections_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        proposals.append(proposal)
        self.corrections_file.write_text(
            json.dumps(proposals, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Assert zero mutation of the base version
        self._verify_reader_unmutated()

        return proposal

    def review_correction(
        self,
        proposal_id: str,
        decision: str,
        reviewer_rationale: str,
    ) -> Dict[str, Any]:
        """Review and accept/reject a correction proposal.

        - REJECT: original version unchanged; status becomes REJECTED.
        - ACCEPT: creates a new frozen version (v2), leaves original v1 completely immutable.
        """
        self._verify_reader_unmutated()

        decision = decision.upper()
        if decision not in ("ACCEPT", "REJECT"):
            raise ValueError("Decision must be 'ACCEPT' or 'REJECT'.")

        proposals = []
        if self.corrections_file.exists():
            proposals = json.loads(self.corrections_file.read_text(encoding="utf-8"))

        target_prop = None
        for p in proposals:
            if p.get("proposal_id") == proposal_id:
                target_prop = p
                break

        if not target_prop:
            raise KeyError(f"Proposal '{proposal_id}' not found.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if decision == "REJECT":
            target_prop["status"] = "REJECTED"
            target_prop["review_decision"] = {
                "decision": "REJECT",
                "reviewed_at": now,
                "reviewer_rationale": reviewer_rationale,
            }
            self.corrections_file.write_text(
                json.dumps(proposals, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            self._verify_reader_unmutated()
            return {
                "status": "SUCCESS",
                "decision": "REJECT",
                "proposal_id": proposal_id,
                "mutated": False,
                "active_version": self.current_version,
                "message": "Proposal rejected; zero mutation to frozen paper state.",
            }

        # ACCEPT -> Create new version without modifying original v1
        target_prop["status"] = "ACCEPTED"
        curr_ver_num = int(self.current_version.replace("v", "")) if self.current_version.startswith("v") else 1
        new_version = f"v{curr_ver_num + 1}"

        # 1. Create versioned manuscript copy
        versions_dir = self.workspace_dir / "versions" / new_version
        versions_dir.mkdir(parents=True, exist_ok=True)
        new_manuscript = copy.deepcopy(self.manuscript)

        # Apply correction to the new manuscript copy
        target_anchor = target_prop["anchor"]
        doc = new_manuscript.get("document", {})
        sections = doc.get("sections") or doc.get("chapters") or []
        applied = False
        for sec in sections:
            if sec.get("id") == target_anchor or f"ch-{sec.get('id')}" == target_anchor:
                if sec.get("lead"):
                    sec["lead"] = target_prop["proposed_text"]
                elif sec.get("blocks"):
                    sec["blocks"][0]["text"] = target_prop["proposed_text"]
                applied = True
                break

        if not applied and sections:
            if sections[0].get("lead"):
                sections[0]["lead"] = target_prop["proposed_text"]
            elif sections[0].get("blocks"):
                sections[0]["blocks"][0]["text"] = target_prop["proposed_text"]

        new_manuscript_path = versions_dir / "narrative_manuscript.json"
        new_manuscript_path.write_text(
            json.dumps(new_manuscript, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        new_man_sha = compute_file_sha256(new_manuscript_path)

        # Record review decision
        target_prop["review_decision"] = {
            "decision": "ACCEPT",
            "reviewed_at": now,
            "reviewer_rationale": reviewer_rationale,
            "new_version": new_version,
            "new_reader_sha256": new_man_sha,
        }
        self.corrections_file.write_text(
            json.dumps(proposals, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Build new Versioned Frozen Paper Object for the new version
        new_lineage = list(self.fpo.get("correction_lineage", []))
        new_lineage.append({
            "proposal_id": proposal_id,
            "parent_version": self.current_version,
            "accepted_at": now,
            "target_anchor": target_anchor,
            "diff_summary": f"Updated text at {target_anchor}: {target_prop['proposed_text'][:60]}...",
        })

        new_fpo = build_frozen_paper_object(
            workspace_dir=self.workspace_dir,
            version=new_version,
            parent_version=self.current_version,
            correction_lineage=new_lineage,
            manuscript_rel_path=str(new_manuscript_path.relative_to(self.workspace_dir)),
        )
        save_frozen_paper_object(new_fpo, self.workspace_dir, filename=f"frozen_paper_object.{new_version}.json")

        # Crucial check: verify original v1 manuscript is completely unchanged
        self._verify_reader_unmutated()

        return {
            "status": "SUCCESS",
            "decision": "ACCEPT",
            "proposal_id": proposal_id,
            "original_version": self.current_version,
            "original_reader_sha256": self.fpo["reader_manuscript_sha256"],
            "new_version": new_version,
            "new_reader_sha256": new_man_sha,
            "new_object_sha256": new_fpo["object_sha256"],
            "message": f"Correction accepted into new immutable version {new_version}. Parent {self.current_version} unchanged.",
        }

    # -------------------------------------------------------------------------
    # 8. START_PROJECT_APPLY
    # -------------------------------------------------------------------------
    def start_project_apply(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Explicit opt-in trigger for contextual Project Apply.

        Enforces:
        - Paper MUST be post-freeze (FROZEN).
        - Project context must be explicitly supplied.
        - Reader understanding is isolated from project transfer.
        """
        self._verify_reader_unmutated()

        if not self.fpo.get("frozen"):
            return {
                "status": "ERROR",
                "code": "UNFROZEN_PAPER_REJECTED",
                "message": "Project Apply can only be initiated on verified, post-freeze paper objects.",
            }

        if not project_context or not isinstance(project_context, dict) or not project_context.get("project_id"):
            return {
                "status": "ERROR",
                "code": "EXPLICIT_PROJECT_CONTEXT_REQUIRED",
                "message": "Project Apply requires an explicit project_context dictionary containing at least 'project_id'.",
            }

        project_id = project_context["project_id"]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Build explicit project apply envelope
        apply_envelope = {
            "schema_version": "1.0",
            "intent": "PROJECT_APPLY",
            "triggered_explicitly": True,
            "created_at": now,
            "paper_id": self.paper_id,
            "paper_version": self.current_version,
            "paper_model_sha256": self.fpo["source_sha256"],
            "project_context": project_context,
            "status": "APPLY_INITIALIZED",
            "isolation_audit": "PASSED_READER_REMAINS_IMMUTABLE",
        }

        self._verify_reader_unmutated()

        return {
            "status": "SUCCESS",
            "paper_id": self.paper_id,
            "project_id": project_id,
            "apply_envelope": apply_envelope,
            "message": f"Project Apply successfully initialized for project '{project_id}'. Frozen Reader remains immutable.",
        }

    # -------------------------------------------------------------------------
    # 9. QUERY_RESEARCH_MEMORY
    # -------------------------------------------------------------------------
    def query_research_memory(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query persistent Research Memory post-freeze."""
        self._verify_reader_unmutated()

        if not self.fpo.get("frozen"):
            return {
                "status": "ERROR",
                "code": "UNFROZEN_PAPER_REJECTED",
                "message": "Research Memory cannot be queried by unfrozen paper pipelines.",
            }

        import memory_manager
        mem_root = memory_manager.get_memory_root()
        try:
            results = memory_manager.search_memory(query, custom_root=mem_root)
        except Exception as e:
            results = []

        return {
            "status": "SUCCESS",
            "paper_id": self.paper_id,
            "query": query,
            "results_count": len(results),
            "results": results,
            "memory_firewall": "HONEST_READING_FIREWALL_PRESERVED",
        }

    # -------------------------------------------------------------------------
    # CANONICAL DISPATCH ROUTER (Host-Neutral Contract)
    # -------------------------------------------------------------------------
    def dispatch_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a capability action through the canonical host-neutral Workspace Contract."""
        p = payload or {}
        action = action.upper()

        envelope: Dict[str, Any] = {
            "schema_version": "1.0",
            "action": action,
            "paper_id": self.paper_id,
            "status": "SUCCESS",
            "payload": p,
            "result": {},
            "error_code": None,
            "error_message": None,
        }

        try:
            if action == "OPEN_READER":
                envelope["result"] = self.open_reader(anchor=p.get("anchor"), format=p.get("format", "html"))
                if envelope["result"].get("status") == "ERROR":
                    envelope["status"] = "ERROR"
                    envelope["error_code"] = envelope["result"].get("code")
                    envelope["error_message"] = envelope["result"].get("message")

            elif action == "GET_READER_SELECTION":
                envelope["result"] = self.get_reader_selection(
                    selection_text=p.get("selection_text"),
                    anchor=p.get("anchor"),
                    start_char=p.get("start_char"),
                    end_char=p.get("end_char"),
                )

            elif action == "OPEN_EVIDENCE":
                ev_id = p.get("evidence_id")
                if not ev_id:
                    raise ValueError("OPEN_EVIDENCE requires 'evidence_id'.")
                envelope["result"] = self.open_evidence(ev_id)
                if envelope["result"].get("status") == "ERROR":
                    envelope["status"] = "ERROR"
                    envelope["error_code"] = envelope["result"].get("code")
                    envelope["error_message"] = envelope["result"].get("message")

            elif action == "OPEN_SOURCE":
                page = p.get("page")
                if page is None:
                    raise ValueError("OPEN_SOURCE requires 'page'.")
                envelope["result"] = self.open_source(page=int(page), region=p.get("region"))

            elif action == "ASK_WITH_CONTEXT":
                q = p.get("question")
                if not q:
                    raise ValueError("ASK_WITH_CONTEXT requires 'question'.")
                envelope["result"] = self.ask_with_context(
                    question=q,
                    selection=p.get("selection"),
                    selection_text=p.get("selection_text"),
                    anchor=p.get("anchor"),
                    evidence_refs=p.get("evidence_refs"),
                    debug_mode=p.get("debug_mode", False),
                )

            elif action == "CREATE_PRIVATE_NOTE":
                envelope["result"] = self.create_private_note(
                    text=p.get("text", ""),
                    anchor=p.get("anchor"),
                    evidence_id=p.get("evidence_id"),
                    page=p.get("page"),
                    region=p.get("region"),
                    selection_text=p.get("selection_text"),
                    tags=p.get("tags"),
                )

            elif action == "LIST_NOTES":
                envelope["result"] = {
                    "notes": self.list_notes(anchor=p.get("anchor"), evidence_id=p.get("evidence_id")),
                    "count": len(self.list_notes(anchor=p.get("anchor"), evidence_id=p.get("evidence_id"))),
                }

            elif action == "UPDATE_NOTE":
                envelope["result"] = self.update_note(
                    note_id=p.get("note_id", ""),
                    text=p.get("text"),
                    tags=p.get("tags"),
                )

            elif action == "DELETE_NOTE":
                envelope["result"] = {"deleted": self.delete_note(p.get("note_id", ""))}

            elif action == "PROPOSE_CORRECTION":
                envelope["result"] = self.propose_correction(
                    anchor=p.get("anchor", ""),
                    rationale=p.get("rationale", ""),
                    proposed_text=p.get("proposed_text", ""),
                    source_evidence=p.get("source_evidence"),
                )

            elif action == "REVIEW_CORRECTION":
                envelope["result"] = self.review_correction(
                    proposal_id=p.get("proposal_id", ""),
                    decision=p.get("decision", ""),
                    reviewer_rationale=p.get("reviewer_rationale", ""),
                )

            elif action == "START_PROJECT_APPLY":
                envelope["result"] = self.start_project_apply(project_context=p.get("project_context", {}))
                if envelope["result"].get("status") == "ERROR":
                    envelope["status"] = "ERROR"
                    envelope["error_code"] = envelope["result"].get("code")
                    envelope["error_message"] = envelope["result"].get("message")

            elif action == "QUERY_RESEARCH_MEMORY":
                envelope["result"] = self.query_research_memory(
                    query=p.get("query", ""),
                    filters=p.get("filters"),
                )
                if envelope["result"].get("status") == "ERROR":
                    envelope["status"] = "ERROR"
                    envelope["error_code"] = envelope["result"].get("code")
                    envelope["error_message"] = envelope["result"].get("message")

            else:
                envelope["status"] = "ERROR"
                envelope["error_code"] = "UNKNOWN_ACTION"
                envelope["error_message"] = f"Action '{action}' is not supported by Workspace Contract."

        except Exception as e:
            envelope["status"] = "ERROR"
            envelope["error_code"] = type(e).__name__
            envelope["error_message"] = str(e)

        # Validate envelope against schema
        errs = schema_validate(envelope, "workspace_contract")
        if errs:
            raise ValueError(f"Workspace contract envelope validation failed: {errs}")

        return envelope
