"""
Auth0 Service Client — Handles ALL Auth0 API interactions.

This is the core of the Double-Blind pattern:
- ONLY this service touches Auth0 credentials
- ONLY this service initiates CIBA requests
- ONLY this service performs token exchanges
- The LangGraph agent NEVER has access to any of these
"""

import json
import httpx
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Auth0Service:
    """Handles all Auth0 API interactions for AegisCloud."""

    def __init__(self):
        self.domain = settings.auth0_domain
        self.client_id = settings.auth0_client_id
        self.client_secret = settings.auth0_client_secret
        self.audience = settings.auth0_audience
        self.base_url = f"https://{self.domain}"
        # Token Vault requires a Custom API Client (resource server type)
        # Falls back to main client if not explicitly configured
        self.tv_client_id = settings.auth0_token_vault_client_id or self.client_id
        self.tv_client_secret = settings.auth0_token_vault_client_secret or self.client_secret
        self._http = httpx.AsyncClient(timeout=30.0)

    async def get_management_token(self) -> str:
        """Get a Management API token via client credentials."""
        resp = await self._http.post(
            f"{self.base_url}/oauth/token",
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "audience": f"{self.base_url}/api/v2/",
                "grant_type": "client_credentials",
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # --- CIBA (Client-Initiated Backchannel Authentication) ---

    async def initiate_ciba(
        self,
        user_id: str,
        authorization_details: list[dict],
        binding_message: str = "AegisCloud Security Action",
        scope: str = "openid",
    ) -> dict:
        """
        Initiate a CIBA request to Auth0.

        This sends a push notification to the user's Guardian app
        with the RAR (Rich Authorization Request) details.

        Args:
            user_id: Auth0 user ID (e.g., "auth0|abc123")
            authorization_details: RAR payload with action diff
            binding_message: Human-readable message (max 64 chars)
            scope: OAuth scopes

        Returns:
            dict with auth_req_id, expires_in, interval
        """
        # QA Issue #6 FIX: Use json.dumps() for safe serialization
        # instead of the unsafe str().replace("'", '"') pattern
        login_hint = json.dumps({
            "format": "iss_sub",
            "iss": f"https://{self.domain}/",
            "sub": user_id,
        })

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "login_hint": login_hint,
            "scope": scope,
            "audience": self.audience,
            "binding_message": binding_message[:64],
            "authorization_details": json.dumps(authorization_details),
        }

        logger.info(f"Initiating CIBA for user {user_id}")

        resp = await self._http.post(
            f"{self.base_url}/bc-authorize",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if resp.status_code != 200:
            logger.error(f"CIBA initiation failed: {resp.status_code} - {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}

        result = resp.json()
        logger.info(f"CIBA initiated: auth_req_id={result.get('auth_req_id', 'N/A')[:20]}...")
        return result

    async def poll_ciba_token(self, auth_req_id: str) -> dict:
        """
        Poll the token endpoint for CIBA completion.

        Returns the token when approved, or status if still pending/denied.
        """
        resp = await self._http.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "urn:openid:params:grant-type:ciba",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_req_id": auth_req_id,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if resp.status_code == 200:
            return {"status": "approved", "token_data": resp.json()}
        elif resp.status_code == 400:
            error_data = resp.json()
            error = error_data.get("error", "unknown")
            if error == "authorization_pending":
                return {"status": "pending"}
            elif error == "slow_down":
                return {"status": "slow_down"}
            elif error == "access_denied":
                return {"status": "rejected", "error": error_data}
            elif error == "expired_token":
                return {"status": "expired", "error": error_data}

        return {"status": "error", "error": resp.text}

    async def poll_ciba_with_backoff(
        self,
        auth_req_id: str,
        interval: int = 5,
        max_attempts: int = 60,
        on_status_change: Any = None,
    ) -> dict:
        """
        Poll CIBA with exponential backoff until completion.

        Args:
            auth_req_id: The CIBA request ID
            interval: Initial polling interval (seconds)
            max_attempts: Maximum polling attempts
            on_status_change: Optional callback for status updates

        Returns:
            Final result (approved/rejected/expired/error)
        """
        current_interval = interval

        for attempt in range(max_attempts):
            logger.info(f"CIBA poll attempt {attempt + 1}/{max_attempts} (interval: {current_interval}s)")

            result = await self.poll_ciba_token(auth_req_id)
            status = result.get("status")

            if on_status_change:
                await on_status_change(status, attempt)

            if status == "approved":
                logger.info("CIBA approved!")
                return result
            elif status == "rejected":
                logger.info("CIBA rejected by user")
                return result
            elif status == "expired":
                logger.info("CIBA request expired")
                return result
            elif status == "slow_down":
                current_interval = min(current_interval + 2, 15)
            elif status == "error":
                logger.error(f"CIBA poll error: {result}")
                return result

            # Wait before next poll
            await asyncio.sleep(current_interval)

        return {"status": "timeout", "error": "Max polling attempts reached"}

    # --- Token Vault (RFC 8693 Token Exchange) ---

    async def token_exchange_for_connection(
        self,
        subject_token: str,
        connection: str = "github",
        subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token",
    ) -> dict:
        """
        Real Token Vault Exchange (RFC 8693).

        Exchanges an Auth0 access token for a provider-specific access token.
        The AI agent NEVER sees this token — only the backend proxy.

        Args:
            subject_token: User's Auth0 access token
            connection: Provider connection name (e.g., "github")
            subject_token_type: Token type being exchanged

        Returns:
            dict with access_token for the provider
        """
        resp = await self._http.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token",
                "client_id": self.tv_client_id,
                "client_secret": self.tv_client_secret,
                "subject_token": subject_token,
                "subject_token_type": subject_token_type,
                "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
                "connection": connection,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if resp.status_code == 200:
            token_data = resp.json()
            logger.info(f"Token Exchange OK for {connection} — got provider token")
            return {
                "status": "success",
                "access_token": token_data.get("access_token"),
                "token_type": token_data.get("token_type"),
                "expires_in": token_data.get("expires_in"),
                "connection": connection,
            }

        logger.error(f"Token Exchange FAILED: {resp.status_code} — {resp.text[:200]}")
        return {
            "status": "error",
            "error": resp.text,
            "code": resp.status_code,
            "connection": connection,
        }

    async def token_exchange(
        self, subject_token: str, connection: str = "aws-aegiscloud"
    ) -> dict:
        """
        Exchange an Auth0 token for a provider-specific token
        from Token Vault (RFC 8693).

        In production, this gives us a short-lived AWS token.
        For the hackathon, the response validates the flow works.
        """
        resp = await self._http.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
                "connection": connection,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if resp.status_code == 200:
            return {"status": "success", "token_data": resp.json()}

        return {"status": "error", "error": resp.text, "code": resp.status_code}

    # --- Token Revocation ---

    async def revoke_token(self, token: str) -> dict:
        """Revoke a specific token."""
        resp = await self._http.post(
            f"{self.base_url}/oauth/revoke",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "token": token,
            },
        )
        return {"status": "revoked" if resp.status_code == 200 else "error"}

    async def close(self):
        """Close HTTP client."""
        await self._http.aclose()


# Singleton
auth0_service = Auth0Service()
