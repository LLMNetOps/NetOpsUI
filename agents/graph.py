"""Build and compile the NetOps LangGraph StateGraph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.nodes import (
    config_node, diagnose_node, document_node, monitor_node, netbox_node,
    route_from_supervisor, security_node, supervisor_node,
)


def build_graph(checkpointer) -> object:
    """Compile and return the full NetOps multi-agent graph."""
    from agent import NetworkOpsState  # noqa: PLC0415 — avoid circular at module level

    builder = StateGraph(NetworkOpsState)

    builder.add_node("supervisor",     supervisor_node)
    builder.add_node("monitor_agent",  monitor_node)
    builder.add_node("diagnose_agent", diagnose_node)
    builder.add_node("config_agent",   config_node)
    builder.add_node("security_agent", security_node)
    builder.add_node("document_agent", document_node)
    builder.add_node("netbox_agent",   netbox_node)

    builder.add_edge(START, "supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "monitor_agent":  "monitor_agent",
            "diagnose_agent": "diagnose_agent",
            "config_agent":   "config_agent",
            "security_agent": "security_agent",
            "document_agent": "document_agent",
            "netbox_agent":   "netbox_agent",
            "END":            END,
        },
    )

    # All specialists report back to supervisor
    for agent in ("monitor_agent", "diagnose_agent", "config_agent", "security_agent", "document_agent", "netbox_agent"):
        builder.add_edge(agent, "supervisor")

    return builder.compile(checkpointer=checkpointer)
