"""
BARRERA DE TESTING RIGUROSO — Step 05: FastAPI Double-Blind Proxy
Automated endpoint testing.
"""
import httpx
import sys
import io
import json
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8000"
results = []

def test(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)

print("=" * 60)
print("  STEP 05 BARRERA: FastAPI Double-Blind Proxy")
print("=" * 60)

client = httpx.Client(timeout=120.0)

# Test 1: Health
print("\n[1] GET /health")
try:
    r = client.get(f"{BASE}/health")
    data = r.json()
    test("Health returns 200", r.status_code == 200)
    test("Health status operational", data.get("status") == "operational")
    test("Health pattern double-blind", data.get("pattern") == "double-blind")
except Exception as e:
    test("Health endpoint", False, str(e))

# Test 2: Swagger
print("\n[2] GET /docs")
try:
    r = client.get(f"{BASE}/docs")
    test("Swagger UI returns 200", r.status_code == 200)
except Exception as e:
    test("Swagger UI", False, str(e))

# Test 3: Infra status
print("\n[3] GET /api/v1/infra/status")
try:
    r = client.get(f"{BASE}/api/v1/infra/status")
    data = r.json()
    test("Infra status 200", r.status_code == 200)
    test("Has security_groups", "security_groups" in data)
    test("Has s3_buckets", "s3_buckets" in data)
    test("Has iam_policies", "iam_policies" in data)
except Exception as e:
    test("Infra status", False, str(e))

# Test 4: Diff
print("\n[4] GET /api/v1/infra/diff/open-port-22")
try:
    r = client.get(f"{BASE}/api/v1/infra/diff/open-port-22")
    data = r.json()
    test("Diff returns 200", r.status_code == 200)
    test("Diff before OPEN", data.get("before", {}).get("status") == "OPEN")
    test("Diff after CLOSED", data.get("after", {}).get("status") == "CLOSED")
except Exception as e:
    test("Diff endpoint", False, str(e))

# Test 5: Start mission
print("\n[5] POST /api/v1/missions/start (open-port-22)")
mission_id = None
try:
    r = client.post(f"{BASE}/api/v1/missions/start", json={"scenario": "open-port-22"})
    data = r.json()
    test("Mission start 200", r.status_code == 200, f"took {r.elapsed.total_seconds():.1f}s")
    test("Has mission_id", "mission_id" in data, data.get("mission_id", "")[:30])
    test("Status awaiting_approval", data.get("status") == "awaiting_approval")
    test("Has proposed_action in details", data.get("details", {}).get("proposed_action") is not None)
    test("Has interrupt in details", data.get("details", {}).get("interrupt") is not None)
    mission_id = data.get("mission_id")
except Exception as e:
    test("Mission start", False, str(e))

# Test 6: Get mission status
if mission_id:
    print(f"\n[6] GET /api/v1/missions/{mission_id}/status")
    try:
        r = client.get(f"{BASE}/api/v1/missions/{mission_id}/status")
        data = r.json()
        test("Status returns 200", r.status_code == 200)
        test("Status is awaiting_approval", data.get("status") == "awaiting_approval")
    except Exception as e:
        test("Mission status", False, str(e))

# Test 7: Approve mission
if mission_id:
    print(f"\n[7] POST /api/v1/missions/{mission_id}/approve")
    try:
        r = client.post(f"{BASE}/api/v1/missions/{mission_id}/approve")
        data = r.json()
        test("Approve returns 200", r.status_code == 200)
        test("Status completed", data.get("status") == "completed")
        test("Has execution_result", data.get("execution_result") is not None)
        er = data.get("execution_result", {})
        test("Execution success", er.get("success") == True)
        test("Resource modified", bool(er.get("resource_modified")))
    except Exception as e:
        test("Mission approve", False, str(e))

# Test 8: Reset infra
print("\n[8] POST /api/v1/infra/reset")
try:
    r = client.post(f"{BASE}/api/v1/infra/reset")
    data = r.json()
    test("Reset returns 200", r.status_code == 200)
    test("Reset status", data.get("status") == "reset")
except Exception as e:
    test("Infra reset", False, str(e))

# Test 9: Start + Reject flow
print("\n[9] Mission Start + Reject flow")
try:
    r = client.post(f"{BASE}/api/v1/missions/start", json={"scenario": "public-s3"})
    data = r.json()
    m2_id = data.get("mission_id")
    test("Start public-s3 mission", data.get("status") == "awaiting_approval")
    
    if m2_id:
        r2 = client.post(f"{BASE}/api/v1/missions/{m2_id}/reject?reason=Too+risky")
        d2 = r2.json()
        test("Reject returns 200", r2.status_code == 200)
        test("Reject status", d2.get("status") == "rejected")
except Exception as e:
    test("Reject flow", False, str(e))

# Test 10: Kill switch
print("\n[10] Kill Switch")
try:
    r = client.post(f"{BASE}/api/v1/missions/start", json={"scenario": "db-exposed"})
    m3_id = r.json().get("mission_id")
    if m3_id:
        r2 = client.post(f"{BASE}/api/v1/missions/{m3_id}/kill")
        d2 = r2.json()
        test("Kill returns 200", r2.status_code == 200)
        test("Kill status", d2.get("status") == "killed")
except Exception as e:
    test("Kill switch", False, str(e))

# Test 11: List active
print("\n[11] GET /api/v1/missions/active")
try:
    r = client.get(f"{BASE}/api/v1/missions/active")
    data = r.json()
    test("Active list 200", r.status_code == 200)
    test("Has missions array", "missions" in data)
    test("Total count > 0", data.get("total", 0) > 0)
except Exception as e:
    test("Active missions", False, str(e))

# Summary
print("\n" + "=" * 60)
print("  GRAND SUMMARY — Step 05 Barrier")
print("=" * 60)

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)
print(f"\n  Total: {total}  Passed: {passed}  Failed: {failed}")

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
