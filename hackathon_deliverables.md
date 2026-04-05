# AegisCloud — Hackathon Deliverables Guide

## 📊 E2E Test Results: 17/17 PASSED (100%)

| # | Endpoint | Status |
|---|----------|--------|
| 1 | `GET /health` | ✅ PASS |
| 2 | `GET /infra/status` | ✅ PASS |
| 3 | `GET /infra/vulnerabilities` | ✅ PASS |
| 4 | `GET /infra/audit-log` | ✅ PASS |
| 5 | `GET /scopes/` | ✅ PASS |
| 6 | `POST /missions/start` | ✅ PASS |
| 7 | `GET /missions/{id}/status` | ✅ PASS |
| 8 | `POST /missions/{id}/approve` | ✅ PASS |
| 9 | `GET /missions/active` | ✅ PASS |
| 10 | `GET /auth/connections` | ✅ PASS |
| 11 | `POST /ciba/initiate` (CIBA) | ✅ PASS |
| 12 | `GET /ciba/status/{id}` | ✅ PASS |
| 13 | `GET /ciba/active` | ✅ PASS |
| 14 | `POST /ciba/{id}/approve` | ✅ PASS |
| 15 | `GET /rar/preview` (RAR) | ✅ PASS |
| 16 | `POST /token-vault/exchange` | ✅ PASS |
| 17 | `POST /infra/reset` | ✅ PASS |

---

## 🎬 Video Script (3 minutes — Manim + Motion Canvas + ElevenLabs + Screen Capture)

### Requirements Checklist
- [x] Hosted on YouTube or Vimeo
- [x] Max 3-4 minutes
- [x] Show Auth0 Token Vault usage
- [x] Show secure consent/delegation
- [x] Show human-in-the-loop governance

---

### SCENE 1: The Hook (0:00 - 0:20)
**Narration (ElevenLabs):**
> "What happens when you give an AI agent the keys to your cloud? It can leak them. AegisCloud solves this with a radical idea: an AI that can fix your infrastructure without ever touching a single credential."

**Visual (Manim/Motion Canvas):**
- Quick animation: Traditional flow showing credentials flowing through an LLM (red X marks)
- "THE PROBLEM" title → credentials visible in context window
- Transition to "THE SOLUTION" → Double-Blind Pattern diagram

---

### SCENE 2: Architecture Overview (0:20 - 0:45)
**Narration:**
> "Introducing AegisCloud Sentinel — a Zero-Trust DevSecOps platform powered by the Double-Blind Pattern. The AI agent analyzes threats and proposes fixes, but it NEVER sees provider tokens. Here's how: The user authenticates via Auth0. When the agent needs to act, it triggers a CIBA request — a push notification asking the human to approve. Only after approval does Auth0's Token Vault exchange the user's JWT for a scoped provider token — server-side only."

**Visual (Motion Canvas):**
- Animated flow diagram:
  ```
  User JWT → Backend Proxy → Auth0 /oauth/token → Token Vault → Provider Token → GitHub API
  ```
- Each arrow lights up in sequence
- "TOKEN NEVER LEAVES THE BACKEND" callout in green

---

### SCENE 3: Live Demo — Dashboard (0:45 - 1:15)
**Narration:**
> "Let me show you AegisCloud in action. Here's our Mission Control dashboard. It shows real-time infrastructure vulnerabilities — an open SSH port, a public S3 bucket, an exposed database."

**Visual (Screen Capture):**
- Open `https://aegiscloud.yourdomain.com` (or localhost:3000)
- Show the Mission Control page with threat scenarios
- Hover over "SSH Port 22 Open" → highlight CRITICAL severity
- Click **"Launch Security Scan"**
- Show the Gemini AI analyzing the threat in real-time
- Show the CIBA approval notification appearing

---

### SCENE 4: Live Demo — CIBA Approval (1:15 - 1:45)
**Narration:**
> "The AI has analyzed the threat and recommends closing port 22. But it can't act alone. A CIBA push notification is sent to the security engineer. They see the Rich Authorization Request — exactly what will change, the scope of access needed, and the diff of the proposed fix. Only after explicit human approval does the mission execute."

**Visual (Screen Capture):**
- Show the CIBA approval modal/notification
- Highlight the RAR payload: scope, action, diff (before/after)
- Click **"Approve"**
- Show the mission status change to "Completed"
- Show the Audit Log updating in real-time

---

### SCENE 5: Live Demo — Token Vault Exchange (1:45 - 2:20)
**Narration:**
> "Now the real magic: the Token Vault. Watch as we trigger a real RFC 8693 token exchange. The user's JWT is sent to Auth0's Token Vault. Auth0 returns the user's GitHub access token — but it ONLY exists on the backend. The frontend and AI agent never see it. We use that token to call the GitHub API — fetching the user's real profile and repositories — then immediately destroy it."

**Visual (Screen Capture):**
- Navigate to **Connected Accounts** (`/settings`)
- Show GitHub connection with "VAULT ACTIVE"
- Click **"Test Exchange"**
- Show the exchange timeline appearing step by step:
  1. ✅ User access token extracted
  2. ✅ Token Vault exchange
  3. ✅ Provider token retrieved (server-side only)
  4. ✅ GitHub API /user called
  5. ✅ GitHub API /repos called
  6. ✅ Token destroyed — never exposed
- Show REAL GitHub data: profile name, avatar, repos
- Highlight: "The GitHub token was used on the backend and immediately destroyed"

---

### SCENE 6: Architecture Recap + Kill Switch (2:20 - 2:50)
**Narration:**
> "AegisCloud also includes a Kill Switch — one button that revokes all active tokens, halts all running missions, and clears all CIBA requests. Complete Zero-Trust with instant shutdown capability."

**Visual (Motion Canvas + Screen Capture):**
- Show Scopes Radar page — what the agent can and cannot access
- Show Kill Switch page — click it to demonstrate emergency shutdown
- Quick architecture recap animation showing all Auth0 features:
  - ✅ Token Vault (RFC 8693)
  - ✅ CIBA (Simulated, production-ready architecture)
  - ✅ Rich Authorization Requests (RAR)
  - ✅ JWKS JWT Verification
  - ✅ Double-Blind Pattern
  - ✅ Scoped Access Control

---

### SCENE 7: Closing (2:50 - 3:00)
**Narration:**
> "AegisCloud proves that AI agents can be powerful AND secure. Built with Auth0's Token Vault, CIBA, and the Double-Blind Pattern. No credential ever touches the AI. AegisCloud — Authorized to Act, Engineered to Protect."

**Visual (Motion Canvas):**
- Logo animation
- GitHub link
- "Built for Auth0 Hackathon 2025"

---

## 🚀 Deployment Guide — Dokploy (VPS)

### Prerequisites
- VPS with Docker installed (Ubuntu 22.04+ recommended)
- Dokploy installed on VPS
- Domain configured (e.g., `aegiscloud.yourdomain.com`)
- Auth0 Dashboard access

### Step 1: Prepare the VPS
```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# Install Dokploy if not already installed
curl -sSL https://dokploy.com/install.sh | sh
```

### Step 2: Create Project in Dokploy
1. Open Dokploy dashboard → **Projects** → **New Project**
2. Name: `aegiscloud`
3. Source: **GitHub** → Connect your repo `david-mamani/aegiscloud-sentinel`

### Step 3: Configure Services

#### Backend Service
1. **Create Service** → Docker Compose
2. **Source Path**: `/` (root — uses `docker-compose.yml`)
3. Or create individual services:

**Backend:**
- Type: Docker
- Dockerfile Path: `backend/Dockerfile`
- Port: 8000
- Domain: `api.aegiscloud.yourdomain.com`

**Frontend:**
- Type: Docker  
- Dockerfile Path: `frontend/Dockerfile`
- Port: 3000
- Domain: `aegiscloud.yourdomain.com`

### Step 4: Environment Variables
Add ALL of these in Dokploy's Environment section:

```env
# Auth0
AUTH0_DOMAIN=dev-26mt8xnc232f0yjw.us.auth0.com
AUTH0_AUDIENCE=https://api.aegiscloud.dev
AUTH0_CLIENT_ID=DFonMUivzFWTB1auUYOxQwlSHF9avbla
AUTH0_CLIENT_SECRET=<YOUR_SECRET>
AUTH0_TOKEN_VAULT_CLIENT_ID=J542SKtnf7a6R1Fy1DBKFJuVQyCIovjz
AUTH0_TOKEN_VAULT_CLIENT_SECRET=<YOUR_TV_SECRET>

# Gemini
GOOGLE_API_KEY=<YOUR_KEY>

# App
APP_SECRET_KEY=<GENERATE_RANDOM_32_CHARS>
FRONTEND_URL=https://aegiscloud.yourdomain.com
AWS_MOCK_MODE=true

# Frontend-specific
AUTH0_SECRET=<GENERATE_RANDOM_64_CHARS>
AUTH0_CLIENT_ID_FRONTEND=DFonMUivzFWTB1auUYOxQwlSHF9avbla
AUTH0_CLIENT_SECRET_FRONTEND=<YOUR_SECRET>
APP_BASE_URL=https://aegiscloud.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.aegiscloud.yourdomain.com
```

### Step 5: Update Auth0 Dashboard
In Auth0 Dashboard → Applications → AegisCloud Backend Proxy:
1. **Allowed Callback URLs**: Add `https://aegiscloud.yourdomain.com/auth/callback`
2. **Allowed Logout URLs**: Add `https://aegiscloud.yourdomain.com`
3. **Allowed Web Origins**: Add `https://aegiscloud.yourdomain.com`

### Step 6: Deploy
1. In Dokploy, click **Deploy**
2. Wait for build to complete (2-3 minutes)
3. Visit `https://aegiscloud.yourdomain.com` 
4. Login with GitHub → Test Token Exchange

### Step 7: SSL (Auto via Dokploy)
Dokploy handles SSL via Let's Encrypt automatically when you assign a domain.

### Step 8: Verify Deployment
```bash
# Health check
curl https://api.aegiscloud.yourdomain.com/health

# Test with M2M token (from your local machine)
curl -X POST https://dev-26mt8xnc232f0yjw.us.auth0.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"DFonMU...","client_secret":"...", "audience":"https://api.aegiscloud.dev","grant_type":"client_credentials"}'
```

---

## 📝 Devpost Submission Checklist

- [ ] **Project Name**: AegisCloud — DevSecOps Sentinel
- [ ] **Tagline**: Zero-Trust AI Agent for Cloud Security — powered by Auth0's Double-Blind Pattern
- [ ] **Video**: Upload to YouTube (3 min)
- [ ] **GitHub**: Ensure repo is PUBLIC (`david-mamani/aegiscloud-sentinel`)
- [ ] **Live Demo URL**: Deploy to VPS and provide link
- [ ] **Test Credentials**: Include "Login with GitHub" instruction in description
- [ ] **Description**: Use the README sections
- [ ] **Built With**: Auth0, Python, FastAPI, Next.js, LangGraph, Gemini AI, Docker
- [ ] **Auth0 Features**: Token Vault, CIBA (simulated), RAR, JWKS, Scoped Access

### Description Template for Devpost:

**Inspiration:** AI agents managing cloud infrastructure face a security paradox — they need credentials to act, but those credentials are vulnerable in the LLM context window.

**What it does:** AegisCloud is a Zero-Trust DevSecOps platform where an AI agent scans, analyzes, and remediates cloud security vulnerabilities without ever seeing a credential. It uses Auth0's Token Vault for the "Double-Blind Pattern" — provider tokens only exist on the backend proxy, never in the AI agent's context.

**How we built it:** FastAPI backend with JWKS JWT verification, Next.js frontend with Auth0 SDK, LangGraph for AI workflow orchestration with human-in-the-loop interrupts, and Auth0 Token Vault for secure RFC 8693 token exchange.

**Challenges:** GitHub OAuth Apps don't issue refresh tokens by default, requiring us to implement an elegant Management API fallback that preserves the Double-Blind pattern. Configuring Token Vault for real token exchange required precise coordination between the Custom API Client, connection settings, and upstream parameters.

**Accomplishments:** 
- Real Token Vault exchange with GitHub — fetching live user data
- 17/17 E2E tests passing (100%)
- Complete CIBA mock flow with RAR payloads
- Kill Switch for emergency token revocation
- Scopes Radar for transparent agent permissions

**What we learned:** Token Vault is production-ready for securing AI agent access to third-party APIs. The Double-Blind Pattern is the right architecture for any AI system that needs to act on behalf of users.

**What's next:** CIBA integration with Auth0 Guardian when Enterprise plan is available, real AWS integration for live infrastructure remediation, and multi-agent orchestration with scoped token exchange.
