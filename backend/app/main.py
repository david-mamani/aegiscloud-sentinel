"""
AegisCloud Backend — FastAPI Application Entry Point.

This is the Double-Blind Proxy: the ONLY component that touches Auth0 credentials.
The AI agent (LangGraph) NEVER has access to tokens or secrets.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.auth_middleware import verify_token

# Import API routers
from app.api.v1.missions import router as missions_router
from app.api.v1.infrastructure import router as infra_router
from app.api.v1.auth import router as auth_router
from app.api.v1.scopes import router as scopes_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AegisCloud DevSecOps Sentinel — Zero-Trust AI Agent Proxy. "
        "Implements the Double-Blind Pattern with Auth0 Token Vault, "
        "CIBA, and RAR for secure autonomous infrastructure remediation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — Allow frontend (restricted methods + headers for production security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include API routers — ALL protected by JWT verification
app.include_router(missions_router, prefix="/api/v1", dependencies=[Depends(verify_token)])
app.include_router(infra_router, prefix="/api/v1", dependencies=[Depends(verify_token)])
app.include_router(auth_router, prefix="/api/v1", dependencies=[Depends(verify_token)])
app.include_router(scopes_router, prefix="/api/v1", dependencies=[Depends(verify_token)])


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint — confirms the Double-Blind Proxy is operational."""
    return {
        "status": "operational",
        "service": settings.app_name,
        "version": settings.app_version,
        "auth0_configured": bool(settings.auth0_domain),
        "aws_mock_mode": settings.aws_mock_mode,
        "pattern": "double-blind",
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with project info."""
    return {
        "project": "AegisCloud DevSecOps Sentinel",
        "tagline": "Zero-Trust AI Agent for Infrastructure Security",
        "architecture": "Double-Blind Pattern",
        "components": {
            "proxy": "FastAPI (this service)",
            "agent": "LangGraph + Google Gemini",
            "identity": "Auth0 Token Vault + CIBA + RAR",
            "frontend": "Next.js Dashboard",
            "cloud": "AWS (Mocked)",
        },
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "api": "/api/v1/",
        },
    }
