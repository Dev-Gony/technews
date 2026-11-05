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
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

# 비우면 구독 플랜의 기본 모델을 쓴다. 예: opus, sonnet
CLAUDE_MODEL = os.environ.get("SHORTS_CLAUDE_MODEL", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_TTS_MODEL = os.environ.get("SHORTS_GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
# 영상마다 번갈아 쓰는 목소리 (쉼표로 구분)
GEMINI_TTS_VOICES = [
    voice.strip()
    for voice in os.environ.get("SHORTS_GEMINI_VOICES", "Leda,Puck,Zephyr,Fenrir").split(",")
    if voice.strip()
]
WHISPER_MODEL = os.environ.get("SHORTS_WHISPER_MODEL", "small")
# Gemini TTS가 실패하면(키 없음, 무료 한도 초과 등) 쓰는 대체 음성
TTS_VOICE = os.environ.get("SHORTS_VOICE", "ko-KR-HyunsuMultilingualNeural")
TTS_RATE = os.environ.get("SHORTS_TTS_RATE", "+22%")
# 업로드 기본값은 비공개: YouTube Studio에서 확인한 뒤 직접 공개로 바꾼다.
UPLOAD_PRIVACY = os.environ.get("SHORTS_PRIVACY", "public")
CHANNEL_NAME = os.environ.get("SHORTS_CHANNEL_NAME", "itgony")
# 영상 배경: ink(먹색, 프로필 사진과 같은 톤) / paper(종이색, 배너·카드뉴스와 같은 톤)
SHORTS_THEME = os.environ.get("SHORTS_THEME") or "ink"

DAILY_ISSUES_DIR = "config/issues"
# 오늘 이슈에 남은 기사가 없으면 며칠 전 이슈까지 거슬러 올라가서 고른다.
LOOKBACK_DAYS = int(os.environ.get("SHORTS_LOOKBACK_DAYS", "3"))
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
# 마지막 대사 뒤 여유
END_PAD_MS = 600


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
                articles.append({**article, "section": section})

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


def recent_issue_dates(base_date, days=LOOKBACK_DAYS):
    """base_date부터 거꾸로 days일 중 이슈 파일이 있는 날짜."""
    base = datetime.strptime(base_date, "%Y-%m-%d")
    dates = [(base - timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(days)]

    return [date for date in dates if os.path.exists(os.path.join(DAILY_ISSUES_DIR, f"{date}.json"))]


def pick_article(issues, used_links):
    """아직 영상으로 안 만든 기사 중 하나를 고른다.

    issues: [(이슈 날짜, 이슈), ...]. 고르는 순서:
    1. 최신 이슈 먼저 (오늘 기사를 다 쓴 뒤에야 전날 기사로 넘어간다)
    2. 같은 날이면 주요 기사(top_stories) → 나머지 상세 기사
    3. 그 안에서 AI 기사 → 점수 높은 순 → 편집 순위
    """
    candidates = [
        {**article, "issue_date": issue_date}
        for issue_date, issue in issues
        for article in issue_articles(issue)
        if article["link"] not in used_links
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda article: (
            article["issue_date"],
            article["section"] == "top_stories",
            is_ai_article(article),
            article.get("selection_score") or 0,
            -(article.get("editorial_rank") or 99),
        ),
    )


# ---------------------------------------------------------------------------
# 대본 생성 (Claude)
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM_PROMPT = """너는 한국어 개발/AI 쇼츠 채널 "{channel}"의 수석 쇼츠 디렉터다.
목표: 확실한 정보를 정확하고, 깔끔하고, 이해하기 쉽게 전달한다. 길이를 줄이는 것보다 시청자가 다 보고 나서 "아, 이거구나" 하고 정확히 이해하는 게 우선이다.
시청자는 1초 안에 넘길지 정하므로 시작은 강하게, 설명은 친절하게. 국어책처럼 읽히면 실패다.
목소리는 AI 음성, 얼굴은 안 나온다.

말투:
- 현업 시니어가 후배한테 뼈 때리듯 말하는 시니컬한 구어체. "~죠", "~거든요", "~한 거예요", "근데", "솔직히" 같은 말로 리듬을 만든다.
  "~했습니다" 같은 발표체, "좋아집니다"·"혁신적입니다" 같은 두루뭉술한 말 금지.
- 한 컷 = 한 호흡 = 사실 하나. line은 짧은 문장 하나(25자 이내). 사실이 두 개면 두 컷으로 쪼갠다.
- line 안에 화면 자막을 끊을 위치를 " / "로 표시한다. 한 조각은 1~3어절, 의미가 붙어 있는 말은 절대 떼지 않는다.
  좋은 예: "엔지니어 / 한 명당 / 병합 5배래요."  나쁜 예: "엔지니어 한 / 명당 병합"
- 컷은 10~15개, 길이는 30~50초. 짧게 줄이려고 맥락(누가, 무엇을, 왜)을 빼지 않는다. 대신 같은 말 반복과 군더더기는 뺀다.
- 영어 약어와 전문 용어는 처음 나올 때 한 번 쉽게 풀어서 말한다. (예: "리드타임, 그러니까 개발 시작부터 배포까지 걸리는 시간")
- 숫자는 반드시 "무엇의" 숫자인지 같이 말한다. ("70% 개선" → "리드타임이 70% 줄었다")

구조:
1. 1컷(훅, 첫 3초): 인사·채널 소개·"오늘은" 절대 금지. 첫 마디부터 개발자의 고통을 찌르는 문제 제기.
   API 요금 폭탄, 에이전트 폭주, 야근, 장애, 보안 사고처럼 기사 주제와 직접 이어지는 아픔으로 시작한다.
   (예: "API 청구서, / 또 폭탄이죠?", "에이전트가 / 혼자 폭주하죠?")
2. 2~3컷: 이 기사가 내놓은 답이나 가장 센 결과를 바로 던진다.
3. 중간 4~5컷: 공간·역할 비유로 구조를 설명한다.
   - 복잡한 구조를 건물·사무실·주방 같은 공간과 사람의 역할로 바꾼다.
     예: "위층 소장실(상주 대장)이 일을 나누고, 아래층 인력사무소(비상주 일꾼)가 필요할 때만 와서 처리"
   - 비유는 영상 하나에 하나만 골라 끝까지 일관되게 쓴다. 비유와 실제 기술을 꼭 짝지어 말한다.
   - 비유가 사실을 왜곡하면 안 된다. 비유로 설명하기 어려운 내용이면 억지로 쓰지 말고 flow나 compare로 설명한다.
4. 수치 2~3컷: 기사에 있는 정량적 수치와 동작 방식(무엇이 무엇을 대신하는지, 몇 단계인지)을 구체적으로.
5. 마지막 1~2컷: 시청자가 이번 주에 할 행동을 뼈 때리는 한 마디로. (예: "청구서 보기 전에 / 구조부터 / 뜯어보세요.")

사실 규칙 (가장 중요):
- 숫자, 회사명, 결과, 동작 방식은 반드시 주어진 기사에 있는 것만. 없는 사실·수치를 지어내지 않는다.
- 위 예시의 수치나 상황을 그대로 가져오지 않는다. 기사에 수치가 없으면 숫자 대신 구체적인 동작 방식으로 말한다.
- 기사가 말하지 않은 인과관계·효과를 덧붙이지 않는다. (예: 기사에 없는 "생산성 향상", "보안 강화" 금지)
- 확실하지 않거나 기사에서 조건이 붙은 내용은 조건까지 같이 말한다. ("~한 경우", "~ 기준")

emphasis: 그 컷에서 화면 자막 색을 바꿀 핵심 단어 0~2개. line에 그대로 들어 있는 어절이어야 한다. 숫자는 꼭 강조한다.

visual: 컷마다 화면 가운데에 띄울 그래픽 하나. 같은 type을 연달아 3번 이상 쓰지 않는다.
- hook: 1컷 전용. value에 화면을 꽉 채울 2~8자 (아픔이나 핵심어). 예: "청구서 폭탄", "250배".
- metaphor: 공간·역할 비유를 입체 건물로 보여준다. 비유를 처음 꺼내는 컷에 꼭 1번, 필요하면 한 번 더.
  rooms에 위층부터 2~3개. place는 비유 공간(8자 이내, 예: "위층 소장실"), actual은 그 공간이 뜻하는 실제 기술(12자 이내, 예: "자체 GLM 서버").
  label은 비유 이름(10자 이내, 예: "AI 인력사무소"), 없으면 비워둔다.
- number: 숫자 하나 카운트업. value에 숫자+단위, label에 무엇의 숫자인지 짧게.
- compare: 2~4개 값을 막대로 비교. bars에 label, value(숫자), display(단위 포함, 예: "10배", "90%"). 기사에 실제 수치가 2개 이상 있을 때만.
- flow: 과정이나 단계 2~4개. items에 단계별 10자 이내 명사구 ("끊고" 같은 동사 조각 금지).
- keywords: 핵심 단어 2~3개 카드. items에 단어별 8자 이내. "=", "vs" 같은 기호만 있는 항목 금지.
- code: 개발자용 코드·명령어 5줄 이내. 기사 내용과 직접 관련 있을 때만.
- question: 질문 카드. label은 line을 그대로 옮기지 말고 12자 이내로 더 짧게.
- none: 그래픽 없이 자막만 크게. 흐름상 쉬어가는 컷에만.
visual의 숫자와 사실도 기사에 있는 것만 쓴다.

cover: 영상 내내 화면 맨 위에 고정되는 제목. 썸네일 역할도 한다. 2줄이면 줄 사이에 \\n, 줄당 10자 이내. 예: "Cursor 확장\\n백도어 주의".
title은 40자 이내, 해시태그 없이 클릭하고 싶은 질문형이나 단정형. hashtags는 # 없이 3~5개.
더보기란용: summary는 무슨 일인지 1~2문장. tips는 시청자가 바로 써먹을 행동 1~3개(명령어·설정이 있으면 그대로). caution은 비용·보안·개인정보 주의점 한 줄, 없으면 빈 문자열."""


VISUAL_TYPES = ["hook", "metaphor", "number", "compare", "flow", "keywords", "code", "question", "none"]

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
        "rooms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "place": {"type": "string"},
                    "actual": {"type": "string"},
                },
                "required": ["place", "actual"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["type"],
    "additionalProperties": False,
}


SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "cover": {"type": "string"},
        "summary": {"type": "string"},
        "tips": {"type": "array", "items": {"type": "string"}},
        "caution": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "cuts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line": {"type": "string"},
                    "emphasis": {"type": "array", "items": {"type": "string"}},
                    "visual": VISUAL_SCHEMA,
                },
                "required": ["line", "emphasis", "visual"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "cover", "summary", "tips", "caution", "hashtags", "cuts"],
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


def claude_json(system_prompt, user_prompt, schema):
    """Claude Code CLI(claude -p)로 schema에 맞는 JSON을 받는다.

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
        "--system-prompt", system_prompt,
        "--json-schema", json.dumps(schema),
    ]

    if CLAUDE_MODEL:
        command += ["--model", CLAUDE_MODEL]

    env = os.environ.copy()
    token = normalize_oauth_token(env.get("CLAUDE_CODE_OAUTH_TOKEN"))

    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    result = subprocess.run(
        command,
        input=user_prompt,
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

        raise RuntimeError(f"Claude 생성 실패: {message}")

    return output["structured_output"]


def generate_script(article):
    script = claude_json(
        SCRIPT_SYSTEM_PROMPT.format(channel=CHANNEL_NAME),
        build_script_prompt(article),
        SCRIPT_SCHEMA,
    )

    return validate_script(script)


def validate_script(script):
    cuts = script.get("cuts") or []

    if not 6 <= len(cuts) <= 20:
        raise ValueError(f"컷 수가 이상합니다: {len(cuts)}")

    for cut in cuts:
        cut["line"] = (cut.get("line") or "").strip()

        if not spoken_line(cut):
            raise ValueError("대사가 비어 있는 컷이 있습니다.")

        # 자막에서 강조할 단어는 대사에 실제로 들어 있는 것만 남긴다.
        cut["emphasis"] = [word for word in cut.get("emphasis") or [] if word and word in spoken_line(cut)]
        cut["visual"] = drop_duplicate_label(validate_visual(cut.get("visual")), spoken_line(cut))

    # 모델이 줄바꿈을 글자 그대로 "\n"으로 쓰는 경우가 있다.
    script["cover"] = (script.get("cover") or script.get("title") or "").replace("\\n", "\n").strip()
    script["summary"] = (script.get("summary") or "").strip()
    script["tips"] = [tip.strip() for tip in script.get("tips") or [] if tip.strip()]
    script["caution"] = (script.get("caution") or "").strip()

    script["hashtags"] = [
        tag.strip().lstrip("#").replace(" ", "")
        for tag in script.get("hashtags") or []
        if tag.strip()
    ]

    return script


def spoken_line(cut):
    """자막 끊는 표시(/)를 뺀, 실제로 읽을 대사."""
    return re.sub(r"\s*/\s*", " ", cut["line"]).strip()


def caption_segments(cut):
    """대본이 표시한 자막 조각별 어절 수. 표시가 없으면 None."""
    if "/" not in cut["line"]:
        return None

    return [len(piece.split()) for piece in cut["line"].split("/") if piece.split()]


def validate_visual(visual):
    """그릴 재료가 없는 그래픽은 자막만 보이는 none으로 바꿔서 빈 화면을 막는다."""
    visual = dict(visual or {})
    kind = visual.get("type")

    # "=", "vs", "→"처럼 글자 없는 항목은 카드로 띄우지 않는다.
    if visual.get("items"):
        visual["items"] = [item for item in visual["items"] if re.search(r"[0-9A-Za-z가-힣]", item or "") and item.strip().lower() != "vs"]

    has_content = {
        "hook": bool((visual.get("value") or "").strip()),
        "metaphor": len([room for room in visual.get("rooms") or [] if (room.get("place") or "").strip()]) >= 2,
        "number": bool(re.search(r"\d", visual.get("value") or "")),
        "compare": len(visual.get("bars") or []) >= 2,
        "flow": len(visual.get("items") or []) >= 2,
        "keywords": len(visual.get("items") or []) >= 1,
        "code": bool((visual.get("code") or "").strip()),
        # 질문 문구가 없어도 물음표 애니메이션만으로 장면이 성립한다.
        "question": True,
        "none": True,
    }

    if not has_content.get(kind):
        return {"type": "none"}

    return visual


def drop_duplicate_label(visual, narration):
    """화면 문구가 자막(내레이션)과 사실상 같은 문장이면 지운다. 같은 말이 두 번 보이지 않게."""
    label = visual.get("label")

    if not label:
        return visual

    def compact(text):
        return re.sub(r"[\s\W_]+", "", text)

    short, long = sorted([compact(label), compact(narration)], key=len)

    if short and short in long and len(short) >= len(long) * 0.6:
        visual = {key: value for key, value in visual.items() if key != "label"}

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


GEMINI_TTS_STYLE = (
    "유튜브 쇼츠 내레이터처럼 읽어줘. 친구한테 놀라운 썰을 푸는 느낌으로, "
    "빠르고 텐션 높게, 문장 끝을 늘이지 말고 툭툭 끊어서. 대사:\n"
)


def gemini_tts(text, path, voice):
    """Gemini TTS로 내레이션 mp3를 만든다. 말투는 GEMINI_TTS_STYLE 지시로 조절한다."""
    import base64

    body = {
        "contents": [{"parts": [{"text": GEMINI_TTS_STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_TTS_MODEL}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY)}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        data = json.loads(response.read().decode("utf-8"))

    inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    rate = re.search(r"rate=(\d+)", inline["mimeType"])
    pcm_path = path + ".pcm"

    with open(pcm_path, "wb") as file:
        file.write(base64.b64decode(inline["data"]))

    # 16bit PCM(little endian) → mp3
    run_ffmpeg(
        ["-f", "s16le", "-ar", rate.group(1) if rate else "24000", "-ac", "1", "-i", pcm_path, "-b:a", "160k", path]
    )
    os.remove(pcm_path)

    return path


def transcribe_words(path):
    """음성을 받아 적어서 단어별 시점(ms)을 얻는다. Gemini TTS는 시점 정보를 주지 않기 때문."""
    import numpy as np
    from faster_whisper import WhisperModel

    raw = subprocess.run(
        [ffmpeg_exe(), "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True,
        check=True,
    ).stdout
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(np.frombuffer(raw, dtype=np.float32), language="ko", word_timestamps=True)

    return [
        {"text": word.word.strip(), "startMs": word.start * 1000, "endMs": word.end * 1000}
        for segment in segments
        for word in segment.words
    ]


def _letters(text):
    return [char for char in text.lower() if char.isalnum()]


def align_to_script(text, heard, duration_ms):
    """받아 적은 단어 시점을 대본의 어절에 글자 단위로 맞춘다.

    "Claude"→"클로드"처럼 표기가 달라 못 맞춘 어절은 앞뒤 어절 사이 시간으로 채운다.
    """
    import difflib

    tokens = text.split()
    script_chars, owner = [], []

    for index, token in enumerate(tokens):
        for char in _letters(token):
            script_chars.append(char)
            owner.append(index)

    heard_chars, heard_times = [], []

    for word in heard:
        chars = _letters(word["text"])
        step = (word["endMs"] - word["startMs"]) / max(len(chars), 1)

        for i, char in enumerate(chars):
            heard_chars.append(char)
            heard_times.append((word["startMs"] + i * step, word["startMs"] + (i + 1) * step))

    starts, ends = [None] * len(tokens), [None] * len(tokens)
    matcher = difflib.SequenceMatcher(None, script_chars, heard_chars, autojunk=False)

    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            index = owner[block.a + offset]
            start, end = heard_times[block.b + offset]
            starts[index] = start if starts[index] is None else min(starts[index], start)
            ends[index] = end if ends[index] is None else max(ends[index], end)

    # 못 맞춘 어절은 앞 어절 끝 ~ 다음으로 맞춘 어절 시작 사이를 글자 수 비율로 나눈다.
    index = 0

    while index < len(tokens):
        if starts[index] is not None:
            index += 1
            continue

        gap_end = index

        while gap_end < len(tokens) and starts[gap_end] is None:
            gap_end += 1

        left = ends[index - 1] if index > 0 else 0.0
        right = starts[gap_end] if gap_end < len(tokens) else duration_ms
        weights = [max(len(_letters(tokens[i])), 1) for i in range(index, gap_end)]
        cursor = left

        for i, weight in zip(range(index, gap_end), weights):
            length = (right - left) * weight / sum(weights)
            starts[i], ends[i] = cursor, cursor + length
            cursor += length

        index = gap_end

    return [{"text": token, "startMs": starts[i], "endMs": ends[i]} for i, token in enumerate(tokens)]


def synthesize_narration(cuts, work_dir, voice):
    """모든 컷의 대사를 한 번에 읽혀서 컷 사이가 끊기지 않게 한다.

    Gemini TTS를 먼저 쓰고, 실패하면 edge-tts로 대체한다.
    돌려주는 값: (mp3 경로, 컷별 단어 목록, 실제로 쓴 목소리). 단어마다 startMs, endMs가 있다.
    """
    path = os.path.join(work_dir, "narration.mp3")
    text = " ".join(spoken_line(cut) for cut in cuts)
    words = None

    if GEMINI_API_KEY:
        try:
            gemini_tts(text, path, voice)
            words = align_to_script(text, transcribe_words(path), audio_duration(path) * 1000)
            print(f"음성: Gemini TTS ({voice})")
        except Exception as error:
            print(f"Gemini TTS 실패, edge-tts로 대체합니다: {error}")

    if words is None:
        boundaries = asyncio.run(_synthesize(text, path))
        words = align_words(text, boundaries, audio_duration(path) * 1000)

        if len(words) != len(text.split()):
            # TTS 단어 수가 대본과 다르면 컷을 나눌 수 없으므로 글자 비율로 추정한다.
            words = align_words(text, [], audio_duration(path) * 1000)

        print(f"음성: edge-tts ({TTS_VOICE})")
        voice = TTS_VOICE

    per_cut, index = [], 0

    for cut in cuts:
        count = len(spoken_line(cut).split())
        per_cut.append(words[index:index + count])
        index += count

    return path, per_cut, voice


# ---------------------------------------------------------------------------
# 영상 렌더링 (Remotion, video/ 폴더의 React 프로젝트)
# ---------------------------------------------------------------------------

def ms_to_frame(ms):
    return round(ms * VIDEO_FPS / 1000)


def caption_chunks(words, emphasis, segments=None):
    """한 컷의 단어를 화면 자막 조각으로 묶는다.

    대본이 "/"로 끊을 위치를 정해 줬으면(segments) 그대로 따르고,
    아니면 1~2어절씩 기계적으로 묶는다.
    """
    chunks, current = [], []

    if segments and sum(segments) == len(words):
        index = 0

        for count in segments:
            chunks.append(words[index:index + count])
            index += count

        words = []

    for word in words:
        if current and (len(current) == 2 or len("".join(w["text"] for w in current + [word])) > 8):
            chunks.append(current)
            current = []

        current.append(word)

    if current:
        chunks.append(current)

    result = []

    for chunk in chunks:
        text = " ".join(w["text"] for w in chunk).rstrip(".,")
        result.append(
            {
                "text": text,
                "startMs": chunk[0]["startMs"],
                "emphasis": any(term in text or text in term for term in emphasis),
            }
        )

    return result


def build_props(script, narration_path, cut_words, source_label, run_name):
    """Remotion에 넘길 props를 만든다. 타이밍은 모두 프레임 단위로 계산해서 넘긴다."""
    public_dir = os.path.join(VIDEO_PROJECT_DIR, "public", run_name)
    os.makedirs(public_dir, exist_ok=True)
    shutil.copyfile(narration_path, os.path.join(public_dir, "narration.mp3"))

    total_frames = ms_to_frame(audio_duration(narration_path) * 1000 + END_PAD_MS)
    cuts = script["cuts"]

    # 컷은 그 컷의 첫 단어를 말하기 시작할 때 바뀐다.
    starts = [0] + [ms_to_frame(words[0]["startMs"]) if words else 0 for words in cut_words[1:]]
    ends = starts[1:] + [total_frames]

    props_cuts, sfx = [], []

    for index, (cut, words) in enumerate(zip(cuts, cut_words)):
        start, end = starts[index], max(ends[index], starts[index] + 1)
        chunks = caption_chunks(words, cut["emphasis"], caption_segments(cut))
        chunk_starts = [max(ms_to_frame(c["startMs"]) - start, 0) for c in chunks]
        chunk_ends = chunk_starts[1:] + [end - start]

        props_cuts.append(
            {
                "from": start,
                "durationInFrames": end - start,
                "visual": cut["visual"],
                "chunks": [
                    {
                        "text": chunk["text"],
                        "from": chunk_start,
                        "durationInFrames": max(chunk_end - chunk_start, 1),
                        "emphasis": chunk["emphasis"],
                    }
                    for chunk, chunk_start, chunk_end in zip(chunks, chunk_starts, chunk_ends)
                ],
            }
        )

        kind = cut["visual"]["type"]

        if index == 0 or kind in ("hook", "number"):
            sfx.append({"src": "sfx/impact.wav", "from": start, "volume": 0.55})
        else:
            sfx.append({"src": f"sfx/whoosh{index % 2 + 1}.wav", "from": max(start - 3, 0), "volume": 0.35})

        if kind in ("keywords", "flow", "compare"):
            sfx.append({"src": "sfx/pop.wav", "from": start + 8, "volume": 0.3})

    return {
        "channel": CHANNEL_NAME,
        "theme": SHORTS_THEME,
        "cover": script["cover"],
        "source": source_label,
        "audio": f"{run_name}/narration.mp3",
        "durationInFrames": total_frames,
        "cuts": props_cuts,
        "sfx": sfx,
    }


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


def build_video(script, narration_path, cut_words, source_label, work_dir, output_path):
    """Remotion으로 컷 편집 영상(내레이션, 효과음 포함)을 렌더링하고 배경음을 깐다."""
    import bgm

    run_name = f"run-{os.path.basename(work_dir)}"
    bgm.write_sfx(os.path.join(VIDEO_PROJECT_DIR, "public", "sfx"))
    props = build_props(script, narration_path, cut_words, source_label, run_name)

    try:
        if BGM_VOLUME <= 0:
            return render_with_remotion(props, work_dir, output_path)

        rendered_path = os.path.join(work_dir, "rendered.mp4")
        render_with_remotion(props, work_dir, rendered_path)
    finally:
        shutil.rmtree(os.path.join(VIDEO_PROJECT_DIR, "public", run_name), ignore_errors=True)

    return add_bgm(rendered_path, work_dir, output_path)


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


def build_description(script, article, history=()):
    hashtags = " ".join(f"#{tag}" for tag in ["shorts", *script["hashtags"]])
    sections = [script.get("summary") or script["title"]]

    if script.get("tips"):
        sections.append("✅ 바로 써먹는 법\n" + "\n".join(f"- {tip}" for tip in script["tips"]))

    if script.get("caution"):
        sections.append(f"⚠️ 주의\n{script['caution']}")

    sections.append(f"🔗 원문\n{article['link']}")

    recent = [entry for entry in history if entry.get("video_id")][-3:]

    if recent:
        sections.append(
            "📺 지난 영상\n"
            + "\n".join(f"- {entry['title']}: https://youtu.be/{entry['video_id']}" for entry in reversed(recent))
        )

    sections += ["이 영상의 대본과 음성은 AI로 생성되었습니다.", hashtags]

    return "\n\n".join(sections)


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


def upload_youtube(video_path, script, article, history=()):
    token = youtube_access_token()
    metadata = {
        "snippet": {
            "title": script["title"][:100],
            "description": build_description(script, article, history)[:5000],
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
        result = json.loads(response.read().decode("utf-8"))

    # 심사를 받지 않은 API 프로젝트는 public으로 요청해도 YouTube가 private으로 잠근다.
    return result["id"], result.get("status", {}).get("privacyStatus", UPLOAD_PRIVACY)


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
    parser.add_argument("--link", help="이 기사로 만들기 (이미 만든 기사도 가능, 테스트용)")
    parser.add_argument("--no-upload", action="store_true", help="영상만 만들고 업로드하지 않음")

    return parser.parse_args()


def main():
    args = parse_args()

    history = load_json(SHORTS_HISTORY_FILE, [])
    used_links = {entry["link"] for entry in history}
    issues = [(date, load_issue(date)) for date in recent_issue_dates(args.date)]

    if args.link:
        article = next(
            (
                {**article, "issue_date": date}
                for date, issue in issues
                for article in issue_articles(issue)
                if article["link"] == args.link
            ),
            None,
        )
    else:
        article = pick_article(issues, used_links)

    if not article:
        print(f"{args.date} 기준 최근 {LOOKBACK_DAYS}일 이슈에 영상으로 만들 새 기사가 없습니다.")
        return

    print(f"선택한 기사: [{article['issue_date']}] {article['title']}")

    # 같은 날 여러 편을 만들 수 있게 기사마다 작업 폴더를 나눈다.
    slug = re.sub(r"[^0-9A-Za-z]+", "-", urllib.parse.urlsplit(article["link"]).path + urllib.parse.urlsplit(article["link"]).query)
    work_dir = os.path.join(OUTPUT_DIR, f"{article['issue_date']}_{slug.strip('-')[-24:]}")
    os.makedirs(work_dir, exist_ok=True)

    if args.script:
        script = validate_script(load_json(args.script, {}))
    else:
        script = generate_script(article)

    save_json(os.path.join(work_dir, "script.json"), script)
    print(f"대본 생성 완료: {script['title']} (컷 {len(script['cuts'])}개)")

    # 영상마다 목소리를 번갈아 쓴다.
    voice = GEMINI_TTS_VOICES[len(history) % len(GEMINI_TTS_VOICES)]
    narration_path, cut_words, voice = synthesize_narration(script["cuts"], work_dir, voice)
    print("음성 생성 완료")

    source_label = f"출처: {article.get('company')} · {urllib.parse.urlsplit(article['link']).netloc}"
    video_path = build_video(
        script, narration_path, cut_words, source_label, work_dir, os.path.join(work_dir, "short.mp4")
    )
    print(f"영상 생성 완료: {video_path}")

    video_id = None
    can_upload = YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN

    if args.no_upload:
        print("--no-upload: 업로드를 건너뜁니다.")
    elif not can_upload:
        print("YouTube 인증 정보가 없어 업로드를 건너뜁니다.")
    else:
        video_id, privacy = upload_youtube(video_path, script, article, history)
        print(f"업로드 완료 ({privacy}): https://youtu.be/{video_id}")

        if privacy == "public":
            headline = f"[{CHANNEL_NAME}] 새 Shorts 공개 업로드"
        else:
            headline = f"[{CHANNEL_NAME}] 새 Shorts 업로드 ({privacy}) — Studio에서 공개로 바꿔주세요"

        notify_slack(
            f"{headline}\n*{script['title']}*\nhttps://youtu.be/{video_id}\n"
            f"https://studio.youtube.com/video/{video_id}/edit\n원문: {article['link']}"
        )

    # 업로드하지 않은 로컬 테스트는 이력에 남기지 않는다. 같은 기사로 다시 만들 수 있게.
    if video_id:
        history.append(
            {
                "date": article["issue_date"],
                "link": article["link"],
                "title": script["title"],
                "video_id": video_id,
                "voice": voice,
            }
        )
        save_json(SHORTS_HISTORY_FILE, history)


if __name__ == "__main__":
    main()
