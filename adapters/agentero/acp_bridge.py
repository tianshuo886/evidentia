#!/usr/bin/env python3
"""Agent Client Protocol (ACP) & MCP Tool Bridge for Agentero.

Exposes Evidentia's Workspace Contract capabilities as structured ACP/MCP tools
without leaking model/provider identities into scientific contracts.
"""
from __future__ import annotations
from typing import Any, Dict, List
from adapters.agentero.agentero_adapter import AgenteroAdapter


def get_agentero_tool_definitions() -> List[Dict[str, Any]]:
    """Return standard ACP/MCP tool schemas for Evidentia workspace actions."""
    return [
        {
            "name": "open_reader",
            "description": "Open Chinese Reader as the primary reading surface, optionally navigating to an anchor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "anchor": {"type": "string", "description": "Section anchor (e.g. 's1', 's2')"},
                    "format": {"type": "string", "enum": ["html", "markdown"], "default": "html"},
                },
            },
        },
        {
            "name": "get_reader_selection",
            "description": "Resolve selected Reader text and extract bound evidence IDs and source anchors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selection_text": {"type": "string"},
                    "anchor": {"type": "string"},
                },
            },
        },
        {
            "name": "open_evidence",
            "description": "Drill down into an evidence item (figure crop, table, equation) with bidirectional links.",
            "parameters": {
                "type": "object",
                "required": ["evidence_id"],
                "properties": {
                    "evidence_id": {"type": "string", "description": "Evidence ID (e.g. 'F01', 'T01')"},
                },
            },
        },
        {
            "name": "open_source",
            "description": "Open source PDF page strictly for verification and original wording lookup.",
            "parameters": {
                "type": "object",
                "required": ["page"],
                "properties": {
                    "page": {"type": "integer", "description": "Source PDF page number (1-based)"},
                },
            },
        },
        {
            "name": "ask_with_context",
            "description": "Ask evidence-grounded question regarding a selected passage with tripartite epistemic attribution.",
            "parameters": {
                "type": "object",
                "required": ["question"],
                "properties": {
                    "question": {"type": "string"},
                    "anchor": {"type": "string"},
                    "selection_text": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        {
            "name": "create_private_note",
            "description": "Record a private user note without mutating the Frozen Paper Object.",
            "parameters": {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {"type": "string"},
                    "anchor": {"type": "string"},
                    "evidence_id": {"type": "string"},
                },
            },
        },
        {
            "name": "propose_correction",
            "description": "Propose a scientific correction to a Reader block without mutating base reader facts.",
            "parameters": {
                "type": "object",
                "required": ["anchor", "rationale", "proposed_text"],
                "properties": {
                    "anchor": {"type": "string"},
                    "rationale": {"type": "string"},
                    "proposed_text": {"type": "string"},
                },
            },
        },
        {
            "name": "start_project_apply",
            "description": "Explicitly trigger post-freeze contextual Project Apply for a given project.",
            "parameters": {
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "goals": {"type": "string"},
                },
            },
        },
    ]


def handle_acp_tool_call(adapter: AgenteroAdapter, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an incoming ACP/MCP tool call through the AgenteroAdapter."""
    action_name = tool_name.upper()
    return adapter.dispatch_action(action_name, arguments)
