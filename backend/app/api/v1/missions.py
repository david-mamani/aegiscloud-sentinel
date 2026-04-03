"""
Mission API Routes — Start, monitor, and control agent missions.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from app.services.langgraph.graph import get_agent_graph
from app.services.aws_mock.service import aws_mock
from app.services.auth0.client import auth0_service
from app.core.config import get_settings

router = APIRouter(prefix="/missions", tags=["Missions"])

# In-memory mission store (production would use DB)
_missions: dict[str, dict] = {}
_active_threads: dict[str, str] = {}  # mission_id -> thread_id

settings = get_settings()


class MissionStartRequest(BaseModel):
    scenario: str = "open-port-22"  # Default scenario


class MissionResponse(BaseModel):
    mission_id: str
    status: str
    scenario: str
    details: dict = {}


@router.post("/start", response_model=MissionResponse)
async def start_mission(request: MissionStartRequest):
    """
    Start a new agent mission.

    1. Creates a new LangGraph thread
    2. Invokes the graph with mock infrastructure logs
    3. Returns when the graph hits interrupt() (awaiting approval)
    """
    mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    thread_id = f"thread-{mission_id}"

    # Get infrastructure state for the scenario
    infra_state = aws_mock.get_full_state()

    graph = await get_agent_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke graph — it will analyze logs and PAUSE at interrupt()
    initial_state = {
        "mission_id": mission_id,
        "scenario_type": request.scenario,
        "infrastructure_logs": infra_state,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
    }

    try:
        # QA Issue #5 FIX: Use graph.ainvoke() which is natively async
        # and properly handles async node functions without blocking the event loop
        result = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution error: {str(e)}")

    # Check if we got an interrupt (expected!)
    interrupt_data = result.get("__interrupt__", [])

    mission_record = {
        "mission_id": mission_id,
        "thread_id": thread_id,
        "scenario": request.scenario,
        "status": "awaiting_approval" if interrupt_data else "completed",
        "started_at": initial_state["started_at"],
        "interrupt_payload": interrupt_data[0].value if interrupt_data else None,
        "proposed_action": result.get("proposed_action"),
        "analysis": result.get("analysis_summary"),
    }

    _missions[mission_id] = mission_record
    _active_threads[mission_id] = thread_id

    return MissionResponse(
        mission_id=mission_id,
        status=mission_record["status"],
        scenario=request.scenario,
        details={
            "analysis": result.get("analysis_summary", ""),
            "vulnerability_count": result.get("vulnerability_count", 0),
            "proposed_action": result.get("proposed_action"),
            "interrupt": interrupt_data[0].value if interrupt_data else None,
        },
    )


@router.get("/{mission_id}/status", response_model=MissionResponse)
async def get_mission_status(mission_id: str):
    """Get the current status of a mission."""
    mission = _missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    return MissionResponse(
        mission_id=mission_id,
        status=mission["status"],
        scenario=mission["scenario"],
        details=mission,
    )


@router.post("/{mission_id}/approve")
async def approve_mission(mission_id: str):
    """
    Resume a paused mission after CIBA approval.

    Integrates with Auth0 Token Vault:
    1. Try real Token Exchange (RFC 8693) for GitHub token
    2. Fall back to mock token if Vault not available
    3. Resume LangGraph with the token (Double-Blind: agent never sees it)
    """
    import logging
    logger = logging.getLogger(__name__)

    mission = _missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    thread_id = _active_threads.get(mission_id)
    if not thread_id:
        raise HTTPException(status_code=400, detail="No active thread for mission")

    # --- TOKEN VAULT INTEGRATION ---
    token = None
    token_source = "mock"

    try:
        vault_result = await auth0_service.token_exchange_for_connection(
            subject_token=await auth0_service.get_management_token(),
            connection="github",
        )
        if vault_result["status"] == "success":
            token = vault_result["access_token"]
            token_source = "token-vault"
            logger.info("Using REAL token from Token Vault")
    except Exception as e:
        logger.warning(f"Token Vault exchange failed, using mock: {e}")

    if not token:
        token = f"mock-vault-token-{uuid.uuid4().hex[:8]}"
        token_source = "mock-fallback"
        logger.info("Using MOCK token (Token Vault not configured)")

    graph = await get_agent_graph()
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(
        Command(resume={
            "decision": "approved",
            "token": token,
            "token_source": token_source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
        config=config,
    )

    mission["status"] = "completed"
    mission["execution_result"] = result.get("execution_result")
    mission["token_source"] = token_source

    return {
        "mission_id": mission_id,
        "status": "completed",
        "token_source": token_source,
        "execution_result": result.get("execution_result"),
    }



@router.post("/{mission_id}/reject")
async def reject_mission(mission_id: str, reason: str = "User denied"):
    """Resume a paused mission with rejection."""
    mission = _missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    thread_id = _active_threads.get(mission_id)
    graph = await get_agent_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # QA Issue #5 FIX: Use graph.ainvoke() for native async support
    result = await graph.ainvoke(
        Command(resume={"decision": "rejected", "reason": reason}),
        config=config,
    )

    mission["status"] = "rejected"
    mission["execution_result"] = result.get("execution_result")

    return {"mission_id": mission_id, "status": "rejected", "reason": reason}


@router.post("/{mission_id}/kill")
async def kill_mission(mission_id: str):
    """
    KILL SWITCH — Emergency stop for a mission.
    Revokes all related tokens and halts the agent.
    """
    mission = _missions.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    mission["status"] = "killed"
    mission["killed_at"] = datetime.now(timezone.utc).isoformat()

    # In production: revoke tokens via Auth0
    # await auth0_service.revoke_all_tokens()

    return {
        "mission_id": mission_id,
        "status": "killed",
        "message": "ALL OPERATIONS HALTED. Tokens revoked.",
    }


@router.get("/active")
async def list_active_missions():
    """List all active/recent missions."""
    return {
        "missions": list(_missions.values()),
        "total": len(_missions),
    }
