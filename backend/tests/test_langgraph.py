"""
Tests for LangGraph Agent Graph.

Tests the complete flow including interrupt() and resume.
Uses a mock LLM response to avoid requiring Google API key.
"""

import asyncio
import sqlite3
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from app.models.agent_state import AgentState


def test_agent_state_creation():
    """Test that AgentState can be instantiated."""
    state = AgentState(
        mission_id="test-001",
        scenario_type="open-port-22",
        messages=[],
    )
    assert state["mission_id"] == "test-001"


def test_interrupt_flow():
    """
    Test the core interrupt/resume flow without LLM.
    This validates that LangGraph's interrupt() works correctly
    with our state schema and SqliteSaver checkpointer.
    """
    from typing import TypedDict, Annotated
    import operator

    class SimpleState(TypedDict, total=False):
        step: str
        approval: str
        messages: Annotated[list, operator.add]

    def step_one(state):
        return {"step": "analyzed", "messages": [{"content": "Analyzed"}]}

    def step_two(state):
        response = interrupt({
            "type": "approval_required",
            "message": "Approve closing port 22?",
        })
        return {
            "approval": response.get("decision", "unknown"),
            "messages": [{"content": f"Decision: {response.get('decision')}"}],
        }

    def step_three(state):
        return {"step": "executed", "messages": [{"content": "Executed"}]}

    builder = StateGraph(SimpleState)
    builder.add_node("analyze", step_one)
    builder.add_node("approve", step_two)
    builder.add_node("execute", step_three)
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "approve")
    builder.add_edge("approve", "execute")
    builder.add_edge("execute", END)

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "test-interrupt-1"}}

    # Step 1: Run graph — should pause at interrupt
    result = graph.invoke(
        {"step": "", "approval": "", "messages": []},
        config=config,
    )

    # Verify interrupt happened
    assert "__interrupt__" in result
    interrupt_data = result["__interrupt__"]
    assert len(interrupt_data) > 0
    assert interrupt_data[0].value["type"] == "approval_required"

    # Step 2: Resume with approval
    resumed = graph.invoke(
        Command(resume={"decision": "approved", "token": "test-token"}),
        config=config,
    )

    # Verify completion
    assert resumed["approval"] == "approved"
    assert resumed["step"] == "executed"

    conn.close()


def test_interrupt_rejection():
    """Test that rejection flow works correctly."""
    from typing import TypedDict, Annotated
    import operator

    class SimpleState(TypedDict, total=False):
        approval: str
        messages: Annotated[list, operator.add]

    def approve_node(state):
        response = interrupt({"message": "Approve?"})
        return {
            "approval": response.get("decision", "rejected"),
            "messages": [{"content": f"Got: {response.get('decision')}"}],
        }

    builder = StateGraph(SimpleState)
    builder.add_node("approve", approve_node)
    builder.add_edge(START, "approve")
    builder.add_edge("approve", END)

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    graph = builder.compile(checkpointer=SqliteSaver(conn))
    config = {"configurable": {"thread_id": "test-reject-1"}}

    # Run and pause
    result = graph.invoke({"approval": "", "messages": []}, config=config)
    assert "__interrupt__" in result

    # Resume with rejection
    resumed = graph.invoke(
        Command(resume={"decision": "rejected", "reason": "Too risky"}),
        config=config,
    )
    assert resumed["approval"] == "rejected"

    conn.close()
