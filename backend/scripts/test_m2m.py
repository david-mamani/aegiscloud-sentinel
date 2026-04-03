import urllib.request, urllib.parse, json

import os

DOMAIN = os.getenv("AUTH0_DOMAIN", "your-tenant.us.auth0.com")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "")
SECRETS = [
    ("env", os.getenv("AUTH0_CLIENT_SECRET", "")),
]
AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.aegiscloud.dev")

results = []
for label, secret in SECRETS:
    payload = json.dumps({
        "client_id": CLIENT_ID,
        "client_secret": secret,
        "audience": AUDIENCE,
        "grant_type": "client_credentials"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://{DOMAIN}/oauth/token",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        results.append(f"{label}: OK token={data['access_token'][:30]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        results.append(f"{label}: FAIL {e.code} {body[:80]}")

with open("scripts/results.txt", "w", encoding="utf-8") as f:
    for r in results:
        f.write(r + "\n")
    f.write("DONE\n")
