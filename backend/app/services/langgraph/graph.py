"""
LangGraph StateGraph Builder — AegisCloud Agent Graph.

Constructs the complete agent workflow graph with:
- Conditional routing based on risk level
- interrupt() for async CIBA approval
- AsyncSqliteSaver checkpointer for async state persistence
"""

import aiosqlite
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.models.agent_state import AgentState
from app.services.langgraph.nodes import (
    analyze_logs_node,
    classify_risk_node,
    propose_action_node,
    await_approval_node,
    execute_remediation_node,
    log_rejection_node,
)


def route_after_approval(state: AgentState) -> str:
    """Route based on human approval decision."""
    status = state.get("approval_status", "rejected")
    if status == "approved":
        return "execute_remediation"
    return "log_rejection"


def route_after_risk(state: AgentState) -> str:
    """
    Route based on risk classification.
    HIGH/CRITICAL -> requires human approval (CIBA)
    LOW/MEDIUM -> could auto-remediate (but for demo, always go to approval)
    """
    # For the hackathon demo, ALWAYS require approval to showcase CIBA
    return "propose_action"


def _build_graph_structure():
    """Build the graph structure (without checkpointer)."""
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("analyze_logs", analyze_logs_node)
    builder.add_node("classify_risk", classify_risk_node)
    builder.add_node("propose_action", propose_action_node)
    builder.add_node("await_approval", await_approval_node)
    builder.add_node("execute_remediation", execute_remediation_node)
    builder.add_node("log_rejection", log_rejection_node)

    # Add edges
    builder.add_edge(START, "analyze_logs")
    builder.add_edge("analyze_logs", "classify_risk")
    builder.add_conditional_edges("classify_risk", route_after_risk)
    builder.add_edge("propose_action", "await_approval")
    builder.add_conditional_edges("await_approval", route_after_approval)
    builder.add_edge("execute_remediation", END)
    builder.add_edge("log_rejection", END)

    return builder


def build_agent_graph(db_path: str = "aegiscloud_checkpoints.db") -> tuple:
    """
    Build and compile the AegisCloud agent graph with SYNC checkpointer.
    Used for testing with SqliteSaver.

    Returns:
        tuple: (compiled_graph, checkpointer)
    """
    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver

    builder = _build_graph_structure()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = builder.compile(checkpointer=checkpointer)

    return graph, checkpointer


async def build_async_agent_graph(db_path: str = "aegiscloud_checkpoints.db") -> tuple:
    """
    Build and compile the AegisCloud agent graph with ASYNC checkpointer.
    Used in production with FastAPI (async event loop).

    Returns:
        tuple: (compiled_graph, checkpointer)
    """
    builder = _build_graph_structure()
    conn = await aiosqlite.connect(db_path)
    checkpointer = AsyncSqliteSaver(conn)
    graph = builder.compile(checkpointer=checkpointer)

    return graph, checkpointer


# Module-level async graph instance
_async_graph = None
_async_checkpointer = None


async def get_agent_graph():
    """Get or create the singleton async agent graph."""
    global _async_graph, _async_checkpointer
    if _async_graph is None:
        _async_graph, _async_checkpointer = await build_async_agent_graph()
    return _async_graph


async def get_checkpointer():
    """Get the current checkpointer."""
    global _async_checkpointer
    if _async_checkpointer is None:
        await get_agent_graph()
    return _async_checkpointer
