"""
STEP 06 — BARRERA DE TESTING RIGUROSO
Self-contained: starts server, runs all tests, stops server.

Tests:
1. Health check
2. Mock flow: Mission start → CIBA initiate → Mock approve → Mission completes
3. Mock flow: Mission start → CIBA initiate → Mock reject → Mission rejected
4. CIBA status and active list
5. RAR payload preview
6. Orchestrator full flow
7. Double-Blind verification
8. Kill switch after CIBA
"""
import subprocess
import time
import sys
import os
import json

os.environ["PYTHONPATH"] = os.getcwd()
os.environ.setdefault("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

# Delete old checkpoint DB
for f in ["aegiscloud_checkpoints.db", "aegiscloud_checkpoints.db-journal"]:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"Deleted {f}")
    except PermissionError:
        print(f"Could not delete {f} (locked), continuing...")

# Start server
print("Starting uvicorn server...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(5)

import httpx

for attempt in range(10):
    try:
        r = httpx.get("http://localhost:8000/health", timeout=5)
        if r.status_code == 200:
            print("Server is ready!\n")
            break
    except Exception:
        time.sleep(1)
else:
    print("Server failed to start!")
    server.kill()
    sys.exit(1)

client = httpx.Client(timeout=120.0)
results = []


def test(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)


print("=" * 60)
print("  STEP 06 BARRERA: CIBA + Interrupt Integration")
print("=" * 60)

# ==================================================
# TEST 1: Health check (verify auth router loaded)
# ==================================================
print("\n[1] GET /health")
r = client.get("http://localhost:8000/health")
test("Health returns 200", r.status_code == 200)

# ==================================================
# TEST 2: RAR Payload Preview
# ==================================================
print("\n[2] GET /api/v1/auth/rar/preview")
r = client.get("http://localhost:8000/api/v1/auth/rar/preview?scenario=open-port-22")
data = r.json()
test("RAR preview 200", r.status_code == 200)
rar = data.get("rar_payload", [{}])[0]
test("RAR has type field", "type" in rar and "urn:aegiscloud" in rar.get("type", ""))
test("RAR has aegis_mission_id", "aegis_mission_id" in rar)
test("RAR has resource", "resource" in rar)
test("RAR has diff", "diff" in rar)
test("RAR has risk_level", "risk_level" in rar)

# ==================================================
# TEST 3: FULL FLOW — Start Mission → CIBA Initiate → Approve → Complete
# ==================================================
print("\n[3] FULL FLOW: Mission Start → CIBA → Approve → Complete")

# 3a: Start mission
print("  3a: Starting mission...")
r = client.post("http://localhost:8000/api/v1/missions/start", json={"scenario": "open-port-22"})
data = r.json()
t_elapsed = r.elapsed.total_seconds()
test("Mission start 200", r.status_code == 200, f"took {t_elapsed:.1f}s")
mission_id = data.get("mission_id", "")
test("Has mission_id", bool(mission_id), mission_id[:30])
test("Status awaiting_approval", data.get("status") == "awaiting_approval")
interrupt = data.get("details", {}).get("interrupt")
test("Has interrupt payload", interrupt is not None)

# 3b: Initiate CIBA with the interrupt payload
if mission_id and interrupt:
    print("  3b: Initiating CIBA...")
    r = client.post("http://localhost:8000/api/v1/auth/ciba/initiate", json={
        "mission_id": mission_id,
        "interrupt_payload": interrupt,
    })
    ciba_data = r.json()
    test("CIBA initiate 200", r.status_code == 200)
    auth_req_id = ciba_data.get("auth_req_id", "")
    test("Has auth_req_id", bool(auth_req_id), auth_req_id[:25])
    test("Status pending", ciba_data.get("status") == "pending")
    ciba_mode = ciba_data.get("details", {}).get("mode", "")
    test("CIBA mode (mock expected)", ciba_mode in ("mock", "real"), f"mode={ciba_mode}")

    # 3c: Check CIBA status
    print("  3c: Checking CIBA status...")
    r = client.get(f"http://localhost:8000/api/v1/auth/ciba/status/{auth_req_id}")
    test("CIBA status 200", r.status_code == 200)
    test("Status still pending", r.json().get("status") == "pending")

    # 3d: Approve via Mock Guardian
    print("  3d: Approving via Mock Guardian...")
    r = client.post(f"http://localhost:8000/api/v1/auth/ciba/{auth_req_id}/approve", json={
        "decision": "approved"
    })
    approve_data = r.json()
    test("CIBA approve 200", r.status_code == 200)
    test("Approve status approved", approve_data.get("status") == "approved")

    # 3e: Verify mission completed
    print("  3e: Verifying mission completed...")
    r = client.get(f"http://localhost:8000/api/v1/missions/{mission_id}/status")
    mission_status = r.json()
    test("Mission status 200", r.status_code == 200)
    test("Mission completed", mission_status.get("status") == "completed")

    # 3f: Check CIBA status updated
    r = client.get(f"http://localhost:8000/api/v1/auth/ciba/status/{auth_req_id}")
    test("CIBA final status approved", r.json().get("status") == "approved")

else:
    for _ in range(10):
        results.append(("SKIPPED (no interrupt)", False, ""))
        print("  [FAIL] SKIPPED — no interrupt payload")

# ==================================================
# TEST 4: Reset infra for reject flow
# ==================================================
print("\n[4] POST /api/v1/infra/reset")
r = client.post("http://localhost:8000/api/v1/infra/reset")
test("Reset returns 200", r.status_code == 200)

# ==================================================
# TEST 5: REJECT FLOW — Start Mission → CIBA Initiate → Reject
# ==================================================
print("\n[5] REJECT FLOW: Mission Start → CIBA → Reject")

r = client.post("http://localhost:8000/api/v1/missions/start", json={"scenario": "public-s3"})
data = r.json()
m2_id = data.get("mission_id", "")
interrupt2 = data.get("details", {}).get("interrupt")
test("Reject mission started", data.get("status") == "awaiting_approval")

if m2_id and interrupt2:
    r = client.post("http://localhost:8000/api/v1/auth/ciba/initiate", json={
        "mission_id": m2_id,
        "interrupt_payload": interrupt2,
    })
    auth2 = r.json().get("auth_req_id", "")
    test("Reject CIBA initiated", r.status_code == 200)

    r = client.post(f"http://localhost:8000/api/v1/auth/ciba/{auth2}/approve", json={
        "decision": "rejected",
        "reason": "Too risky, need more analysis"
    })
    test("Reject via mock Guardian", r.status_code == 200)
    test("Reject status", r.json().get("status") == "rejected")

    r = client.get(f"http://localhost:8000/api/v1/missions/{m2_id}/status")
    test("Mission rejected", r.json().get("status") == "rejected")
else:
    for _ in range(4):
        results.append(("SKIPPED (no interrupt)", False, ""))

# ==================================================
# TEST 6: CIBA Active List
# ==================================================
print("\n[6] GET /api/v1/auth/ciba/active")
r = client.get("http://localhost:8000/api/v1/auth/ciba/active")
data = r.json()
test("CIBA active 200", r.status_code == 200)
test("Has requests array", "requests" in data)
test("CIBA total > 0", data.get("total", 0) > 0, f"total={data.get('total', 0)}")

# ==================================================
# TEST 7: Double-Blind Verification
# ==================================================
print("\n[7] DOUBLE-BLIND VERIFICATION")
r = client.get("http://localhost:8000/api/v1/missions/active")
data = r.json()
missions = data.get("missions", [])
test("Active missions exist", len(missions) > 0)

# Verify no tokens in mission data that would be visible to LLM
has_token_leak = False
for m in missions:
    m_str = json.dumps(m)
    if "mock-vault-token" in m_str and "messages" in m_str:
        has_token_leak = True
test("No token leak in mission data", not has_token_leak, "Token never reaches LLM messages")

# ==================================================
# TEST 8: Kill Switch after CIBA
# ==================================================
print("\n[8] Kill Switch")
if missions:
    first_mission = missions[0].get("mission_id", "")
    if first_mission:
        r = client.post(f"http://localhost:8000/api/v1/missions/{first_mission}/kill")
        test("Kill returns 200", r.status_code == 200)
        test("Kill status", r.json().get("status") == "killed")

# ==================================================
# GRAND SUMMARY
# ==================================================
print("\n" + "=" * 60)
print("  GRAND SUMMARY — Step 06 Barrier")
print("=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)
print(f"\n  Total: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
if failed > 0:
    print(f"\n  FAILURES:")
    for name, ok, detail in results:
        if not ok:
            print(f"    [FAIL] {name} -- {detail}")
print()
if failed == 0:
    print("  >>> ALL TESTS PASSED — BARRIER CLEARED <<<")
else:
    print("  >>> BARRIER NOT CLEARED — Fix failures <<<")

client.close()
print("\nStopping server...")
server.terminate()
server.wait(timeout=5)
print("Server stopped.")
