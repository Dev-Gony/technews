"""YouTube 업로드 인증을 한 번에 끝내는 로컬 스크립트.

Google Cloud에서 받은 OAuth 클라이언트 JSON 파일로 로그인한 뒤,
YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN을
GitHub Secrets에 바로 등록한다. 토큰을 손으로 복사할 일이 없다.

사용법:
    python youtube_auth.py                       # 다운로드 폴더의 client_secret*.json 자동 탐색
    python youtube_auth.py path/to/client.json   # 파일 직접 지정
"""

import os
import base64
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
# upload: 영상 업로드 / readonly: 연결된 채널 확인 / email: 어느 계정으로 로그인했는지 확인
SCOPE = (
    "https://www.googleapis.com/auth/youtube.upload "
    "https://www.googleapis.com/auth/youtube.readonly "
    "openid email"
)


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
            "prompt": "select_account consent",
            "state": state,
        }
    )

    print("브라우저에서 itgony 채널 계정으로 로그인하고 허용을 누르세요.")
    print("브라우저가 열리지 않으면 아래 주소를 직접 여세요.\n")
    print(auth_url)
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), CallbackHandler)
    server.timeout = 300

    # 브라우저가 favicon 요청을 먼저 보내거나, 이전 실행의 로그인 결과가 늦게 도착할 수 있다.
    # 이번 실행의 state와 맞는 결과가 올 때까지 다른 요청은 무시하고 기다린다.
    while True:
        CallbackHandler.result = None
        server.handle_request()
        result = CallbackHandler.result

        if result is None:
            raise SystemExit("5분 안에 로그인 결과가 오지 않았습니다. 다시 실행해 주세요.")

        if result.get("state") != state:
            continue

        if "error" in result:
            raise SystemExit(f"인증 실패: {result['error']}")

        if "code" in result:
            break

    server.server_close()

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

    return token["refresh_token"], token["access_token"], token_email(token.get("id_token"))


def token_email(id_token):
    """id_token(JWT) 본문에서 로그인한 계정 이메일을 꺼낸다. 서명 검증은 하지 않는다(표시용)."""
    if not id_token:
        return "알 수 없음"

    payload = id_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)

    return json.loads(base64.urlsafe_b64decode(payload)).get("email", "알 수 없음")


def connected_channel(access_token):
    """허용한 계정에 연결된 YouTube 채널 이름을 돌려준다. 채널이 없으면 None."""
    request = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        items = json.loads(response.read().decode("utf-8")).get("items") or []

    if not items:
        return None

    return items[0]["snippet"]["title"]


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
    refresh_token, access_token, email = authorize(client_id, client_secret)

    print(f"\n로그인한 Google 계정: {email}")
    channel = connected_channel(access_token)

    if not channel:
        raise SystemExit(
            "\n방금 허용한 Google 계정에는 YouTube 채널이 없습니다. 아무것도 저장하지 않았습니다.\n"
            "다시 실행해서 itgony 채널을 가진 계정을 고르세요.\n"
            "itgony가 브랜드 채널이면, 계정을 고른 뒤 나오는 '채널 선택' 화면에서 itgony를 고르세요."
        )

    print(f"\n연결된 채널: {channel}")

    if input("이 채널에 업로드할까요? (y/n): ").strip().lower() != "y":
        raise SystemExit("취소했습니다. 아무것도 저장하지 않았습니다.")

    print()
    set_secret(gh, "YOUTUBE_CLIENT_ID", client_id)
    set_secret(gh, "YOUTUBE_CLIENT_SECRET", client_secret)
    set_secret(gh, "YOUTUBE_REFRESH_TOKEN", refresh_token)

    print(f"\n완료. 이제 {REPO}의 Daily Shorts가 YouTube에 자동 업로드합니다.")


if __name__ == "__main__":
    main()
