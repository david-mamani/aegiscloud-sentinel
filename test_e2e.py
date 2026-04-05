"""
AegisCloud Comprehensive E2E Test Suite
Tests ALL endpoints with real authentication.
"""
import httpx
import json
import time
import sys
import os

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
DOMAIN = os.environ["AUTH0_DOMAIN"]
CLIENT_ID = os.environ["AUTH0_M2M_CLIENT_ID"]
CLIENT_SECRET = os.environ["AUTH0_M2M_CLIENT_SECRET"]

results = []

def log(test_name, status, detail=""):
    icon = "PASS" if status else "FAIL"
    results.append(f"[{icon}] {test_name}: {detail[:120]}")
    print(f"  [{icon}] {test_name}: {detail[:120]}")

# Get M2M token for our API
print("=== Getting Access Token ===")
r = httpx.post(f"https://{DOMAIN}/oauth/token", json={
    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "audience": "https://api.aegiscloud.dev", "grant_type": "client_credentials",
})
if r.status_code != 200:
    print(f"FATAL: Cannot get token: {r.text[:200]}")
    sys.exit(1)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"  Token OK (length: {len(token)})\n")

# ═══════════════════════════════════════
print("=== 1. INFRASTRUCTURE ENDPOINTS ===")
# ═══════════════════════════════════════

# 1a. Health check (no auth needed)
r = httpx.get(f"{BACKEND}/health")
log("GET /health", r.status_code == 200, f"status={r.status_code}")

# 1b. Infrastructure status
r = httpx.get(f"{BACKEND}/api/v1/infra/status", headers=headers)
log("GET /infra/status", r.status_code == 200, f"status={r.status_code} data={r.text[:80]}")

# 1c. Vulnerabilities
r = httpx.get(f"{BACKEND}/api/v1/infra/vulnerabilities", headers=headers)
log("GET /infra/vulnerabilities", r.status_code == 200, f"count={len(r.json()) if r.status_code==200 else 'N/A'}")

# 1d. Audit log
r = httpx.get(f"{BACKEND}/api/v1/infra/audit-log", headers=headers)
log("GET /infra/audit-log", r.status_code == 200, f"entries={len(r.json()) if r.status_code==200 else 'N/A'}")

# ═══════════════════════════════════════
print("\n=== 2. SCOPES RADAR ===")
# ═══════════════════════════════════════
r = httpx.get(f"{BACKEND}/api/v1/scopes/", headers=headers)
log("GET /scopes/", r.status_code == 200, f"status={r.status_code} data={r.text[:80]}")

# ═══════════════════════════════════════
print("\n=== 3. MISSIONS (FULL LIFECYCLE) ===")
# ═══════════════════════════════════════

# 3a. Start mission  
r = httpx.post(f"{BACKEND}/api/v1/missions/start", headers=headers,
    json={"scenario_id": "ssh_open_port", "severity": "critical"})
log("POST /missions/start", r.status_code == 200, f"status={r.status_code} resp={r.text[:100]}")
mission_id = r.json().get("mission_id", "") if r.status_code == 200 else ""

if mission_id:
    # 3b. Get mission status
    time.sleep(2)  # wait for analysis
    r = httpx.get(f"{BACKEND}/api/v1/missions/{mission_id}/status", headers=headers)
    log("GET /missions/{id}/status", r.status_code == 200, f"status={r.json().get('status','?')}")

    # 3c. Approve mission
    r = httpx.post(f"{BACKEND}/api/v1/missions/{mission_id}/approve", headers=headers)
    log("POST /missions/{id}/approve", r.status_code == 200, f"resp={r.text[:80]}")

    # 3d. Active missions
    r = httpx.get(f"{BACKEND}/api/v1/missions/active", headers=headers)
    log("GET /missions/active", r.status_code == 200, f"count={len(r.json()) if r.status_code==200 else 'N/A'}")

# ═══════════════════════════════════════
print("\n=== 4. AUTH - CONNECTIONS ===")
# ═══════════════════════════════════════
r = httpx.get(f"{BACKEND}/api/v1/auth/connections", headers=headers)
log("GET /auth/connections", r.status_code == 200, f"conns={r.json().get('total',0) if r.status_code==200 else 'N/A'}")

# ═══════════════════════════════════════
print("\n=== 5. CIBA FLOW ===")
# ═══════════════════════════════════════

# 5a. Initiate CIBA
r = httpx.post(f"{BACKEND}/api/v1/auth/ciba/initiate", headers=headers, json={
    "mission_id": mission_id or "test-mission-001",
    "interrupt_payload": {
        "scenario_id": "ssh_open_port",
        "severity": "critical",
        "description": "Close SSH port 22 and enable firewall",
        "scope": "infra:firewall:write",
    },
})
log("POST /ciba/initiate", r.status_code == 200, f"resp={r.text[:100]}")
auth_req_id = r.json().get("auth_req_id", "") if r.status_code == 200 else ""

if auth_req_id:
    # 5b. Check CIBA status
    r = httpx.get(f"{BACKEND}/api/v1/auth/ciba/status/{auth_req_id}", headers=headers)
    log("GET /ciba/status/{id}", r.status_code == 200, f"status={r.json().get('status','?')}")

    # 5c. Active CIBA requests
    r = httpx.get(f"{BACKEND}/api/v1/auth/ciba/active", headers=headers)
    log("GET /ciba/active", r.status_code == 200, f"count={len(r.json()) if r.status_code==200 else 'N/A'}")

    # 5d. Approve CIBA
    r = httpx.post(f"{BACKEND}/api/v1/auth/ciba/{auth_req_id}/approve", headers=headers)
    log("POST /ciba/{id}/approve", r.status_code == 200, f"resp={r.text[:100]}")

# ═══════════════════════════════════════
print("\n=== 6. RAR PREVIEW ===")
# ═══════════════════════════════════════
r = httpx.get(f"{BACKEND}/api/v1/auth/rar/preview", headers=headers)
log("GET /rar/preview", r.status_code == 200, f"resp={r.text[:100]}")

# ═══════════════════════════════════════
print("\n=== 7. TOKEN VAULT EXCHANGE ===")
# ═══════════════════════════════════════
r = httpx.post(f"{BACKEND}/api/v1/auth/token-vault/exchange", headers=headers,
    json={"connection": "github"})
log("POST /token-vault/exchange", r.status_code == 200, f"resp={r.text[:100]}")

# ═══════════════════════════════════════
print("\n=== 8. INFRASTRUCTURE RESET ===")
# ═══════════════════════════════════════
r = httpx.post(f"{BACKEND}/api/v1/infra/reset", headers=headers)
log("POST /infra/reset", r.status_code == 200, f"resp={r.text[:80]}")

# ═══════════════════════════════════════
print("\n\n" + "=" * 50)
print("TEST RESULTS SUMMARY")
print("=" * 50)
passed = sum(1 for r in results if r.startswith("[PASS]"))
failed = sum(1 for r in results if r.startswith("[FAIL]"))
print(f"PASSED: {passed}")
print(f"FAILED: {failed}")
print(f"TOTAL:  {len(results)}")
print(f"RATE:   {passed/len(results)*100:.0f}%")
print()
for r in results:
    print(f"  {r}")

# Write results
with open("test_results.txt", "w", encoding="utf-8") as f:
    f.write(f"PASSED: {passed}\nFAILED: {failed}\nTOTAL: {len(results)}\n\n")
    for r in results:
        f.write(f"{r}\n")
