#!/usr/bin/env python3
"""Cheap, safe ways to hold the same bytes once (Issue #55).

A single paper used to keep three copies of its own PDF and six copies of every
source page: `working/`, `source/`, the paper root, plus one full `copytree` per
Lens input snapshot. On a real 30-page paper that is hundreds of megabytes of
identical bytes per run.

`link_or_copy` prefers a hard link (same inode, zero extra bytes, works across
directories on the same filesystem), falls back to a symlink, and only copies
when neither is possible. Callers that need byte independence pass
`independent=True`.

`link_tree` mirrors a directory the same way, so a Lens snapshot still sees a
complete isolated view while sharing storage with the canonical source.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def link_or_copy(src: Path, dst: Path, *, independent: bool = False) -> str:
    """Materialise `dst` from `src`, returning the strategy used."""
    src = Path(src)
    dst = Path(dst)
    if _same_file(src, dst):
        return "SAME_PATH"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()

    if not independent:
        try:
            os.link(src, dst)
            return "HARDLINK"
        except OSError:
            pass
        try:
            dst.symlink_to(os.path.relpath(src, dst.parent))
            return "SYMLINK"
        except OSError:
            pass

    shutil.copy2(src, dst)
    return "COPY"


def link_tree(src: Path, dst: Path, *, independent: bool = False) -> dict:
    """Mirror `src` into `dst`, hard-linking files instead of duplicating bytes."""
    src = Path(src)
    dst = Path(dst)
    strategies: dict[str, int] = {}
    for root, _dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)
        (dst / rel_root).mkdir(parents=True, exist_ok=True)
        for name in files:
            strategy = link_or_copy(
                Path(root) / name, dst / rel_root / name, independent=independent
            )
            strategies[strategy] = strategies.get(strategy, 0) + 1
    return strategies


def shared_bytes(path: Path) -> tuple[int, int]:
    """Return (apparent_size, unique_size) for a file.

    `unique_size` is 0 when the inode has more than one hard link, because the
    bytes are already accounted for elsewhere.
    """
    path = Path(path)
    try:
        st = path.stat()
    except OSError:
        return 0, 0
    if path.is_symlink():
        return 0, 0
    if st.st_nlink > 1:
        return st.st_size, 0
    return st.st_size, st.st_size
