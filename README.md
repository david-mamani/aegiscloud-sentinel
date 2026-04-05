# AegisCloud — DevSecOps Sentinel

> **Zero-Trust AI Agent for Cloud Infrastructure Security.**
> An AI-powered DevSecOps platform where an autonomous agent scans, analyzes, and remediates cloud security vulnerabilities — without **ever** touching a credential.

Built for the **[Authorized to Act: Auth0 for AI Agents](https://auth0.com/ai)** Hackathon.

---

## 🎬 Demo

▶️ **[Watch the 3-minute Demo Video →](YOUR_VIDEO_LINK)**

🌐 **[Live Demo →](YOUR_DEPLOY_URL)**

> **E2E Tests: 17/17 PASSED (100%)** — All endpoints verified with real Auth0 JWT authentication.

---

## 📑 Table of Contents

- [The Problem](#the-problem)
- [The Solution: Double-Blind Pattern](#the-solution-double-blind-pattern)
- [Architecture](#architecture)
- [Auth0 Features Used](#auth0-features-used)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works — The Mission Lifecycle](#how-it-works--the-mission-lifecycle)
- [Security Guarantees](#security-guarantees)
- [Getting Started](#getting-started)
- [Auth0 Configuration Guide](#auth0-configuration-guide)
- [Environment Variables](#environment-variables)
- [Docker Deployment](#docker-deployment)
- [Testing](#testing)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Bonus Blog Post](#bonus-blog-post)

---

## The Problem

AI agents are increasingly being used to manage cloud infrastructure, but they create a fundamental security paradox:

> *"How do you give an AI agent permission to fix your servers without giving it the keys to your kingdom?"*

Traditional approaches pass cloud credentials (AWS keys, GitHub tokens) directly to the LLM as function call parameters. This means:

- 🔴 The LLM can see, log, or leak credentials through prompt injection
- 🔴 Tokens live in the LLM's context window alongside user conversations
- 🔴 No human oversight over destructive infrastructure changes
- 🔴 No audit trail of what the agent accessed and why

---

## The Solution: Double-Blind Pattern

AegisCloud introduces the **Double-Blind Pattern** — an architecture where neither the AI agent nor the frontend ever handles raw provider tokens:

```
┌────────────┐      ┌──────────────┐      ┌────────────────┐      ┌──────────────┐
│  Frontend  │ JWT  │   Backend    │ RFC  │  Auth0 Token   │      │   Provider   │
│  (Next.js) │─────▶│   Proxy      │─8693▶│    Vault       │─────▶│  (AWS/GitHub) │
│            │      │  (FastAPI)   │      │                │      │              │
│ Never sees │      │ Only place   │      │ Stores tokens  │      │ Real API     │
│ any token  │      │ tokens exist │      │ securely       │      │ calls made   │
└────────────┘      └──────────────┘      └────────────────┘      └──────────────┘
                           │
                    ┌──────┴───────┐
                    │  AI Agent    │
                    │ (LangGraph)  │
                    │              │
                    │ Zero tokens  │
                    │ Zero secrets │
                    │ in messages  │
                    └──────────────┘
```

**The AI reasons about _what_ to do. The backend decides _whether_ to do it (via CIBA). Auth0 Token Vault handles _how_ to authenticate. No component has the full picture.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AegisCloud Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──── Frontend (Next.js 16) ────────────────────────────────┐  │
│  │  Auth0 SDK v4 ─── Middleware (JWT extraction) ─── Proxy   │  │
│  │  6 Pages: Mission Control │ Scopes │ Audit │ Infra │ ...  │  │
│  └────────────────────────────┬───────────────────────────────┘  │
│                               │ Bearer JWT (server-side only)    │
│  ┌──── Backend Proxy (FastAPI) ──────────────────────────────┐  │
│  │  JWT Validation (JWKS/RS256) ──── Route Handlers          │  │
│  │                                                            │  │
│  │  ┌── LangGraph Agent ──────────────────────────────────┐  │  │
│  │  │  scan_node → analyze_node → propose_node            │  │  │
│  │  │       → await_approval_node (interrupt())           │  │  │
│  │  │       → execute_node → report_node                  │  │  │
│  │  │                                                      │  │  │
│  │  │  Gemini 2.5 Flash ── AsyncSqliteSaver Checkpointer  │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌── Auth0 Client ─────────────────────────────────────┐  │  │
│  │  │  CIBA (/bc-authorize) ── Token Exchange (RFC 8693)  │  │  │
│  │  │  RAR Payloads ── Management API ── Token Revocation │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌── AWS Mock Service ─────────────────────────────────┐  │  │
│  │  │  EC2 Security Groups ── S3 Buckets ── IAM Policies  │  │  │
│  │  │  Mutable state ── Diff generation ── Action logging │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──── Auth0 Tenant ─────────────────────────────────────────┐  │
│  │  Universal Login ── Token Vault ── CIBA ── Guardian       │  │
│  │  Management API ── Custom API (resource_server)           │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Auth0 Features Used

| Feature | How It's Used | File |
|---------|--------------|------|
| **Token Vault** (RFC 8693) | Exchange user access tokens for scoped provider tokens (GitHub). Provider token used on backend and immediately destroyed. | `backend/app/services/auth0/client.py` → `token_exchange_for_connection()` |
| **CIBA** (Client-Initiated Backchannel Authentication) | When the AI agent proposes a destructive action, CIBA sends a push notification to Auth0 Guardian for human approval. | `backend/app/services/auth0/client.py` → `initiate_ciba()` |
| **RAR** (Rich Authorization Requests) | The CIBA request includes a detailed RAR payload describing exactly what the agent wants to do (resource, action, before/after diff, risk level). | `backend/app/api/v1/auth.py` → `_build_rar_payload()` |
| **Universal Login** | Auth0-hosted login with email/password, Google, and GitHub social connections. | `frontend/middleware.ts` |
| **Auth0 SDK v4** for Next.js | Server-side session management, JWT extraction in API proxy routes. | `frontend/lib/auth0.ts`, `frontend/components/providers.tsx` |
| **Management API** | Fetches user's linked identities (connected accounts), token revocation (kill switch). | `backend/app/services/auth0/client.py` → `get_management_token()` |
| **JWT Validation** (JWKS/RS256) | All backend API endpoints validate Bearer tokens against Auth0's JWKS endpoint with audience and issuer verification. | `backend/app/core/auth_middleware.py` |

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **FastAPI** | 0.115.6 | API framework / backend proxy |
| **LangGraph** | 0.4.8 | Agentic orchestration with interrupt/resume |
| **Google Gemini 2.5 Flash** | latest | LLM for security analysis and reasoning |
| **python-jose** | 3.4.0 | JWT validation (RS256, JWKS) |
| **httpx** | 0.28.1 | Async HTTP client for Auth0 API calls |
| **auth0-python** | 4.9.0 | Auth0 Management API SDK |
| **SQLite** (via aiosqlite) | — | LangGraph checkpoint persistence |
| **Pydantic Settings** | 2.7.1 | Type-safe configuration management |

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 16.2.2 | React framework with App Router |
| **React** | 19.2.4 | UI library |
| **@auth0/nextjs-auth0** | 4.16.1 | Auth0 SDK v4 (server-side sessions) |
| **Framer Motion** | 12.38.0 | Animations and transitions |
| **Recharts** | 3.8.1 | Radar chart for scopes visualization |
| **Tailwind CSS** | 4.x | Utility-first CSS |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| **Docker** + **Docker Compose** | Containerized deployment |
| **Dokploy** | VPS deployment platform |

---

## Project Structure

```
aegiscloud/
├── .env.example                    # Environment variables template
├── .env.production.example         # Production deployment template
├── .gitignore                      # Git ignore rules
├── docker-compose.yml              # Multi-service Docker configuration
├── README.md                       # This file
│
├── backend/
│   ├── Dockerfile                  # Python 3.11-slim with healthcheck
│   ├── requirements.txt            # 15 Python dependencies
│   ├── data/
│   │   ├── infrastructure_state.json   # Simulated AWS infrastructure (4 vulnerabilities)
│   │   └── scenarios.json              # 4 remediation scenarios with CIS benchmarks
│   ├── app/
│   │   ├── main.py                     # FastAPI app entry point, CORS, router mounting
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic Settings (14 env vars)
│   │   │   └── auth_middleware.py      # JWT validation against Auth0 JWKS (RS256)
│   │   ├── models/
│   │   │   └── agent_state.py          # LangGraph TypedDict state schema (15 fields)
│   │   ├── api/v1/
│   │   │   ├── auth.py                 # CIBA, RAR, Token Vault, Kill Switch (648 lines)
│   │   │   ├── missions.py             # Mission lifecycle: start/approve/reject/kill
│   │   │   ├── scopes.py               # Dynamic agent scopes from JWT claims
│   │   │   └── infrastructure.py       # Infrastructure status, vulnerabilities, diffs
│   │   └── services/
│   │       ├── orchestrator.py         # Mission → LangGraph bridge
│   │       ├── auth0/
│   │       │   └── client.py           # Auth0 API client (CIBA, Token Exchange, MGMT)
│   │       ├── langgraph/
│   │       │   ├── graph.py            # StateGraph definition (6 nodes, conditional routing)
│   │       │   └── nodes.py            # Node implementations (scan, analyze, propose, approve, execute, report)
│   │       └── aws_mock/
│   │           └── service.py          # AWS simulation (EC2, S3, IAM) with mutable state
│   └── tests/
│       ├── test_e2e.py                 # Full mission lifecycle + auth gate tests (12 tests)
│       ├── test_langgraph.py           # interrupt()/resume flow tests (3 tests)
│       └── test_aws_mock.py            # AWS mock CRUD + diff tests (6 tests)
│
└── frontend/
    ├── Dockerfile                  # Multi-stage Node 20-alpine build
    ├── package.json                # 14 dependencies
    ├── middleware.ts                # Auth0 route protection (redirects to /auth/login)
    ├── lib/
    │   ├── auth0.ts                # Auth0Client configuration (scopes, audience)
    │   └── api.ts                  # Typed API client (all calls via /api/proxy/*)
    ├── components/
    │   ├── providers.tsx            # Auth0Provider wrapper
    │   ├── layout/
    │   │   ├── sidebar.tsx          # Navigation (6 items, typography-only, no icons)
    │   │   └── header.tsx           # User info + sign out (Auth0 useUser hook)
    │   └── dashboard/
    │       ├── mission-control.tsx   # Main dashboard: scenario select → scan → approve
    │       └── infra-diff-viewer.tsx # Before/after diff visualization
    └── app/
        ├── layout.tsx              # Root layout (Inter + JetBrains Mono + Bebas Neue)
        ├── globals.css             # Design system (light/dark themes, 20+ CSS tokens)
        ├── page.tsx                # Home → Mission Control
        ├── scopes/page.tsx         # Scopes Radar (Recharts radar chart + scope list)
        ├── audit/page.tsx          # Audit Log (mission history, token source tracking)
        ├── infra/page.tsx          # Infrastructure (vulnerability list, CIS benchmarks)
        ├── kill-switch/page.tsx    # Kill Switch (arm checkbox → revoke all tokens)
        ├── settings/page.tsx       # Connected Accounts (Token Vault exchange demo)
        └── api/
            ├── proxy/[...path]/route.ts     # JWT proxy → FastAPI backend
            └── token-proxy/route.ts         # Token Vault exchange proxy
```

---

## How It Works — The Mission Lifecycle

The complete flow from vulnerability detection to remediation:

### Step 1: Infrastructure Scan
The user selects a threat scenario from the dashboard. The backend loads the simulated AWS infrastructure state and identifies non-compliant resources against CIS benchmarks.

```
User clicks "Launch Security Scan" → POST /api/v1/missions/start
```

### Step 2: AI Analysis (LangGraph)
The LangGraph agent processes the scan through 6 sequential nodes:

```
scan_node        →  Loads infrastructure state, identifies vulnerabilities
analyze_node     →  Gemini 2.5 Flash analyzes severity and impact
propose_node     →  Generates remediation plan with before/after diff
await_approval   →  interrupt() — pauses execution, waits for human
execute_node     →  Applies remediation using Token Vault credentials
report_node      →  Generates final compliance report
```

### Step 3: CIBA + Human Approval
When the agent reaches `await_approval_node`, it calls `interrupt()` with a payload containing **only metadata** (resource ID, proposed action, risk level) — **zero tokens, zero credentials**.

The backend initiates a CIBA request to Auth0 with a RAR payload:
```json
{
  "type": "urn:aegiscloud:remediation:v1:security-group-update",
  "aegis_mission_id": "mission-abc123",
  "resource_type": "security-group",
  "resource_id": "sg-0a1b2c3d4e5f6g7h8",
  "action": "revoke_security_group_ingress",
  "risk_level": "CRITICAL",
  "diff": {
    "before": "🔴 Port 22 (TCP) — OPEN to 0.0.0.0/0",
    "after": "🟢 Port 22 (TCP) — CLOSED (rule removed)"
  }
}
```

### Step 4: Token Vault Exchange (RFC 8693)
Upon approval, the backend performs a Token Exchange:

```
1. Extract user's Auth0 access token from the request
2. POST to Auth0 /oauth/token with grant_type=urn:ietf:params:oauth:grant-type:token-exchange
3. Receive scoped provider token (e.g., GitHub access token)
4. Use provider token to call the target API
5. Immediately destroy the provider token
```

**At no point does the AI agent or the frontend see the provider token.**

### Step 5: Remediation & Report
The approved action is executed against the simulated infrastructure. The state is mutated (e.g., security group rule removed, S3 bucket locked down), and a complete audit trail is generated.

---

## Security Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| **AI agent never sees tokens** | The `messages` array passed to Gemini contains only analysis text. Token handling happens in `execute_node` at the infrastructure layer, never in the LLM context. |
| **Frontend never sees tokens** | The Next.js proxy (`/api/proxy/[...path]`) extracts the Auth0 access token server-side using `auth0.getAccessToken()`. The browser only makes cookie-authenticated requests. |
| **All API routes require JWT** | `verify_token` dependency on every router validates Bearer tokens against Auth0's JWKS endpoint with RS256, audience, and issuer checks. |
| **Unauthenticated = 401** | Verified empirically: all `/api/v1/*` endpoints return HTTP 401 without a valid JWT. |
| **Emergency stop** | Kill Switch (`POST /api/v1/auth/kill-switch`) revokes the management token, clears all CIBA requests, and kills all active missions in a single atomic operation. |
| **CORS hardened** | Explicit origin allowlist — no wildcard origins. |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- An [Auth0](https://auth0.com) account (free tier works)
- A [Google AI Studio](https://aistudio.google.com) API key (Gemini 2.5 Flash)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/aegiscloud-sentinel.git
cd aegiscloud-sentinel
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your Auth0 and Google API credentials
```

### 3. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify: `http://localhost:8000/health` should return `{"status": "operational", "pattern": "double-blind"}`

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` — you'll be redirected to Auth0 login.

---

## Auth0 Configuration Guide

### 1. Create Two Applications in Auth0 Dashboard

#### Backend — Machine-to-Machine (M2M) Application
- **Type**: Machine to Machine
- **Authorized API**: Auth0 Management API
- **Permissions**: `read:users`, `read:user_idp_tokens`, `read:connections`
- Copy `Client ID` → `AUTH0_M2M_CLIENT_ID`
- Copy `Client Secret` → `AUTH0_M2M_CLIENT_SECRET`

#### Frontend — Regular Web Application
- **Type**: Regular Web Application
- **Allowed Callback URLs**: `http://localhost:3000/auth/callback`
- **Allowed Logout URLs**: `http://localhost:3000`
- Copy `Client ID` → `AUTH0_CLIENT_ID_FRONTEND`
- Copy `Client Secret` → `AUTH0_CLIENT_SECRET_FRONTEND`

### 2. Create a Custom API

- **Name**: `AegisCloud Backend Proxy`
- **Identifier (Audience)**: `https://api.aegiscloud.dev`
- **Signing Algorithm**: RS256

### 3. Enable GitHub Social Connection (for Token Vault)

- Go to **Authentication → Social → GitHub**
- Enable the connection
- Toggle **"Token Vault"** (or "Authentication and Connected Accounts")
- Add scopes: `read:user`, `repo`

### 4. Create Token Vault Custom API Client

The Token Vault requires a Custom API Client of type `resource_server` for RFC 8693 exchange. Create it via the Management API:

```bash
curl -X POST "https://YOUR_DOMAIN.auth0.com/api/v2/clients" \
  -H "Authorization: Bearer YOUR_MGMT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AegisCloud Token Vault Exchange",
    "app_type": "non_interactive",
    "token_endpoint_auth_method": "client_secret_post",
    "grant_types": ["urn:ietf:params:oauth:grant-type:token-exchange"]
  }'
```

Copy the returned `client_id` → `AUTH0_TOKEN_VAULT_CLIENT_ID` and `client_secret` → `AUTH0_TOKEN_VAULT_CLIENT_SECRET`.

### 5. Configure CIBA (Optional — Enterprise Plan)

If your tenant supports CIBA:
- Enable **Auth0 Guardian** for push notifications
- Configure the CIBA endpoint in your API settings

If CIBA is not available (non-Enterprise plan), AegisCloud automatically falls back to a mock CIBA mode that preserves the same architectural flow.

---

## Environment Variables

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH0_DOMAIN` | ✅ | Your Auth0 tenant domain (e.g., `dev-xxx.us.auth0.com`) |
| `AUTH0_CLIENT_ID` | ✅ | Backend application Client ID |
| `AUTH0_CLIENT_SECRET` | ✅ | Backend application Client Secret |
| `AUTH0_AUDIENCE` | ✅ | Custom API identifier (`https://api.aegiscloud.dev`) |
| `AUTH0_M2M_CLIENT_ID` | ✅ | M2M application Client ID (Management API access) |
| `AUTH0_M2M_CLIENT_SECRET` | ✅ | M2M application Client Secret |
| `AUTH0_USER_ID` | ✅ | Your Auth0 user ID (for CIBA binding messages) |
| `AUTH0_TOKEN_VAULT_CLIENT_ID` | ✅ | Token Vault API Client ID (RFC 8693) |
| `AUTH0_TOKEN_VAULT_CLIENT_SECRET` | ✅ | Token Vault API Client Secret |
| `GOOGLE_API_KEY` | ✅ | Google AI Studio API key (Gemini 2.5 Flash) |
| `APP_SECRET_KEY` | ✅ | Random secret for backend security (32+ chars) |
| `FRONTEND_URL` | — | Frontend origin for CORS (default: `http://localhost:3000`) |
| `AWS_MOCK_MODE` | — | Enable AWS mock mode (default: `true`) |

### Frontend (Next.js env)

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH0_SECRET` | ✅ | Random secret for session encryption (32+ chars) |
| `AUTH0_DOMAIN` | ✅ | Same Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | ✅ | Frontend Regular Web App Client ID |
| `AUTH0_CLIENT_SECRET` | ✅ | Frontend Regular Web App Client Secret |
| `AUTH0_AUDIENCE` | ✅ | Same custom API identifier |
| `APP_BASE_URL` | — | Frontend URL (default: `http://localhost:3000`) |
| `NEXT_PUBLIC_API_URL` | — | Backend URL (default: `http://localhost:8000`) |

---

## Docker Deployment

### Development

```bash
docker compose up --build
```

This starts both services:
- **Backend**: `http://localhost:8000` (with healthcheck)
- **Frontend**: `http://localhost:3000` (waits for backend health)

### Production

```bash
cp .env.production.example .env
# Configure all variables for your domain
docker compose up -d --build
```

The frontend Dockerfile uses a **multi-stage build** (deps → builder → runner) for optimal image size with Next.js standalone output.

---

## Testing

### Run All Backend Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Test Suite Overview

| File | Tests | What It Validates |
|------|-------|-------------------|
| `test_e2e.py` | 12 | Full mission lifecycle: health → infra → scopes → connections → start → approve → audit → RAR → kill switch → reset. Includes `TestAuthGate` that verifies unauthenticated requests return 401. |
| `test_langgraph.py` | 3 | LangGraph `interrupt()`/`Command(resume)` flow with `SqliteSaver` checkpointer. Tests both approval and rejection paths. |
| `test_aws_mock.py` | 6 | AWS mock CRUD operations: describe SGs, revoke ingress, put public access block, generate diffs, reset state. |

Tests use `app.dependency_overrides` to bypass JWT auth with a mock claims payload that includes full RBAC permissions.

---

## API Reference

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns `{ status: "operational", pattern: "double-blind" }` |
| `GET` | `/` | Project info and endpoint listing |
| `GET` | `/docs` | FastAPI Swagger UI |

### Protected Endpoints (require `Authorization: Bearer <JWT>`)

#### Missions
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/missions/start` | Start a security scan mission. Body: `{ "scenario": "open-port-22" }` |
| `GET` | `/api/v1/missions/{id}/status` | Get mission status and details |
| `POST` | `/api/v1/missions/{id}/approve` | Approve mission (triggers Token Vault exchange + execution) |
| `POST` | `/api/v1/missions/{id}/reject` | Reject mission with optional reason |
| `POST` | `/api/v1/missions/{id}/kill` | Kill a specific mission |
| `GET` | `/api/v1/missions/active` | List all missions (audit trail) |

#### Infrastructure
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/infra/status` | Current infrastructure state with vulnerability counts |
| `GET` | `/api/v1/infra/vulnerabilities` | Flat list of non-compliant findings sorted by risk score |
| `GET` | `/api/v1/infra/audit-log` | Log of all infrastructure actions taken |
| `GET` | `/api/v1/infra/diff/{scenario_id}` | Before/after diff for a remediation scenario |
| `POST` | `/api/v1/infra/reset` | Reset infrastructure to initial vulnerable state (demo rerun) |

#### Auth & Token Vault
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/ciba/initiate` | Initiate CIBA request with RAR payload |
| `POST` | `/api/v1/auth/ciba/{id}/approve` | Approve/reject a CIBA approval request |
| `GET` | `/api/v1/auth/ciba/status/{id}` | Check CIBA request status |
| `GET` | `/api/v1/auth/ciba/active` | List active CIBA requests |
| `GET` | `/api/v1/auth/connections` | List Token Vault connected accounts |
| `POST` | `/api/v1/auth/token-vault/exchange-real` | Execute RFC 8693 Token Exchange (GitHub) |
| `GET` | `/api/v1/auth/rar/preview` | Preview RAR payload for a scenario |
| `POST` | `/api/v1/auth/kill-switch` | Emergency: revoke all tokens, halt all operations |

#### Scopes
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/scopes/` | Agent scopes dynamically derived from JWT claims |

---

## Frontend Pages

### Mission Control (`/`)
The primary dashboard. Select a threat scenario (SSH Port 22 Open, S3 Bucket Public, Database Exposed), launch a security scan, and manage the approval/rejection flow. Displays real-time mission status with animated transitions.

### Scopes Radar (`/scopes`)
Radar chart visualization of the AI agent's permission boundaries. Scopes are dynamically derived from the authenticated user's JWT claims — the intersection of Token Vault capabilities and user-granted permissions.

### Audit Log (`/audit`)
Complete mission history with token source tracking. Shows total missions, completed count, rejected count, and how many used Token Vault for credential exchange.

### Infrastructure (`/infra`)
Live infrastructure monitoring showing all AWS resources (security groups, S3 buckets, IAM policies) with severity indicators and CIS benchmark references.

### Kill Switch (`/kill-switch`)
Emergency control. Requires explicit "I understand this action is irreversible" confirmation before revoking all active tokens in Auth0 Token Vault and halting all agent operations.

### Connected Accounts (`/settings`)
Displays Token Vault-linked identity providers. The **"Test Exchange"** button triggers a live RFC 8693 Token Exchange: the backend exchanges the user's Auth0 token for a GitHub access token, calls the GitHub API (`/user` and `/user/repos`), returns the profile and repositories, and immediately destroys the provider token. A step-by-step animated timeline shows the exchange process.

---

## Bonus Blog Post

### Double-Blind: A Pattern for Secure AI Agent Authorization

*How we built an AI security agent that can remediate your cloud infrastructure without ever seeing a credential.*

The biggest challenge in building AI agents for infrastructure management isn't the AI — it's the credentials. When an LLM needs to close a firewall port, it traditionally receives AWS access keys as function call parameters. Those keys end up in the model's context window, in logs, in prompt injection attack surfaces.

We built AegisCloud to solve this with what we call the **Double-Blind Pattern**: the AI agent knows *what* action to take, but never *how* to authenticate to the provider. The user's frontend knows *who* is requesting the action, but never *what* token is used. Only the backend proxy, for a brief ephemeral moment, handles the real credential — and it's destroyed immediately after use.

Auth0's Token Vault (RFC 8693) made this possible. Our LangGraph agent uses `interrupt()` to pause execution when it identifies a destructive action. The backend sends a CIBA request to Auth0 with a RAR payload describing exactly what will change. Only after the human approves via Auth0 Guardian does the backend exchange the user's access token for a scoped provider token through Token Vault.

The hardest technical challenge was CIBA availability — it requires an Auth0 Enterprise plan. We implemented a graceful fallback that preserves the identical architectural flow: the same RAR payload, the same interrupt/resume lifecycle, the same Token Vault exchange — just with the approval step handled in the dashboard UI instead of Guardian push notifications.

Three insights for the Auth0 team:
1. **Token Vault's Custom API Client requirement** (type `resource_server`) for Token Exchange isn't clearly documented. We had to discover this through the Management API.
2. **CIBA + RAR + LangGraph interrupt()** is a natural fit for agent authorization. Consider providing an SDK integration.
3. **The Double-Blind Pattern** could be a reusable architecture that Auth0 documents and evangelizes for any AI agent framework.

The pattern transfers beyond AWS — any OAuth-connected service (GitHub, GCP, Slack) can be secured this way. We believe this is the future of AI agent authorization: agents that can act with authority without ever holding the keys.

---

## E2E Test Results

All 17 endpoints verified with real Auth0 M2M JWT authentication:

```
PASSED: 17 | FAILED: 0 | TOTAL: 17 | RATE: 100%

✅ GET  /health
✅ GET  /infra/status
✅ GET  /infra/vulnerabilities
✅ GET  /infra/audit-log
✅ GET  /scopes/
✅ POST /missions/start
✅ GET  /missions/{id}/status
✅ POST /missions/{id}/approve
✅ GET  /missions/active
✅ GET  /auth/connections
✅ POST /ciba/initiate
✅ GET  /ciba/status/{id}
✅ GET  /ciba/active
✅ POST /ciba/{id}/approve
✅ GET  /rar/preview
✅ POST /token-vault/exchange
✅ POST /infra/reset
```

Run the test suite:
```bash
cd backend && python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt
cd .. && python test_e2e.py
```

---

## License

MIT

---

**Built with 🛡️ by [David Mamani](https://github.com/david-mamani) for the [Authorized to Act: Auth0 for AI Agents](https://auth0.com/ai) Hackathon**
