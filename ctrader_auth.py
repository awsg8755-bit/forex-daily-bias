"""
Step 1 of cTrader Open API OAuth setup.

Run this to print the authorization URL. Open it in your browser,
log in with your Pepperstone/cTrader credentials, and approve access.

You'll be redirected to your redirect URI (http://localhost) which will
fail to load (that's expected, nothing is running there) - but the
browser's address bar will contain a "code=" parameter. Copy that full
redirected URL (or just the code value) and give it to the next step.
"""

import os
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["CTRADER_CLIENT_ID"]
REDIRECT_URI = os.environ["CTRADER_REDIRECT_URI"]

AUTH_BASE = "https://connect.spotware.com/apps/auth"

params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "trading",
}

url = f"{AUTH_BASE}?{urlencode(params)}"

print("Open this URL in your browser, log in, and approve access:\n")
print(url)
print("\nAfter approving, copy the FULL redirected URL (it will fail to load, that's fine) and paste it back.")
