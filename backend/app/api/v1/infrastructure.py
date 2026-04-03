"""Infrastructure status and audit log endpoints."""

from fastapi import APIRouter
from app.services.aws_mock.service import aws_mock

router = APIRouter(prefix="/infra", tags=["Infrastructure"])


@router.get("/status")
async def get_infrastructure_status():
    """Get current infrastructure state with vulnerability counts."""
    state = aws_mock.get_full_state()
    vulns = aws_mock.get_vulnerabilities()

    return {
        "security_groups": len(state.get("security_groups", {})),
        "s3_buckets": len(state.get("s3_buckets", {})),
        "iam_policies": len(state.get("iam_policies", {})),
        "vulnerabilities": vulns,
        "total_vulnerabilities": len(vulns),
        "scan_timestamp": state.get("metadata", {}).get("scan_timestamp"),
        "region": state.get("metadata", {}).get("region"),
    }


@router.get("/vulnerabilities")
async def get_vulnerabilities():
    """Get flat list of current vulnerabilities sorted by risk score."""
    return {"vulnerabilities": aws_mock.get_vulnerabilities()}


@router.get("/audit-log")
async def get_audit_log():
    """Get log of all actions performed."""
    return {"actions": aws_mock.get_action_log()}


@router.post("/reset")
async def reset_infrastructure():
    """Reset infrastructure to initial (vulnerable) state for demo reruns."""
    aws_mock.reset_state()
    return {"status": "reset", "message": "Infrastructure reset to initial vulnerable state."}


@router.get("/diff/{scenario_id}")
async def get_scenario_diff(scenario_id: str):
    """Get the before/after diff for a specific scenario."""
    diff = aws_mock.generate_diff(scenario_id)
    return diff
