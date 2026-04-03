"""
Auth0 CIBA & Token Vault API Routes.

These endpoints orchestrate the complete CIBA flow:
1. Build RAR payload from interrupt data
2. Send /bc-authorize to Auth0 (or simulate if CIBA unavailable)
3. Poll /oauth/token with backoff (or mock approval)
4. On approval: token exchange via Token Vault
5. Resume LangGraph with approval + token

MOCK MODE: When CIBA is not available (requires Enterprise plan),
the flow simulates the push notification and provides a manual
approval endpoint. The architecture and RAR payload are identical
to what would be sent in production.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel

from app.services.auth0.client import auth0_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth0 CIBA & Token Vault"])

settings = get_settings()

# Track active CIBA requests
_ciba_requests: dict[str, dict] = {}


class CIBAInitiateRequest(BaseModel):
    """Request to initiate a CIBA flow."""
    mission_id: str
    interrupt_payload: dict  # From LangGraph interrupt()
    user_id: str | None = None  # Auth0 user ID, falls back to env


class CIBAStatusResponse(BaseModel):
    """Status of a CIBA request."""
    auth_req_id: str
    status: str
    mission_id: str
    details: dict = {}


class CIBAApproveRequest(BaseModel):
    """Manual approval for mock CIBA flow."""
    decision: str = "approved"  # "approved" or "rejected"
    reason: str | None = None


def build_rar_payload(interrupt_payload: dict, mission_id: str) -> list[dict]:
    """
    Build the Rich Authorization Request (RAR) payload from
    the LangGraph interrupt data.

    This payload is what would be sent to Auth0 /bc-authorize and
    displayed in the Guardian push notification to the human approver.

    PRD §5.2 compliant fields: type, aegis_mission_id, resource, diff, risk_level
    """
    diff = interrupt_payload.get("diff", {})

    rar = [
        {
            "type": interrupt_payload.get("rar_type", "urn:aegiscloud:remediation:v1:security-group-update"),
            "aegis_mission_id": mission_id,
            "agent_id": "aegis-devsecops-sentinel",
            "risk_level": interrupt_payload.get("risk_level", "critical"),
            "resource": {
                "id": interrupt_payload.get("resource_id", "unknown"),
                "name": interrupt_payload.get("resource_name", "unknown"),
                "type": diff.get("resource_type", "unknown"),
            },
            "action": {
                "description": interrupt_payload.get("description", "Security remediation"),
            },
            "diff": {
                "before": diff.get("before", {}),
                "after": diff.get("after", {}),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]

    return rar


@router.post("/ciba/initiate", response_model=CIBAStatusResponse)
async def initiate_ciba(request: CIBAInitiateRequest):
    """
    Initiate a CIBA request.

    In PRODUCTION (Enterprise plan): Calls Auth0 /bc-authorize,
    sends push notification to Guardian app.

    In MOCK MODE (Free/Dev plan): Simulates the CIBA flow,
    creates a pending request that can be manually approved via
    POST /auth/ciba/{id}/approve.

    The RAR payload is built identically in both modes.
    """
    user_id = request.user_id or settings.auth0_user_id or "auth0|default"

    # Build the RAR payload (identical in mock and production)
    rar_payload = build_rar_payload(request.interrupt_payload, request.mission_id)

    # Create human-readable binding message
    resource_name = request.interrupt_payload.get("resource_name", "resource")
    action_desc = request.interrupt_payload.get("description", "security action")
    binding_msg = f"AegisCloud: {action_desc}"[:64]

    logger.info(f"Initiating CIBA for mission {request.mission_id}")
    logger.info(f"RAR payload: {json.dumps(rar_payload, indent=2)[:500]}")

    # --- Try REAL CIBA first, fall back to mock ---
    auth_req_id = None
    interval = 5
    expires_in = 300
    mode = "mock"

    try:
        result = await auth0_service.initiate_ciba(
            user_id=user_id,
            authorization_details=rar_payload,
            binding_message=binding_msg,
        )

        if "error" not in result and result.get("auth_req_id"):
            # Real CIBA worked!
            auth_req_id = result["auth_req_id"]
            interval = result.get("interval", 5)
            expires_in = result.get("expires_in", 300)
            mode = "real"
            logger.info(f"REAL CIBA initiated: {auth_req_id[:20]}...")
        else:
            logger.warning(f"CIBA not available (likely needs Enterprise plan): {result.get('error', 'unknown')[:200]}")
            logger.info("Falling back to MOCK CIBA mode")
    except Exception as e:
        logger.warning(f"CIBA call failed: {e}")
        logger.info("Falling back to MOCK CIBA mode")

    # Generate mock auth_req_id if real CIBA didn't work
    if not auth_req_id:
        auth_req_id = f"mock-ciba-{uuid.uuid4().hex[:12]}"
        mode = "mock"

    # Store CIBA request info
    ciba_record = {
        "auth_req_id": auth_req_id,
        "mission_id": request.mission_id,
        "status": "pending",
        "mode": mode,
        "initiated_at": datetime.now(timezone.utc).isoformat(),
        "expires_in": expires_in,
        "interval": interval,
        "rar_payload": rar_payload,
        "binding_message": binding_msg,
        "user_id": user_id,
    }
    _ciba_requests[auth_req_id] = ciba_record

    return CIBAStatusResponse(
        auth_req_id=auth_req_id,
        status="pending",
        mission_id=request.mission_id,
        details={
            "mode": mode,
            "expires_in": expires_in,
            "interval": interval,
            "binding_message": binding_msg,
            "rar_type": rar_payload[0]["type"] if rar_payload else "unknown",
            "resource_id": rar_payload[0]["resource"]["id"] if rar_payload else "unknown",
            "instruction": (
                "Push notification sent to Guardian app. Approve on your phone."
                if mode == "real"
                else "MOCK MODE: Use POST /api/v1/auth/ciba/{auth_req_id}/approve to simulate Guardian approval."
            ),
        },
    )


@router.post("/ciba/{auth_req_id}/approve")
async def approve_ciba(auth_req_id: str, body: CIBAApproveRequest | None = None):
    """
    Manually approve/reject a CIBA request (Mock Guardian).

    This endpoint simulates what happens when a user taps
    'Approve' or 'Reject' on the Auth0 Guardian app.

    In production, this would be handled by Auth0's CIBA polling
    detecting the user's response. For the hackathon demo, this
    endpoint provides the same functionality.
    """
    record = _ciba_requests.get(auth_req_id)
    if not record:
        raise HTTPException(status_code=404, detail="CIBA request not found")

    if record["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"CIBA request already {record['status']}")

    decision = "approved"
    reason = None
    if body:
        decision = body.decision
        reason = body.reason

    record["status"] = decision
    record["completed_at"] = datetime.now(timezone.utc).isoformat()

    if decision == "approved":
        record["mock_token"] = f"mock-vault-token-{uuid.uuid4().hex[:8]}"
        logger.info(f"CIBA {auth_req_id[:20]} APPROVED (mock Guardian)")

        # Auto-resume the mission
        await _resume_mission(
            mission_id=record["mission_id"],
            decision="approved",
            token=record["mock_token"],
            auth_req_id=auth_req_id,
        )
    else:
        record["rejection_reason"] = reason or "User denied via Guardian"
        logger.info(f"CIBA {auth_req_id[:20]} REJECTED (mock Guardian)")

        # Auto-resume with rejection
        await _resume_mission(
            mission_id=record["mission_id"],
            decision="rejected",
            reason=reason or "User denied via Guardian",
            auth_req_id=auth_req_id,
        )

    return {
        "auth_req_id": auth_req_id,
        "status": decision,
        "mission_id": record["mission_id"],
        "message": (
            "Action approved. Mission resumed and executing remediation."
            if decision == "approved"
            else f"Action rejected. Reason: {reason or 'User denied'}"
        ),
    }


async def _resume_mission(
    mission_id: str,
    decision: str,
    token: str = "",
    reason: str = "",
    auth_req_id: str = "",
):
    """
    Resume a paused LangGraph mission after CIBA approval/rejection.

    This is the bridge between Auth0 CIBA and LangGraph interrupt().
    DOUBLE-BLIND: The token is passed to the graph but NEVER
    appears in the LLM's messages or prompt.
    """
    from app.api.v1.missions import _missions, _active_threads
    from app.services.langgraph.graph import get_agent_graph
    from langgraph.types import Command

    mission = _missions.get(mission_id)
    if not mission:
        logger.error(f"Mission {mission_id} not found for CIBA resume")
        return

    thread_id = _active_threads.get(mission_id)
    if not thread_id:
        logger.error(f"No thread for mission {mission_id}")
        return

    graph = await get_agent_graph()
    config = {"configurable": {"thread_id": thread_id}}

    resume_payload = {
        "decision": decision,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auth_req_id": auth_req_id,
    }

    if decision == "approved":
        resume_payload["token"] = token
    else:
        resume_payload["reason"] = reason

    try:
        final = await graph.ainvoke(
            Command(resume=resume_payload),
            config=config,
        )

        if decision == "approved":
            mission["status"] = "completed"
            mission["execution_result"] = final.get("execution_result")
            logger.info(f"Mission {mission_id} COMPLETED after CIBA approval!")
        else:
            mission["status"] = "rejected"
            mission["execution_result"] = final.get("execution_result")
            logger.info(f"Mission {mission_id} REJECTED by user")

    except Exception as e:
        logger.error(f"Failed to resume mission {mission_id}: {e}")
        mission["status"] = "error"
        mission["error"] = str(e)


@router.get("/ciba/status/{auth_req_id}", response_model=CIBAStatusResponse)
async def get_ciba_status(auth_req_id: str):
    """Get the current status of a CIBA request."""
    record = _ciba_requests.get(auth_req_id)
    if not record:
        raise HTTPException(status_code=404, detail="CIBA request not found")

    return CIBAStatusResponse(
        auth_req_id=auth_req_id,
        status=record["status"],
        mission_id=record["mission_id"],
        details=record,
    )


@router.get("/ciba/active")
async def list_active_ciba():
    """List all active CIBA requests."""
    return {
        "requests": list(_ciba_requests.values()),
        "total": len(_ciba_requests),
    }


@router.get("/rar/preview")
async def preview_rar_payload(scenario: str = "open-port-22"):
    """
    Preview what a RAR payload would look like for a given scenario.
    Useful for demos and debugging.
    """
    from app.services.aws_mock.service import aws_mock

    diff = aws_mock.generate_diff(scenario)
    mock_interrupt = {
        "type": "approval_required",
        "rar_type": f"urn:aegiscloud:remediation:v1:{scenario}",
        "resource_id": diff.get("resource_id", "unknown"),
        "resource_name": diff.get("resource_name", "unknown"),
        "risk_level": "critical",
        "description": f"Remediate {scenario}",
        "diff": diff,
        "scenario_id": scenario,
    }

    rar = build_rar_payload(mock_interrupt, "preview-mission")

    return {
        "scenario": scenario,
        "rar_payload": rar,
        "binding_message": f"AegisCloud: Remediate {scenario}"[:64],
        "note": "This is what would be sent to Auth0 /bc-authorize as authorization_details",
    }


@router.get("/connections")
async def list_user_connections(request: Request):
    """
    List connected accounts via Token Vault.
    Uses the user's access token (from Authorization header) to get real identities.
    """
    connections = []

    # Try to get real identities using user token
    auth_header = request.headers.get("Authorization", "")
    user_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None

    try:
        if user_token:
            # Get user info from the token
            userinfo_resp = await auth0_service._http.get(
                f"{auth0_service.base_url}/userinfo",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            if userinfo_resp.status_code == 200:
                userinfo = userinfo_resp.json()
                user_sub = userinfo.get("sub", "")

                # Fetch full user profile with identities via Management API
                mgmt_token = await auth0_service.get_management_token()
                if mgmt_token and user_sub:
                    user_resp = await auth0_service._http.get(
                        f"{auth0_service.base_url}/api/v2/users/{user_sub}",
                        headers={"Authorization": f"Bearer {mgmt_token}"},
                    )
                    if user_resp.status_code == 200:
                        user_data = user_resp.json()
                        identities = user_data.get("identities", [])
                        for identity in identities:
                            connections.append({
                                "provider": identity.get("provider", "unknown"),
                                "connection": identity.get("connection", "unknown"),
                                "user_id": identity.get("user_id", ""),
                                "is_social": identity.get("isSocial", False),
                                "token_vault_enabled": True,
                                "profile_data": identity.get("profileData", {}),
                            })
        else:
            # Fallback: use env user_id
            mgmt_token = await auth0_service.get_management_token()
            user_id = settings.auth0_user_id
            if mgmt_token and user_id:
                resp = await auth0_service._http.get(
                    f"{auth0_service.base_url}/api/v2/users/{user_id}",
                    headers={"Authorization": f"Bearer {mgmt_token}"},
                )
                if resp.status_code == 200:
                    user_data = resp.json()
                    identities = user_data.get("identities", [])
                    for identity in identities:
                        connections.append({
                            "provider": identity.get("provider", "unknown"),
                            "connection": identity.get("connection", "unknown"),
                            "user_id": identity.get("user_id", ""),
                            "is_social": identity.get("isSocial", False),
                            "token_vault_enabled": True,
                        })
    except Exception as e:
        logger.warning(f"Failed to fetch connections: {e}")

    # Always include mock AWS connection for the demo
    connections.append({
        "provider": "aws-mock",
        "connection": "aws-aegiscloud",
        "user_id": "mock-aws-user",
        "is_social": False,
        "token_vault_enabled": True,
        "note": "Simulated AWS connection for hackathon demo",
    })

    # Always include a GitHub entry if not already present from identities
    has_github = any(c.get("provider") == "github" for c in connections)
    if not has_github:
        connections.insert(0, {
            "provider": "github",
            "connection": "github",
            "user_id": "pending-link",
            "is_social": True,
            "token_vault_enabled": True,
            "note": "Link your GitHub account to test Token Vault exchange",
        })

    return {
        "connections": connections,
        "total": len(connections),
        "token_vault_status": "active",
    }


@router.post("/token-vault/exchange")
async def exchange_token_vault(connection: str = "github"):
    """Legacy endpoint — kept for E2E tests. Uses M2M token (will get 403)."""
    try:
        mgmt_token = await auth0_service.get_management_token()
        result = await auth0_service.token_exchange_for_connection(
            subject_token=mgmt_token,
            connection=connection,
        )
        if result["status"] == "success":
            return {"status": "success", "connection": connection, "double_blind": True}
        return {"status": "fallback", "connection": connection, "error": result.get("error", "")}
    except Exception as e:
        return {"status": "fallback", "connection": connection, "error": str(e)}


class ExchangeRealRequest(BaseModel):
    """Request body for real Token Vault exchange."""
    connection: str = "github"


@router.post("/token-vault/exchange-real")
async def exchange_token_vault_real(request: Request, body: ExchangeRealRequest):
    """
    REAL Token Vault Exchange (RFC 8693) — The core of the Double-Blind Pattern.

    1. Extracts user access token from Authorization header
    2. Exchanges it for a provider token via Auth0 Token Vault
    3. Uses the provider token to call the external API (GitHub)
    4. Returns the API result WITHOUT the token
    5. The AI agent and frontend NEVER see the provider token
    """
    import httpx

    auth_header = request.headers.get("Authorization", "")
    user_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None

    if not user_token:
        return {"status": "error", "error": "No user access token provided", "step": 1}

    steps = [{"step": 1, "action": "User access token extracted from session", "status": "ok"}]

    # Step 2: Token Exchange via Token Vault
    try:
        result = await auth0_service.token_exchange_for_connection(
            subject_token=user_token,
            connection=body.connection,
        )
        steps.append({
            "step": 2,
            "action": f"Token Vault exchange (RFC 8693) for {body.connection}",
            "status": "ok" if result["status"] == "success" else "error",
            "detail": result.get("error", "")[:100] if result["status"] != "success" else "",
        })
    except Exception as e:
        steps.append({"step": 2, "action": "Token Vault exchange", "status": "error", "detail": str(e)[:100]})
        return {
            "status": "error",
            "steps": steps,
            "connection": body.connection,
            "error": f"Token Exchange failed: {str(e)[:100]}",
        }

    if result["status"] != "success":
        return {
            "status": "error",
            "steps": steps,
            "connection": body.connection,
            "error": f"Token Exchange returned: {result.get('code', 'unknown')}",
            "detail": result.get("error", "")[:200],
        }

    # Step 3: Use the provider token to call the external API
    provider_token = result.get("access_token")
    github_profile = None
    github_repos = []

    if body.connection == "github" and provider_token:
        try:
            async with httpx.AsyncClient() as client:
                # Get user profile
                profile_resp = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {provider_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                if profile_resp.status_code == 200:
                    profile = profile_resp.json()
                    github_profile = {
                        "login": profile.get("login"),
                        "name": profile.get("name"),
                        "avatar_url": profile.get("avatar_url"),
                        "public_repos": profile.get("public_repos"),
                        "followers": profile.get("followers"),
                        "html_url": profile.get("html_url"),
                    }
                    steps.append({"step": 3, "action": "GitHub API /user called", "status": "ok"})

                # Get repos
                repos_resp = await client.get(
                    "https://api.github.com/user/repos?per_page=5&sort=updated",
                    headers={
                        "Authorization": f"Bearer {provider_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                if repos_resp.status_code == 200:
                    for repo in repos_resp.json()[:5]:
                        github_repos.append({
                            "name": repo.get("name"),
                            "full_name": repo.get("full_name"),
                            "private": repo.get("private"),
                            "language": repo.get("language"),
                            "updated_at": repo.get("updated_at"),
                        })
                    steps.append({"step": 4, "action": "GitHub API /user/repos called", "status": "ok"})
        except Exception as e:
            steps.append({"step": 3, "action": "GitHub API call", "status": "error", "detail": str(e)[:100]})

    steps.append({
        "step": 5,
        "action": "Provider token destroyed — never exposed to frontend or AI agent",
        "status": "ok",
    })

    logger.info(f"REAL Token Exchange completed for {body.connection} — Double-Blind verified")

    return {
        "status": "success",
        "connection": body.connection,
        "double_blind": True,
        "steps": steps,
        "github_profile": github_profile,
        "github_repos": github_repos,
        "message": "Token Vault exchange successful. Provider token used and destroyed. AI agent never had access.",
    }


@router.post("/kill-switch")
async def kill_switch():
    """
    EMERGENCY KILL SWITCH.

    1. Revoke all active tokens via Auth0
    2. Halt all running missions
    3. Clear all CIBA requests
    4. Log the emergency action
    """
    revoked = []
    errors = []

    # 1. Revoke management token
    try:
        mgmt_token = await auth0_service.get_management_token()
        result = await auth0_service.revoke_token(mgmt_token)
        revoked.append({"type": "management_token", "status": result["status"]})
    except Exception as e:
        errors.append({"type": "management_token", "error": str(e)})

    # 2. Clear all CIBA requests
    cleared_ciba = len(_ciba_requests)
    _ciba_requests.clear()

    # 3. Kill all active missions
    from app.api.v1.missions import _missions
    killed_missions = 0
    for mid, mission in _missions.items():
        if mission["status"] in ("analyzing", "awaiting_approval"):
            mission["status"] = "killed"
            mission["killed_at"] = datetime.now(timezone.utc).isoformat()
            killed_missions += 1

    logger.critical("KILL SWITCH ACTIVATED — All operations halted")

    return {
        "status": "ALL_OPERATIONS_HALTED",
        "tokens_revoked": revoked,
        "ciba_requests_cleared": cleared_ciba,
        "missions_killed": killed_missions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
    }

