"""
LangGraph Node Functions — The AI reasoning pipeline.

Each function is a node in the StateGraph:
1. analyze_logs: Uses Gemini LLM to analyze infrastructure logs
2. classify_risk: Determines risk level of vulnerabilities
3. propose_action: Generates a remediation proposal
4. await_approval: PAUSES via interrupt() for CIBA approval
5. execute_remediation: Executes approved action via AWS mock
6. log_rejection: Handles rejected actions
"""

import json
import re
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt

from app.models.agent_state import AgentState, ProposedAction
from app.services.aws_mock.service import aws_mock


# -- LLM Configuration --
def get_llm():
    """Get the configured Google Gemini LLM instance."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.1,  # Low temp for consistent analysis
    )


def _parse_llm_json(content: str) -> dict:
    """
    Robustly parse JSON from LLM response.

    Gemini often wraps JSON in markdown code blocks like:
    ```json
    { ... }
    ```
    This function strips those wrappers before parsing.
    """
    # Strip markdown code blocks
    # Pattern: ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if match:
        content = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


# -- Node 1: Analyze Logs --
async def analyze_logs_node(state: AgentState) -> dict:
    """
    Analyze infrastructure logs using LLM to identify vulnerabilities.

    Input: infrastructure_logs (dict from AWS mock)
    Output: analysis_summary (str), detected_vulnerabilities (list)
    """
    llm = get_llm()
    logs = state.get("infrastructure_logs", {})
    scenario = state.get("scenario_type", "open-port-22")

    prompt = f"""You are AegisCloud, a DevSecOps AI security agent. 
Analyze the following AWS infrastructure scan results and identify ALL security vulnerabilities.

Focus on the scenario: {scenario}

Infrastructure Data:
{json.dumps(logs, indent=2)[:3000]}

For each vulnerability found, provide:
1. Resource ID and type
2. Severity (CRITICAL/HIGH/MEDIUM/LOW)
3. CIS Benchmark violation (if applicable)
4. Risk description
5. Recommended remediation

Respond ONLY with valid JSON (no markdown, no explanation) with keys: "summary", "vulnerabilities" (array of objects with: resource_id, resource_type, severity, cis_benchmark, description, remediation)
"""

    response = await llm.ainvoke(prompt)

    analysis = _parse_llm_json(response.content)
    vulns = analysis.get("vulnerabilities", [])
    summary = analysis.get("summary", response.content[:500])

    return {
        "analysis_summary": summary,
        "detected_vulnerabilities": vulns,
        "vulnerability_count": len(vulns),
        "current_node": "analyze_logs",
        "messages": [{"role": "assistant", "content": f"Analysis: {summary}"}],
    }


# -- Node 2: Classify Risk --
async def classify_risk_node(state: AgentState) -> dict:
    """
    Classify the overall risk level based on detected vulnerabilities.

    Determines if human approval (CIBA) is required.
    Rule: Any CRITICAL or HIGH vulnerability -> requires approval.
    """
    vulns = state.get("detected_vulnerabilities", [])

    has_critical = any(
        v.get("severity", "").upper() in ("CRITICAL", "HIGH") for v in vulns
    )

    risk_level = "critical" if has_critical else "low"

    return {
        "current_node": "classify_risk",
        "messages": [
            {
                "role": "assistant",
                "content": f"Risk classified as {risk_level}. "
                + ("Human approval REQUIRED via CIBA." if has_critical else "Auto-remediation possible."),
            }
        ],
    }


# -- Node 3: Propose Action --
async def propose_action_node(state: AgentState) -> dict:
    """
    Generate a specific remediation proposal based on the scenario.

    Maps the detected vulnerability to a concrete AWS action and
    creates the diff that will be shown in the CIBA/Guardian approval.
    """
    scenario_id = state.get("scenario_type", "open-port-22")

    # Load scenario details
    from pathlib import Path

    scenarios_file = Path(__file__).parent.parent.parent.parent / "data" / "scenarios.json"
    with open(scenarios_file) as f:
        scenarios = json.load(f)["scenarios"]

    scenario = next((s for s in scenarios if s["id"] == scenario_id), scenarios[0])

    # Generate the diff using AWS mock
    diff = aws_mock.generate_diff(scenario_id)

    proposed = ProposedAction(
        type=scenario["remediation"]["rar_type"].split(":")[-1],
        action_name=scenario["remediation"]["action"],
        resource_id=scenario["target_resource"],
        resource_name=scenario.get("name", "Unknown Resource"),
        risk_level="critical",
        rar_type=scenario["remediation"]["rar_type"],
        description_human=scenario["remediation"]["description"],
        diff=diff,
        scenario_id=scenario_id,
        target_rule=scenario.get("target_rule", ""),
    )

    return {
        "proposed_action": proposed,
        "current_node": "propose_action",
        "messages": [
            {
                "role": "assistant",
                "content": f"Proposed: {scenario['remediation']['description']}. "
                f"Awaiting human approval via CIBA push notification.",
            }
        ],
    }


# -- Node 4: Await Approval (INTERRUPT) --
async def await_approval_node(state: AgentState) -> dict:
    """
    CRITICAL NODE — Pauses the graph via interrupt().

    This is where the Double-Blind pattern shines:
    1. The interrupt payload contains the proposed action details
    2. FastAPI backend receives this payload
    3. Backend sends CIBA request to Auth0 with RAR payload
    4. Human approves/rejects via Guardian push notification
    5. Backend resumes graph with Command(resume=approval_response)

    The AI NEVER sees the token. Only the backend handles credentials.

    DOUBLE-BLIND VERIFICATION:
    - The interrupt() payload contains ONLY metadata (resource_id, diff, rar_type)
    - ZERO tokens, ZERO credentials, ZERO secrets in the payload
    """
    proposed = state.get("proposed_action")

    if not proposed:
        return {
            "approval_status": "rejected",
            "error": "No action proposed",
            "current_node": "await_approval",
        }

    # --- THIS IS THE MAGIC ---
    # interrupt() pauses the graph and persists state via checkpointer.
    # The payload becomes available in the graph result as __interrupt__
    # The backend will use this to construct the CIBA/RAR request.
    approval_response = interrupt({
        "type": "approval_required",
        "action_type": proposed.get("type", "unknown"),
        "rar_type": proposed.get("rar_type", ""),
        "resource_id": proposed.get("resource_id", ""),
        "resource_name": proposed.get("resource_name", ""),
        "risk_level": proposed.get("risk_level", "critical"),
        "description": proposed.get("description_human", ""),
        "diff": proposed.get("diff", {}),
        "scenario_id": proposed.get("scenario_id", ""),
        "message": f"\U0001f510 Approve action: {proposed.get('description_human', 'Unknown action')}?",
        # NOTE: NO tokens, NO credentials, NO secrets in this payload.
        # Only metadata for the CIBA/RAR request.
    })
    # --- END MAGIC ---

    # When we get here, the human has responded via CIBA
    decision = approval_response.get("decision", "rejected")

    return {
        "approval_status": decision,
        "approval_response": approval_response,
        "current_node": "await_approval",
        "messages": [
            {
                "role": "assistant",
                "content": f"Human decision: {decision}. "
                + (f"Token received." if decision == "approved" else f"Reason: {approval_response.get('reason', 'N/A')}"),
            }
        ],
    }


# -- Node 5: Execute Remediation --
async def execute_remediation_node(state: AgentState) -> dict:
    """
    Execute the approved remediation action using AWS Mock.

    IMPORTANT: In production, the token from Token Vault would be
    used here. For the hackathon, we use the mock token.
    The key insight is that the AI NEVER sees the real token —
    only the backend proxy handles it.
    """
    proposed = state.get("proposed_action", {})
    approval = state.get("approval_response", {})
    token = approval.get("token", "mock-approved-token")

    action_name = proposed.get("action_name", "")
    resource_id = proposed.get("resource_id", "")
    target_rule = proposed.get("target_rule", "")

    result = None

    if action_name == "revoke_security_group_ingress":
        result = await aws_mock.revoke_security_group_ingress(
            resource_id, target_rule, token=token
        )
    elif action_name == "put_public_access_block":
        result = await aws_mock.put_public_access_block(
            resource_id, token=token
        )
    else:
        result = {"error": f"Unknown action: {action_name}"}

    success = result.get("Return", result.get("RequestId")) is not None and "error" not in result

    return {
        "execution_result": {
            "success": success,
            "action_taken": action_name,
            "resource_modified": resource_id,
            "details": result,
            "token_used_at": datetime.now(timezone.utc).isoformat(),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        },
        "current_node": "execute_remediation",
        "messages": [
            {
                "role": "assistant",
                "content": f"\u2705 Remediation executed: {action_name} on {resource_id}. Success: {success}",
            }
        ],
    }


# -- Node 6: Log Rejection --
async def log_rejection_node(state: AgentState) -> dict:
    """Log that the human rejected the proposed action."""
    proposed = state.get("proposed_action", {})
    approval = state.get("approval_response", {})

    return {
        "execution_result": {
            "success": False,
            "action_taken": "NONE \u2014 Rejected by human operator",
            "resource_modified": proposed.get("resource_id", "unknown"),
            "details": {"rejection_reason": approval.get("reason", "User denied")},
            "executed_at": datetime.now(timezone.utc).isoformat(),
        },
        "current_node": "log_rejection",
        "messages": [
            {
                "role": "assistant",
                "content": f"\u274c Action rejected by human operator. No changes made.",
            }
        ],
    }
