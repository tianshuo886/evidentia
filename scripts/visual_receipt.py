#!/usr/bin/env python3
"""Proof that the model was actually shown the figures it talks about (Issue #45).

The failure this prevents: the Reader wrote confident prose about Fig. 9/10/11
after receiving only a JSON inventory of captions. Nothing in the pipeline
recorded whether an image was ever put in front of the model, so "visual review"
was unfalsifiable.

`build_visual_receipt` enumerates the images a task must actually see, with the
hash and dimensions of each one, and produces a receipt that the executor fills
in only when the bytes were genuinely attached to the request. A receipt that
lists a path but records no attachment does not count.

The receipt is intentionally minimal: which image, from where, how big, and
whether it was delivered. It is not a per-figure attribute schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _dimensions(path: Path) -> tuple[int, int] | tuple[None, None]:
    try:
        from PIL import Image

        with Image.open(path) as im:
            return im.size
    except Exception:
        return None, None


def _is_readable(path: Path, min_dimension: int) -> tuple[bool, str]:
    width, height = _dimensions(path)
    if width is None:
        return False, "image could not be decoded"
    if min(width, height) < min_dimension:
        return False, f"image too small to read ({width}x{height})"
    return True, ""


def collect_images(root: Path, rel_paths: list[str], *, min_dimension: int = 400) -> dict:
    """Build a visual-input receipt for the images a task is expected to see."""
    root = Path(root).resolve()
    entries: list[dict] = []
    problems: list[str] = []
    for rel in rel_paths:
        path = root / rel
        if not path.is_file():
            problems.append(f"declared visual input is missing: {rel}")
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            problems.append(f"declared visual input is not an image: {rel}")
            continue
        readable, why = _is_readable(path, min_dimension)
        width, height = _dimensions(path)
        entry = {
            "path": rel,
            "sha256": _sha256(path),
            "width": width,
            "height": height,
            "readable": readable,
            "attached": False,
        }
        if not readable:
            problems.append(f"{rel}: {why}")
        entries.append(entry)
    return {
        "schema_version": "1.0",
        "min_dimension": min_dimension,
        "images": entries,
        "problems": problems,
    }


def receipt_errors(receipt: dict) -> list[str]:
    """Validate that a completed receipt proves real visual delivery."""
    errors: list[str] = []
    images = receipt.get("images") or []
    if not images:
        errors.append("visual receipt declares no images at all")
    attached = [im for im in images if im.get("attached") is True]
    if not attached:
        errors.append("no image in the visual receipt was actually attached to the model request")
    for im in images:
        if im.get("attached") is True and not im.get("sha256"):
            errors.append(f"attached image {im.get('path')} has no content hash")
        if im.get("attached") is True and im.get("readable") is False:
            errors.append(f"attached image {im.get('path')} was declared unreadable")
    return errors


def must_show_images(root: Path, manuscript: dict) -> list[str]:
    """Images the Lead Writer used as decisive evidence, from the manuscript."""
    assets: list[str] = []
    for chapter in manuscript.get("document", {}).get("chapters", []):
        for block in chapter.get("blocks", []):
            if block.get("type") not in ("figure", "table"):
                continue
            for key in ("asset", "fallback_asset"):
                asset = block.get(key)
                if asset and asset not in assets:
                    assets.append(asset)
    return assets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="Paper workspace")
    ap.add_argument("--check", action="store_true", help="Validate an existing receipt")
    args = ap.parse_args()

    root = Path(args.out).resolve()
    receipt_p = root / "reader/visual_input_receipt.json"

    if args.check:
        if not receipt_p.is_file():
            print(json.dumps({"status": "NOT_RUN", "reason": "missing reader/visual_input_receipt.json"}))
            return 1
        receipt = json.loads(receipt_p.read_text(encoding="utf-8"))
        errors = receipt_errors(receipt)
        print(json.dumps(
            {"status": "PASS" if not errors else "NEEDS_REVIEW", "errors": errors},
            indent=2, ensure_ascii=False,
        ))
        return 0 if not errors else 1

    manuscript_p = root / "reader/narrative_manuscript.json"
    if not manuscript_p.is_file():
        print(json.dumps({"error": f"missing {manuscript_p}"}, ensure_ascii=False))
        return 2
    manuscript = json.loads(manuscript_p.read_text(encoding="utf-8"))
    receipt = collect_images(root, must_show_images(root, manuscript))
    receipt_p.parent.mkdir(parents=True, exist_ok=True)
    receipt_p.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(
        {
            "receipt": str(receipt_p),
            "images": len(receipt["images"]),
            "problems": receipt["problems"],
            "note": (
                "The executor must set attached=true only for images actually sent to the "
                "model as image input."
            ),
        },
        indent=2, ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
