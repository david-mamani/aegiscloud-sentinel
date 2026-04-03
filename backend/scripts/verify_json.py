"""Write results to JSON for clean reading"""
import os, sys, json, subprocess, io, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MONOREPO = Path(__file__).parent.parent.parent
BACKEND = MONOREPO / "backend"
FRONTEND = MONOREPO / "frontend"
ENV_FILE = MONOREPO / ".env"

env_vars = {}
for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()
        os.environ[key.strip()] = value.strip()

results = {}

# Step 01 checks
results["step01"] = {}

# Versions
out = subprocess.run("node --version", shell=True, capture_output=True, text=True).stdout.strip()
results["step01"]["node_version"] = out

out = subprocess.run("npm --version", shell=True, capture_output=True, text=True).stdout.strip()
results["step01"]["npm_version"] = out

out = subprocess.run("python --version", shell=True, capture_output=True, text=True).stdout.strip()
results["step01"]["python_version"] = out

out = subprocess.run("git --version", shell=True, capture_output=True, text=True).stdout.strip()
results["step01"]["git_version"] = out

# Deps
out = subprocess.run(f"{BACKEND/'venv/Scripts/pip.exe'} list --format=json", shell=True, capture_output=True, text=True).stdout.strip()
pkgs = {p["name"].lower(): p["version"] for p in json.loads(out)} if out else {}
results["step01"]["key_packages"] = {
    k: pkgs.get(k, "MISSING") for k in ["fastapi", "langgraph", "auth0-python", "uvicorn", "httpx", "python-dotenv"]
}

# Structure
dirs = ["backend/app", "backend/app/api/v1", "backend/app/core", "backend/app/models",
        "backend/app/services", "backend/app/services/auth0", "backend/app/services/aws_mock",
        "backend/app/services/langgraph", "frontend", "docs", "docs/steps"]
results["step01"]["directories"] = {d: (MONOREPO / d).exists() for d in dirs}

files = ["backend/app/main.py", "backend/app/core/config.py", "backend/requirements.txt", 
         ".env", ".env.example", ".gitignore"]
results["step01"]["files"] = {f: (MONOREPO / f).exists() for f in files}

# Env vars
results["step01"]["env_vars"] = {k: ("SET" if env_vars.get(k) else "EMPTY") for k in 
    ["AUTH0_DOMAIN","AUTH0_CLIENT_ID","AUTH0_CLIENT_SECRET","AUTH0_AUDIENCE",
     "AUTH0_M2M_CLIENT_ID","AUTH0_M2M_CLIENT_SECRET","AUTH0_USER_ID",
     "APP_SECRET_KEY","DATABASE_URL","FRONTEND_URL","BACKEND_URL","AWS_MOCK_MODE"]}

# Step 02 checks
results["step02"] = {}
DOMAIN = env_vars.get("AUTH0_DOMAIN", "")

# OIDC
try:
    resp = urllib.request.urlopen(f"https://{DOMAIN}/.well-known/openid-configuration", timeout=10)
    oidc = json.loads(resp.read())
    results["step02"]["oidc"] = {
        "issuer": oidc.get("issuer"),
        "token_endpoint": oidc.get("token_endpoint"),
        "ciba_endpoint": oidc.get("backchannel_authentication_endpoint", "NOT_FOUND"),
    }
except Exception as e:
    results["step02"]["oidc"] = {"error": str(e)}

# M2M Token
try:
    payload = json.dumps({
        "client_id": env_vars["AUTH0_CLIENT_ID"],
        "client_secret": env_vars["AUTH0_CLIENT_SECRET"],
        "audience": env_vars["AUTH0_AUDIENCE"],
        "grant_type": "client_credentials"
    }).encode()
    req = urllib.request.Request(f"https://{DOMAIN}/oauth/token", data=payload,
                                headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=15)
    td = json.loads(resp.read())
    
    import base64
    parts = td["access_token"].split(".")
    hdr = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
    pay = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    
    results["step02"]["m2m_token"] = {
        "success": True,
        "token_type": td.get("token_type"),
        "expires_in": td.get("expires_in"),
        "scope": td.get("scope"),
        "jwt_alg": hdr.get("alg"),
        "jwt_iss": pay.get("iss"),
        "jwt_aud": pay.get("aud"),
        "jwt_permissions": pay.get("permissions", []),
    }
except Exception as e:
    results["step02"]["m2m_token"] = {"success": False, "error": str(e)}

# User ID
results["step02"]["user_id"] = {
    "value": env_vars.get("AUTH0_USER_ID", ""),
    "valid_format": env_vars.get("AUTH0_USER_ID", "").startswith("auth0|"),
}

# Frontend env
fe = FRONTEND / ".env.local"
results["step02"]["frontend_env"] = {
    "exists": fe.exists(),
    "has_secret": env_vars.get("AUTH0_CLIENT_SECRET", "") in fe.read_text(encoding="utf-8") if fe.exists() else False,
}

# Write JSON
out_path = MONOREPO / "backend" / "scripts" / "verify_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Summary
s01_pass = all(v for v in results["step01"]["directories"].values())
s01_pass &= all(v for v in results["step01"]["files"].values())
s01_pass &= all(v == "SET" for v in results["step01"]["env_vars"].values())
s02_pass = results["step02"]["m2m_token"].get("success", False)
s02_pass &= "NOT_FOUND" not in results["step02"].get("oidc", {}).get("ciba_endpoint", "NOT_FOUND")
s02_pass &= results["step02"]["user_id"]["valid_format"]

print(f"Step 01: {'PASS' if s01_pass else 'FAIL'}")
print(f"Step 02: {'PASS' if s02_pass else 'FAIL'}")
print(f"Results saved to: {out_path}")
