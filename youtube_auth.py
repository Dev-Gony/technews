"""YouTube 업로드용 refresh token을 한 번 발급받는 로컬 스크립트.

사용법:
    YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... python youtube_auth.py

브라우저에서 itgony 채널 계정으로 로그인해 권한을 허용하면
터미널에 refresh token이 출력된다. 이 값을 GitHub Secret YOUTUBE_REFRESH_TOKEN에 넣는다.
"""

import os
import json
import secrets
import webbrowser
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class CallbackHandler(BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        CallbackHandler.result = {key: values[0] for key, values in query.items()}

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("인증 완료. 이 창을 닫고 터미널을 확인하세요.".encode("utf-8"))

    def log_message(self, *args):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit("YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET 환경변수가 필요합니다.")

    state = secrets.token_urlsafe(16)
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )

    print("브라우저에서 로그인하세요. 열리지 않으면 아래 주소를 직접 여세요.")
    print(auth_url)
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), CallbackHandler)
    server.handle_request()

    result = CallbackHandler.result

    if result.get("state") != state or "code" not in result:
        raise SystemExit(f"인증 실패: {result}")

    data = urllib.parse.urlencode(
        {
            "code": result["code"],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")

    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.loads(response.read().decode("utf-8"))

    print("\nYOUTUBE_REFRESH_TOKEN:")
    print(token["refresh_token"])


if __name__ == "__main__":
    main()
