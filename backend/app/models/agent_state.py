"""
LangGraph Agent State — The heart of AegisCloud's AI orchestration.

This TypedDict defines the complete state that flows through the
LangGraph StateGraph. It's persisted via SqliteSaver to enable
async pause/resume during CIBA approval flows.
"""

from typing import TypedDict, Any
from typing_extensions import Annotated
import operator


class InfraDiff(TypedDict, total=False):
    """Before/after diff for infrastructure changes."""
    resource_type: str
    resource_id: str
    resource_name: str
    change_type: str
    before: dict
    after: dict


class ProposedAction(TypedDict, total=False):
    """An action proposed by the AI agent for remediation."""
    type: str                # e.g., "security-group-update"
    action_name: str         # e.g., "revoke_security_group_ingress"
    resource_id: str         # e.g., "sg-0a1b2c3d"
    resource_name: str       # e.g., "web-server-sg"
    risk_level: str          # "low" | "medium" | "high" | "critical"
    rar_type: str            # e.g., "urn:aegiscloud:remediation:v1:security-group-update"
    description_human: str   # Human-readable description
    diff: InfraDiff
    scenario_id: str         # Reference to the scenario
    target_rule: str         # Specific rule to modify (if applicable)


class ExecutionResult(TypedDict, total=False):
    """Result of executing an approved remediation action."""
    success: bool
    action_taken: str
    resource_modified: str
    details: dict
    token_used_at: str
    executed_at: str


class AgentState(TypedDict, total=False):
    """
    Complete state for the AegisCloud DevSecOps Agent.

    This state is persisted via SqliteSaver checkpointer,
    allowing the graph to pause (interrupt) during CIBA
    approval and resume when the human approves.
    """
    # -- Thread Metadata --
    mission_id: str
    scenario_id: str
    started_at: str

    # -- Input --
    infrastructure_logs: dict        # Raw infrastructure data from mock
    scenario_type: str               # "open-port-22", "public-s3", etc.

    # -- Analysis --
    analysis_summary: str            # LLM-generated analysis
    detected_vulnerabilities: list   # List of found vulnerabilities
    vulnerability_count: int

    # -- Proposed Action --
    proposed_action: ProposedAction | None

    # -- Approval (populated after CIBA flow) --
    approval_status: str | None      # "pending", "approved", "rejected", "timeout"
    approval_response: dict | None   # Full response from CIBA

    # -- Execution --
    execution_result: ExecutionResult | None

    # -- Messages for LLM --
    messages: Annotated[list, operator.add]

    # -- Status --
    current_node: str
    error: str | None
