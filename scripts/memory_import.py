#!/usr/bin/env python3
"""Import bundle manager for Frozen Research Memory."""
import argparse, json, os, sys, tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import memory_manager

def import_memory(bundle_file, custom_root=None):
    bf = Path(bundle_file)
    if not bf.exists():
        sys.exit(f"Error: Bundle file not found at {bf}")

    root = memory_manager.get_memory_root(custom_root)
    with tarfile.open(bf, "r:gz") as tar:
        tar.extractall(path=root)

    # Rebuild SQLite index from imported canonical objects
    reindexed = memory_manager.rebuild_index(custom_root=root)
    print(f"OK: Successfully imported memory from {bf} ({reindexed} items indexed).")
    return reindexed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--memory-root')
    args = ap.parse_args()
    import_memory(args.file, custom_root=args.memory_root)

if __name__ == '__main__':
    main()
