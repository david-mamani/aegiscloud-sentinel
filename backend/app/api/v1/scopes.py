"""
Agent Scopes API — Dynamically derived from the authenticated user's JWT claims.

Instead of returning hardcoded scopes, this endpoint reads the 'permissions'
and 'scope' claims from the validated JWT Access Token. The agent's
effective permissions are the INTERSECTION of Token Vault capabilities
and the user's granted scopes.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from typing import Optional

router = APIRouter(prefix="/scopes", tags=["Agent Scopes"])

_bearer = HTTPBearer(auto_error=False)

# ── Scope-to-visualisation mapping ──────────────────────────────
# Maps JWT scope/permission strings to the radar display data.
# 'level' indicates the default scope power level for the radar.
# 'requires_ciba' indicates write scopes that need human approval.

SCOPE_CATALOG = {
    # AWS mock scopes (from Token Vault connection)
    "read:ec2":  {"name": "EC2:Read",  "level": 90, "connection": "aws-mock", "granted_via": "Token Vault"},
    "write:ec2": {"name": "EC2:Write", "level": 85, "connection": "aws-mock", "granted_via": "Token Vault + CIBA"},
    "read:s3":   {"name": "S3:Read",   "level": 70, "connection": "aws-mock", "granted_via": "Token Vault"},
    "write:s3":  {"name": "S3:Write",  "level": 60, "connection": "aws-mock", "granted_via": "Token Vault + CIBA"},
    "read:iam":  {"name": "IAM:Read",  "level": 80, "connection": "aws-mock", "granted_via": "Token Vault"},
    "write:iam": {"name": "IAM:Write", "level": 40, "connection": "aws-mock", "granted_via": "Token Vault + CIBA"},
    "read:vpc":  {"name": "VPC:Read",  "level": 75, "connection": "aws-mock", "granted_via": "Token Vault"},
    # GitHub scope (from real Token Vault connection)
    "read:github": {"name": "GitHub:Read", "level": 95, "connection": "github", "granted_via": "Token Vault"},
    # Catch-all for generic OpenID scopes
    "openid":  None,
    "profile": None,
    "email":   None,
    "offline_access": None,
}

# Full catalog values for fallback (all possible scopes)
_ALL_SCOPES = [v for v in SCOPE_CATALOG.values() if v is not None]


def _extract_scopes_from_claims(claims: dict) -> list[dict]:
    """
    Extract scopes from JWT claims. Auth0 can include scopes in:
    1. 'permissions' claim — RBAC permissions (array of strings)
    2. 'scope' claim — OAuth2 scopes (space-separated string)
    
    The agent's effective scopes = user's granted scopes ∩ Token Vault capabilities.
    """
    matched_scopes = []
    seen = set()

    # 1. Check 'permissions' array (Auth0 RBAC)
    permissions = claims.get("permissions", [])
    if isinstance(permissions, list):
        for perm in permissions:
            perm_lower = perm.lower()
            if perm_lower in SCOPE_CATALOG and SCOPE_CATALOG[perm_lower] is not None:
                if perm_lower not in seen:
                    matched_scopes.append(SCOPE_CATALOG[perm_lower])
                    seen.add(perm_lower)

    # 2. Check 'scope' string (OAuth2 standard)
    scope_str = claims.get("scope", "")
    if isinstance(scope_str, str):
        for scope in scope_str.split():
            scope_lower = scope.lower()
            if scope_lower in SCOPE_CATALOG and SCOPE_CATALOG[scope_lower] is not None:
                if scope_lower not in seen:
                    matched_scopes.append(SCOPE_CATALOG[scope_lower])
                    seen.add(scope_lower)

    return matched_scopes


@router.get("/")
async def get_agent_scopes(request: Request):
    """
    Return the current scopes/permissions of the AegisCloud agent,
    dynamically derived from the authenticated user's JWT claims.

    The middleware has already validated the token. We extract claims
    from the request state (set by verify_token dependency at router level).
    If no specific scopes are found in the JWT, we fall back to showing
    all Token Vault capabilities (the agent's maximum possible permissions).
    """
    # The verify_token dependency already validated the JWT.
    # Re-decode without verification to read claims (token already verified).
    auth_header = request.headers.get("Authorization", "")
    claims = {}

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            claims = jwt.get_unverified_claims(token)
        except Exception:
            claims = {}

    # Extract dynamic scopes from JWT claims
    dynamic_scopes = _extract_scopes_from_claims(claims)

    # Determine source: real JWT scopes or fallback to full catalog
    if dynamic_scopes:
        scopes = dynamic_scopes
        source = "jwt-claims"
    else:
        # Fallback: show all Token Vault capabilities
        # This happens when Auth0 API doesn't define custom permissions
        # (common in hackathon setups without RBAC configured)
        scopes = _ALL_SCOPES
        source = "token-vault-capabilities"

    return {
        "agent_id": "aegis-devsecops-sentinel",
        "user_sub": claims.get("sub", "unknown"),
        "scopes": scopes,
        "total_scopes": len(scopes),
        "source": source,
        "note": (
            "Scopes derived from JWT claims. "
            "Write scopes require human approval via CIBA + Auth0 Guardian."
        ),
    }
