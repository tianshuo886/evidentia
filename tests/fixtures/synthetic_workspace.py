"""Tiny deterministic workspaces for interaction tests, without run outputs."""
from __future__ import annotations

import base64
import json
from pathlib import Path

PAPER_ID = "SYNTHETIC-PAPER"
SECTION_TITLE = "Synthetic observation and explanation"


def _source_pdf() -> bytes:
    """Build a valid two-page blank PDF without a PDF-library dependency."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> >>",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        data += f"{offset:010d} 00000 n \n".encode()
    data += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return data


def create_synthetic_workspace(
    destination: Path, *, paper_id: str = PAPER_ID,
    section_prefix: str = "s", document_key: str = "sections",
) -> Path:
    """Create only artifacts required by WorkspaceSession and the adapter.

    Section- and chapter-shaped manuscripts use the same generic content;
    alternate anchor spelling exercises navigation without benchmark identities.
    """
    destination = Path(destination)
    sections = []
    for index in range(1, 4):
        anchor = f"{section_prefix}{index:02d}" if section_prefix == "SEC-" else f"{section_prefix}{index}"
        refs = ["T01"] if index == 1 else ["F01"]
        sections.append({
            "id": anchor,
            "title": SECTION_TITLE if index == 1 else f"Synthetic section {index}",
            "blocks": [{
                "type": "paragraph",
                "text": "A synthetic measurement increases under the stated test condition. The author proposes a simple explanation supported by the linked evidence.",
                "evidence_refs": refs,
                "source_anchors": [f"p.{1 if index == 1 else 2}"],
            }],
        })
    files = {
        "reader/narrative_manuscript.json": {
            "paper_id": paper_id,
            "document": {"title": "Synthetic Measurement Study", document_key: sections},
        },
        "reader/evidence_atlas.json": {"items": [
            {"id": "F01", "kind": "figure", "page": 1, "label": "Figure 1",
             "caption": "Synthetic comparison", "asset": "assets/crop_F01.png", "verification_status": "VERIFIED"},
            {"id": "T01", "kind": "table", "page": 2, "label": "Table 1",
             "caption": "Synthetic measurements", "verification_status": "VERIFIED"},
        ]},
        "model/source_map.json": {"blocks": [
            {"page": 1, "text": "The synthetic observation is supported by Figure 1."},
            {"page": 2, "text": "Table 1 lists measurements under controlled conditions."},
        ]},
    }
    for relative, payload in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (destination / "source").mkdir(parents=True, exist_ok=True)
    (destination / "source/paper.pdf").write_bytes(_source_pdf())
    (destination / "assets").mkdir(parents=True, exist_ok=True)
    (destination / "assets/crop_F01.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII="
    ))
    html = "<!doctype html><html><body>" + "".join(
        f'<section id="{section["id"]}"><h2>{section["title"]}</h2><p>{section["blocks"][0]["text"]}</p></section>'
        for section in sections
    ) + "</body></html>"
    (destination / "reader/paper_reader.html").write_text(html, encoding="utf-8")
    return destination
