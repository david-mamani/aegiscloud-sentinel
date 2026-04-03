"""
===============================================================================
  BARRERA DE TESTING RIGUROSO -- STEPS 01 + 02 COMBINED
  AegisCloud DevSecOps Sentinel
  
  This script covers ALL automated verification points from both barriers.
===============================================================================
"""
import os, sys, json, subprocess, io, urllib.request, urllib.parse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Paths
MONOREPO = Path(__file__).parent.parent.parent  # scripts -> backend -> monorepo
BACKEND = MONOREPO / "backend"
FRONTEND = MONOREPO / "frontend"
ENV_FILE = MONOREPO / ".env"
ENV_EXAMPLE = MONOREPO / ".env.example"
GITIGNORE = MONOREPO / ".gitignore"

results = []

def test(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)

def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=cwd)
        return r.stdout.strip(), r.returncode
    except:
        return "", 1

# Load env
env_vars = {}
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
            os.environ[key.strip()] = value.strip()

# ===========================================================================
print("=" * 70)
print("  STEP 01 -- PROJECT SCAFFOLDING VERIFICATION")
print("=" * 70)

# 1.1 Tool versions
print("\n[1.1] Tool Versions")
out, _ = run("node --version")
test("Node.js v18+", out.startswith("v") and int(out.split(".")[0][1:]) >= 18, out)

out, _ = run("npm --version")
test("npm v9+", out and int(out.split(".")[0]) >= 9, out)

out, _ = run("python --version")
test("Python 3.11+", "3.11" in out or "3.12" in out or "3.13" in out, out)

out, _ = run("git --version")
test("Git installed", "git version" in out, out)

# 1.2 Backend dependencies
print("\n[1.2] Backend Dependencies")
out, _ = run(f".\\venv\\Scripts\\pip.exe list --format=json", cwd=str(BACKEND))
if out:
    pkgs = {p["name"].lower(): p["version"] for p in json.loads(out)}
    test("fastapi installed", "fastapi" in pkgs, pkgs.get("fastapi", "MISSING"))
    test("langgraph installed", "langgraph" in pkgs, pkgs.get("langgraph", "MISSING"))
    test("auth0-python installed", "auth0-python" in pkgs, pkgs.get("auth0-python", "MISSING"))
    test("uvicorn installed", "uvicorn" in pkgs, pkgs.get("uvicorn", "MISSING"))
    test("python-dotenv installed", "python-dotenv" in pkgs, pkgs.get("python-dotenv", "MISSING"))
    test("httpx installed", "httpx" in pkgs, pkgs.get("httpx", "MISSING"))
else:
    test("pip list", False, "Failed to list packages")

# 1.3 Directory structure
print("\n[1.3] Project Structure")
dirs_to_check = [
    "backend/app",
    "backend/app/api",
    "backend/app/api/v1",
    "backend/app/core",
    "backend/app/models",
    "backend/app/services",
    "backend/app/services/auth0",
    "backend/app/services/aws_mock",
    "backend/app/services/langgraph",
    "frontend",
    "frontend/src" if (MONOREPO / "frontend/src").exists() else "frontend/app",
    "docs",
    "docs/steps",
]
for d in dirs_to_check:
    p = MONOREPO / d
    test(f"Dir: {d}", p.exists() and p.is_dir())

# 1.4 Key files
print("\n[1.4] Key Files")
files_to_check = [
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/core/__init__.py",
    "backend/requirements.txt",
    ".env",
    ".gitignore",
]
for f in files_to_check:
    test(f"File: {f}", (MONOREPO / f).exists())

# 1.5 .env validation
print("\n[1.5] .env Variables")
required_env = [
    "AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET",
    "AUTH0_AUDIENCE", "AUTH0_M2M_CLIENT_ID", "AUTH0_M2M_CLIENT_SECRET",
    "AUTH0_USER_ID", "APP_SECRET_KEY", "DATABASE_URL",
    "FRONTEND_URL", "BACKEND_URL", "AWS_MOCK_MODE"
]
for var in required_env:
    val = env_vars.get(var, "")
    test(f".env {var}", bool(val), f"{'set' if val else 'EMPTY'}")

# 1.6 .env.example
print("\n[1.6] .env.example")
test(".env.example exists", ENV_EXAMPLE.exists())

# 1.7 .gitignore
print("\n[1.7] .gitignore")
if GITIGNORE.exists():
    gi = GITIGNORE.read_text(encoding="utf-8", errors="replace")
    test(".gitignore has node_modules", "node_modules" in gi)
    test(".gitignore has venv", "venv" in gi)
    test(".gitignore has .env", ".env" in gi)
    test(".gitignore has *.db", "*.db" in gi or ".db" in gi)
else:
    test(".gitignore exists", False)

# 1.8 Config module
print("\n[1.8] Config Module")
try:
    sys.path.insert(0, str(BACKEND))
    from app.core.config import get_settings
    s = get_settings()
    test("config.auth0_domain", bool(s.auth0_domain), s.auth0_domain)
    test("config.auth0_client_id", bool(s.auth0_client_id), s.auth0_client_id[:10])
    test("config.auth0_user_id field exists", hasattr(s, "auth0_user_id"))
    test("config.auth0_user_id not empty", bool(s.auth0_user_id), s.auth0_user_id)
except Exception as e:
    test("Config module loads", False, str(e))

# 1.9 Backend app imports
print("\n[1.9] Backend App Import")
try:
    from app.main import app
    test("FastAPI app imports", True)
    # Check health route exists
    routes = [r.path for r in app.routes]
    test("/health route exists", "/health" in routes, str(routes[:5]))
except Exception as e:
    test("FastAPI app imports", False, str(e))

# ===========================================================================
print("\n" + "=" * 70)
print("  STEP 02 -- AUTH0 CONFIGURATION VERIFICATION")
print("=" * 70)

DOMAIN = env_vars.get("AUTH0_DOMAIN", "")
CLIENT_ID = env_vars.get("AUTH0_CLIENT_ID", "")
CLIENT_SECRET = env_vars.get("AUTH0_CLIENT_SECRET", "")
AUDIENCE = env_vars.get("AUTH0_AUDIENCE", "")
USER_ID = env_vars.get("AUTH0_USER_ID", "")

# 2.1 OIDC Discovery
print("\n[2.1] OIDC Discovery")
oidc_data = None
try:
    url = f"https://{DOMAIN}/.well-known/openid-configuration"
    resp = urllib.request.urlopen(url, timeout=10)
    oidc_data = json.loads(resp.read())
    test("OIDC issuer present", "issuer" in oidc_data, oidc_data.get("issuer"))
    test("OIDC token_endpoint", "token_endpoint" in oidc_data)
    test("OIDC authorization_endpoint", "authorization_endpoint" in oidc_data)
except Exception as e:
    test("OIDC Discovery reachable", False, str(e))

# 2.2 CIBA endpoint
print("\n[2.2] CIBA Endpoint")
if oidc_data:
    ciba = oidc_data.get("backchannel_authentication_endpoint", "")
    test("CIBA endpoint in OIDC", bool(ciba), ciba)
else:
    test("CIBA endpoint", False, "OIDC not loaded")

# 2.3 M2M Token (Client Credentials)
print("\n[2.3] M2M Token Request")
m2m_token = None
try:
    payload = json.dumps({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": AUDIENCE,
        "grant_type": "client_credentials"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://{DOMAIN}/oauth/token",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    token_data = json.loads(resp.read())
    m2m_token = token_data.get("access_token", "")
    test("M2M token received", bool(m2m_token), f"{m2m_token[:30]}...")
    test("Token type is Bearer", token_data.get("token_type", "").lower() == "bearer")
    test("Token has expiry", "expires_in" in token_data, f"{token_data.get('expires_in')}s")
    
    # Check scopes in token
    scope = token_data.get("scope", "")
    test("Scope: read:sentinel", "read:sentinel" in scope)
    test("Scope: write:sentinel", "write:sentinel" in scope)
    test("Scope: trigger:ciba", "trigger:ciba" in scope)
    test("Scope: use:tokenvault", "use:tokenvault" in scope)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    test("M2M token request", False, f"HTTP {e.code}: {body[:80]}")
except Exception as e:
    test("M2M token request", False, str(e))

# 2.4 JWT Token Validation
print("\n[2.4] JWT Token Structure")
if m2m_token:
    import base64
    parts = m2m_token.split(".")
    test("JWT has 3 parts", len(parts) == 3)
    if len(parts) >= 2:
        # Decode header
        header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        test("JWT alg is RS256", header.get("alg") == "RS256", header.get("alg"))
        
        # Decode payload  
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload_data = json.loads(base64.urlsafe_b64decode(payload_b64))
        test("JWT iss matches domain", DOMAIN in payload_data.get("iss", ""))
        test("JWT aud matches audience", payload_data.get("aud") == AUDIENCE, payload_data.get("aud"))
        
        # Check permissions in token (from RBAC)
        perms = payload_data.get("permissions", [])
        test("JWT has permissions claim", len(perms) > 0, str(perms))
else:
    test("JWT validation", False, "No token to validate")

# 2.5 AUTH0_USER_ID format
print("\n[2.5] User ID Validation")
test("USER_ID set", bool(USER_ID), USER_ID)
test("USER_ID format auth0|...", USER_ID.startswith("auth0|"), USER_ID)

# 2.6 Frontend env
print("\n[2.6] Frontend .env.local")
fe_env = FRONTEND / ".env.local"
test("frontend/.env.local exists", fe_env.exists())
if fe_env.exists():
    fe_content = fe_env.read_text(encoding="utf-8")
    test("AUTH0_SECRET set", "AUTH0_SECRET=" in fe_content)
    test("AUTH0_ISSUER_BASE_URL set", "AUTH0_ISSUER_BASE_URL=" in fe_content)
    test("AUTH0_CLIENT_ID set", "AUTH0_CLIENT_ID=" in fe_content)
    test("AUTH0_CLIENT_SECRET set", "AUTH0_CLIENT_SECRET=" in fe_content)
    test("Secret matches backend", CLIENT_SECRET in fe_content)

# ===========================================================================
# GRAND SUMMARY
# ===========================================================================
print("\n" + "=" * 70)
print("  GRAND SUMMARY -- STEPS 01 + 02")
print("=" * 70)

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)

print(f"\n  Total Tests: {total}")
print(f"  Passed:      {passed}")
print(f"  Failed:      {failed}")
print(f"  Score:       {passed}/{total} ({100*passed//total}%)")

if failed > 0:
    print(f"\n  FAILURES:")
    for name, ok, detail in results:
        if not ok:
            line = f"    [FAIL] {name}"
            if detail:
                line += f" -- {detail}"
            print(line)

print()
if failed == 0:
    print("  ============================================")
    print("  >>> ALL TESTS PASSED -- BARRIERS CLEARED <<<")
    print("  ============================================")
elif failed <= 3:
    print("  MOSTLY PASSED -- Review failures above")
else:
    print("  BARRIERS NOT CLEARED -- Fix failures above")
