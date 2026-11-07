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
# 쓰는 목소리 (쉼표로 여러 개 넣으면 영상마다 번갈아 쓴다). 기본은 여성 목소리 Leda 하나로 고정.
GEMINI_TTS_VOICES = [
    voice.strip()
    for voice in os.environ.get("SHORTS_GEMINI_VOICES", "Leda").split(",")
    if voice.strip()
]
WHISPER_MODEL = os.environ.get("SHORTS_WHISPER_MODEL", "small")
# Gemini TTS가 실패하면(키 없음, 무료 한도 초과 등) 쓰는 대체 음성. 기본 목소리와 맞춰 여성 음성.
TTS_VOICE = os.environ.get("SHORTS_VOICE", "ko-KR-SunHiNeural")
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
# 업로드 후 썸네일(1080x1920)을 만들어 적용한다. 0이면 끈다.
# 채널에 맞춤 썸네일 권한(전화번호 인증)이 있어야 한다. 없으면 403 forbidden.
# itgony 채널은 2026-11-07 인증 후 --thumbnail-only 시험으로 적용 확인.
THUMBNAIL_ENABLED = os.environ.get("SHORTS_THUMBNAIL") != "0"
# video/src/Thumbnail.tsx의 THUMBNAIL_FRAME과 같은 값 (그림이 다 그려진 시점)
THUMBNAIL_FRAME = 90
# 일괄 적용 한 번에 넣을 최대 개수 (새 영상 썸네일 몫을 남긴다)
THUMBNAIL_BATCH_LIMIT = int(os.environ.get("SHORTS_THUMBNAIL_BATCH_LIMIT", "5"))
# 썸네일 그림으로 쓸 그래픽 우선순위
THUMBNAIL_VISUALS = ["metaphor", "number", "compare", "flow", "keywords"]
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
   이어서 짧은 "약속" 한 컷: 이 영상에서 알게 될 것을 한 줄로 말해 끝까지 볼 이유를 준다.
   (예: "어떻게 줄였는지 / 30초면 돼요.", "왜 위험한지 / 바로 볼게요.")
3. 중간 4~5컷: 공간·역할 비유로 구조를 설명한다.
   - 복잡한 구조를 건물·사무실·주방 같은 공간과 사람의 역할로 바꾼다.
     예: "위층 소장실(상주 대장)이 일을 나누고, 아래층 인력사무소(비상주 일꾼)가 필요할 때만 와서 처리"
   - 비유는 영상 하나에 하나만 골라 끝까지 일관되게 쓴다. 비유와 실제 기술을 꼭 짝지어 말한다.
   - 비유가 사실을 왜곡하면 안 된다. 비유로 설명하기 어려운 내용이면 억지로 쓰지 말고 flow나 compare로 설명한다.
4. 수치 2~3컷: 기사에 있는 정량적 수치와 동작 방식(무엇이 무엇을 대신하는지, 몇 단계인지)을 구체적으로.
   변화는 "줄었다"·"늘었다"로 뭉뚱그리지 말고 기사에 전후 숫자가 있으면 "처음엔 A, 지금은 B"로 말한다.
5. 끝에서 두 번째 컷: 시청자가 이번 주에 할 행동을 뼈 때리는 한 마디로. (예: "청구서 보기 전에 / 구조부터 / 뜯어보세요.")
6. 마지막 컷: 다음 영상으로 잇는 짧은 한 줄(12자 안팎). 매번 같은 문장을 쓰지 말고 주제에 맞게 바꾼다.
   (예: "이런 소식, / 매일 올려요.", "AI 뉴스는 / 3시간마다 와요.")

사실 규칙 (가장 중요):
- 숫자, 회사명, 결과, 동작 방식은 반드시 주어진 기사에 있는 것만. 없는 사실·수치를 지어내지 않는다.
- 위 예시의 수치나 상황을 그대로 가져오지 않는다. 기사에 수치가 없으면 숫자 대신 구체적인 동작 방식으로 말한다.
- 기사가 말하지 않은 인과관계·효과를 덧붙이지 않는다. (예: 기사에 없는 "생산성 향상", "보안 강화" 금지)
- 확실하지 않거나 기사에서 조건이 붙은 내용은 조건까지 같이 말한다. ("~한 경우", "~ 기준")
- 기사에 없는 내용은 말하지 않고 그냥 넘어간다. "기사에 없어요", "자료엔 안 나와요"처럼 대본 밖 사정을 말하지 않는다.

emphasis: 그 컷에서 화면 자막 색을 바꿀 핵심 단어 0~2개. line에 그대로 들어 있는 어절이어야 한다. 숫자는 꼭 강조한다.

visual: 컷마다 화면 가운데에 띄울 그래픽 하나. 같은 type을 연달아 3번 이상 쓰지 않는다.
- hook: 1컷 전용. 1컷 동안은 cover(제목)가 화면 가운데에 크게 나오므로 이 그래픽은 화면에 그리지 않는다. 1컷 visual은 hook으로 둔다.
- metaphor: 공간·역할 비유를 입체 사물 그림(아이소메트릭)으로 보여준다. 그림이 있으면 시청자가 넘기지 않고 보므로,
  비유를 꺼내는 컷에 꼭 1번, 구조가 바뀌는 지점에 한 번 더 써도 된다.
  rooms에 핵심부터 2~3개(가로로 나란히 놓인다). place는 비유 이름(8자 이내, 예: "내 주방"), actual은 그것이 뜻하는 실제 기술(12자 이내, 예: "자체 호스팅 GLM").
  icon은 그 실제 기술을 가장 직관적으로 보여줄 사물 하나: {icons}.
  (서버·모델=server, GPU·칩=gpu, 클라우드·외부 서비스=cloud, 데이터=database, AI 에이전트·봇=robot, 사용자·직원=person,
   앱·개발 도구=laptop, 문서·코드·정책=document, 비용·돈=coins, 외부 호출·배달·전송=truck, 보안·권한=lock, 회사·조직=building)
  label은 비유 이름(10자 이내, 예: "배달 vs 내 주방"), 없으면 비워둔다.
- number: 숫자 하나 카운트업. value에 숫자+단위, label에 무엇의 숫자인지 짧게.
- compare: 2~4개 값을 막대로 비교. bars에 label, value(숫자), display(단위 포함, 예: "10배", "90%"). 기사에 실제 수치가 2개 이상 있을 때만.
- flow: 과정이나 단계 2~4개. items에 단계별 10자 이내 명사구 ("끊고" 같은 동사 조각 금지).
- keywords: 핵심 단어 2~3개 카드. items에 단어별 8자 이내. "=", "vs" 같은 기호만 있는 항목 금지.
- code: 개발자용 코드·명령어 5줄 이내. 기사 내용과 직접 관련 있을 때만.
- question: 질문 카드. label은 line을 그대로 옮기지 말고 12자 이내로 더 짧게.
- none: 그래픽 없이 자막만 크게. 흐름상 쉬어가는 컷에만.
visual의 숫자와 사실도 기사에 있는 것만 쓴다.

cover: 이 영상의 훅이자 썸네일. 1컷 동안 화면 가운데에 크게 나왔다가 위로 줄어들어 영상 내내 고정된다.
  기사에서 가장 센 구체적 결과(숫자가 있으면 숫자 포함)를 담는다. 숫자가 든 어절은 자동으로 골드로 강조된다.
  2줄, 줄 사이에 \\n, 줄당 10자 이내. 예: "API 끊고\\nAI 비용 90%↓", "Cursor 확장\\n백도어 주의".
title은 40자 이내, 해시태그 없이. 사람들이 실제로 검색할 말(회사명·제품명·기술명)을 앞쪽에 넣고 핵심 결과를 붙인다.
  예: "Revolut 자체 호스팅 GLM, AI 비용 90% 절감" (O) / "AI 비용 이렇게 줄인다고?" (X, 검색어가 없음)
question: 이 영상이 답하는 질문 한 줄(30자 이내). 설명란 첫 줄에 들어간다. 예: "Revolut은 어떻게 AI 비용을 90% 줄였나?"
hashtags는 # 없이 3~5개.
더보기란용: summary는 무슨 일인지 1~2문장. tips는 시청자가 바로 써먹을 행동 1~3개(명령어·설정이 있으면 그대로). caution은 비용·보안·개인정보 주의점 한 줄, 없으면 빈 문자열."""


# video/src/Isometric.tsx의 ICONS와 같은 목록 (비유 그림에 올리는 사물)
ICONS = [
    "server", "gpu", "cloud", "database", "robot", "person",
    "laptop", "document", "coins", "truck", "lock", "building",
]

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
                    "icon": {"type": "string", "enum": ICONS},
                },
                "required": ["place", "actual", "icon"],
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
        "question": {"type": "string"},
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
    "required": ["title", "question", "cover", "summary", "tips", "caution", "hashtags", "cuts"],
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
        SCRIPT_SYSTEM_PROMPT.format(channel=CHANNEL_NAME, icons=", ".join(ICONS)),
        build_script_prompt(article),
        SCRIPT_SCHEMA,
    )

    return validate_script(script)


# 화면·제목·설명란에서 지울 글자: 깨진 글자, 제어 문자, 보이지 않는 문자(폭 없는 공백, 방향 표시, BOM, 소프트 하이픈)
UNWANTED_CHARS = re.compile("[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f\u2060\ufeff\u00ad]")


def clean_text(value):
    """모델 출력에 가끔 섞이는 깨진 글자·제어 문자·보이지 않는 문자를 지운다. 화면에 깨진 글자로 보이는 것을 막는다."""
    if isinstance(value, str):
        return UNWANTED_CHARS.sub("", value)

    if isinstance(value, list):
        return [clean_text(item) for item in value]

    if isinstance(value, dict):
        return {key: clean_text(item) for key, item in value.items()}

    return value


def validate_script(script):
    script = clean_text(script)
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
    script["question"] = (script.get("question") or "").strip()
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

    props_cuts = []

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

    return {
        "channel": CHANNEL_NAME,
        "theme": SHORTS_THEME,
        "cover": script["cover"],
        "source": source_label,
        "audio": f"{run_name}/narration.mp3",
        "durationInFrames": total_frames,
        "cuts": props_cuts,
        "sfx": pick_sfx(cuts, starts),
    }


def pick_sfx(cuts, starts):
    """효과음은 꼭 필요한 순간에만: 첫 컷(훅)의 임팩트, 비유 건물이 처음 나올 때의 휙 소리.

    컷마다 소리를 넣으면 화면이 넘어갈 때마다 소리가 나서 거슬린다.
    """
    sfx = [{"src": "sfx/impact.wav", "from": 0, "volume": 0.5}]
    metaphor = next((index for index, cut in enumerate(cuts) if index > 0 and cut["visual"]["type"] == "metaphor"), None)

    if metaphor is not None:
        sfx.append({"src": "sfx/whoosh1.wav", "from": max(starts[metaphor] - 3, 0), "volume": 0.25})

    return sfx


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


def pick_thumbnail_visual(cuts):
    """썸네일에 넣을 대표 그래픽 하나: 비유 그림 → 숫자 → 비교 → 흐름 → 키워드 순. 없으면 None(제목만)."""
    for kind in THUMBNAIL_VISUALS:
        for cut in cuts[1:]:
            if cut["visual"]["type"] == kind:
                return cut["visual"]

    return None


def render_thumbnail(script, work_dir):
    """제목(cover) + 대표 그래픽으로 썸네일 PNG를 만든다."""
    npx = shutil.which("npx")
    props = {
        "channel": CHANNEL_NAME,
        "theme": SHORTS_THEME,
        "cover": script["cover"],
        # 그림이 없어도 null로 넘긴다(빼면 Remotion이 기본 예시 그림을 넣는다).
        "visual": pick_thumbnail_visual(script["cuts"]),
    }

    props_path = os.path.abspath(os.path.join(work_dir, "thumbnail-props.json"))
    output_path = os.path.abspath(os.path.join(work_dir, "thumbnail.png"))
    save_json(props_path, props)

    result = subprocess.run(
        [
            npx, "remotion", "still", "src/index.ts", "Thumbnail", output_path,
            f"--frame={THUMBNAIL_FRAME}", f"--props={props_path}", "--log=error",
        ],
        cwd=VIDEO_PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"썸네일 렌더링 실패: {(result.stderr or result.stdout).strip()[-1000:]}")

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


# ---------------------------------------------------------------------------
# 업로드 전 자동 검수
# ---------------------------------------------------------------------------

QA_SIZE = (1080, 1920)
QA_FPS = 30
QA_MIN_SECONDS = 15
QA_MAX_SECONDS = 75
# 이보다 긴 무음 구간이 있으면 음성이 끊긴 것으로 본다(배경음이 깔려 있어 정상 영상엔 없음).
QA_MAX_SILENCE_SECONDS = 2.5
# 최대 음량이 이보다 크면 소리가 찢어질 수 있다(loudnorm 상한 -1.5dB).
QA_MAX_PEAK_DB = -0.5
# 평균 음량이 이보다 작으면 사실상 소리가 안 들린다.
QA_MIN_MEAN_DB = -35.0


def probe_video(path):
    """ffmpeg 한 번으로 해상도·fps·길이·소리 유무·음량·무음 구간을 읽는다."""
    result = subprocess.run(
        [
            ffmpeg_exe(), "-hide_banner", "-i", path,
            "-af", f"silencedetect=noise=-45dB:d={QA_MAX_SILENCE_SECONDS},volumedetect",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    return parse_probe(result.stderr)


def parse_probe(stderr):
    report = {"width": None, "height": None, "fps": None, "duration": None,
              "has_audio": False, "max_volume": None, "mean_volume": None, "silences": []}

    duration = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", stderr)

    if duration:
        hours, minutes, seconds = duration.groups()
        report["duration"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    video = re.search(r"Stream #\S+.*Video:.*?, (\d{2,5})x(\d{2,5})", stderr)

    if video:
        report["width"], report["height"] = int(video.group(1)), int(video.group(2))

    fps = re.search(r"Video:.*?([\d.]+) fps", stderr)

    if fps:
        report["fps"] = float(fps.group(1))

    report["has_audio"] = re.search(r"Stream #\S+.*Audio:", stderr) is not None

    for key in ("max_volume", "mean_volume"):
        match = re.search(rf"{key}: (-?[\d.]+) dB", stderr)

        if match:
            report[key] = float(match.group(1))

    report["silences"] = [float(value) for value in re.findall(r"silence_duration: ([\d.]+)", stderr)]

    return report


def find_video_problems(report, texts=()):
    """검수 기준에 안 맞는 항목을 사람이 읽을 수 있는 문장으로 돌려준다. 빈 목록이면 통과."""
    problems = []

    if (report["width"], report["height"]) != QA_SIZE:
        problems.append(f"해상도가 {report['width']}x{report['height']}입니다 (기대: 1080x1920)")

    if report["fps"] is None or abs(report["fps"] - QA_FPS) > 0.5:
        problems.append(f"fps가 {report['fps']}입니다 (기대: {QA_FPS})")

    if report["duration"] is None or not QA_MIN_SECONDS <= report["duration"] <= QA_MAX_SECONDS:
        problems.append(f"길이가 {report['duration']}초입니다 (기대: {QA_MIN_SECONDS}~{QA_MAX_SECONDS}초)")

    if not report["has_audio"]:
        problems.append("소리 트랙이 없습니다")
    else:
        if report["max_volume"] is not None and report["max_volume"] > QA_MAX_PEAK_DB:
            problems.append(f"최대 음량이 {report['max_volume']}dB라 소리가 찢어질 수 있습니다")

        if report["mean_volume"] is None or report["mean_volume"] < QA_MIN_MEAN_DB:
            problems.append(f"평균 음량이 {report['mean_volume']}dB라 너무 작습니다")

        long_silences = [s for s in report["silences"] if s > QA_MAX_SILENCE_SECONDS]

        if long_silences:
            problems.append(f"{QA_MAX_SILENCE_SECONDS}초 넘는 무음 구간이 {len(long_silences)}곳 있습니다")

    for label, text in texts:
        if UNWANTED_CHARS.search(text or ""):
            problems.append(f"{label}에 깨진 글자나 보이지 않는 문자가 있습니다")

    return problems


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
            "loudnorm=I=-14:TP=-1.5:LRA=11,"
            # loudnorm 한 번만으로는 순간 최대 음량이 0dB 가까이 튈 수 있어서 -1.5dB에서 한 번 더 눌러준다.
            "alimiter=limit=0.84:level=disabled[out]",
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
    # 첫 줄은 검색 결과·미리보기에 보이는 줄이라 "이 영상이 답하는 질문"을 둔다.
    sections = [script["question"]] if script.get("question") else []
    sections.append(script.get("summary") or script["title"])

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

    return clean_text("\n\n".join(sections))


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


def wait_until_processed(video_id, token, attempts=10, interval=30):
    """쇼츠 썸네일은 영상 처리가 끝난 뒤에 넣어야 적용된다. 처리 상태를 확인한다(호출당 1유닛)."""
    import time

    for _ in range(attempts):
        request = urllib.request.Request(
            f"https://www.googleapis.com/youtube/v3/videos?part=processingDetails&id={video_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            items = json.loads(response.read().decode("utf-8")).get("items") or []

        status = (items[0].get("processingDetails") or {}).get("processingStatus") if items else None

        if status == "succeeded":
            return True

        if status in ("failed", "terminated"):
            return False

        time.sleep(interval)

    return False


def set_youtube_thumbnail(video_id, image_path):
    """업로드한 쇼츠에 썸네일을 적용한다(50유닛). 실패해도 영상은 그대로 두고 이유만 돌려준다.

    돌려주는 값: None이면 성공, 문자열이면 실패 이유.
    """
    token = youtube_access_token()

    if not wait_until_processed(video_id, token):
        return "영상 처리가 끝나지 않아 썸네일을 넣지 못했습니다"

    with open(image_path, "rb") as file:
        data = file.read()

    request = urllib.request.Request(
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}&uploadType=media",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png", "Content-Length": str(len(data))},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120):
            return None
    except urllib.error.HTTPError as error:
        return f"{error.code} {youtube_error_reason(error)}"


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
    parser.add_argument(
        "--thumbnail-batch",
        metavar="FILE",
        help="[{video_id, title, script}] 목록 파일로 이미 올린 영상들에 썸네일을 한꺼번에 적용",
    )
    parser.add_argument(
        "--thumbnail-only",
        metavar="VIDEO_ID",
        help="영상은 만들지 않고, --script 대본으로 썸네일만 만들어 이미 올린 영상에 적용",
    )

    return parser.parse_args()


def title_cover(title, width=9):
    """cover가 없는 예전 대본용: 제목을 한 줄 9자 안팎으로 끊어 최대 4줄로 만든다."""
    words = re.sub(r"[?!]+$", "", title).split()
    lines, current = [], ""

    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()

    if current:
        lines.append(current)

    return "\n".join(lines[:4])


def thumbnail_script(entry):
    """일괄 적용용 대본 정리. 예전 형식(장면 scenes)이라 검증이 안 되면 제목만 쓰는 썸네일로."""
    try:
        script = validate_script(entry["script"])
    except (ValueError, KeyError):
        script = {"title": entry["title"], "cover": "", "cuts": []}

    if not script.get("cover") or script["cover"] == script.get("title"):
        script["cover"] = title_cover(entry["title"])

    return script


def apply_thumbnail_batch(path):
    """이미 올린 영상들에 썸네일을 적용한다. 할당량이 떨어지면 멈추고, 다시 실행하면 남은 것부터 한다."""
    entries = load_json(path, [])
    done_path = os.path.join(OUTPUT_DIR, "thumbnail_batch_done.json")
    done = set(load_json(done_path, []))
    applied, failed = [], []

    for entry in entries:
        video_id = entry["video_id"]

        if video_id in done:
            continue

        # 썸네일 업로드 횟수 제한(대략 하루 10개 안팎)이 있어서, 새 영상 몫을 남기고 한 번에 조금씩만.
        if len(applied) >= THUMBNAIL_BATCH_LIMIT:
            break

        work_dir = os.path.join(OUTPUT_DIR, f"thumbnail_{video_id}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            problem = set_youtube_thumbnail(video_id, render_thumbnail(thumbnail_script(entry), work_dir))
        except Exception as error:
            problem = str(error)

        if problem is None:
            applied.append(video_id)
            done.add(video_id)
            save_json(done_path, sorted(done))
            print(f"적용: {video_id} {entry['title']}")
            continue

        failed.append((video_id, problem))
        print(f"실패: {video_id} {entry['title']} - {problem}")

        if "quota" in problem.lower() or problem.startswith("429"):
            print("YouTube 한도(썸네일 업로드 횟수 또는 API 할당량)에 걸려 멈춥니다. 나중에 남은 것만 다시 실행하세요.")
            break

    print(f"\n완료 {len(applied)}개, 실패 {len(failed)}개, 남은 것 {len(entries) - len(done)}개")


def main():
    args = parse_args()

    if args.thumbnail_batch:
        apply_thumbnail_batch(args.thumbnail_batch)
        return

    if args.thumbnail_only:
        if not args.script:
            raise SystemExit("--thumbnail-only에는 --script 대본 파일이 필요합니다.")

        work_dir = os.path.join(OUTPUT_DIR, f"thumbnail_{args.thumbnail_only}")
        os.makedirs(work_dir, exist_ok=True)
        image = render_thumbnail(validate_script(load_json(args.script, {})), work_dir)
        print(f"썸네일 생성 완료: {image}")
        problem = set_youtube_thumbnail(args.thumbnail_only, image)

        if problem:
            raise SystemExit(f"썸네일 적용 실패: {problem}")

        print(f"썸네일 적용 완료: https://youtu.be/{args.thumbnail_only}")
        return

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

    report = probe_video(video_path)
    problems = find_video_problems(
        report,
        [("제목", script["title"]), ("설명란", build_description(script, article, history)),
         ("자막", " ".join(cut["line"] for cut in script["cuts"]))],
    )
    save_json(os.path.join(work_dir, "qa.json"), {"report": report, "problems": problems})

    if problems:
        print("검수 실패:\n- " + "\n- ".join(problems))
    else:
        print(f"검수 통과: {report['width']}x{report['height']}, {report['fps']}fps, {report['duration']:.1f}초, "
              f"평균 {report['mean_volume']}dB / 최대 {report['max_volume']}dB")

    video_id = None
    can_upload = YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN

    if args.no_upload:
        print("--no-upload: 업로드를 건너뜁니다.")
    elif problems:
        # 이상한 영상은 올리지 않는다. 기록에 남기지 않으므로 다음 실행에서 같은 기사로 다시 만든다.
        notify_slack(
            f"[{CHANNEL_NAME}] Shorts 업로드 보류 (검수 실패)\n*{script['title']}*\n"
            + "\n".join(f"- {problem}" for problem in problems)
            + f"\n원문: {article['link']}"
        )
        raise SystemExit("검수 실패로 업로드하지 않았습니다.")
    elif not can_upload:
        print("YouTube 인증 정보가 없어 업로드를 건너뜁니다.")
    else:
        video_id, privacy = upload_youtube(video_path, script, article, history)
        print(f"업로드 완료 ({privacy}): https://youtu.be/{video_id}")

        thumbnail_note = ""

        if THUMBNAIL_ENABLED:
            # 썸네일은 덤이다: 실패해도 업로드는 성공으로 두고 이유만 알린다.
            try:
                problem = set_youtube_thumbnail(video_id, render_thumbnail(script, work_dir))
            except Exception as error:
                problem = str(error)

            thumbnail_note = "\n썸네일: 적용 완료" if problem is None else f"\n썸네일 적용 실패: {problem}"
            print(thumbnail_note.strip())

        if privacy == "public":
            headline = f"[{CHANNEL_NAME}] 새 Shorts 공개 업로드"
        else:
            headline = f"[{CHANNEL_NAME}] 새 Shorts 업로드 ({privacy}) — Studio에서 공개로 바꿔주세요"

        notify_slack(
            f"{headline}\n*{script['title']}*\nhttps://youtu.be/{video_id}\n"
            f"https://studio.youtube.com/video/{video_id}/edit\n원문: {article['link']}{thumbnail_note}"
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
