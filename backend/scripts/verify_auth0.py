"""BARRERA DE TESTING Step 02 - Auth0 Verification"""
import urllib.request, json, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load env from root
from pathlib import Path
root = Path(__file__).parent.parent.parent  # scripts -> backend -> monorepo root
env_path = root / ".env"
env_vars = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()
        os.environ[key.strip()] = value.strip()

DOMAIN = env_vars["AUTH0_DOMAIN"]
CLIENT_ID = env_vars["AUTH0_CLIENT_ID"]
CLIENT_SECRET = env_vars["AUTH0_CLIENT_SECRET"]
AUDIENCE = env_vars["AUTH0_AUDIENCE"]
USER_ID = env_vars["AUTH0_USER_ID"]

results = []
print("=" * 60)
print("BARRERA DE TESTING -- Step 02: Auth0 Config Verification")
print("=" * 60)

# Test 1: Settings
print("\n[TEST 1] Settings loaded from .env")
print(f"  DOMAIN:    {DOMAIN}")
print(f"  CLIENT_ID: {CLIENT_ID[:10]}...")
print(f"  SECRET:    ...{CLIENT_SECRET[20:30]}...")
print(f"  AUDIENCE:  {AUDIENCE}")
print(f"  USER_ID:   {USER_ID}")
results.append(("Settings Load", True))

# Test 2: OIDC Discovery
print("\n[TEST 2] OIDC Discovery...")
try:
    url = f"https://{DOMAIN}/.well-known/openid-configuration"
    resp = urllib.request.urlopen(url, timeout=10)
    oidc = json.loads(resp.read())
    print(f"  Issuer: {oidc['issuer']}")
    print(f"  Token:  {oidc['token_endpoint']}")
    ciba_ep = oidc.get("backchannel_authentication_endpoint", "NOT FOUND")
    print(f"  CIBA:   {ciba_ep}")
    results.append(("OIDC Discovery", True))
    results.append(("CIBA Endpoint", ciba_ep != "NOT FOUND"))
except Exception as e:
    print(f"  FAIL: {e}")
    results.append(("OIDC Discovery", False))

# Test 3: M2M Token
print("\n[TEST 3] M2M Token (Client Credentials)...")
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
    token = token_data["access_token"]
    print(f"  Token:   {token[:40]}...")
    print(f"  Type:    {token_data.get('token_type')}")
    print(f"  Expires: {token_data.get('expires_in')}s")
    print(f"  Scope:   {token_data.get('scope', 'N/A')}")
    results.append(("M2M Token", True))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"  FAIL HTTP {e.code}: {body[:100]}")
    results.append(("M2M Token", False))
except Exception as e:
    print(f"  FAIL: {e}")
    results.append(("M2M Token", False))

# Test 4: App Config module
print("\n[TEST 4] App Config Module...")
try:
    sys.path.insert(0, str(root / "backend"))
    from app.core.config import get_settings
    s = get_settings()
    assert s.auth0_domain == DOMAIN
    assert s.auth0_client_id == CLIENT_ID
    print(f"  Config module loads correctly")
    results.append(("Config Module", True))
except Exception as e:
    print(f"  FAIL: {e}")
    results.append(("Config Module", False))

# Summary
print("\n" + "=" * 60)
print("RESULT SUMMARY -- Step 02 Barrier")
print("=" * 60)
passed = sum(1 for _, ok in results if ok)
total = len(results)
for name, ok in results:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
print(f"\n  {passed}/{total} tests passed")
if passed >= 4:
    print("  >>> BARRERA SUPERADA -- Step 02 APROBADO <<<")
else:
    print("  >>> BARRERA NO SUPERADA <<<")
