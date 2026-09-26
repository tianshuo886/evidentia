#!/usr/bin/env python3
"""Point-in-time snapshot manager for Frozen Research Memory.

Creates consistent snapshots of canonical objects, manifest, and SQLite index.
"""
import argparse, json, os, shutil, sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import memory_manager

def create_snapshot(out_dir=None, custom_root=None):
    root = memory_manager.get_memory_root(custom_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_snapshot = Path(out_dir) if out_dir else (root / 'snapshots' / f"snapshot_{timestamp}")
    target_snapshot.mkdir(parents=True, exist_ok=True)

    # Copy objects
    shutil.copytree(root / 'objects', target_snapshot / 'objects', dirs_exist_ok=True)
    shutil.copy2(root / 'memory_manifest.json', target_snapshot / 'memory_manifest.json')
    if (root / 'memory.sqlite').exists():
        shutil.copy2(root / 'memory.sqlite', target_snapshot / 'memory.sqlite')

    # Record snapshot metadata
    snap_meta = {
        "snapshot_id": f"SNAP-{timestamp}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root.resolve()),
        "target": str(target_snapshot.resolve())
    }
    (target_snapshot / 'snapshot_meta.json').write_text(json.dumps(snap_meta, indent=2) + '\n', encoding='utf-8')
    print(f"OK: Created Frozen Research Memory snapshot at {target_snapshot}")
    return target_snapshot

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--memory-root')
    args = ap.parse_args()
    create_snapshot(out_dir=args.out, custom_root=args.memory_root)

if __name__ == '__main__':
    main()
