"""
JWT Authentication Middleware for AegisCloud Backend.

Validates Auth0 Access Tokens against the tenant's JWKS endpoint.
This is the CRITICAL security layer that was missing — every API
endpoint (except /health and /docs) MUST go through this middleware.

The Double-Blind Pattern requires:
1. Frontend authenticates via Auth0 SDK (session-based)
2. Frontend proxy extracts Access Token server-side
3. Proxy forwards the token to backend via Authorization header
4. THIS MIDDLEWARE validates the JWT before any route handler runs
"""

from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWKError
from functools import lru_cache
import httpx
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# HTTP Bearer scheme — extracted from Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)

# ── JWKS Cache ──────────────────────────────────────────────────
# Cache the JWKS keys from Auth0 to avoid hitting the endpoint on
# every request. They rotate infrequently (days/weeks).
_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    """Fetch and cache Auth0's JWKS (JSON Web Key Set)."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    settings = get_settings()
    jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            logger.info(f"JWKS fetched from {jwks_url}")
            return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to validate tokens: JWKS unavailable",
        )


def _find_rsa_key(jwks: dict, kid: str) -> Optional[dict]:
    """Find the matching RSA key in the JWKS set by Key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return None


# ── Token Verification ──────────────────────────────────────────

async def verify_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency that validates the Auth0 JWT Access Token.

    Returns the decoded token payload (claims) on success.
    Raises HTTP 401 on any validation failure.

    Usage:
        @router.get("/protected")
        async def protected_route(claims: dict = Depends(verify_token)):
            user_sub = claims["sub"]
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    settings = get_settings()

    # Decode the header WITHOUT verification to get the Key ID (kid)
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch JWKS and find matching key
    jwks = await _get_jwks()
    rsa_key = _find_rsa_key(jwks, unverified_header.get("kid", ""))

    if rsa_key is None:
        # Invalidate cache and retry once — key may have rotated
        global _jwks_cache
        _jwks_cache = None
        jwks = await _get_jwks()
        rsa_key = _find_rsa_key(jwks, unverified_header.get("kid", ""))

        if rsa_key is None:
            raise HTTPException(
                status_code=401,
                detail="Unable to find appropriate key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Verify the JWT signature, audience, issuer, and expiry
    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
