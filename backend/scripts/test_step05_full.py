"""
FULL CLEAN BARRIER TEST — Starts server, runs all tests, stops server.
"""
import subprocess
import time
import sys
import os

# Set env
os.environ["PYTHONPATH"] = os.getcwd()
os.environ.setdefault("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

# Delete old checkpoint DB (ignore if locked)
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

# Wait for startup
time.sleep(5)

import httpx
for attempt in range(10):
    try:
        r = httpx.get("http://localhost:8000/health", timeout=5)
        if r.status_code == 200:
            print("Server is ready!")
            break
    except Exception:
        time.sleep(1)
else:
    print("Server failed to start!")
    server.kill()
    sys.exit(1)

# Run tests
print("\n" + "=" * 60)
print("  STEP 05 BARRERA: FastAPI Double-Blind Proxy (CLEAN RUN)")
print("=" * 60)

client = httpx.Client(timeout=120.0)
results = []

def test(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)

# Test 1: Health
print("\n[1] GET /health")
r = client.get("http://localhost:8000/health")
data = r.json()
test("Health returns 200", r.status_code == 200)
test("Health status operational", data.get("status") == "operational")
test("Health pattern double-blind", data.get("pattern") == "double-blind")

# Test 2: Swagger
print("\n[2] GET /docs")
r = client.get("http://localhost:8000/docs")
test("Swagger UI returns 200", r.status_code == 200)

# Test 3: Infra status
print("\n[3] GET /api/v1/infra/status")
r = client.get("http://localhost:8000/api/v1/infra/status")
data = r.json()
test("Infra status 200", r.status_code == 200)
test("Has security_groups", "security_groups" in data)
test("Has s3_buckets", "s3_buckets" in data)
test("Has iam_policies", "iam_policies" in data)

# Test 4: Diff
print("\n[4] GET /api/v1/infra/diff/open-port-22")
r = client.get("http://localhost:8000/api/v1/infra/diff/open-port-22")
data = r.json()
test("Diff returns 200", r.status_code == 200)
test("Diff before OPEN", data.get("before", {}).get("status") == "OPEN")
test("Diff after CLOSED", data.get("after", {}).get("status") == "CLOSED")

# Test 5: Start mission
print("\n[5] POST /api/v1/missions/start (open-port-22)")
r = client.post("http://localhost:8000/api/v1/missions/start", json={"scenario": "open-port-22"})
data = r.json()
elapsed = r.elapsed.total_seconds()
test("Mission start 200", r.status_code == 200, f"took {elapsed:.1f}s")
test("Has mission_id", "mission_id" in data, str(data.get("mission_id", ""))[:30])
test("Status awaiting_approval", data.get("status") == "awaiting_approval")
test("Has proposed_action in details", data.get("details", {}).get("proposed_action") is not None)
test("Has interrupt in details", data.get("details", {}).get("interrupt") is not None)
mission_id = data.get("mission_id")

# Test 6: Get mission status
if mission_id:
    print(f"\n[6] GET /api/v1/missions/{mission_id}/status")
    r = client.get(f"http://localhost:8000/api/v1/missions/{mission_id}/status")
    data = r.json()
    test("Status returns 200", r.status_code == 200)
    test("Status is awaiting_approval", data.get("status") == "awaiting_approval")

# Test 7: Approve mission
if mission_id:
    print(f"\n[7] POST /api/v1/missions/{mission_id}/approve")
    r = client.post(f"http://localhost:8000/api/v1/missions/{mission_id}/approve")
    data = r.json()
    test("Approve returns 200", r.status_code == 200)
    test("Status completed", data.get("status") == "completed")
    test("Has execution_result", data.get("execution_result") is not None)
    er = data.get("execution_result", {})
    test("Execution success", er.get("success") == True)
    test("Resource modified", bool(er.get("resource_modified")))

# Test 8: Reset infra
print("\n[8] POST /api/v1/infra/reset")
r = client.post("http://localhost:8000/api/v1/infra/reset")
data = r.json()
test("Reset returns 200", r.status_code == 200)
test("Reset status", data.get("status") == "reset")

# Test 9: Start + Reject flow
print("\n[9] Mission Start + Reject flow (public-s3)")
r = client.post("http://localhost:8000/api/v1/missions/start", json={"scenario": "public-s3"})
data = r.json()
m2_id = data.get("mission_id")
test("Start public-s3 mission", data.get("status") == "awaiting_approval")
if m2_id:
    r2 = client.post(f"http://localhost:8000/api/v1/missions/{m2_id}/reject?reason=Too+risky")
    d2 = r2.json()
    test("Reject returns 200", r2.status_code == 200)
    test("Reject status", d2.get("status") == "rejected")

# Test 10: Kill switch
print("\n[10] Kill Switch (db-exposed)")
r = client.post("http://localhost:8000/api/v1/missions/start", json={"scenario": "db-exposed"})
m3_id = r.json().get("mission_id")
if m3_id:
    r2 = client.post(f"http://localhost:8000/api/v1/missions/{m3_id}/kill")
    d2 = r2.json()
    test("Kill returns 200", r2.status_code == 200)
    test("Kill status", d2.get("status") == "killed")

# Test 11: List active
print("\n[11] GET /api/v1/missions/active")
r = client.get("http://localhost:8000/api/v1/missions/active")
data = r.json()
test("Active list 200", r.status_code == 200)
test("Has missions array", "missions" in data)
test("Total count > 0", data.get("total", 0) > 0, f"total={data.get('total', 0)}")

# Summary
print("\n" + "=" * 60)
print("  GRAND SUMMARY")
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
    print("  >>> BARRIER NOT CLEARED <<<")

client.close()

# Stop server
print("\nStopping server...")
server.terminate()
server.wait(timeout=5)
print("Server stopped.")
