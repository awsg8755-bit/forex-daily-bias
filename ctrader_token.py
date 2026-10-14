"""
Step 2 of cTrader Open API OAuth setup.

Takes the "code" from the redirected localhost URL (from ctrader_auth.py's
step 1) and exchanges it for an access token + refresh token. Saves both
into .env as CTRADER_ACCESS_TOKEN and CTRADER_REFRESH_TOKEN.

Usage:
    python3 ctrader_token.py "http://localhost/?code=XXXXX"
    (or just pass the code value directly)
"""

import os
import sys
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["CTRADER_CLIENT_ID"]
CLIENT_SECRET = os.environ["CTRADER_CLIENT_SECRET"]
REDIRECT_URI = os.environ["CTRADER_REDIRECT_URI"]

TOKEN_URL = "https://openapi.ctrader.com/apps/token"

if len(sys.argv) < 2:
    print("Usage: python3 ctrader_token.py \"<redirected URL or code>\"")
    sys.exit(1)

arg = sys.argv[1]
if arg.startswith("http"):
    code = parse_qs(urlparse(arg).query).get("code", [None])[0]
    if not code:
        print("Could not find 'code=' in the URL you passed.")
        sys.exit(1)
else:
    code = arg

resp = requests.post(TOKEN_URL, data={
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
})

if resp.status_code != 200:
    print(f"Token exchange failed: {resp.status_code}")
    print(resp.text)
    sys.exit(1)

data = resp.json()
access_token = data.get("accessToken") or data.get("access_token")
refresh_token = data.get("refreshToken") or data.get("refresh_token")

if not access_token:
    print("No access token in response:")
    print(data)
    sys.exit(1)

print("Success. Access token (truncated):", access_token[:12] + "...")

env_path = ".env"
with open(env_path, "r") as f:
    lines = f.readlines()

def upsert(lines, key, value):
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            return
    lines.append(f"{key}={value}\n")

upsert(lines, "CTRADER_ACCESS_TOKEN", access_token)
if refresh_token:
    upsert(lines, "CTRADER_REFRESH_TOKEN", refresh_token)

with open(env_path, "w") as f:
    f.writelines(lines)

print("Saved CTRADER_ACCESS_TOKEN" + (" and CTRADER_REFRESH_TOKEN" if refresh_token else "") + " to .env")
