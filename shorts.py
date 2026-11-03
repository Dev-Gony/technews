"""GONY DAILY 이슈에서 AI 기사 1개를 골라 YouTube Shorts 영상으로 만든다.

흐름: 이슈 JSON → 기사 선택 → Claude 대본 → TTS 음성 → 장면 이미지 → ffmpeg 합성 → YouTube 업로드
"""

import os
import re
import json
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

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SCENE_TAIL_SECONDS = 0.3

COLORS = {
    "background": (14, 17, 22),
    "text": (245, 246, 248),
    "muted": (140, 148, 160),
    "accent": (255, 92, 77),
    "subtitle_box": (0, 0, 0, 170),
}

FONT_CANDIDATES = [
    os.environ.get("SHORTS_FONT", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


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
- hashtags는 # 없이 3~5개."""


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
                },
                "required": ["headline", "narration"],
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

    script["hashtags"] = [
        tag.strip().lstrip("#").replace(" ", "")
        for tag in script.get("hashtags") or []
        if tag.strip()
    ]

    return script


# ---------------------------------------------------------------------------
# 음성 (TTS)
# ---------------------------------------------------------------------------

async def _synthesize(text, path):
    import edge_tts

    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
    await communicate.save(path)


def synthesize_scenes(scenes, work_dir):
    paths = []

    for index, scene in enumerate(scenes):
        path = os.path.join(work_dir, f"scene_{index:02d}.mp3")
        asyncio.run(_synthesize(scene["narration"], path))
        paths.append(path)

    return paths


# ---------------------------------------------------------------------------
# 장면 이미지
# ---------------------------------------------------------------------------

def load_font(size):
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)

    raise RuntimeError("한글 폰트를 찾지 못했습니다. SHORTS_FONT 환경변수로 지정하세요.")


def wrap_text(text, font, max_width, measure):
    """단어 단위로 줄바꿈하고, 한 단어가 너무 길면 글자 단위로 자른다."""
    lines = []
    current = ""

    for word in text.split():
        candidate = f"{current} {word}".strip()

        if measure(candidate, font) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""

        while measure(word, font) > max_width:
            cut = len(word)

            while cut > 1 and measure(word[:cut], font) > max_width:
                cut -= 1

            lines.append(word[:cut])
            word = word[cut:]

        current = word

    if current:
        lines.append(current)

    return lines


def render_scene(scene, index, total, source_label, path):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), COLORS["background"])
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    overlay_draw = ImageDraw.Draw(overlay)

    def measure(text, font):
        return draw.textlength(text, font=font)

    margin = 80
    content_width = VIDEO_WIDTH - margin * 2

    brand_font = load_font(44)
    headline_font = load_font(112)
    subtitle_font = load_font(54)
    source_font = load_font(34)

    # 상단: 채널명 + 진행 표시
    draw.text((margin, 150), CHANNEL_NAME, font=brand_font, fill=COLORS["accent"])

    bar_y = 230
    bar_gap = 12
    bar_width = (content_width - bar_gap * (total - 1)) / total

    for bar in range(total):
        x0 = margin + bar * (bar_width + bar_gap)
        color = COLORS["accent"] if bar <= index else (48, 54, 64)
        draw.rounded_rectangle((x0, bar_y, x0 + bar_width, bar_y + 10), radius=5, fill=color)

    # 중앙: 헤드라인
    headline_lines = wrap_text(scene["headline"], headline_font, content_width, measure)
    line_height = 140
    block_height = line_height * len(headline_lines)
    y = 720 - block_height // 2

    for line in headline_lines:
        width = measure(line, headline_font)
        draw.text(((VIDEO_WIDTH - width) / 2, y), line, font=headline_font, fill=COLORS["text"])
        y += line_height

    draw.rounded_rectangle(
        (VIDEO_WIDTH / 2 - 60, y + 20, VIDEO_WIDTH / 2 + 60, y + 32),
        radius=6,
        fill=COLORS["accent"],
    )

    # 하단: 자막. Shorts UI(제목, 버튼)에 가리지 않도록 1200~1550 구간에 둔다.
    subtitle_lines = wrap_text(scene["narration"], subtitle_font, content_width - 60, measure)[:5]
    subtitle_line_height = 76
    box_top = 1200
    box_bottom = box_top + subtitle_line_height * len(subtitle_lines) + 60

    overlay_draw.rounded_rectangle(
        (margin - 10, box_top, VIDEO_WIDTH - margin + 10, box_bottom),
        radius=28,
        fill=COLORS["subtitle_box"],
    )
    image.paste(overlay, (0, 0), overlay)

    y = box_top + 30

    for line in subtitle_lines:
        width = measure(line, subtitle_font)
        draw.text(((VIDEO_WIDTH - width) / 2, y), line, font=subtitle_font, fill=COLORS["text"])
        y += subtitle_line_height

    draw.text((margin, box_bottom + 30), source_label, font=source_font, fill=COLORS["muted"])

    image.save(path)

    return path


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


def build_video(image_paths, audio_paths, work_dir, output_path):
    segments = []

    for index, (image_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
        segment = os.path.join(work_dir, f"segment_{index:02d}.mp4")
        duration = audio_duration(audio_path) + SCENE_TAIL_SECONDS

        run_ffmpeg(
            [
                "-loop", "1", "-i", image_path,
                "-i", audio_path,
                "-af", "apad",
                "-t", f"{duration:.2f}",
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-r", "30", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                segment,
            ]
        )
        segments.append(segment)

    list_path = os.path.join(work_dir, "segments.txt")

    with open(list_path, "w", encoding="utf-8") as file:
        for segment in segments:
            file.write(f"file '{os.path.abspath(segment)}'\n")

    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_path])

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

    with urllib.request.urlopen(start, timeout=60) as response:
        upload_url = response.headers["Location"]

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

    audio_paths = synthesize_scenes(script["scenes"], work_dir)
    print("음성 생성 완료")

    source_label = f"출처: {article.get('company')} · {urllib.parse.urlsplit(article['link']).netloc}"
    image_paths = [
        render_scene(
            scene,
            index,
            len(script["scenes"]),
            source_label,
            os.path.join(work_dir, f"scene_{index:02d}.png"),
        )
        for index, scene in enumerate(script["scenes"])
    ]

    video_path = build_video(image_paths, audio_paths, work_dir, os.path.join(work_dir, "short.mp4"))
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
