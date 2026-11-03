"""YouTube 업로드 인증을 한 번에 끝내는 로컬 스크립트.

Google Cloud에서 받은 OAuth 클라이언트 JSON 파일로 로그인한 뒤,
YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN을
GitHub Secrets에 바로 등록한다. 토큰을 손으로 복사할 일이 없다.

사용법:
    python youtube_auth.py                       # 다운로드 폴더의 client_secret*.json 자동 탐색
    python youtube_auth.py path/to/client.json   # 파일 직접 지정
"""

import os
import sys
import glob
import json
import shutil
import secrets
import subprocess
import webbrowser
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


REPO = os.environ.get("GITHUB_REPOSITORY", "Dev-Gony/technews")
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


def find_client_file():
    if len(sys.argv) > 1:
        return sys.argv[1]

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    candidates = sorted(
        glob.glob(os.path.join(downloads, "client_secret*.json")),
        key=os.path.getmtime,
        reverse=True,
    )

    if not candidates:
        raise SystemExit(
            "OAuth 클라이언트 JSON을 찾지 못했습니다. "
            "다운로드 폴더에 client_secret*.json을 받거나 경로를 인자로 주세요."
        )

    return candidates[0]


def load_client(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    client = data.get("installed") or data.get("web")

    if not client:
        raise SystemExit(f"OAuth 클라이언트 JSON 형식이 아닙니다: {path}")

    return client["client_id"], client["client_secret"]


def authorize(client_id, client_secret):
    state = secrets.token_urlsafe(16)
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )

    print("브라우저에서 itgony 채널 계정으로 로그인하고 허용을 누르세요.")
    print("브라우저가 열리지 않으면 아래 주소를 직접 여세요.\n")
    print(auth_url)
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), CallbackHandler)
    server.handle_request()

    result = CallbackHandler.result

    if result.get("state") != state or "code" not in result:
        raise SystemExit(f"인증 실패: {result.get('error') or result}")

    data = urllib.parse.urlencode(
        {
            "code": result["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")

    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.loads(response.read().decode("utf-8"))

    if "refresh_token" not in token:
        raise SystemExit("refresh token을 받지 못했습니다. 다시 실행해 주세요.")

    return token["refresh_token"]


def find_gh():
    gh = shutil.which("gh")

    if gh:
        return gh

    default = r"C:\Program Files\GitHub CLI\gh.exe"

    if os.path.exists(default):
        return default

    raise SystemExit("GitHub CLI(gh)가 없습니다. 설치 후 gh auth login을 먼저 해주세요.")


def set_secret(gh, name, value):
    result = subprocess.run(
        [gh, "secret", "set", name, "--repo", REPO],
        input=value,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(f"{name} 등록 실패: {result.stderr.strip()}")

    print(f"✓ {name} 등록 완료")


def main():
    gh = find_gh()
    client_file = find_client_file()
    print(f"OAuth 클라이언트 파일: {client_file}\n")

    client_id, client_secret = load_client(client_file)
    refresh_token = authorize(client_id, client_secret)

    print()
    set_secret(gh, "YOUTUBE_CLIENT_ID", client_id)
    set_secret(gh, "YOUTUBE_CLIENT_SECRET", client_secret)
    set_secret(gh, "YOUTUBE_REFRESH_TOKEN", refresh_token)

    print(f"\n완료. 이제 {REPO}의 Daily Shorts가 YouTube에 자동 업로드합니다.")


if __name__ == "__main__":
    main()
