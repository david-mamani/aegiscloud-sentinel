# AegisCloud: DevSecOps Sentinel

**Zero-Trust AI Agent for Infrastructure Security — Built with Auth0 Token Vault**

[![Auth0](https://img.shields.io/badge/Auth0-Token_Vault-blue)](https://auth0.com)
[![CIBA](https://img.shields.io/badge/CIBA-Backchannel_Auth-orange)](https://auth0.com)
[![RFC 8693](https://img.shields.io/badge/RFC_8693-Token_Exchange-green)](https://datatracker.ietf.org/doc/html/rfc8693)

AegisCloud is an AI-powered DevSecOps dashboard that scans cloud infrastructure for security vulnerabilities and proposes automated remediation — all while ensuring the AI agent **never** touches a credential.

## The Double-Blind Pattern

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   Frontend   │───▶│   FastAPI     │───▶│  LangGraph   │───▶│   Gemini     │
│   (Next.js)  │    │   Backend    │    │   Agent      │    │   2.5 Flash  │
└──────┬───────┘    └──────┬───────┘    └──────────────┘    └──────────────┘
       │                    │
       │ Never sees         │ Token Exchange
       │ tokens             │ (RFC 8693)
       │                    ▼
       │            ┌──────────────┐
       │            │  Auth0       │
       └───────────▶│  Token Vault │
          Login     └───────┬──────┘
          only              │
                            ▼
                    ┌──────────────┐
                    │   GitHub /   │
                    │   AWS Mock   │
                    └──────────────┘
```

**Neither the AI agent nor the frontend user ever sees the provider tokens.** Only the backend proxy has access via Token Vault.

## Features

| Feature | Description |
|---------|-------------|
| **Mission Control** | AI scans infrastructure and proposes remediations |
| **Token Vault** | RFC 8693 Token Exchange for secure credential delegation |
| **CIBA** | Client-Initiated Backchannel Authentication for human approval |
| **RAR** | Rich Authorization Requests for fine-grained permissions |
| **Kill Switch** | Emergency stop that revokes all tokens and halts operations |
| **Scopes Radar** | Visual agent permission boundaries |
| **Audit Log** | Full mission history and compliance trail |
| **Connected Accounts** | Token Vault connection management |

## Tech Stack

- **Frontend:** Next.js 16, Auth0 SDK v4, Framer Motion, Tailwind CSS
- **Backend:** FastAPI, LangGraph, Google Gemini 2.5 Flash
- **Auth:** Auth0 Token Vault, CIBA, RAR, Guardian
- **Infrastructure:** Docker, Docker Compose

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Auth0 account (free tier works)
- Google Cloud API key (Gemini)

### Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Create .env file with:
# AUTH0_DOMAIN=your-tenant.us.auth0.com
# AUTH0_CLIENT_ID=your-m2m-client-id
# AUTH0_CLIENT_SECRET=your-m2m-client-secret
# AUTH0_AUDIENCE=https://api.aegiscloud.dev
# GOOGLE_API_KEY=your-gemini-api-key

$env:PYTHONPATH="$PWD"
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install

# Create .env.local with:
# AUTH0_SECRET=your-random-secret
# AUTH0_DOMAIN=your-tenant.us.auth0.com
# AUTH0_CLIENT_ID=your-frontend-client-id
# AUTH0_CLIENT_SECRET=your-frontend-client-secret
# AUTH0_AUDIENCE=https://api.aegiscloud.dev
# APP_BASE_URL=http://localhost:3000
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

### Auth0 Configuration

1. Create a **Regular Web Application** ("AegisCloud Backend Proxy")
   - Callback URLs: `http://localhost:3000/auth/callback`
   - Enable grant types: Authorization Code, Refresh Token, CIBA, Token Vault
2. Create a **Machine-to-Machine** application for backend API calls
3. Create a **Custom API** with identifier `https://api.aegiscloud.dev`
4. Create a **Custom API Client** (resource_server) via the Management API for Token Exchange:
   ```bash
   curl -X POST 'https://YOUR-DOMAIN/api/v2/clients' \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer YOUR_MANAGEMENT_TOKEN' \
     -d '{"name": "AegisCloud Token Vault Client", "app_type": "resource_server", "resource_server_identifier": "https://api.aegiscloud.dev", "grant_types": ["urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token"]}'
   ```
5. Enable **GitHub** as a Social Connection with "Authentication and Connected Accounts for Token Vault"
6. Copy the generated Client ID/Secret to `AUTH0_TOKEN_VAULT_CLIENT_ID` / `AUTH0_TOKEN_VAULT_CLIENT_SECRET`
7. See `.env.example` for all required environment variables

### Docker

```bash
docker compose build
docker compose up -d
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| POST | `/api/v1/missions/start` | Start a security scan mission |
| GET | `/api/v1/missions/{id}/status` | Check mission status |
| POST | `/api/v1/missions/{id}/approve` | Approve remediation (Token Vault) |
| POST | `/api/v1/missions/{id}/reject` | Reject remediation |
| GET | `/api/v1/infra/status` | Infrastructure scan results |
| POST | `/api/v1/infra/reset` | Reset to vulnerable state (demo) |
| GET | `/api/v1/scopes/` | Agent permission boundaries |
| GET | `/api/v1/auth/connections` | Connected accounts (Token Vault) |
| POST | `/api/v1/auth/token-vault/exchange` | Test Token Exchange |
| POST | `/api/v1/auth/kill-switch` | Emergency kill switch |
| GET | `/api/v1/auth/rar/preview` | Preview RAR payload |

## Security Architecture

1. **JWT Authentication:** All backend API routes are protected by JWT validation against Auth0 JWKS
2. **Token Vault:** Provider tokens stored in Auth0, accessed via RFC 8693 Token Exchange
3. **Double-Blind:** AI agent and frontend NEVER see provider tokens
4. **CIBA:** Human approval via Guardian push notification before any remediation
5. **RAR:** Rich Authorization Requests describe exactly what the agent does
6. **Kill Switch:** One-click revocation of all tokens and operations
7. **CORS Hardened:** Explicit allowlist for methods, headers, and origins

## License

MIT

## Hackathon

Built for the **"Authorized to Act: AI Agents with Auth0"** hackathon on Devpost.
