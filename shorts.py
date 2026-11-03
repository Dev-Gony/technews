"""GONY DAILY 이슈에서 AI 기사 1개를 골라 YouTube Shorts 영상으로 만든다.

흐름: 이슈 JSON → 기사 선택 → Claude 대본 → TTS 음성 → 장면 이미지 → ffmpeg 합성 → YouTube 업로드
"""

import os
import re
import json
import math
import shutil
import asyncio
import argparse
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

# 비우면 구독 플랜의 기본 모델을 쓴다. 예: opus, sonnet
CLAUDE_MODEL = os.environ.get("SHORTS_CLAUDE_MODEL", "").strip()
TTS_VOICE = os.environ.get("SHORTS_VOICE", "ko-KR-InJoonNeural")
TTS_RATE = os.environ.get("SHORTS_TTS_RATE", "+8%")
# 업로드 기본값은 비공개: YouTube Studio에서 확인한 뒤 직접 공개로 바꾼다.
UPLOAD_PRIVACY = os.environ.get("SHORTS_PRIVACY", "private")
CHANNEL_NAME = os.environ.get("SHORTS_CHANNEL_NAME", "itgony")

DAILY_ISSUES_DIR = "config/issues"
SHORTS_HISTORY_FILE = "config/shorts_history.json"
OUTPUT_DIR = "runtime/shorts"

KST = ZoneInfo("Asia/Seoul")

AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "anthropic", "openai",
    "qwen", "llama", "mistral", "copilot", "mcp", "agent", "에이전트",
    "인공지능", "머신러닝", "딥러닝", "생성형", "언어 모델", "언어모델",
    "프롬프트", "추론 모델", "파인튜닝", "rag",
]

# 배경음 크기 (0이면 배경음 없음)
BGM_VOLUME = float(os.environ.get("SHORTS_BGM_VOLUME", "0.15"))

VIDEO_PROJECT_DIR = "video"
VIDEO_FPS = 30
# 장면 끝 여유. 장면 전환(video/src/schema.ts의 TRANSITION_FRAMES = 10프레임)이
# 이 여유 구간에서 겹치므로 말이 잘리지 않는다.
SCENE_TAIL_SECONDS = 0.5


# ---------------------------------------------------------------------------
# 기사 선택
# ---------------------------------------------------------------------------

def today_kst():
    return datetime.now(KST).strftime("%Y-%m-%d")


def load_json(path, default):
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_issue(issue_date):
    path = os.path.join(DAILY_ISSUES_DIR, f"{issue_date}.json")

    if not os.path.exists(path):
        raise FileNotFoundError(f"이슈 파일이 없습니다: {path}")

    return load_json(path, {})


def issue_articles(issue):
    """요약(key_points)이 있는 기사만 후보로 쓴다. 단신은 정보가 부족하다."""
    articles = []

    for section in ("top_stories", "more_detailed"):
        for article in issue.get(section) or []:
            if article.get("key_points") and article.get("link"):
                articles.append(article)

    return articles


def is_ai_article(article):
    text = " ".join(
        [
            article.get("title") or "",
            article.get("one_line") or "",
            " ".join(article.get("topics") or []),
        ]
    ).lower()

    for keyword in AI_KEYWORDS:
        # 영문 약어(ai, rag 등)는 다른 단어 안에 섞이지 않도록 단어 경계로 찾는다.
        if keyword.isascii():
            if re.search(rf"(?<![a-z]){re.escape(keyword)}(?![a-z])", text):
                return True
        elif keyword in text:
            return True

    return False


def pick_article(issue, used_links):
    candidates = [
        article
        for article in issue_articles(issue)
        if is_ai_article(article) and article["link"] not in used_links
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda article: (
            article.get("selection_score") or 0,
            -(article.get("editorial_rank") or 99),
        ),
    )


# ---------------------------------------------------------------------------
# 대본 생성 (Claude)
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM_PROMPT = """너는 한국어 YouTube Shorts 채널 "{channel}"의 작가다.
채널 콘셉트: 개발자·직장인이 출퇴근길 1분으로 AI 트렌드를 따라잡는 채널.
목소리는 AI 음성(TTS)이고 얼굴은 나오지 않는다.

대본 규칙:
- 뉴스를 나열하지 말고, 기사 하나를 "A인데 왜 B?" 같은 질문이나 상식을 뒤집는 한 문장으로 바꿔서 답하는 구조로 쓴다.
- 첫 장면(훅)은 3초 안에 읽히는 한 문장. 인사, 채널 소개로 시작하지 않는다.
- 장면은 4~6개. 마지막 장면은 시청자에게 던지는 질문이나 한 줄 의미로 끝낸다.
- 전체 내레이션은 공백 포함 230~300자 (약 45초).
- 내레이션은 소리 내어 읽기 쉬운 구어체 존댓말. 영어 약어는 한 번은 풀어서 말한다.
- 숫자, 회사명, 결과는 반드시 주어진 기사 정보에 있는 것만 쓴다. 없는 사실을 지어내지 않는다.
- headline은 화면 중앙에 크게 들어갈 핵심 문구로 14자 이내. 숫자가 있으면 숫자를 쓴다.
- title은 40자 이내, 해시태그 없이. 클릭하고 싶은 질문형이나 단정형.
- hashtags는 # 없이 3~5개.

장면마다 visual(화면 중앙 인포그래픽)을 하나 고른다. 같은 type을 연달아 쓰지 않는다.
- number: 숫자 하나를 크게 카운트업. value에 "0.016%", "250배"처럼 숫자+단위, label에 무엇의 숫자인지 짧게.
- compare: 2~4개 값을 막대로 비교. bars에 label, value(숫자), display(화면 표기). 기사에 실제 수치가 2개 이상 있을 때만.
- flow: 과정이나 원리를 2~4단계로. items에 단계별 12자 이내 문구.
- keywords: 핵심 단어 2~4개 카드. items에 단어별 8자 이내.
- code: 개발자용 코드·명령어 예시 7줄 이내. code에 넣는다. 기사 내용과 직접 관련 있을 때만.
- question: 마지막 장면용 질문 카드. label에 질문 한 줄.
- none: 헤드라인만 크게. 다른 type이 어울리지 않을 때만.
visual에 들어가는 숫자와 사실도 기사에 있는 것만 쓴다."""


VISUAL_TYPES = ["number", "compare", "flow", "keywords", "code", "question", "none"]

# video/src/schema.ts의 visualSchema와 같은 구조
VISUAL_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": VISUAL_TYPES},
        "value": {"type": "string"},
        "label": {"type": "string"},
        "items": {"type": "array", "items": {"type": "string"}},
        "bars": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "number"},
                    "display": {"type": "string"},
                },
                "required": ["label", "value", "display"],
                "additionalProperties": False,
            },
        },
        "code": {"type": "string"},
    },
    "required": ["type"],
    "additionalProperties": False,
}


SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "narration": {"type": "string"},
                    "visual": VISUAL_SCHEMA,
                },
                "required": ["headline", "narration", "visual"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "description", "hashtags", "scenes"],
    "additionalProperties": False,
}


def build_script_prompt(article):
    lines = [
        "아래 기사로 Shorts 대본을 써줘.",
        "",
        f"제목: {article.get('title')}",
        f"한 줄 요약: {article.get('one_line')}",
        "핵심 포인트:",
    ]

    for point in article.get("key_points") or []:
        lines.append(f"- {point}")

    lines += [
        f"키워드: {', '.join(article.get('topics') or [])}",
        f"추천 대상: {article.get('recommended_for') or ''}",
        f"출처: {article.get('company')} ({article.get('link')})",
    ]

    return "\n".join(lines)


def normalize_oauth_token(value):
    """복사 과정에서 섞인 공백, 줄바꿈, 안내 문구를 걷어내고 토큰만 남긴다.

    터미널 폭이 좁으면 토큰이 줄바꿈된 자리가 복사할 때 줄바꿈이나 공백으로 바뀐다.
    토큰이 시작된 곳부터 "토큰 글자로만 된 조각"을 이어 붙이고,
    안내 문장(마침표, 콜론 등이 섞인 조각)이나 빈 줄에서 멈춘다.
    """
    lines = [line.strip() for line in (value or "").splitlines()]

    def is_token_piece(piece):
        return re.fullmatch(r"[A-Za-z0-9_\-]+", piece) is not None

    for index, line in enumerate(lines):
        start = line.find("sk-ant-oat")

        if start < 0:
            continue

        token = ""

        for piece in line[start:].split():
            if not is_token_piece(piece):
                break

            token += piece

        for next_line in lines[index + 1:]:
            pieces = next_line.split()

            if not pieces or not all(is_token_piece(piece) for piece in pieces):
                break

            token += "".join(pieces)

        return token

    return re.sub(r"\s+", "", value or "")


def describe_oauth_token(token):
    """토큰 값은 노출하지 않고 형식만 설명한다. 인증 실패 원인 확인용."""
    if not token:
        return "토큰 없음"

    return (
        f"길이 {len(token)}, "
        f"sk-ant-oat 접두사 {'있음' if token.startswith('sk-ant-oat') else '없음'}"
    )


def generate_script(article):
    """Claude Code CLI(claude -p)로 대본을 만든다.

    API 키 대신 Claude 구독 계정으로 실행된다. 로컬은 로그인된 상태를 쓰고,
    GitHub Actions에서는 `claude setup-token`으로 만든 CLAUDE_CODE_OAUTH_TOKEN을 쓴다.
    """
    claude = shutil.which("claude")

    if not claude:
        raise RuntimeError("claude CLI가 없습니다. Claude Code를 설치하세요.")

    command = [
        claude,
        "-p",
        "--output-format", "json",
        "--tools", "",
        "--system-prompt", SCRIPT_SYSTEM_PROMPT.format(channel=CHANNEL_NAME),
        "--json-schema", json.dumps(SCRIPT_SCHEMA),
    ]

    if CLAUDE_MODEL:
        command += ["--model", CLAUDE_MODEL]

    env = os.environ.copy()
    token = normalize_oauth_token(env.get("CLAUDE_CODE_OAUTH_TOKEN"))

    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    result = subprocess.run(
        command,
        input=build_script_prompt(article),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=300,
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude 실행 실패: {result.stderr.strip() or result.stdout.strip()}")

    if output.get("is_error") or not output.get("structured_output"):
        message = output.get("result") or output.get("subtype")

        if "CLAUDE_CODE_OAUTH_TOKEN" in os.environ:
            message += f" (CLAUDE_CODE_OAUTH_TOKEN: {describe_oauth_token(token)})"

        raise RuntimeError(f"대본 생성 실패: {message}")

    return validate_script(output["structured_output"])


def validate_script(script):
    scenes = script.get("scenes") or []

    if not 3 <= len(scenes) <= 8:
        raise ValueError(f"장면 수가 이상합니다: {len(scenes)}")

    for scene in scenes:
        if not scene.get("narration", "").strip():
            raise ValueError("내레이션이 비어 있는 장면이 있습니다.")

        scene["visual"] = validate_visual(scene.get("visual"))

    script["hashtags"] = [
        tag.strip().lstrip("#").replace(" ", "")
        for tag in script.get("hashtags") or []
        if tag.strip()
    ]

    return script


def validate_visual(visual):
    """그릴 재료가 없는 인포그래픽은 헤드라인만 보이는 none으로 바꿔서 빈 화면을 막는다."""
    visual = dict(visual or {})
    kind = visual.get("type")

    has_content = {
        "number": bool(re.search(r"\d", visual.get("value") or "")),
        "compare": len(visual.get("bars") or []) >= 2,
        "flow": len(visual.get("items") or []) >= 2,
        "keywords": len(visual.get("items") or []) >= 1,
        "code": bool((visual.get("code") or "").strip()),
        "question": bool((visual.get("label") or "").strip()),
        "none": True,
    }

    if not has_content.get(kind):
        return {"type": "none"}

    return visual


# ---------------------------------------------------------------------------
# 음성 (TTS)
# ---------------------------------------------------------------------------

async def _synthesize(text, path):
    """mp3를 저장하고, 단어별로 말하는 시점(ms)을 돌려준다. 자막 강조에 쓴다."""
    import edge_tts

    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE, boundary="WordBoundary")
    boundaries = []

    with open(path, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset, duration 단위는 100ns
                start = chunk["offset"] / 10_000
                boundaries.append(
                    {"text": chunk["text"], "startMs": start, "endMs": start + chunk["duration"] / 10_000}
                )

    return boundaries


def align_words(narration, boundaries, duration_ms):
    """TTS 단어 시점에 대본의 원래 단어(문장부호 포함)를 붙인다.

    단어 수가 다르면 TTS가 준 단어를 그대로 쓰고, 시점 정보가 아예 없으면
    글자 수 비율로 나눠서 대략 맞춘다.
    """
    tokens = narration.split()

    if boundaries and len(boundaries) == len(tokens):
        return [{**b, "text": token} for b, token in zip(boundaries, tokens)]

    if boundaries:
        return boundaries

    total = sum(len(token) for token in tokens) or 1
    words, cursor = [], 0.0

    for token in tokens:
        length = duration_ms * len(token) / total
        words.append({"text": token, "startMs": cursor, "endMs": cursor + length})
        cursor += length

    return words


def synthesize_scenes(scenes, work_dir):
    """장면마다 mp3 경로와 단어 시점 목록을 돌려준다."""
    results = []

    for index, scene in enumerate(scenes):
        path = os.path.join(work_dir, f"scene_{index:02d}.mp3")
        boundaries = asyncio.run(_synthesize(scene["narration"], path))
        words = align_words(scene["narration"], boundaries, audio_duration(path) * 1000)
        results.append((path, words))

    return results


# ---------------------------------------------------------------------------
# 영상 렌더링 (Remotion, video/ 폴더의 React 프로젝트)
# ---------------------------------------------------------------------------

def build_props(script, scene_audio, source_label, run_name):
    """Remotion에 넘길 props를 만든다. 음성 파일은 video/public/<run_name>/ 으로 복사한다."""
    public_dir = os.path.join(VIDEO_PROJECT_DIR, "public", run_name)
    os.makedirs(public_dir, exist_ok=True)

    scenes = []

    for index, (scene, (audio_path, words)) in enumerate(zip(script["scenes"], scene_audio)):
        name = f"scene_{index:02d}.mp3"
        shutil.copyfile(audio_path, os.path.join(public_dir, name))

        scenes.append(
            {
                "headline": scene["headline"],
                "narration": scene["narration"],
                "audio": f"{run_name}/{name}",
                "durationInFrames": math.ceil((audio_duration(audio_path) + SCENE_TAIL_SECONDS) * VIDEO_FPS),
                "words": words,
                "visual": scene["visual"],
            }
        )

    return {"channel": CHANNEL_NAME, "source": source_label, "scenes": scenes}


def render_with_remotion(props, work_dir, output_path):
    npx = shutil.which("npx")

    if not npx:
        raise RuntimeError("Node.js(npx)가 없습니다. video/ 폴더에서 npm ci를 먼저 실행하세요.")

    props_path = os.path.abspath(os.path.join(work_dir, "props.json"))
    save_json(props_path, props)

    result = subprocess.run(
        [
            npx, "remotion", "render", "src/index.ts", "Short",
            os.path.abspath(output_path),
            f"--props={props_path}",
            "--log=error",
        ],
        cwd=VIDEO_PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=1800,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Remotion 렌더링 실패: {(result.stderr or result.stdout).strip()[-2000:]}")

    return output_path


# ---------------------------------------------------------------------------
# 영상 합성 (ffmpeg)
# ---------------------------------------------------------------------------

def ffmpeg_exe():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def audio_duration(path):
    result = subprocess.run(
        [ffmpeg_exe(), "-i", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)

    if not match:
        raise RuntimeError(f"오디오 길이를 읽지 못했습니다: {path}")

    hours, minutes, seconds = match.groups()

    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def run_ffmpeg(args):
    result = subprocess.run(
        [ffmpeg_exe(), "-y", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {result.stderr.strip()}")


def build_video(script, scene_audio, source_label, work_dir, output_path):
    """Remotion으로 장면 영상(내레이션 포함)을 렌더링하고 배경음을 깐다."""
    run_name = f"run-{os.path.basename(work_dir)}"
    props = build_props(script, scene_audio, source_label, run_name)

    try:
        if BGM_VOLUME <= 0:
            return render_with_remotion(props, work_dir, output_path)

        narration_path = os.path.join(work_dir, "narration.mp4")
        render_with_remotion(props, work_dir, narration_path)
    finally:
        shutil.rmtree(os.path.join(VIDEO_PROJECT_DIR, "public", run_name), ignore_errors=True)

    return add_bgm(narration_path, work_dir, output_path)


def add_bgm(video_path, work_dir, output_path):
    """코드로 만든 배경음을 내레이션 아래에 깐다. 말할 때는 음악이 자동으로 작아진다."""
    import bgm

    duration = audio_duration(video_path)
    bgm_path = bgm.write_wav(
        bgm.generate_bgm(duration, seed=os.path.basename(work_dir)),
        os.path.join(work_dir, "bgm.wav"),
    )

    run_ffmpeg(
        [
            "-i", video_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={BGM_VOLUME}[music];"
            "[0:a]asplit=2[voice][key];"
            # 내레이션이 나올 때 배경음을 눌러준다(사이드체인 덕킹).
            "[music][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[ducked];"
            "[voice][ducked]amix=inputs=2:duration=first:normalize=0,"
            # 휴대폰 스피커에서도 잘 들리게 Shorts 평균 음량(-14 LUFS)으로 맞춘다.
            "loudnorm=I=-14:TP=-1.5:LRA=11[out]",
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "160k",
            output_path,
        ]
    )

    return output_path


# ---------------------------------------------------------------------------
# 업로드 (YouTube Data API v3)
# ---------------------------------------------------------------------------

def youtube_access_token():
    data = urllib.parse.urlencode(
        {
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": YOUTUBE_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def build_description(script, article):
    hashtags = " ".join(f"#{tag}" for tag in ["shorts", *script["hashtags"]])

    return "\n\n".join(
        [
            script["description"].strip(),
            f"원문: {article['link']}",
            "이 영상의 대본과 음성은 AI로 생성되었습니다.",
            hashtags,
        ]
    )


YOUTUBE_ERROR_HINTS = {
    "youtubeSignupRequired": "허용한 Google 계정에 YouTube 채널이 없습니다. youtube_auth.py를 다시 실행해 itgony 채널 계정(브랜드 채널이면 채널 선택)으로 허용하세요.",
    "accessNotConfigured": "Google Cloud 프로젝트에서 YouTube Data API v3가 꺼져 있습니다.",
    "quotaExceeded": "오늘 YouTube API 사용량을 다 썼습니다. 내일 다시 시도됩니다.",
    "uploadLimitExceeded": "채널의 하루 업로드 한도를 넘었습니다.",
}


def youtube_error_reason(error):
    """YouTube API 오류 응답에서 reason을 꺼내 사람이 읽을 수 있게 바꾼다."""
    try:
        body = json.loads(error.read().decode("utf-8"))
    except Exception:
        return error.reason

    detail = body.get("error", {})
    reasons = [item.get("reason", "") for item in detail.get("errors", [])]

    for reason in reasons:
        if reason in YOUTUBE_ERROR_HINTS:
            return f"{reason}: {YOUTUBE_ERROR_HINTS[reason]}"

    return f"{', '.join(filter(None, reasons))} {detail.get('message', '')}".strip()


def upload_youtube(video_path, script, article):
    token = youtube_access_token()
    metadata = {
        "snippet": {
            "title": script["title"][:100],
            "description": build_description(script, article)[:5000],
            "tags": script["hashtags"],
            "categoryId": "28",  # Science & Technology
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": UPLOAD_PRIVACY,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }
    size = os.path.getsize(video_path)

    start = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        data=json.dumps(metadata).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(size),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(start, timeout=60) as response:
            upload_url = response.headers["Location"]
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"YouTube 업로드 시작 실패 ({error.code}): {youtube_error_reason(error)}")

    with open(video_path, "rb") as file:
        upload = urllib.request.Request(
            upload_url,
            data=file.read(),
            headers={"Content-Type": "video/mp4", "Content-Length": str(size)},
            method="PUT",
        )

    with urllib.request.urlopen(upload, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))["id"]


def notify_slack(text):
    if not SLACK_WEBHOOK_URL:
        return

    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        urllib.request.urlopen(request, timeout=30).close()
    except urllib.error.URLError as error:
        print(f"Slack 알림 실패: {error}")


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="GONY DAILY 기사로 YouTube Shorts 만들기")
    parser.add_argument("--date", default=today_kst(), help="이슈 날짜 (기본: 오늘, KST)")
    parser.add_argument("--script", help="Claude 대신 이 대본 JSON 파일을 사용")
    parser.add_argument("--no-upload", action="store_true", help="영상만 만들고 업로드하지 않음")

    return parser.parse_args()


def main():
    args = parse_args()

    issue = load_issue(args.date)
    history = load_json(SHORTS_HISTORY_FILE, [])
    used_links = {entry["link"] for entry in history}

    article = pick_article(issue, used_links)

    if not article:
        print(f"{args.date} 이슈에 영상으로 만들 새 AI 기사가 없습니다.")
        return

    print(f"선택한 기사: {article['title']}")

    work_dir = os.path.join(OUTPUT_DIR, args.date)
    os.makedirs(work_dir, exist_ok=True)

    if args.script:
        script = validate_script(load_json(args.script, {}))
    else:
        script = generate_script(article)

    save_json(os.path.join(work_dir, "script.json"), script)
    print(f"대본 생성 완료: {script['title']} (장면 {len(script['scenes'])}개)")

    scene_audio = synthesize_scenes(script["scenes"], work_dir)
    print("음성 생성 완료")

    source_label = f"출처: {article.get('company')} · {urllib.parse.urlsplit(article['link']).netloc}"
    video_path = build_video(script, scene_audio, source_label, work_dir, os.path.join(work_dir, "short.mp4"))
    print(f"영상 생성 완료: {video_path}")

    video_id = None
    can_upload = YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN

    if args.no_upload:
        print("--no-upload: 업로드를 건너뜁니다.")
    elif not can_upload:
        print("YouTube 인증 정보가 없어 업로드를 건너뜁니다.")
    else:
        video_id = upload_youtube(video_path, script, article)
        print(f"업로드 완료 ({UPLOAD_PRIVACY}): https://youtu.be/{video_id}")
        notify_slack(
            f"[{CHANNEL_NAME}] 새 Shorts 업로드 ({UPLOAD_PRIVACY}) — 확인 후 공개로 바꿔주세요\n"
            f"*{script['title']}*\nhttps://studio.youtube.com/video/{video_id}/edit\n원문: {article['link']}"
        )

    # 업로드하지 않은 로컬 테스트는 이력에 남기지 않는다. 같은 기사로 다시 만들 수 있게.
    if video_id:
        history.append(
            {
                "date": args.date,
                "link": article["link"],
                "title": script["title"],
                "video_id": video_id,
            }
        )
        save_json(SHORTS_HISTORY_FILE, history)


if __name__ == "__main__":
    main()
