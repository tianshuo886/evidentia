#!/usr/bin/env python3
"""CLI utility for Agentero adapter management."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from adapters.agentero.agentero_adapter import AgenteroAdapter, is_agentero_available


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidentia Agentero Reference Adapter CLI")
    parser.add_argument("--paper-path", "-p", required=True, help="Path to paper workspace or Agentero paper folder")
    parser.add_argument("--version", default="v1", help="Paper version (default: v1)")

    subparsers = parser.add_subparsers(dest="command", help="Agentero adapter command")

    subparsers.add_parser("status", help="Inspect host availability and paper layout")

    p_reader = subparsers.add_parser("open-reader", help="Open Reader through Agentero adapter")
    p_reader.add_argument("--anchor", "-a", help="Reader anchor")

    p_ask = subparsers.add_parser("ask", help="Ask evidence-grounded question")
    p_ask.add_argument("--question", "-q", required=True, help="Question")
    p_ask.add_argument("--anchor", "-a", help="Anchor")

    p_note = subparsers.add_parser("note", help="Create note")
    p_note.add_argument("--text", "-t", required=True, help="Note text")
    p_note.add_argument("--anchor", "-a", help="Anchor")

    args = parser.parse_args()

    adapter = AgenteroAdapter(args.paper_path, version=args.version)

    if args.command == "status":
        info = {
            "paper_id": adapter.paper_id,
            "version": adapter.version,
            "host_available": adapter.host_available,
            "host_mode": adapter.host_mode,
            "evidentia_dir": str(adapter.layout.evidentia_dir),
            "notes_md": str(adapter.layout.notes_md_path),
        }
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0

    elif args.command == "open-reader":
        res = adapter.open_reader(anchor=args.anchor)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "ask":
        res = adapter.ask_with_context(question=args.question, anchor=args.anchor)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "note":
        res = adapter.create_private_note(text=args.text, anchor=args.anchor)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
