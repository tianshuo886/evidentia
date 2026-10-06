#!/usr/bin/env python3
"""Minimal Host-Neutral Reference Workspace Harness for Evidentia (Issue #24).

Demonstrates and verifies all capabilities of the Workspace Contract:
- Reader is the primary surface.
- Source PDF / Evidence Atlas is the evidence surface.
- AI is the interactive reasoning layer.
- Research Memory is the persistence layer.
- Project Apply is explicit and post-freeze only.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from workspace_contract import WorkspaceSession


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evidentia Host-Neutral Research Workspace Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--workspace", "-w", required=True, help="Path to frozen paper workspace directory")
    parser.add_argument("--version", default="v1", help="Paper version (default: v1)")

    subparsers = parser.add_subparsers(dest="command", help="Workspace command")

    # open-reader
    p_reader = subparsers.add_parser("open-reader", help="Open Reader (primary surface)")
    p_reader.add_argument("--anchor", "-a", help="Reader anchor (e.g. s1, SEC-01, ch-s2)")
    p_reader.add_argument("--format", default="html", choices=["html", "markdown"], help="Content format")

    # open-evidence
    p_ev = subparsers.add_parser("open-evidence", help="Open Evidence item (drill-down)")
    p_ev.add_argument("--id", required=True, help="Evidence ID (e.g. F01, T01, EQ-01, p.1)")

    # open-source
    p_src = subparsers.add_parser("open-source", help="Open Source PDF (verification only)")
    p_src.add_argument("--page", "-p", type=int, required=True, help="Source page number")

    # ask
    p_ask = subparsers.add_parser("ask", help="Evidence-grounded Ask with selection context")
    p_ask.add_argument("--question", "-q", required=True, help="Question to ask")
    p_ask.add_argument("--anchor", "-a", help="Reader anchor context")
    p_ask.add_argument("--selection-text", help="Selected Reader text excerpt")
    p_ask.add_argument("--evidence-id", help="Explicit evidence ID context")
    p_ask.add_argument("--debug", action="store_true", help="Include internal debug trace")

    # notes
    p_note = subparsers.add_parser("note", help="Manage private user notes")
    p_note.add_argument("--create", help="Create note with supplied text")
    p_note.add_argument("--list", action="store_true", help="List notes")
    p_note.add_argument("--anchor", help="Anchor binding")
    p_note.add_argument("--evidence-id", help="Evidence ID binding")

    # propose-correction
    p_prop = subparsers.add_parser("propose-correction", help="Propose a correction without mutating Reader")
    p_prop.add_argument("--anchor", required=True, help="Reader anchor to correct")
    p_prop.add_argument("--proposed-text", required=True, help="Proposed replacement text")
    p_prop.add_argument("--rationale", required=True, help="Scientific rationale for correction")

    # review-correction
    p_rev = subparsers.add_parser("review-correction", help="Review a correction proposal")
    p_rev.add_argument("--proposal-id", required=True, help="Proposal ID")
    p_rev.add_argument("--decision", required=True, choices=["ACCEPT", "REJECT"], help="Decision")
    p_rev.add_argument("--rationale", required=True, help="Reviewer rationale")

    # apply
    p_apply = subparsers.add_parser("apply", help="Start explicit Project Apply")
    p_apply.add_argument("--project-id", required=True, help="Target project ID")
    p_apply.add_argument("--goals", help="Project goals/focus description")

    # dispatch
    p_dispatch = subparsers.add_parser("dispatch", help="Raw capability action dispatch")
    p_dispatch.add_argument("--action", required=True, help="Contract action name")
    p_dispatch.add_argument("--payload", default="{}", help="JSON payload")

    args = parser.parse_args()

    session = WorkspaceSession(args.workspace, version=args.version)

    if args.command == "open-reader":
        res = session.dispatch_action("OPEN_READER", {"anchor": args.anchor, "format": args.format})
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "open-evidence":
        res = session.dispatch_action("OPEN_EVIDENCE", {"evidence_id": args.id})
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "open-source":
        res = session.dispatch_action("OPEN_SOURCE", {"page": args.page})
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "ask":
        ev_refs = [args.evidence_id] if args.evidence_id else []
        res = session.dispatch_action(
            "ASK_WITH_CONTEXT",
            {
                "question": args.question,
                "anchor": args.anchor,
                "selection_text": args.selection_text,
                "evidence_refs": ev_refs,
                "debug_mode": args.debug,
            },
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "note":
        if args.create:
            res = session.dispatch_action(
                "CREATE_PRIVATE_NOTE",
                {
                    "text": args.create,
                    "anchor": args.anchor,
                    "evidence_id": args.evidence_id,
                },
            )
        else:
            res = session.dispatch_action(
                "LIST_NOTES",
                {"anchor": args.anchor, "evidence_id": args.evidence_id},
            )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "propose-correction":
        res = session.dispatch_action(
            "PROPOSE_CORRECTION",
            {
                "anchor": args.anchor,
                "proposed_text": args.proposed_text,
                "rationale": args.rationale,
            },
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "review-correction":
        res = session.dispatch_action(
            "REVIEW_CORRECTION",
            {
                "proposal_id": args.proposal_id,
                "decision": args.decision,
                "reviewer_rationale": args.rationale,
            },
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "apply":
        res = session.dispatch_action(
            "START_PROJECT_APPLY",
            {"project_context": {"project_id": args.project_id, "goals": args.goals or ""}},
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    elif args.command == "dispatch":
        payload = json.loads(args.payload)
        res = session.dispatch_action(args.action, payload)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["status"] == "SUCCESS" else 1

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
