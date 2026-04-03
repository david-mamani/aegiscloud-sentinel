"""
Mission Orchestrator — Connects LangGraph, CIBA, and Token Vault.

This is the high-level flow controller that:
1. Starts a LangGraph mission
2. Detects when interrupt() fires
3. Initiates CIBA with the interrupt payload
4. Handles the async approval/rejection
5. Resumes the graph with the result

DOUBLE-BLIND PATTERN:
- The orchestrator starts the graph and receives the interrupt payload
- The interrupt payload contains ONLY metadata (resource_id, diff, rar_type)
- The orchestrator passes this to the CIBA service
- CIBA service handles Auth0 credentials (the LLM never sees them)
- On approval, the mock/real token is passed back through Command(resume=...)
- The token flows through the state but NEVER appears in LLM messages
"""

import uuid
import logging
from datetime import datetime, timezone

from app.services.langgraph.graph import get_agent_graph
from app.services.auth0.client import auth0_service
from app.services.aws_mock.service import aws_mock
from app.api.v1.auth import build_rar_payload
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MissionOrchestrator:
    """Orchestrates the complete mission lifecycle."""

    async def start_mission_with_ciba(
        self,
        scenario: str,
        user_id: str | None = None,
    ) -> dict:
        """
        Start a mission and automatically initiate CIBA when interrupt fires.

        This is the main entry point for the full Double-Blind flow:
        1. Invoke LangGraph → analyze → classify → propose → interrupt()
        2. Extract interrupt payload
        3. Build RAR payload
        4. Initiate CIBA (real or mock)
        5. Return mission info with CIBA request ID

        The actual approval happens asynchronously:
        - Real CIBA: User approves on Guardian app
        - Mock CIBA: User calls POST /auth/ciba/{id}/approve
        """
        mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        thread_id = f"thread-{mission_id}"

        graph = await get_agent_graph()
        config = {"configurable": {"thread_id": thread_id}}

        # Step 1: Invoke graph with infrastructure data
        infra_state = aws_mock.get_full_state()

        logger.info(f"Starting mission {mission_id} with scenario: {scenario}")

        result = await graph.ainvoke(
            {
                "mission_id": mission_id,
                "scenario_type": scenario,
                "infrastructure_logs": infra_state,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "messages": [],
            },
            config=config,
        )

        interrupt_data = result.get("__interrupt__", [])

        if not interrupt_data:
            logger.info(f"Mission {mission_id} completed without needing approval")
            return {
                "mission_id": mission_id,
                "thread_id": thread_id,
                "status": "completed_no_approval",
                "result": result,
            }

        # Step 2: We have an interrupt — prepare CIBA
        interrupt_payload = interrupt_data[0].value

        logger.info(f"Mission {mission_id}: interrupt received, preparing CIBA...")

        target_user = user_id or settings.auth0_user_id or "auth0|default"

        # Build RAR payload (same for real and mock CIBA)
        rar = build_rar_payload(interrupt_payload, mission_id)

        # Step 3: Try real CIBA, fall back to mock
        ciba_result = None
        ciba_mode = "mock"

        try:
            ciba_result = await auth0_service.initiate_ciba(
                user_id=target_user,
                authorization_details=rar,
                binding_message=f"AegisCloud: Approve {scenario}"[:64],
            )

            if "error" not in ciba_result and ciba_result.get("auth_req_id"):
                ciba_mode = "real"
                logger.info(f"Real CIBA initiated for mission {mission_id}")
            else:
                logger.info(f"CIBA not available, using mock mode for mission {mission_id}")
                ciba_result = {"auth_req_id": f"mock-ciba-{uuid.uuid4().hex[:12]}"}
        except Exception as e:
            logger.warning(f"CIBA failed ({e}), using mock mode")
            ciba_result = {"auth_req_id": f"mock-ciba-{uuid.uuid4().hex[:12]}"}

        return {
            "mission_id": mission_id,
            "thread_id": thread_id,
            "status": "awaiting_approval",
            "interrupt_payload": interrupt_payload,
            "ciba": {
                "auth_req_id": ciba_result.get("auth_req_id"),
                "mode": ciba_mode,
                "rar_payload": rar,
            },
            "analysis": result.get("analysis_summary"),
            "proposed_action": result.get("proposed_action"),
        }


# Singleton
orchestrator = MissionOrchestrator()
