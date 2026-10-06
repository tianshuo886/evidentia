"""Evidentia Agentero Reference Adapter.

Provides seamless host integration with Agentero while preserving:
- Reader-first default surface
- Evidentia Core host neutrality
- Zero silent mutation of Frozen Paper Objects
- Explicit post-freeze Project Apply
"""
from adapters.agentero.agentero_adapter import AgenteroAdapter, is_agentero_available
from adapters.agentero.vault_layout import AgenteroVaultLayout
from adapters.agentero.acp_bridge import get_agentero_tool_definitions, handle_acp_tool_call

__all__ = [
    "AgenteroAdapter",
    "AgenteroVaultLayout",
    "is_agentero_available",
    "get_agentero_tool_definitions",
    "handle_acp_tool_call",
]
