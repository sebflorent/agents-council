#!/usr/bin/env python3
"""
One-shot OAuth helper to get a Google refresh token.
Run: python3 briefings/get_token.py
Then paste the code shown in the browser and copy the refresh token into config.py.
"""

import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

REDIRECT_URI = "http://localhost:8085"
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

auth_code: str | None = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        auth_code = params.get("code")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Done! You can close this tab.</h2>")

    def log_message(self, *_):
        pass


def main():
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode(
            {
                "client_id": GOOGLE_CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": " ".join(SCOPES),
                "access_type": "offline",
                "prompt": "consent",
            }
        )
    )

    print("\n==> Opening browser for Google login...")
    print("    Use your WORK account: sebastien.florent@swissmarketplace.group\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8085), _Handler)
    print("Waiting for redirect on http://localhost:8085 ...")
    server.handle_request()

    if not auth_code:
        print("ERROR: no auth code received.")
        sys.exit(1)

    data = urllib.parse.urlencode(
        {
            "code": auth_code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data, method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read())

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("ERROR: no refresh_token in response. Make sure you approved the consent screen.")
        print("Full response:", tokens)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS — your new WORK refresh token:")
    print()
    print(refresh_token)
    print()
    print("=" * 60)
    print("\nPaste it into briefings/config.py as the default for WORK_REFRESH_TOKEN:")
    print('  WORK_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "<paste here>")')
    print()


if __name__ == "__main__":
    main()
