#!/usr/bin/env python3
"""Agentero Vault Layout and Path Resolution for Evidentia.

Maps between Agentero's local-first vault structure and Evidentia's workspace conventions:
<vault>/papers/<paper-id>/
├── <paper-id>.pdf
├── NOTES.md
├── marks/
└── evidentia/
    ├── reader/
    ├── model/
    ├── source/
    └── notes/
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

ROOT = Path(__file__).resolve().parents[2]


class AgenteroVaultLayout:
    """Resolves and manages directory mapping between an Agentero paper vault and Evidentia."""

    def __init__(self, target_path: Path | str, paper_id: Optional[str] = None):
        self.raw_path = Path(target_path).resolve()
        self._paper_id = paper_id
        self._resolve_paths()

    def _resolve_paths(self) -> None:
        """Detect whether target_path is an Evidentia workspace, an Agentero paper dir, or a vault root."""
        # Case 1: Directly points to an Evidentia workspace (contains reader/ or source/)
        if (self.raw_path / "reader").exists() or (self.raw_path / "source").exists():
            self.evidentia_dir = self.raw_path
            # Parent might be an Agentero paper dir or arbitrary directory
            self.paper_dir = self.raw_path.parent if self.raw_path.name == "evidentia" else self.raw_path
            self.paper_id = self._paper_id or self.evidentia_dir.name
            if self.evidentia_dir.name == "evidentia":
                self.paper_id = self._paper_id or self.paper_dir.name
            self.vault_dir = self.paper_dir.parent.parent if self.paper_dir.parent.name == "papers" else self.paper_dir.parent
            return

        # Case 2: Points to an Agentero paper directory containing evidentia/ subfolder
        if (self.raw_path / "evidentia").exists():
            self.paper_dir = self.raw_path
            self.evidentia_dir = self.raw_path / "evidentia"
            self.paper_id = self._paper_id or self.paper_dir.name
            self.vault_dir = self.paper_dir.parent.parent if self.paper_dir.parent.name == "papers" else self.paper_dir.parent
            return

        # Case 3: Points to an Agentero paper directory without evidentia/ yet
        self.paper_dir = self.raw_path
        self.evidentia_dir = self.raw_path / "evidentia"
        self.paper_id = self._paper_id or self.paper_dir.name
        self.vault_dir = self.paper_dir.parent.parent if self.paper_dir.parent.name == "papers" else self.paper_dir.parent

    @property
    def notes_md_path(self) -> Path:
        """Path to Agentero's native NOTES.md in the paper directory."""
        return self.paper_dir / "NOTES.md"

    @property
    def marks_dir_path(self) -> Path:
        """Path to Agentero's marks/ directory."""
        return self.paper_dir / "marks"

    @property
    def canonical_pdf_path(self) -> Path:
        """Path to the paper PDF in Agentero."""
        named_pdf = self.paper_dir / f"{self.paper_id}.pdf"
        if named_pdf.exists():
            return named_pdf
        source_pdf = self.evidentia_dir / "source" / "paper.pdf"
        if source_pdf.exists():
            return source_pdf
        return named_pdf

    def ensure_agentero_facade(self, create_notes: bool = False) -> None:
        """Ensure the Agentero-facing directory structure exists without dirtying read-only workspaces."""
        if self.paper_dir != self.evidentia_dir:
            self.paper_dir.mkdir(parents=True, exist_ok=True)
            self.marks_dir_path.mkdir(parents=True, exist_ok=True)
        if create_notes and not self.notes_md_path.exists():
            self.notes_md_path.parent.mkdir(parents=True, exist_ok=True)
            self.notes_md_path.write_text(
                f"# Notes: {self.paper_id}\n\n*Evidentia Human Interaction Layer Notes*\n\n",
                encoding="utf-8",
            )

    def sync_note_to_markdown(self, note: Dict[str, Any]) -> None:
        """Synchronize an Evidentia structured note into Agentero's native NOTES.md."""
        self.ensure_agentero_facade(create_notes=True)
        note_id = note.get("note_id", "unknown")
        content = note.get("content", "")
        target = note.get("target", {})
        anchor = target.get("anchor") or ""
        evidence_id = target.get("evidence_id") or ""
        timestamp = note.get("created_at", "")

        prefix_parts = []
        if anchor:
            prefix_parts.append(f"Anchor: {anchor}")
        if evidence_id:
            prefix_parts.append(f"Evidence: {evidence_id}")
        prefix = f" [{', '.join(prefix_parts)}]" if prefix_parts else ""

        entry = (
            f"### Note {prefix} ({timestamp[:10] if timestamp else 'Recent'})\n"
            f"{content}\n\n"
            f"<!-- evidentia:note-id={note_id} -->\n\n"
        )

        existing_text = self.notes_md_path.read_text(encoding="utf-8") if self.notes_md_path.exists() else ""
        marker = f"<!-- evidentia:note-id={note_id} -->"
        if marker not in existing_text:
            with open(self.notes_md_path, "a", encoding="utf-8") as f:
                f.write(entry)
