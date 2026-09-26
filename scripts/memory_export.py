#!/usr/bin/env python3
"""Export bundle manager for Frozen Research Memory."""
import argparse, os, sys, tarfile
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import memory_manager

def export_memory(out_file=None, custom_root=None):
    root = memory_manager.get_memory_root(custom_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_file = Path(out_file) if out_file else (root / 'exports' / f"memory_export_{timestamp}.tar.gz")
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(target_file, "w:gz") as tar:
        tar.add(root / 'objects', arcname='objects')
        tar.add(root / 'memory_manifest.json', arcname='memory_manifest.json')

    print(f"OK: Exported Frozen Research Memory to {target_file}")
    return target_file

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--memory-root')
    args = ap.parse_args()
    export_memory(out_file=args.out, custom_root=args.memory_root)

if __name__ == '__main__':
    main()
