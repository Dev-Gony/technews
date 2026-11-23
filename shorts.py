"""GONY DAILY 이슈에서 AI 기사 1개를 골라 YouTube Shorts 영상으로 만든다.

흐름: 이슈 JSON → 기사 선택 → Claude 대본 → TTS 음성 → 장면 이미지 → ffmpeg 합성 → YouTube 업로드
"""

import os
import re
import json
import math
import hashlib
import shutil
import asyncio
import argparse
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

# 비우면 구독 플랜의 기본 모델을 쓴다. 예: opus, sonnet
# 대본 단계(취재·후보·심사·검증)에 쓸 모델. 품질을 위해 기본은 opus, 비우면 구독 플랜 기본 모델.
CLAUDE_MODEL = os.environ.get("SHORTS_CLAUDE_MODEL", "opus").strip()
# 대본 후보 작성용 모델. 후보 3개가 사용량 대부분이라 가벼운 sonnet으로 쓰고, 심사·검증만 CLAUDE_MODEL(opus).
# (쇼츠 대본은 사람이 쓰는 대화와 같은 구독 사용량 한도를 나눠 쓴다)
CANDIDATE_MODEL = os.environ.get("SHORTS_CANDIDATE_MODEL", "sonnet").strip()
# Claude가 사용량 한도 등으로 대본을 못 쓰면 무료 Gemini로 대신 쓴다.
GEMINI_SCRIPT_MODEL = os.environ.get("SHORTS_GEMINI_SCRIPT_MODEL", "gemini-3.1-flash-lite")
# 대본 작성자: claude(기본) / gemini(시험용으로 예비 경로를 바로 쓴다)
SCRIPT_WRITER = os.environ.get("SHORTS_SCRIPT_WRITER") or "claude"
# 대본 후보 수. 1이면 예전처럼 한 번에 쓰고 심사 단계를 건너뛴다.
SCRIPT_CANDIDATES = int(os.environ.get("SHORTS_SCRIPT_CANDIDATES", "3"))
# 원문 본문을 대본 재료로 넣을 최대 글자 수
SOURCE_MAX_CHARS = 14000
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
# 공개 시각 (KST, 시). GitHub 예약 실행은 몇 시간씩 늦게 시작되기도 해서, 영상은 미리 만들어
# 비공개로 올리고 YouTube 예약 공개(publishAt)로 이 시각에 정확히 공개한다. 비우면 올리자마자 공개.
PUBLISH_SLOTS = [
    int(hour) for hour in os.environ.get("SHORTS_PUBLISH_SLOTS", "18").split(",") if hour.strip()
]
# 업로드·처리 시간을 감안해 지금부터 최소 이만큼 뒤의 시각에만 예약한다 (분).
PUBLISH_LEAD_MINUTES = 20
CHANNEL_NAME = os.environ.get("SHORTS_CHANNEL_NAME", "itgony")
# 영상 배경: ink(먹색, 프로필 사진과 같은 톤) / paper(종이색, 배너·카드뉴스와 같은 톤)
SHORTS_THEME = os.environ.get("SHORTS_THEME") or "ink"
# 화면 스타일: auto(대본이 기사마다 news/explain 중 고름, 기본) / news(크림 잡지) / explain(남색 다크 + 코드 창)
# / classic(예전 먹색·3D 화면). news/explain에서는 3D 장면을 쓰지 않는다.
SHORTS_STYLE = (os.environ.get("SHORTS_STYLE") or "auto").strip().lower()
EDITORIAL_STYLES = ("news", "explain")
# 배경: glow(장면마다 옮겨 가는 빛) / type(빛 + 장면 핵심어 윤곽 글자) / 3D 장면(아래 SCENE3D_FILES)
SHORTS_BACKDROP = os.environ.get("SHORTS_BACKDROP") or "glow"
# 3D 장면(video/public/assets3d/*_loop.webm, 사용자 PC에서 Blender로 미리 렌더링)은 배경이 아니라
# 설명 컷의 그림(visual type "scene3d")으로 쓴다. 1이면 예전처럼 배경에도 깐다.
DESK3D_AUTO = os.environ.get("SHORTS_DESK3D") == "1"
# 3D 장면 이름 → 루프 파일. 파일이 저장소에 없으면 그 장면은 고르지 않는다.
SCENE3D_FILES = {
    "vault3d": "vault_world_loop.webm",  # 살짝 열린 금고, 방패, 자물쇠
    "law3d": "law_world_loop.webm",  # 법원 건물, 의사봉, 도장
    "coins3d": "coins_world_loop.webm",  # 저울, 동전 탑, 긴 영수증
    "server3d": "server_world_loop.webm",  # 서버 랙, 케이블 빛 줄기, 구름, 속도계
    "chip3d": "chip_world_loop.webm",  # 큰 칩, 회로 선, 웨이퍼, 냉각 팬
    "robot3d": "robot_world_loop.webm",  # 손 흔드는 로봇, 둥근 길을 도는 자율주행차, 드론
    "lab3d": "lab_world_loop.webm",  # 점수판, 시상대, 실험대
    "math3d": "math_world_loop.webm",  # 칠판 식과 곡선, 도는 도형, 원을 그리는 컴퍼스
    "data3d": "data_world_loop.webm",  # DB 원통, 표에서 골라지는 행, 원그래프
    "media3d": "media_world_loop.webm",  # 이젤 그림, 슬레이트, 캠코더, 떠 있는 사진
    "game3d": "game_world_loop.webm",  # 큰 게임 패드, 픽셀 하트, 아케이드 조이스틱, 픽셀 동전
    "voice3d": "voice_world_loop.webm",  # 스튜디오 마이크, 음파 막대, 헤드폰, 음표
    "search3d": "search_world_loop.webm",  # 큰 검색창, 결과 카드를 훑는 돋보기, 책 더미
    "invest3d": "invest_world_loop.webm",  # 빌딩 3채, 치솟는 빨간 화살표, 돈 자루, 지폐 다발
    "web3d": "web_world_loop.webm",
    "chat3d": "chat_world_loop.webm",  # 열리는 편지 봉투, 말풍선, 도는 종이비행기  # 떠 있는 브라우저 창, 지구본, 버튼 누르는 화살표
    "deploy3d": "deploy_world_loop.webm",
    "terminal3d": "terminal_world_loop.webm",  # 터미널 창과 프롬프트, 맞물린 톱니바퀴, 폴더  # 빌드 톱니 → 검사 터널 → 체크 깃발 컨베이어, 신호등
    "lang3d": "lang_world_loop.webm",  # '</>' 조형물, 코드 블록을 0·1 로 바꾸는 컴파일러 기계
    "repo3d": "repo_world_loop.webm",  # 깃 가지 그래프, 열린 패키지 상자, 금색 별
    "desk3d": "desk_world_loop.webm",  # 노트북 앞 꼬마 에이전트들, 토큰 동전 탑
    # '업무', '팀'처럼 넓은 말이 많아 책상(코딩 도구) 뒤
    "work3d": "work_world_loop.webm",  # 칸반 보드, 벽시계, 김 나는 커피와 달력
    # '앱'은 데스크톱 앱에도 쓰는 말이라 책상(코딩 도구) 뒤
    "phone3d": "phone_world_loop.webm",  # 큰 스마트폰과 앱 아이콘, 태블릿, 알림 종
    # 출시·공개는 다른 주제와 자주 겹치는 넓은 말이라 맨 뒤(점수가 같으면 더 구체적인 장면이 이긴다)
    "launch3d": "launch_world_loop.webm",  # 발사대 위 로켓, 카운트다운, 선물 상자
    # AI 모델·챗봇 일반: 다른 장면이 하나도 안 맞을 때의 마지막 선택지
    "ai3d": "ai_world_loop.webm",  # 신경망 조형물, 금색 반짝이, 'AI' 말풍선
}
# 장면마다 어울리는 주제어. 영문·숫자는 단어 경계로만 찾고(예: 'ide'가 'video'에 걸리지 않게),
# 한글은 그대로 찾는다. 're:'로 시작하면 정규식(예: 'MaxxBench'의 bench).
# 지난 영상 제목으로 확인한 배정은 tests/test_shorts.py test_pick_backdrop_past_titles 참고.
SCENE3D_KEYWORDS = {
    "vault3d": [
        "보안", "백도어", "backdoor", "해킹", "해커", "취약점", "vulnerability", "cve", "제로데이", "zero-day",
        "유출", "탈취", "뚫", "악성", "malware", "멀웨어", "랜섬웨어", "피싱", "phishing", "공급망 공격", "공격", "익스플로잇", "exploit",
        "인증", "2fa", "mfa", "otp", "비밀번호", "패스워드", "password", "dmarc", "spf", "dkim", "스푸핑", "스팸",
        "위협", "권한 상승", "시크릿", "api 키", "토큰 점검", "암호화", "개인정보", "프라이버시", "privacy",
        "외부 사이트", "외부로", "외부 전송", "인젝션", "injection", "security",
        "인증서", "certificate", "암호", "post-quantum", "양자내성", "스파이웨어", "spyware", "안티바이러스", "antivirus", "tls", "ssl",
    ],
    "coins3d": [
        "비용", "요금", "사용료", "가격", "청구서", "과금", "수수료", "구독료", "예산", "지출", "원가",
        "절감", "절약", "인하", "할인", "낭비", "손해", "토큰값", "토큰 값", "비싸", "저렴", "가성비",
        "cost", "costs", "price", "pricing", "billing",
    ],
    "server3d": [
        "서버", "server", "servers", "클라우드", "cloud", "ec2", "aws", "gcp", "azure", "데이터센터", "인프라",
        "메모리", "ram", "지연", "레이턴시", "latency", "처리량", "throughput", "캐시", "cdn",
        "스케일업", "스케일 아웃", "오토스케일", "용량", "쿠버네티스", "kubernetes", "k8s", "컨테이너", "도커", "docker",
        "트래픽", "장애", "다운타임", "분산", "네트워크", "배 성능", "배 빨라", "배 빠른",
        "dns", "serverless", "서버리스", "api gateway", "wireguard", "vpn", "터널", "스토리지", "storage",
    ],
    "lab3d": [
        "벤치마크", "벤치", "benchmark", r"re:[a-z0-9-]*bench(?![a-z])", "리더보드", "leaderboard", "sota", "mmlu",
        "가중치", "weights", "오픈 웨이트", "파라미터", "학습", "훈련", "training", "파인튜닝", "fine-tuning",
        "연구", "research", "논문", "arxiv", "안전성", "안전 연구", "정렬", "alignment", "평가", "eval", "evals",
        "점수", "정확도", "accuracy",
    ],
    # '법'만으로는 고르지 않는다 ('~하는 법', '방법'), '정책'도 너무 넓다
    "law3d": [
        "법원", "판결", "판사", "소송", "고소", "제소", "재판", "규제", "법안", "입법", "법률", "위법", "불법", "합법",
        "저작권", "copyright", "특허", "patent", "라이선스", "license", "약관", "반독점", "독점", "antitrust", "공정위", "ftc",
        "gdpr", "ai act", "ai 기본법", "의회", "국회", "벌금", "과징금", "제재", "변호사", "lawsuit", "court", "regulation",
    ],
    "chip3d": [
        "칩", "반도체", "웨이퍼", "파운드리", "tsmc", "nvidia", "엔비디아", "gpu", "gpus", "npu", "tpu", "cpu", "프로세서", "processor",
        "실리콘", "silicon", "하드웨어", "hardware", "amd", "intel", "인텔", "퀄컴", "qualcomm", "hbm", "asic", "fpga",
        "블랙웰", "blackwell", "b200", "h100", "h200", "라즈베리 파이", "raspberry pi", "m5", "m6",
    ],
    "phone3d": [
        "모바일", "mobile", "앱", "ios", "android", "안드로이드", "아이폰", "iphone", "갤럭시", "galaxy",
        "스마트폰", "휴대폰", "핸드폰", "태블릿", "ipad", "아이패드", "앱스토어", "app store", "플레이스토어", "play store",
        "xcode", "swift", "kotlin", "flutter", "react native", "푸시 알림", "애플워치", "워치", "watchos",
    ],
    "deploy3d": [
        "배포", "deploy", "deployment", "ci", "ci/cd", "파이프라인", "pipeline", "github actions", "테스트", "test", "tests",
        "testing", "빌드", "build", r"re:(?<!스크)롤백", "rollback", "데브옵스", "devops", "sre", "모니터링", "monitoring", "관측성",
        "observability", "온콜", "on-call", "카나리", "canary", "terraform", "테라폼", "helm", "gitops", "릴리스 파이프라인",
    ],
    "media3d": [
        # 제목 끝 '[영상]', '[동영상]'은 발표 영상 링크 표시라 주제가 아니다
        "이미지", "image", "images", r"re:(?<![\[동])영상(?!\])", r"re:(?<!\[)동영상(?!\])", "video", "videos", "사진", "photo", "그림", "디자인",
        "이미지 생성", "영상 생성", "sora", "veo", "midjourney", "미드저니", "stable diffusion", "diffusion", "확산 모델",
        "애니메이션", "animation", "카메라", "영상 편집", "이미지 편집", "유튜브", "youtube", "틱톡", "썸네일", "jpeg", "png", "3d",
    ],
    "search3d": [
        "검색", "search", "검색엔진", "검색 엔진", "구글 검색", "google search", "perplexity", "퍼플렉시티", "rag",
        "색인", "indexing", "추천", "recommendation", "랭킹", "ranking", "seo", "임베딩", "embedding", "벡터 검색", "retrieval",
    ],
    "invest3d": [
        "투자", "invest", "investment", "스타트업", "startup", "상장", "ipo", r"re:인수(?!인계)", "acquisition", "acquire",
        "합병", "m&a", "기업가치", "밸류에이션", "valuation", "펀딩", "funding", "시리즈 a", "시리즈 b", "유니콘",
        "revenue", "arr", "주가", "주식", "나스닥", "nasdaq", "증권", "억 달러", "조 원", "실적", "흑자", "적자", "벤처",
    ],
    "terminal3d": [
        "터미널", "terminal", "cli", "셸", "shell", "bash", "zsh", "명령줄", "커맨드", "command line", "리눅스", "linux",
        "macos", "맥os", "윈도우", "windows", "운영체제", "os", "커널", "kernel", "우분투", "ubuntu", "데비안", "nixos",
        "tmux", "vim", "neovim", "emacs", "dotfiles", "파일 시스템", "filesystem",
    ],
    # '이메일'은 '메일'로 같이 센다 (두 번 세지 않게)
    "chat3d": [
        "메일", "email", "e-mail", "메신저", "messenger", "slack", "슬랙", "텔레그램", "telegram", "카카오톡", "카톡",
        "채팅", "메시지", "message", "messages", "dm", "뉴스레터", "newsletter", "imessage", "whatsapp", "왓츠앱",
    ],
    "voice3d": [
        "음성", "voice", "tts", "stt", "speech", "받아쓰기", "전사", "transcribe", "transcription", "오디오", "audio",
        "팟캐스트", "podcast", "목소리", "음악", "music", "노래", "사운드", "sound", "녹음", "마이크", "더빙", "elevenlabs",
    ],
    "robot3d": [
        "로봇", "robot", "robots", "robotics", "휴머노이드", "humanoid", "자율주행", "self-driving", "waymo", "웨이모",
        "tesla", "테슬라", "드론", "drone", "그리퍼", "자동차", "차량", "운전", "fleet", "물리 ai", "physical ai", "로보택시",
    ],
    "ai3d": [
        "llm", "llms", "챗봇", "chatbot", "chatgpt", "gpt", "claude", "클로드", "gemini", "제미나이", "언어 모델",
        "ai 모델", "모델", "추론", "reasoning", "프롬프트", "prompt", "컨텍스트", "context", "환각", "hallucination",
        "멀티모달", "multimodal", "트랜스포머", "transformer", "openai", "anthropic", "딥시크", "deepseek",
    ],
    # '언어 모델'은 언어(프로그래밍)가 아니다
    "lang3d": [
        "프로그래밍", "programming", r"re:언어(?! ?모델)", "컴파일러", "compiler", "컴파일", "jit", "런타임", "runtime",
        "rust", "python", "파이썬", "golang", "go의", "zig", "ocaml", "haskell", "java", "jdk", "c++", "c#", ".net",
        "webassembly", "wasm", "타입 시스템", "타입 안전", "리팩터링", "refactoring", "함수형", "문법", "syntax", "가비지",
    ],
    "work3d": [
        "일하는 방식", "일자리", "주니어", "시니어", "커리어", "채용", "면접", "이직", "해고", "레이오프", "layoff",
        "조직", "팀", "생산성", "productivity", "자동화", "워크플로", "workflow", "업무", "회의", "기획", "협업",
        "리더십", "매니저", "번아웃", "과부하", "주간보고", "보고서", "jira", "노션", "notion", "n8n", "zapier", "ax",
    ],
    "game3d": [
        "게임", "game", "games", "gaming", "게이밍", "닌텐도", "nintendo", "steam", "스팀", "플레이스테이션", "playstation",
        "ps2", "ps5", "xbox", "에뮬레이터", "emulator", "unity", "언리얼", "unreal", "godot", "콘솔",
    ],
    # '정리'(요약)는 수학이 아니다
    "math3d": [
        "수학", "math", "mathematics", "수학자", "증명", "proof", "알고리즘", "알고리듬", "algorithm", "방정식",
        "미적분", "기하", "확률", "푸리에", "추측", "terence tao", "테렌스 타오",
    ],
    # '분석'만으로는 고르지 않는다 ('~라는 분석' 같은 기사 제목이 많다)
    "data3d": [
        "데이터", "data", "db", "dbms", "데이터베이스", "database", "sql", "nosql", "postgres", "postgresql", "mysql",
        "sqlite", "duckdb", "clickhouse", "bigquery", "snowflake", "databricks", "쿼리", "query", "지표", "metric", "metrics",
        "대시보드", "dashboard", "스프레드시트", "엑셀", "excel", "데이터 분석", "로그 분석", "etl", "벡터 db", "인덱스",
    ],
    "web3d": [
        "웹", "web", "브라우저", "browser", "chrome", "크롬", "safari", "사파리", "firefox", "파이어폭스",
        "사이트", "website", "html", "css", "javascript", "자바스크립트", "typescript", "타입스크립트", "react", "next.js",
        "프런트엔드", "프론트엔드", "frontend", "http", "https", "url", "seo", "웹앱", "pwa", "확장 프로그램",
    ],
    "repo3d": [
        "오픈소스", "오픈 소스", "open source", "open-source", "깃허브", "github", "gitlab", "git", "깃",
        "레포", "repo", "저장소", "라이브러리", "library", "패키지", "package", "npm", "pypi", "crate", "crates",
        "포크", "fork", "커밋", "commit", "브랜치", "branch", "머지", "merge", "pr", "pull request", "풀 리퀘스트", "기여", "메인테이너",
    ],
    "desk3d": [
        "에이전트", "agent", "agents", "agentic",
        "토큰", "token", "tokens",
        "코딩", "coding", "바이브 코딩", "vibe coding", "코드 리뷰", "코드 짜", "코드를 짜",
        "claude code", "클로드 코드", "codex", "코덱스", "copilot", "코파일럿",
        "cursor", "windsurf", "ide", "mcp",
    ],
    "launch3d": [
        r"re:(?<!퇴)출시", "공개", "발표", "런칭", "론칭", "launch", "릴리스", "릴리즈", "release", "정식", "베타", "beta",
        "프리뷰", "preview", "신모델", "새 모델", "신제품", "선보", "데뷔", "generally available", "ga",
    ],
}
# 예전 이름 (책상 장면 주제어)
DESK3D_KEYWORDS = SCENE3D_KEYWORDS["desk3d"]
# 다른 장면이 하나도 맞지 않을 때만 고르는 장면 (AI 일반 주제는 거의 모든 기사에 걸린다)
SCENE3D_FALLBACK = ("ai3d",)
# 제목(cover) 주제어 한 개는 대사 주제어 몇 개와 맞먹는지. 제목이 기사 주제를 가장 잘 말한다.
SCENE3D_COVER_WEIGHT = 3

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
THUMBNAIL_VISUALS = ["diagram", "metaphor", "beforeafter", "scale", "number", "compare", "flow", "keywords"]
VIDEO_FPS = 30
# 마지막 대사 뒤 여유
END_PAD_MS = 600
# 마지막 대사 뒤 채널 마무리 장면 길이 (뚝 끊기지 않게)
OUTRO_FRAMES = 42


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


# 시청자 기준 기사 고르기 (11/23 채널 방향 재설정)
# 자동 요약 뉴스 쇼츠는 다른 채널도 조회수가 안 나온다. 개발자가 아닌 친구에게 보내고 싶은 소식만 고른다.
PICK_POOL = int(os.environ.get("SHORTS_PICK_POOL", "20"))
PICK_MIN_SCORE = int(os.environ.get("SHORTS_PICK_MIN_SCORE", "5"))

# 기사 종류 → 시리즈 이름 (화면 위 채널 이름 옆, 해시태그)
SERIES = {
    "accident": "AI 사고일지",
    "wow": "이게 된다고?",
    "life": "내 일상 IT",
    "tip": "써먹는 AI",
    "drama": "IT 드라마",
    "dev": "개발자 소식",
}

# 종류별로 시청자가 가져가야 할 것 (대본 요청에 붙인다)
KIND_PAYOFF = {
    "accident": "AI·기술이 사고 친 일. 무슨 일이 벌어졌는지 장면처럼 보여 주고, 마지막은 반전이나 웃픈 한마디로.",
    "wow": "눈이 휘둥그레지는 결과·데모. 뭐가 신기한지 바로 보여 주고(원문 이미지가 있으면 2컷에), 마지막은 감탄이나 웃긴 한마디로.",
    "life": "생활·돈·일자리에 닿는 소식. 내 하루·지갑에 뭐가 달라지는지 원문 사실로, 마지막은 공감 한마디로.",
    "tip": "누구나 바로 써먹는 팁. 원문에 나온 방법을 따라 할 수 있게 쉬운 말로, 마지막은 '저도 해 볼래요' 같은 한마디로.",
    "drama": "빅테크·유명인 업계 드라마. 누가 누구와 무엇으로 부딪쳤는지 이야기처럼, 마지막은 관전평 한마디로.",
    "dev": "개발자 소식이지만 일반인도 알아들을 핵심 하나만. 마지막은 쉬운 한마디로.",
}

VIEWER_PICK_PROMPT = """너는 한국어 IT 쇼츠 채널의 편집장이다. 시청자는 개발자가 아닌 일반인(학생·직장인)이다.
아래 후보 기사마다 "개발자가 아닌 친구에게 이 소식을 보내고 싶은가?"로 점수(1~10)와 종류를 매긴다.
높은 점수(7~10): AI·기술이 사고 친 일, 눈이 휘둥그레지는 데모·결과, 생활·돈·일자리에 닿는 소식,
  누구나 바로 써먹는 팁, 빅테크·유명인 드라마, 누구나 아는 서비스(챗GPT·구글·애플·삼성·카카오·유튜브 등)의 큰 변화.
낮은 점수(1~3): 서버·인프라·CI·프로토콜·데이터베이스 내부·보안 취약점 번호(CVE)·라이브러리 버전·개발 방법론·논문 수식처럼
  개발자끼리만 알아듣는 소식, 광고성 글, 의견 칼럼.
kind: accident(사고) / wow(신기한 결과·데모) / life(생활·돈·일) / tip(써먹는 팁) / drama(업계 드라마) / dev(개발자 전용).
reason은 한 줄. 모든 후보에 점수를 매긴다(index는 0부터)."""

VIEWER_PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "score": {"type": "integer"},
                    "kind": {"type": "string", "enum": list(SERIES)},
                    "reason": {"type": "string"},
                },
                "required": ["index", "score", "kind", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["picks"],
    "additionalProperties": False,
}

# 모델을 못 쓸 때: 제목·요약에 이런 말이 있으면 개발자 전용으로 보고 뒤로 미룬다
DEV_ONLY_WORDS = (
    "cve", "취약점", "nginx", "kubernetes", "k8s", "ci/cd", "github actions", "러너", "프로토콜", "합의 알고리즘",
    "컴파일러", "런타임", "데이터베이스", "postgres", "redis", "kafka", "grpc", "임베딩", "게이트웨이", "rfc",
)


# 모델을 못 쓸 때: 누구나 아는 이름·사고·돈 이야기
CONSUMER_WORDS = (
    "챗gpt", "chatgpt", "openai", "오픈ai", "구글", "google", "애플", "apple", "아이폰", "삼성", "갤럭시", "테슬라", "tesla",
    "유튜브", "youtube", "카카오", "네이버", "메타", "엔비디아", "nvidia", "anthropic", "앤트로픽", "클로드", "claude",
    "제미나이", "gemini", "주가", "ipo", "개인정보", "해킹", "유출", "소송", "로봇", "스팸",
)


def viewer_pick_prompt(candidates):
    lines = ["후보 기사:"]

    for index, article in enumerate(candidates):
        lines.append(f"[{index}] {article.get('title')}")
        lines.append(f"    요약: {article.get('one_line') or ''}")

    return "\n".join(lines)


def rank_for_viewers(candidates):
    """후보마다 (점수, 종류, 이유). Claude → Gemini → 단어 규칙 순서로 시도한다."""
    prompt = viewer_pick_prompt(candidates)

    for name, ask in (
        ("claude", lambda: claude_json(VIEWER_PICK_PROMPT, prompt, VIEWER_PICK_SCHEMA, model=CANDIDATE_MODEL)),
        ("gemini", lambda: gemini_json(VIEWER_PICK_PROMPT, prompt, VIEWER_PICK_SCHEMA)),
    ):
        try:
            picks = ask()["picks"]
            ranked = {pick["index"]: pick for pick in picks if 0 <= pick["index"] < len(candidates)}

            if ranked:
                return [ranked.get(index, {"score": 0, "kind": "dev", "reason": "점수 없음"}) for index in range(len(candidates))], name
        except Exception as error:
            print(f"기사 고르기({name}) 실패: {error}")

    rules = []

    for article in candidates:
        title = (article.get("title") or "").lower()
        dev = any(word in title for word in DEV_ONLY_WORDS)
        known = any(word in title for word in CONSUMER_WORDS)
        # 누구나 아는 이름·사고·돈 이야기만 기준을 넘긴다. 나머지는 모델 판단 없이 올리지 않는다.
        score = 2 if dev else PICK_MIN_SCORE + 1 if known else PICK_MIN_SCORE - 1
        rules.append({"score": score, "kind": "dev" if dev else "wow", "reason": "단어 규칙"})

    return rules, "rules"


def pick_article_for_viewers(issues, used_links, keep=lambda name, data: None):
    """최근 기사 PICK_POOL개를 시청자 기준(보내고 싶은 소식)으로 점수 매겨 가장 높은 것 하나. 기준 미달이면 None."""
    candidates = [
        {**article, "issue_date": issue_date}
        for issue_date, issue in issues
        for article in issue_articles(issue)
        if article["link"] not in used_links
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda article: (
            article["issue_date"],
            article["section"] == "top_stories",
            article.get("selection_score") or 0,
            -(article.get("editorial_rank") or 99),
        ),
        reverse=True,
    )
    candidates = candidates[:PICK_POOL]
    ranks, judge = rank_for_viewers(candidates)
    keep("pick.json", {
        "judge": judge,
        "candidates": [
            {"title": article.get("title"), "link": article["link"], **rank}
            for article, rank in zip(candidates, ranks)
        ],
    })

    # 점수 → 최신 순 (정렬이 안정적이라 같은 점수면 앞쪽=최신·주요 기사)
    best = max(range(len(candidates)), key=lambda index: ranks[index]["score"])
    rank = ranks[best]

    if rank["score"] < PICK_MIN_SCORE:
        print(f"시청자 기준 {PICK_MIN_SCORE}점 넘는 기사가 없습니다 (최고 {rank['score']}점: {candidates[best].get('title')})")
        return None

    kind = rank.get("kind") if rank.get("kind") in SERIES else "wow"
    print(f"기사 고르기({judge}): {rank['score']}점 {SERIES[kind]} — {rank.get('reason', '')}")
    return {**candidates[best], "kind": kind, "series": SERIES[kind], "pick_score": rank["score"]}


# ---------------------------------------------------------------------------
# 대본 생성 (Claude)
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM_PROMPT = """너는 한국어 개발/AI 쇼츠 채널 "{channel}"의 수석 쇼츠 디렉터다.
목표: 기술을 전혀 모르는 사람도, 5살 아이에게 설명하듯 쉽게 알아듣게 만든다.
정확한 사실만 쓰되, 많고 깊은 정보보다 "아, 그런 거구나!" 하고 머릿속에 그림이 그려지는 게 우선이다.
시청자는 1초 안에 넘길지 정하므로 첫 마디는 궁금해서 못 넘기게. 보고서·국어책처럼 읽히면 실패다.
목소리는 AI 음성, 얼굴은 안 나온다. 화면에는 귀여운 3D 꼬마 캐릭터들이 나와서 이야기를 연기한다.
진행자는 채널 마스코트 "잇고니": IT 소식을 제일 먼저 물어 오는 친구. 정보를 읽어 주는 게 아니라 친구한테 "야, 이거 봤어?" 하고 들려준다.
영상마다 시청자가 확실히 가져가는 게 하나 있어야 한다: 웃음, 바로 써먹는 쓸모, 돈·생활 정보, 눈이 휘둥그레지는 신기함 중 하나.

쉽게 말하기 (가장 중요한 연출 규칙):
- 영상 하나 = 이야기 하나. 기사에서 가장 신기하거나 나와 상관있는 핵심 한 가지만 고르고 나머지는 과감히 버린다.
  고객사 사례 나열, 세부 기능 목록, 버전 번호, 수치 여러 개를 늘어놓지 않는다.
- 아이도 아는 말로 말한다. 전문 용어·영어 약어는 되도록 안 쓴다. 제품·회사 이름은 써도 되지만,
  기술 용어가 꼭 필요하면 바로 일상 사물로 풀어 준다. (예: "API, 그러니까 / 프로그램끼리 쓰는 / 주문서예요.")
- 숫자는 영상 전체에서 1~2개만, 가장 센 것만. 체감되게 바꿔 말한다. (예: 성공률 74.8% → "100번 중 / 약 75번 성공")
  바꿔 말한 값도 원문 숫자와 같아야 한다 (반올림하면 "약"을 붙인다).
- 일상 비유 하나로 끝까지 설명한다: 학교·식당·집·택배·놀이터·도서관처럼 아이도 아는 장면. 비유와 실제 기술을 꼭 짝지어 말한다.
  비유가 사실을 왜곡하면 안 된다.
- 대사마다 스스로 묻는다: "5살 아이가 이 말을 듣고 머릿속에 그림이 그려지나?" 아니면 더 쉬운 말로 바꾼다.

말투:
- 신기한 얘기를 들려주는 친절한 형·누나 말투. "~래요", "~거예요", "~했대요", "신기하죠?" 같은 말로 리듬을 만든다.
  비꼬는 말, 겁주는 말, "~했습니다" 같은 발표체, "혁신적입니다" 같은 두루뭉술한 말 금지.
- 한 컷 = 한 호흡 = 사실 하나. line은 짧은 문장 하나(20자 이내). 사실이 두 개면 두 컷으로 쪼갠다.
- line 안에 화면 자막을 끊을 위치를 " / "로 표시한다. 한 조각은 1~3어절, 의미가 붙어 있는 말은 절대 떼지 않는다.
  좋은 예: "로봇한테 / 전용 뇌가 / 필요 없대요."  나쁜 예: "로봇한 / 테 전용"
- 컷은 6~8개, 길이는 20~30초. 맥락(누가, 무엇을)은 빼지 않는다. 같은 말 반복과 군더더기는 뺀다.
- 숫자는 소리 내어 읽기 자연스럽게 쓴다: 소수점 끝 0 금지("0.30달러" X → "0.3달러" O).
- 숫자는 반드시 "무엇의" 숫자인지 같이 말한다. ("70% 개선" → "리드타임이 70% 줄었다")

구조:
1. 1컷(훅, 첫 3초): 인사·채널 소개·"오늘은" 절대 금지. 전문 용어 없이, 들으면 "진짜?" 하게 되는 궁금증이나 놀라운 사실 하나.
   (예: "로봇한테 / 전용 뇌가 / 필요 없대요.", "AI가 / 수학 숙제를 / 혼자 끝냈대요.", "내 비밀 메시지가 / 다 보였대요.")
2. 2컷: 무슨 일인지 한 문장으로 쉽게 (누가 무엇을 했는지).
   시청자에게 뭘 하라고 시키거나("끝까지 보세요") 내용을 미리 늘어놓지 않는다.
3. 중간 2~4컷: 일상 비유 하나로 "어떻게, 왜"를 설명한다. 이 중 2~3컷은 3D 꼬마 캐릭터 장면(scene3d)으로 연기한다.
   - 비유는 영상 하나에 하나만 골라 끝까지 일관되게 쓴다. 비유와 실제 기술을 꼭 짝지어 말한다.
     예: "AI는 / 요리사, / 프롬프트는 / 주문서예요."
   - 비유로 설명하기 어려운 내용이면 억지로 쓰지 말고 쉬운 말과 flow로 설명한다.
4. 핵심 숫자 1컷(원문에 센 숫자가 있을 때만): 가장 센 숫자 하나를 체감되게 ("처음엔 A, 지금은 B" 또는 "100번 중 몇 번").
5. 끝에서 두 번째 컷: "그래서 나한테 뭐가 달라지나"를 쉬운 말 한 마디로. 단, 원문에 나온 사실·행동만 쓴다
   (원문의 설치·업데이트 방법, 명령어, 설정, 권고, 주의 사항). 원문에 없는 조언·절차·일반 상식은 지어내지 않는다.
   그래픽(flow 단계, keywords 등)도 원문에 나온 행동만. 원문에 행동이 없으면 이 컷은 원문 사실로 의미를 정리한다.
   (예: 원문에 "rustup update stable"이 있으면 "rustup update로 / 바로 올려 보세요.")
6. 마지막 컷: 잇고니의 한 방 결말. 채널 소개·"구독해 주세요"·"매일 올려요" 금지.
   기사 사실을 듣고 친구가 할 법한 짧은 반응·농담·반전 한마디(15자 안팎)로 끝낸다. 시청자가 피식 웃거나 고개를 끄덕이게.
   새 사실·숫자·예측·조언을 넣지 않는다. 반응은 내 감정·느낌으로만 ("~할 것 같아요", "~인가 봐요"처럼 사실을 추측하는 말 금지).
   예: "솔직히 / 좀 무섭네요.", "저 주식 / 없어서 다행이에요.", "저도 / 오늘 써 볼래요.", "이건 / 좀 부럽네요."

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

움직이는 그림 그래픽 (시청자가 넘기지 않고 보게 만든다. 영상마다 아래 중 2개 이상을 쓰고, 같은 종류는 한 번씩만):
- diagram: 구조도. 동작 방식·요청 흐름·구성을 사물 2~4개와 화살표로 보여준다. 화살표가 그려지고 일감이 흐른 뒤 카메라가 focus 마디로 밀고 들어간다.
  nodes에 흐름 순서대로 {{label(10자 이내), icon}}, focus에 핵심 마디 번호(0부터). 예: 사용자(person) → 게이트웨이(lock) → 자체 모델(server) → GPU(gpu), focus 2.
- beforeafter: 전후 비교. 기사에 바뀌기 전과 후의 값이 둘 다 있을 때만. before / after에 {{title(8자 이내), value(숫자+단위, 10자 이내), icon}}.
  예: before {{"외부 API", "$3", cloud}} / after {{"자체 GLM", "$0.3", server}}. label에 무엇의 비교인지(예: "100만 토큰당").
- scale: 규모. 같은 사물을 격자로 깔아 숫자를 체감시킨다. count에 깔 개수(1~60), icon, value에 화면에 크게 쓸 말(예: "B200 56개"), label에 설명.
  실제 숫자가 60보다 크면 count는 상징적인 개수(예: 40)로 두고 value와 label에 실제 숫자를 쓴다.
- scene3d: 3D 꼬마 캐릭터 장면. 꼬마들과 사물이 있는 입체 장면을 크게 띄우고, 카메라가 대사 속 배역으로 다가간다.
  쉬운 설명의 중심이다. 영상마다 꼭 2~3번 쓴다 (비유 컷은 metaphor·diagram보다 scene3d를 먼저 고른다):
  비유를 처음 꺼내는 컷(보통 3~4번째 컷)에 한 번, 비유가 이어지며 "어떻게" 되는지 보여 주는 컷에 한 번,
  결과나 "나한테 뭐가 달라지나"가 나오는 뒤쪽 컷에 한 번. 연달아 붙은 컷에는 쓰지 않는다(사이에 다른 컷 하나 이상).
  같은 장면을 다시 써도 되지만, 다시 쓸 때는 다른 배역(꼬마·사물)에 이름표를 붙여 이야기가 이어지게 한다.
  문제와 해결이 다르면 다른 장면도 좋다(예: 문제는 vault3d, 해결은 deploy3d). scene은 주제에 가장 맞는 것 하나:
  vault3d(보안·유출·해킹·인증) / law3d(법·규제·소송·저작권) / coins3d(비용·절감·가격) / server3d(서버·클라우드·인프라·성능)
  / chip3d(칩·반도체·GPU·하드웨어) / lab3d(연구·학습·벤치마크) / data3d(데이터·DB·SQL·지표) / web3d(웹·브라우저·사이트)
  / media3d(이미지·영상 생성·사진·디자인) / search3d(검색·RAG·추천) / invest3d(투자·스타트업·상장·인수·매출)
  / phone3d(모바일·앱·iOS·Android) / deploy3d(배포·CI/CD·테스트·빌드) / terminal3d(터미널·CLI·리눅스·OS)
  / chat3d(메일·메신저·채팅) / voice3d(음성·TTS·오디오·음악) / robot3d(로봇·자율주행·드론)
  / lang3d(프로그래밍 언어·컴파일러·런타임) / work3d(일하는 방식·조직·커리어·업무 자동화) / game3d(게임) / math3d(수학·알고리즘·증명)
  / repo3d(오픈소스·깃허브·Git·라이브러리)
  / desk3d(AI 에이전트·코딩 도구·토큰·MCP) / launch3d(새 모델·제품 출시·공개·베타)
  / ai3d(AI 모델·LLM·챗봇 일반: 위 장면이 하나도 맞지 않을 때).
  scene3d는 장식이 아니라 그 컷의 대사를 설명하는 짧은 이야기다. beats(배역) 2~4개를 반드시 쓴다:
  장면 속 사물·꼬마(아래 대본 요청의 "3D 장면 배역" 목록에 있는 이름만)에 대사 속 개념을 하나씩 붙이면,
  카메라가 대사 순서대로 그 대상으로 밀고 들어가 이름표를 띄운다. beat는 {{target: 배역 이름, label: 이름표(12자 이내)}}.
  예: 대사 "나쁜 꼬마가 / 문틈으로 / 금고를 엿봤대요" → [{{red, "해커"}}, {{door, "뚫린 틈"}}, {{safe, "개인 정보"}}].
  꼬마(white·yellow·red·blue 등)는 사람·역할(사용자, 개발자, 해커, AI 일꾼)을 맡기기 좋다. 이름표는 아이도 아는 쉬운 말로.
  label은 그 컷 대사나 기사에 나오는 말만 쓰고, 대사에 나오는 순서대로 놓는다. 기사에 없는 비유·역할을 지어내지 않는다.
  배역 목록이 없는 장면은 쓰지 않는다. 이름표를 읽을 시간이 필요하니 scene3d 컷 대사는 20자 이상(말하는 데 3초 이상)으로 쓴다.
  label(장면 위 문구)은 비워둔다. 주제가 어느 장면에도 맞지 않으면 쓰지 않는다.
- quote: 원문 인용 카드. 원문의 핵심 문장 하나를 그대로(40자 이내) quote에. 쉬운 문장일 때만 쓴다. label에 출처(예: "GeekNews 정리").
  원문에 없는 문장은 절대 만들지 않는다.
- image: 원문에 실린 실제 사진·화면을 크게 보여 준다. 대본 요청에 "원문 이미지" 목록이 있을 때만 쓰고, image에 그 이름(img1 등)을 쓴다.
  무언가를 만들거나 공개한 기사(앱·도구·게임·서비스·모델의 결과물)는 시청자가 "그래서 뭘 만들었는데?"를 바로 보게
  2컷(무슨 일)에 꼭 쓴다. 영상당 1~2번. 그림을 직접 볼 수 없으니 목록의 설명 말고는 그림 속 내용을 대사·label로 묘사하지 않는다
  ("실제 화면은 / 이렇게 생겼대요"처럼). label은 원문에 나온 이름(12자 이내)이나 빈 문자열.
visual의 숫자와 사실도 기사에 있는 것만 쓴다.

cover: 이 영상의 훅이자 썸네일. 1컷 동안 화면 가운데에 크게 나왔다가 위로 줄어들어 영상 내내 고정된다.
  전문 용어 없이 궁금해지는 쉬운 말로, 기사에서 가장 놀라운 결과를 담는다(체감되는 숫자면 포함). 숫자가 든 어절은 자동으로 강조된다.
  2줄, 줄 사이에 \\n, 줄당 10자 이내. 예: "로봇 전용 뇌\\n필요 없대요", "비밀 메시지\\n20만 건 노출".
title은 28자 이내, 해시태그 없이. 친구한테 말하듯 짧은 궁금증 제목 하나. 보고서식 "제품명, 수치, 기술 용어" 나열 금지.
  잘 되는 형식: "~인 이유", "왜 다들 ~할까?", "~했더니 ~됨", "~가 ~했다고?", "결국 ~한 ~".
  누구나 아는 이름(챗GPT·구글·애플·삼성·테슬라·유튜브 등)은 넣고, 일반인이 모르는 제품명·버전 번호는 빼거나 쉬운 말로 바꾼다.
  제목의 사실·숫자도 원문에 있는 것만.
  예: "7GB짜리 AI가 수능 399점 받은 이유" (O) / "Gemma 4 12B 7GB 경량 LLM, 수능 399.2점 기록" (X)
question: 이 영상이 답하는 질문 한 줄(30자 이내). 설명란 첫 줄에 들어간다. 예: "Revolut은 어떻게 AI 비용을 90% 줄였나?"
hashtags는 # 없이 3~5개.
더보기란용: summary는 무슨 일인지 1~2문장. tips는 원문에 나온 행동(명령어·설정·권고) 1~3개, 원문 그대로. 원문에 행동이 없으면 빈 배열. caution은 비용·보안·개인정보 주의점 한 줄, 없으면 빈 문자열."""


# video/src/Isometric.tsx의 ICONS와 같은 목록 (비유 그림에 올리는 사물)
ICONS = [
    "server", "gpu", "cloud", "database", "robot", "person",
    "laptop", "document", "coins", "truck", "lock", "building",
]

VISUAL_TYPES = [
    "hook", "metaphor", "diagram", "beforeafter", "scale", "quote", "scene3d",
    "number", "compare", "flow", "keywords", "code", "question", "none", "image",
]

# 전후 비교 한쪽 (video/src/schema.ts의 sideSchema)
SIDE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "value": {"type": "string"},
        "icon": {"type": "string", "enum": ICONS},
    },
    "required": ["title", "value", "icon"],
    "additionalProperties": False,
}

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
        "highlight": {"type": "integer"},
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
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "icon": {"type": "string", "enum": ICONS},
                },
                "required": ["label", "icon"],
                "additionalProperties": False,
            },
        },
        "focus": {"type": "integer"},
        "before": SIDE_SCHEMA,
        "after": SIDE_SCHEMA,
        "count": {"type": "integer"},
        "icon": {"type": "string", "enum": ICONS},
        "quote": {"type": "string"},
        # image: 원문 이미지 이름 (대본 요청의 "원문 이미지" 목록에 있는 img1, img2 …)
        "image": {"type": "string"},
        "scene": {"type": "string", "enum": list(SCENE3D_FILES)},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["target", "label"],
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
                    "heading": {"type": "string"},
                    "section": {"type": "string"},
                    "visual": VISUAL_SCHEMA,
                },
                "required": ["line", "emphasis", "heading", "section", "visual"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "question", "cover", "summary", "tips", "caution", "hashtags", "cuts"],
    "additionalProperties": False,
}


def build_script_prompt(article, source_text="", angle=""):
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

    if source_text:
        lines += [
            "",
            "원문 본문 (요약보다 이걸 우선해서 사실·숫자·동작 방식을 가져온다. 여기에 없는 내용은 쓰지 않는다):",
            "<<<원문",
            source_text,
            "원문>>>",
        ]

    if angle:
        lines += ["", f"이번 대본의 각도: {angle}"]

    if article.get("kind") in KIND_PAYOFF:
        lines += ["", f"이 기사 종류: {SERIES[article['kind']]} — {KIND_PAYOFF[article['kind']]}"]

    roles = scene3d_roles_prompt(article)

    if roles:
        lines += ["", roles]

    images = source_images_prompt(article.get("source_images") or [])

    if images:
        lines += ["", images]

    return "\n".join(lines)


def source_images_prompt(images):
    """대본 요청에 붙일 원문 이미지 목록. 모델은 그림을 볼 수 없으니 원문의 이미지 설명(alt)만 알려 준다."""
    if not images:
        return ""

    lines = ["원문 이미지 (원문에 실린 실제 사진·화면. visual type image로 띄울 수 있다. image에는 아래 이름만 쓴다):"]

    for image in images:
        shape = "가로형" if image["width"] >= image["height"] else "세로형"
        lines.append(f"  - {image['id']}: {image.get('alt') or '설명 없음'} ({shape})")

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


def claude_json(system_prompt, user_prompt, schema, model=None):
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

    if model or CLAUDE_MODEL:
        command += ["--model", model or CLAUDE_MODEL]

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
        timeout=600,
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


# ---------------------------------------------------------------------------
# 취재: 원문 본문 가져오기
# ---------------------------------------------------------------------------

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 본문을 긁어올 수 없는 곳(로그인·스크립트로만 보이는 SNS)
UNFETCHABLE_HOSTS = ("twitter.com", "x.com", "linkedin.com", "facebook.com", "instagram.com", "youtube.com", "youtu.be")


def download_page(url):
    request = urllib.request.Request(url, headers=BROWSER_HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def page_text(html):
    """웹페이지에서 본문 글만 뽑는다: 스크립트·메뉴·꼬리말을 빼고 article → main → body 순으로."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg"]):
        tag.decompose()

    root = soup.find("article") or soup.find("main") or soup.body or soup
    blocks = [block.get_text(" ", strip=True) for block in root.find_all(["h1", "h2", "h3", "p", "li", "pre", "blockquote"])]
    text = "\n".join(block for block in blocks if len(block) > 1)

    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fetch_source_text(article):
    """기사 원문 본문을 가져온다. GeekNews는 자세한 한국어 정리 + 원본 글(가능하면)까지. 실패하면 빈 문자열."""
    from bs4 import BeautifulSoup

    link = article.get("link") or ""
    parts = []

    try:
        if d2_post_id(link):
            # D2 글 페이지는 스크립트로 그려져 메뉴만 받아진다. 글 데이터 주소에서 본문을 받는다.
            post = fetch_d2_post(link)
            parts.append(f"{post.get('postTitle') or ''}\n" + page_text(post.get("postHtml") or ""))
            return clean_text("\n\n".join(part for part in parts if part.strip()))[:SOURCE_MAX_CHARS]

        html = download_page(link)

        if "news.hada.io" in link:
            soup = BeautifulSoup(html, "html.parser")
            contents = soup.select_one("#topic_contents")

            if contents:
                # 굵은 글씨 등 인라인 태그에서 줄이 끊기지 않게 문단·목록 단위로 모은다.
                blocks = [el.get_text(" ", strip=True) for el in contents.find_all(["h2", "h3", "h4", "p", "li", "pre"])]
                text = "\n".join(block for block in blocks if block) or contents.get_text(" ", strip=True)
                parts.append("[GeekNews 정리]\n" + text)

            original = soup.select_one(".topictitle a")
            original_url = original.get("href") if original else ""

            if original_url and not any(host in original_url for host in UNFETCHABLE_HOSTS):
                try:
                    parts.append(f"[원본 글: {original_url}]\n" + page_text(download_page(original_url)))
                except Exception as error:
                    print(f"원본 글을 가져오지 못했습니다: {original_url} ({error})")
        else:
            parts.append(page_text(html))
    except Exception as error:
        print(f"원문을 가져오지 못했습니다: {link} ({error})")

    return clean_text("\n\n".join(part for part in parts if part.strip()))[:SOURCE_MAX_CHARS]


# 원문 이미지: 원문에 실린 실제 사진·화면을 받아 두었다가 image 컷으로 크게 보여 준다.
SOURCE_IMAGES = os.environ.get("SHORTS_SOURCE_IMAGES", "1") != "0"
SOURCE_IMAGE_COUNT = 3  # 받아 둘 최대 장수
SOURCE_IMAGE_MAX_CUTS = 2  # 영상 하나에 image 컷 최대 수
SOURCE_IMAGE_MAX_BYTES = 8 * 1024 * 1024
SOURCE_IMAGE_MIN_SIZE = (480, 270)  # 이보다 작으면 화면에서 뭉개진다
# 로고·아이콘·배지·프로필 사진·자동 생성 저장소 카드는 "결과물"이 아니다
IMAGE_SKIP_WORDS = (
    "logo", "icon", "avatar", "badge", "shields.io", "emoji", "sprite", "favicon", "pixel", "tracking",
    "spinner", "gravatar", "profile", "githubassets.com", "avatars.githubusercontent.com", "news.hada.io",
)


# 언론사·사진 통신사: 기사 사진은 대부분 통신사(Getty·Reuters·AP 등) 저작물이라 쓰지 않는다 (저작권 신고 위험).
# 이미지는 소식의 주인공이 직접 낸 자료(회사 블로그·프로젝트 사이트·GitHub·공식 영상)에서만.
NEWS_MEDIA_HOSTS = (
    "nbcnews.com", "cnbc.com", "reuters.com", "bloomberg.com", "nytimes.com", "wsj.com", "ft.com", "theguardian.com",
    "bbc.co.uk", "bbc.com", "cnn.com", "apnews.com", "washingtonpost.com", "theverge.com", "techcrunch.com",
    "arstechnica.com", "wired.com", "engadget.com", "zdnet.com", "businessinsider.com", "axios.com", "forbes.com",
    "economist.com", "theinformation.com", "semafor.com", "fortune.com", "cnet.com", "404media.co", "theregister.com",
    "yna.co.kr", "chosun.com", "joongang.co.kr", "donga.com", "hani.co.kr", "khan.co.kr", "mk.co.kr", "hankyung.com",
    "etnews.com", "zdnet.co.kr", "bloter.net", "aitimes.com", "edaily.co.kr", "sedaily.com", "mt.co.kr", "news1.kr",
    "newsis.com", "ytn.co.kr", "sbs.co.kr", "kbs.co.kr", "imbc.com", "jtbc.co.kr",
)
STOCK_PHOTO_WORDS = ("gettyimages", "getty", "reuters", "apimages", "ap.org", "shutterstock", "alamy", "istockphoto", "afp")


def is_news_media(url):
    host = urllib.parse.urlparse(url or "").netloc.lower()
    return any(host == news or host.endswith("." + news) for news in NEWS_MEDIA_HOSTS)


def image_candidates(html, base_url, use_meta=True):
    """웹페이지에서 쓸 만한 이미지 주소와 설명(alt): 대표 이미지(og:image) → 본문 이미지 순. 언론사 기사면 쓰지 않는다."""
    from bs4 import BeautifulSoup

    if is_news_media(base_url):
        return []

    soup = BeautifulSoup(html, "html.parser")
    found = []

    if use_meta:
        for key in ("og:image", "twitter:image"):
            meta = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})

            if meta and meta.get("content"):
                found.append((meta["content"], "원문 대표 이미지"))

    root = soup.select_one("#topic_contents") or soup.find("article") or soup.find("main") or soup.body or soup

    for img in root.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        sizes = [img.get("width"), img.get("height")]

        # 크기가 적혀 있고 작으면(아이콘·배지) 건너뛴다
        if any(str(size).isdigit() and int(size) < 200 for size in sizes):
            continue

        found.append((src, (img.get("alt") or "").strip()))

    result, seen = [], set()

    for src, alt in found:
        url = urllib.parse.urljoin(base_url, src.strip())
        path = urllib.parse.urlparse(url).path.lower()

        if not url.startswith(("http://", "https://")) or url in seen:
            continue

        if path.endswith((".svg", ".gif", ".ico")) or any(word in url.lower() for word in IMAGE_SKIP_WORDS + STOCK_PHOTO_WORDS):
            continue

        seen.add(url)
        result.append({"url": url, "alt": re.sub(r"\s+", " ", alt)[:80]})

    return result


def png_size(path):
    with open(path, "rb") as file:
        head = file.read(24)

    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0

    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def download_image(url, path):
    """이미지를 받아 가로 1080 이하 PNG로 바꿔 저장한다. 이미지가 아니거나 너무 크거나 작으면 None."""
    request = urllib.request.Request(url, headers={**BROWSER_HEADERS, "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8"})

    with urllib.request.urlopen(request, timeout=20) as response:
        kind = (response.headers.get("Content-Type") or "").lower()
        data = response.read(SOURCE_IMAGE_MAX_BYTES + 1)

    if not kind.startswith("image/") or "svg" in kind or "gif" in kind or len(data) > SOURCE_IMAGE_MAX_BYTES:
        return None

    raw = path + ".raw"

    with open(raw, "wb") as file:
        file.write(data)

    try:
        subprocess.run(
            [ffmpeg_exe(), "-v", "error", "-y", "-i", raw, "-vf", "scale='min(1080,iw)':-2", "-frames:v", "1", path],
            check=True, capture_output=True, timeout=60,
        )
    finally:
        os.remove(raw)

    width, height = png_size(path)

    if width < SOURCE_IMAGE_MIN_SIZE[0] or height < SOURCE_IMAGE_MIN_SIZE[1] or not 0.4 <= width / height <= 3:
        os.remove(path)
        return None

    return {"width": width, "height": height, "hash": hashlib.sha1(data).hexdigest()}


D2_POST = re.compile(r"https?://d2\.naver\.com/helloworld/(\d+)")
YOUTUBE_ID = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})")
GITHUB_REPO = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?(?:[#?].*)?$")


def d2_post_id(link):
    match = D2_POST.match(link or "")
    return match.group(1) if match else ""


def fetch_d2_post(link):
    """네이버 D2 글은 화면을 스크립트로 그려서 페이지에는 메뉴뿐이다. 글 데이터 주소에서 제목·본문 HTML을 받는다."""
    request = urllib.request.Request(
        f"https://d2.naver.com/api/v1/contents/{d2_post_id(link)}",
        headers={**BROWSER_HEADERS, "Accept": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def d2_image_candidates(post):
    """D2 글 본문에 실린 이미지와 발표 영상 썸네일(네이버 이미지 서버)."""
    import html as html_lib

    body = html_lib.unescape(post.get("postHtml") or "")
    urls = re.findall(r"https://[a-z0-9.-]*pstatic\.net/[^\"'\s<>\\]+\.(?:png|jpe?g|webp)", body, flags=re.I)
    result = []

    for url in dict.fromkeys(urls):
        result.append({"url": url, "alt": "원문(D2) 글에 실린 이미지·발표 영상 썸네일", "source": "d2.naver.com"})

    return result


def youtube_candidates(pages):
    """원문에 걸린 YouTube 영상의 썸네일 (영상 제목·채널은 oEmbed로). 원문이 직접 건 영상만 쓴다."""
    from bs4 import BeautifulSoup

    ids = []

    for html, page_url in pages:
        if is_news_media(page_url):
            continue

        # 본문에서만 (사이드바·꼬리말의 다른 영상은 원문이 아니다)
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["nav", "header", "footer", "aside"]):
            tag.decompose()

        root = soup.find("article") or soup.find("main") or soup.body or soup
        ids += YOUTUBE_ID.findall(str(root).replace("&amp;", "&"))

    result = []

    for video_id in list(dict.fromkeys(ids))[:2]:
        title, author = "", ""

        try:
            query = urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"})

            with urllib.request.urlopen(f"https://www.youtube.com/oembed?{query}", timeout=15) as response:
                meta = json.loads(response.read().decode("utf-8", errors="ignore"))

            title, author = meta.get("title") or "", meta.get("author_name") or ""
        except Exception:
            pass

        alt = f"원문에 걸린 YouTube 영상 썸네일: {title}".strip().rstrip(":")
        source = f"YouTube · {author}" if author else "YouTube"

        for size in ("maxresdefault", "hqdefault"):
            # 큰 썸네일이 없는 영상이 있어 작은 것도 후보로 두되, 같은 영상(group)은 한 장만
            result.append({"url": f"https://i.ytimg.com/vi/{video_id}/{size}.jpg", "alt": alt[:80], "source": source, "group": video_id})

    return result


def github_homepage_candidates(url):
    """원문이 GitHub 저장소면, 저장소에 등록된 공식 홈페이지의 이미지."""
    match = GITHUB_REPO.match(url or "")

    if not match:
        return []

    request = urllib.request.Request(
        f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "itgony-shorts"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        homepage = (json.loads(response.read().decode("utf-8", errors="ignore")).get("homepage") or "").strip()

    if not homepage.startswith(("http://", "https://")) or "github.com" in homepage:
        return []

    host = urllib.parse.urlparse(homepage).netloc
    found = image_candidates(download_page(homepage), homepage)

    return [{**item, "alt": f"공식 홈페이지 이미지: {item['alt']}"[:80], "source": f"공식 홈페이지 · {host}"} for item in found]


def linked_image_candidates(url, pages):
    """원문에 그림이 없을 때 쓸 예비 이미지: 원문이 직접 링크한 공식 자료에서만 찾는다.

    검색으로 아무 데서나 가져오지 않는다 (저작권 신고 위험, 그 그림이 정말 그 프로젝트인지 보장 못 함)."""
    result = []

    try:
        result += github_homepage_candidates(url)
    except Exception as error:
        print(f"저장소 홈페이지 이미지를 찾지 못했습니다: {error}")

    return result + youtube_candidates(pages)


def fetch_source_images(article, out_dir):
    """원문(GeekNews면 원본 글 + 정리 글)에 실린 이미지를 최대 SOURCE_IMAGE_COUNT장 받아 둔다. 실패해도 빈 목록."""
    link = article.get("link") or ""
    candidates = []
    pages = []  # (html, 주소): 원문이 건 링크(YouTube 등)를 찾을 때 쓴다
    original_url = ""

    try:
        if d2_post_id(link):
            post = fetch_d2_post(link)
            pages.append((post["postHtml"], link))
            candidates += d2_image_candidates(post)
        else:
            html = download_page(link)
            pages.append((html, link))

            if "news.hada.io" in link:
                from bs4 import BeautifulSoup

                # GeekNews의 대표 이미지는 사이트 로고라 본문 이미지만
                candidates += image_candidates(html, link, use_meta=False)
                soup = BeautifulSoup(html, "html.parser")
                # YouTube 링크는 정리 글 본문에서만 찾는다 (댓글에 단 남의 영상은 원문이 아니다)
                contents = soup.select_one("#topic_contents")
                pages[-1] = (str(contents) if contents else "", link)
                original = soup.select_one(".topictitle a")
                original_url = original.get("href") if original else ""

                if original_url and not any(host in original_url for host in UNFETCHABLE_HOSTS):
                    original_html = download_page(original_url)
                    pages.append((original_html, original_url))
                    candidates = image_candidates(original_html, original_url) + candidates
            else:
                candidates += image_candidates(html, link)
    except Exception as error:
        print(f"원문 이미지 목록을 가져오지 못했습니다: {error}")

    # 원문에 그림이 없을 때를 위한 예비: 원문이 직접 링크한 공식 자료 (뒤에 붙여서 원문 이미지가 먼저 쓰이게)
    try:
        candidates += linked_image_candidates(original_url or link, pages)
    except Exception as error:
        print(f"원문이 건 자료의 이미지를 찾지 못했습니다: {error}")

    os.makedirs(out_dir, exist_ok=True)
    images, hashes, groups = [], set(), set()

    for candidate in candidates[:12]:
        if len(images) >= SOURCE_IMAGE_COUNT:
            break

        if candidate.get("group") in groups:
            continue

        image_id = f"img{len(images) + 1}"
        path = os.path.join(out_dir, f"{image_id}.png")

        try:
            info = download_image(candidate["url"], path)
        except Exception as error:
            print(f"원문 이미지를 받지 못했습니다: {candidate['url']} ({error})")
            continue

        if not info:
            continue

        if info["hash"] in hashes:
            os.remove(path)
            continue

        hashes.add(info["hash"])
        groups.add(candidate.get("group") or candidate["url"])
        images.append({"id": image_id, "file": os.path.abspath(path), "url": candidate["url"], "alt": candidate["alt"],
                       "source": candidate.get("source") or urllib.parse.urlparse(candidate["url"]).netloc,
                       "width": info["width"], "height": info["height"]})

    return images


# ---------------------------------------------------------------------------
# 다단계 대본: 후보 여러 개 → 심사 → 사실 검증
# ---------------------------------------------------------------------------

SCRIPT_ANGLES = [
    "꼬마 캐릭터 비유 중심. 식당·학교·택배 같은 일상 장면 하나로, 이게 어떻게 동작하는지 5살 아이도 알게 꼬마들이 연기하게 한다.",
    "놀라운 결과 하나 중심. 가장 신기한 사실 하나로 궁금증을 걸고, 그게 왜 신기한지 쉬운 말로 풀어 준다. 숫자는 1~2개만.",
    "나랑 무슨 상관 중심. 이 소식이 평범한 사람의 일상·일에 어떻게 닿는지 쉬운 말로 이어 준다. 원문에 있는 사실·행동만 쓴다.",
]

JUDGE_SYSTEM_PROMPT = """너는 한국어 개발/AI 쇼츠 채널의 편집장이다. 같은 기사로 쓴 쇼츠 대본 후보들을 심사해서 하나를 고른다.
기준(각 1~10점):
- easy: 기술을 전혀 모르는 사람(5살 아이에게 설명하듯)도 알아듣는가. 전문 용어·영어 약어·숫자가 적을수록, 이야기가 하나로 모일수록,
  일상 비유와 꼬마 캐릭터 장면(scene3d)으로 그림이 그려질수록 높다. 수치·사례를 늘어놓으면 크게 깎는다.
- hook: 첫 3초에 넘기던 손가락을 멈추게 하는가. 전문 용어 없이 "진짜?" 하게 되는 궁금증·놀라운 사실인가.
- accuracy: 모든 숫자·사실·동작 방식이 원문에 있는가. 원문에 없는 내용이 하나라도 있으면 크게 깎는다. 원문에 없는 행동 제안·조언도 원문에 없는 내용이다.
- clarity: 처음 보는 사람이 끝까지 보고 정확히 이해하는가. 용어 설명, 한 컷에 사실 하나, 맥락(누가·무엇을·왜).
- visual: 비유 그림·숫자·비교 그래픽이 내용을 직관적으로 보여주는가. 비유가 사실을 왜곡하지 않는가.
- retention: 짧은 연결 컷, 리듬, 군더더기 없음, 마지막 컷이 피식 웃거나 고개를 끄덕이게 하는 한 방 결말인가(채널 홍보·"매일 올려요"면 크게 깎는다).
total은 accuracy와 easy를 2배로 쳐서 합산한다(accuracy*2 + easy*2 + 나머지). 가장 높은 후보를 best로 고른다(0부터 센 번호)."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate": {"type": "integer"},
                    "easy": {"type": "integer"},
                    "hook": {"type": "integer"},
                    "accuracy": {"type": "integer"},
                    "clarity": {"type": "integer"},
                    "visual": {"type": "integer"},
                    "retention": {"type": "integer"},
                    "total": {"type": "integer"},
                    "note": {"type": "string"},
                },
                "required": ["candidate", "easy", "hook", "accuracy", "clarity", "visual", "retention", "total", "note"],
                "additionalProperties": False,
            },
        },
        "best": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["scores", "best", "reason"],
    "additionalProperties": False,
}

FACTCHECK_SYSTEM_PROMPT = """너는 기술 뉴스 쇼츠의 팩트체커다. 대본(JSON)의 모든 문장, 숫자, 회사·제품명, 그래픽 값(value, label, items, bars, rooms, beats의 label), cover, title, question, summary, tips, caution을 원문과 하나씩 대조한다.
- 원문에 근거가 없거나 원문과 다른 내용은 원문에 있는 사실로 고치고, 고칠 수 없으면 그 문장·그래픽을 뺀다(컷을 빼도 된다).
- 원문에 조건이 붙은 내용(예: "내부 지표 기준", "약")은 조건을 살린다.
- 행동 제안(끝에서 두 번째 컷의 대사·그래픽, tips)도 대조한다. 원문에 나온 행동·명령어·설정·권고가 아니면
  (일반 상식 조언, 원문에 없는 절차·단계 포함) 원문에 있는 행동으로 고치고, 없으면 원문 사실로 의미를 정리하는 문장으로 바꾸거나 뺀다.
- 마지막 컷은 진행자 "잇고니"의 한 방 결말(반응·농담)이다. 사실을 주장하지 않는 감정·느낌 표현("솔직히 좀 아찔하네요",
  "저도 써 보고 싶어요")은 원문에 없어도 그대로 둔다. 새 사실·숫자·예측·조언을 담았거나 그렇게 읽히면
  (예: "곧 회복되겠죠", "잠깐 쉬는 거예요") 사실을 주장하지 않는 감정 표현으로 바꾼다. 원문 사실 요약으로 바꾸지 않는다.
- 맞는 내용은 그대로 둔다. 말투, 구조, 자막 끊기(" / "), 컷 순서, 그래픽 종류는 바꾸지 않는다.
- "기사에 없어요" 같은 대본 밖 이야기를 넣지 않는다.
script에 고친 대본 전체를, changes에 고친 곳마다 before / after / reason을 적는다. 고칠 게 없으면 changes는 빈 배열."""


def factcheck_schema():
    return {
        "type": "object",
        "properties": {
            "script": SCRIPT_SCHEMA,
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "before": {"type": "string"},
                        "after": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["before", "after", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["script", "changes"],
        "additionalProperties": False,
    }


STYLE_PROMPT = """
이 영상은 잡지 페이지처럼 만든다. 컷 하나 = 페이지 하나: 위에 섹션 이름, 그 아래 큰 헤드라인, 가운데 큰 카드 하나, 아래 자막.
scene3d(꼬마 캐릭터 장면)는 카드 대신 헤드라인 아래를 크게 채운다. 위 scene3d 설명대로 영상마다 2~3번 꼭 쓴다.
글자 목록 카드(keywords·flow·diagram·metaphor)는 영상 전체에서 합쳐 1번까지. 글자를 읽게 하는 화면은 넘긴다.
나머지는 scene3d, image, number(숫자 하나 크게), none(헤드라인만 크게)으로 채운다.
metaphor·diagram은 아이콘 없이 글자 표·단계 목록으로 보인다.

컷마다 heading과 section을 쓴다 (1컷은 cover가 훅이라 둘 다 빈 문자열):
- heading: 그 페이지의 큰 헤드라인. 이 컷 대사의 핵심을 신문 제목처럼. 한 줄 10자 이내, 2줄까지("\\n"으로 줄바꿈).
  대사와 원문에 있는 말·숫자만 쓴다. 새 사실·과장 금지. 강조 단어(emphasis)를 넣으면 그 단어가 강조색으로 보인다.
  "구조 분석", "한 줄 요약", "다음 소식", "빠르게 보기"처럼 내용 없는 안내 문구는 헤드라인으로 쓰지 않는다.
  헤드라인만 봐도 이 컷의 사실 하나가 전달돼야 한다. 아이도 아는 쉬운 말로, 전문 용어는 빼고.
  (예: "100번 중 75번 성공", "로봇한테 따로 뇌가 필요 없다", "나쁜 꼬마가 문틈을 봤다")
  마지막 컷(한 방 결말)도 내용 정리 헤드라인으로 (예: "다시 안 배우고 계획만 바꿨다").
- section: 페이지 위 "02 — ○○" 자리의 섹션 이름. 6자 이내, 쉬운 말 (예: "무슨 일", "어떻게", "얼마나", "나한테는", "정리").
  같은 이야기가 이어지는 컷은 같은 section을 써도 된다.

카드: 그래픽 없는 none 컷은 헤드라인만 크게 보인다. none은 영상 전체에서 3컷 이하.
나머지 컷은 scene3d, image, number, beforeafter, compare, flow, keywords, quote, diagram, metaphor, code 중 대사에 맞는 것으로 채운다.
image(원문 이미지)는 카드 자리에 원문의 실제 사진·화면을 크게 띄운다.
숫자 카드(number·compare·beforeafter)는 영상 전체에서 2번까지 (숫자를 늘어놓으면 어렵다).
keywords는 1~3개를 큰 글씨 줄로 보여 준다 (각 12자 이내). 기사에 나온 기술·기능 이름을 쓰기 좋다.

code 카드 (에디터 창으로 보인다. 대본에 code 컷이 있으면 남색 다크 화면, 없으면 크림 잡지 화면이 된다):
- 원문에 실제로 나온 코드·명령어·설정·API 이름만 쓴다. 원문에 없는 코드를 지어내지 않는다. 원문에 코드가 없으면 code를 쓰지 않는다.
- 원문에 코드·명령어가 나오면 code 카드를 1컷까지 쓴다. 그 컷 대사는 코드를 읽지 말고 "이 한 줄이 무슨 일을 하는지"를 쉬운 말로.
- 7줄 이내, 한 줄 40자 이내. 쉘 명령은 "$ "로 시작한다. 한 줄 설명이 필요하면 "// " 또는 "# " 주석 줄로.
- label에 파일 이름이나 창 이름(예: "main.zig", "zsh", "config.yaml"), highlight에 그 컷 대사가 가리키는 줄 번호(1부터).
  highlight 줄로 커서와 카메라가 다가가므로 대사와 같은 줄을 고른다. 가리킬 줄이 없으면 highlight는 0.
"""


# 원문에 코드·명령어가 있는지: 함수 호출+괄호/세미콜론, 쉘 프롬프트, 전처리기·import·함수 정의 같은 흔적
SOURCE_CODE_PATTERN = re.compile(
    r"(^\s*\$ \S)|(#include|#ifdef|#define)|(\b(def|fn|func|function|class|import|const|let|var)\s+\w+)"
    r"|(\w+\([^()\n]*\)\s*[{;])|(\w+\.\w+\.\w+\s*==)|(```)",
    re.MULTILINE,
)


def source_has_code(source_text):
    return len(SOURCE_CODE_PATTERN.findall(source_text or "")) >= 2


def apply_source_style(script, source_text):
    """화면 스타일: 대본에 code 카드가 있거나 원문에 코드가 나오는 개발 기사면 explain(다크), 아니면 news(크림 잡지)."""
    if script.get("style") != "explain" and source_has_code(source_text):
        script["style"] = "explain"

    return script


# code 카드에서 원문 대조를 하지 않는 줄: 설명 주석("// ", "# "), 괄호·생략 기호만 있는 줄
CODE_COMMENT_LINE = re.compile(r"^\s*(//|#\s|--\s|/\*|\*(\s|/|$))")
CODE_TRIVIAL_LINE = re.compile(r"^[\s{}()\[\];,.…]*$")


def squash_code(text):
    """공백을 모두 지운 글자열. 원문 추출 과정에서 줄바꿈·들여쓰기가 바뀌어도 같은 코드로 본다."""
    return re.sub(r"\s+", "", text or "")


def code_line_in_source(line, squashed_source):
    """code 카드의 한 줄이 원문에 실제로 있는지. 쉘 프롬프트("$ "), 줄 끝 이음표(역슬래시)·생략 기호(...)는 떼고 본다."""
    if CODE_COMMENT_LINE.match(line) or CODE_TRIVIAL_LINE.match(line):
        return True

    body = re.sub(r"^\s*\$\s+", "", line)
    body = re.sub(r"(\\|\.\.\.|…)\s*$", "", body.rstrip())
    body = squash_code(body)

    return len(body) < 3 or body in squashed_source


def unverified_code_lines(visual, source_text):
    """code 카드에서 원문에 없는 코드 줄 목록."""
    squashed_source = squash_code(source_text)

    return [line for line in (visual.get("code") or "").split("\n") if not code_line_in_source(line, squashed_source)]


def drop_unverified_code(script, source_text, keep=lambda name, data: None):
    """원문에 없는 코드 줄이 하나라도 있는 code 카드는 빼고(그래픽 없음), 화면 스타일을 다시 정한다.
    모델이 그럴듯한 코드를 지어내는 것을 막는다. 팩트체크 뒤에 한 번 더 기계적으로 대조한다."""
    dropped = []

    for index, cut in enumerate(script.get("cuts") or []):
        visual = cut.get("visual") or {}

        if visual.get("type") != "code":
            continue

        missing = unverified_code_lines(visual, source_text)

        if missing:
            dropped.append({"cut": index, "missing": missing, "code": visual.get("code")})
            cut["visual"] = {"type": "none"}

    if dropped:
        print(f"원문에 없는 코드가 든 code 카드 {len(dropped)}개를 뺍니다: " + " / ".join(item["missing"][0] for item in dropped))
        keep("code_check.json", dropped)
        has_code = any((cut.get("visual") or {}).get("type") == "code" for cut in script.get("cuts") or [])
        script["style"] = "explain" if has_code else "news"

    return script


def finish_script(script, source_text, keep=lambda name, data: None, images=None):
    """팩트체크를 마친 대본의 마지막 손질: 원문에 없는 코드 카드 빼기 → 원문 이미지 붙이기 → 원문 기준 화면 스타일."""
    script = attach_source_images(drop_unverified_code(script, source_text, keep), images or [])
    return apply_source_style(script, source_text)


def attach_source_images(script, images):
    """image 컷은 실제로 받아 둔 원문 이미지만 남긴다. 대본이 하나도 안 썼으면 2컷(무슨 일) 근처에 대표 이미지를 띄운다.

    "그래서 뭘 만들었는데?"를 바로 보여 주려는 것 (댓글 피드백 11/17). 원문에 실린 이미지만 쓴다."""
    known = {image["id"]: image for image in images}
    cuts = script["cuts"]
    used = 0

    for cut in cuts:
        visual = cut["visual"]

        if visual.get("type") != "image":
            continue

        if visual.get("image") not in known or used >= SOURCE_IMAGE_MAX_CUTS:
            cut["visual"] = {"type": "none"}
        else:
            used += 1

    if images and not used:
        spots = [index for index in range(1, len(cuts) - 2) if cuts[index]["visual"].get("type") in ("none", "keywords", "question")]

        if spots:
            cuts[spots[0]]["visual"] = {"type": "image", "image": images[0]["id"], "label": ""}

    script["images"] = [image for image in images if any(cut["visual"].get("image") == image["id"] for cut in cuts)]
    return script


def editorial_mode():
    """news/explain 스타일(잡지·다크 화면)을 쓰는지. classic이면 예전 먹색·3D 화면."""
    return SHORTS_STYLE != "classic"


def script_system_prompt():
    prompt = SCRIPT_SYSTEM_PROMPT.format(channel=CHANNEL_NAME, icons=", ".join(ICONS))

    return prompt + "\n" + STYLE_PROMPT if editorial_mode() else prompt


def script_style(script):
    """이 영상의 화면 스타일. SHORTS_STYLE이 news/explain이면 그걸로 고정, auto면 대본이 고른 것 (없으면 news)."""
    if SHORTS_STYLE in EDITORIAL_STYLES:
        return SHORTS_STYLE

    if SHORTS_STYLE == "classic":
        return "classic"

    return script.get("style") if script.get("style") in EDITORIAL_STYLES else "news"


def write_candidate(article, source_text, angle):
    return validate_script(
        claude_json(
            script_system_prompt(),
            build_script_prompt(article, source_text, angle),
            SCRIPT_SCHEMA,
            model=CANDIDATE_MODEL,
        )
    )


GEMINI_RETRIES = 4


def gemini_json(system_prompt, user_prompt, schema):
    """Gemini(무료 등급)로 schema에 맞는 JSON을 받는다. Claude를 못 쓸 때의 예비 경로."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 없어 Gemini 예비 경로를 쓸 수 없습니다.")

    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": user_prompt
                        + "\n\n아래 JSON 스키마를 정확히 따르는 JSON 하나만 답한다. 설명·코드블록 없이.\n"
                        + json.dumps(schema, ensure_ascii=False)
                    }
                ],
            }
        ],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_SCRIPT_MODEL}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY)}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # 무료 등급은 붐빌 때 503/429를 자주 준다. 잠깐 쉬었다가 몇 번 더 시도한다.
    for attempt in range(GEMINI_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 503) or attempt == GEMINI_RETRIES - 1:
                raise
            wait = 20 * (attempt + 1)
            print(f"Gemini {error.code}, {wait}초 뒤 다시 시도 ({attempt + 1}/{GEMINI_RETRIES - 1})")
            time.sleep(wait)

    text = "".join(part.get("text", "") for part in result["candidates"][0]["content"]["parts"])
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())

    return json.loads(text)


def write_candidate_with_gemini(article, source_text):
    return validate_script(
        gemini_json(script_system_prompt(), build_script_prompt(article, source_text, SCRIPT_ANGLES[0]), SCRIPT_SCHEMA)
    )


def judge_candidates(candidates, article, source_text):
    prompt = "\n".join(
        [
            f"기사 제목: {article.get('title')}",
            "",
            "<<<원문",
            source_text or "(원문 없음. 아래 요약만 사실로 인정한다)\n" + build_script_prompt(article),
            "원문>>>",
            "",
            *[f"[후보 {index}]\n{json.dumps(script, ensure_ascii=False)}" for index, script in enumerate(candidates)],
        ]
    )

    return claude_json(JUDGE_SYSTEM_PROMPT, prompt, JUDGE_SCHEMA)


class FactCheckFailed(Exception):
    """팩트체크를 끝내지 못한 대본. 사실 확인이 안 된 영상은 올리지 않는다."""

    reason = "factcheck"
    label = "팩트체크 실패"


class FactCheckRejected(Exception):
    """팩트체커가 대본 대부분을 원문에 없다고 빼 버림. 다른 모델에게 다시 맡기지 않는다 (덜 엄격한 쪽이 통과시키는 것을 막는다)."""


class SourceTooShort(FactCheckFailed):
    """원문 본문을 거의 못 가져옴 (자바스크립트로 그리는 페이지 등). 사실을 대조할 수 없으니 이 기사로는 만들지 않는다."""

    reason = "source"
    label = "원문을 가져오지 못함"


# 원문 본문이 이보다 짧으면 메뉴·꼬리말만 받은 것으로 본다 (11/17 D2 글: 메뉴만 136자)
SOURCE_MIN_CHARS = int(os.environ.get("SHORTS_SOURCE_MIN_CHARS", "800"))


class ScriptQualityFailed(Exception):
    """예비(Gemini) 대본이 화면 품질 기준에 못 미침. 올리지 않고, 기록도 남기지 않아 다음 실행에서 Claude로 다시 시도한다."""


# 예비(Gemini) 대본 품질 기준. Claude 대본(11/15 확인)은 빈 헤드라인 0개, 카드 없는 컷 2~4개였다.
FALLBACK_MAX_WEAK_HEADINGS = 1   # 비었거나 내용 없는 헤드라인이 2개 이상이면 건너뜀
FALLBACK_MAX_CARDLESS_CUTS = 3   # 카드 없는 컷이 4개 이상이면 건너뜀 (프롬프트 기준이 3개 이하)

# 내용 없는 낱말 ("핵심 비결", "한 줄 요약", "구조 분석", "다음 소식", "DB 구조", "유출 원인 분석" 같은 헤드라인을 만든다)
GENERIC_HEADING_WORDS = {
    "핵심", "핵심은", "주요", "중요", "중요한", "비결", "포인트", "정리", "총정리", "요약", "한", "줄", "한줄",
    "구조", "분석", "다음", "소식", "빠르게", "보기", "결론", "특징", "이유", "의미", "변화", "소개", "마무리",
    "살펴보기", "알아보기", "이야기", "내용", "개요", "관전", "포인트는", "오늘의", "이번", "뉴스", "새", "새로운",
    "원인", "현황", "상세", "문제", "방법", "과정", "배경", "결과", "효과", "정체", "비밀",
}


def is_weak_heading(heading):
    """헤드라인이 비었거나 내용이 없는지: 숫자가 없고, 내용 없는 낱말이 나머지 낱말 수 이상이면 약하다.
    "DB 구조"(1:1), "유출 원인 분석"(2:1)은 약하고, "접근 제어 오류"(0:3), "성공률 22%→85%"(숫자)는 괜찮다."""
    if re.search(r"\d", heading or ""):
        return False

    words = [re.sub(r"[^0-9A-Za-z가-힣]", "", word) for word in (heading or "").split()]
    words = [word for word in words if word]
    generic = sum(word in GENERIC_HEADING_WORDS for word in words)

    return not words or generic * 2 >= len(words)


def fallback_quality_problems(script):
    """예비(Gemini) 대본을 올려도 되는지. 문제 목록(비었으면 통과). 1컷(훅)은 헤드라인·카드가 원래 없어서 뺀다."""
    cuts = (script.get("cuts") or [])[1:]
    weak = [cut.get("heading") or "(빈 헤드라인)" for cut in cuts if is_weak_heading(cut.get("heading"))]
    cardless = [cut for cut in cuts if (cut.get("visual") or {}).get("type", "none") == "none"]
    problems = []

    if len(weak) > FALLBACK_MAX_WEAK_HEADINGS:
        problems.append(f"내용 없는 헤드라인 {len(weak)}개: " + ", ".join(text.replace("\n", " ") for text in weak[:5]))

    if len(cardless) > FALLBACK_MAX_CARDLESS_CUTS:
        problems.append(f"카드 없는 컷 {len(cardless)}개 / {len(cuts)}컷")

    return problems


def factcheck_script(script, article, source_text, writer="claude"):
    prompt = "\n".join(
        [
            "<<<원문",
            source_text or "(원문 없음. 아래 요약만 사실로 인정한다)\n" + build_script_prompt(article),
            "원문>>>",
            "",
            "[대본]",
            json.dumps(script, ensure_ascii=False),
        ]
    )
    ask = gemini_json if writer == "gemini" else claude_json
    result = ask(FACTCHECK_SYSTEM_PROMPT, prompt, factcheck_schema())

    try:
        checked = validate_script(result["script"])
    except ValueError as error:
        # 팩트체커가 원문에 없는 내용을 빼다 보니 대본이 거의 남지 않았다 = 대본 대부분이 원문으로 확인되지 않는다
        raise FactCheckRejected(f"{writer} 팩트체크가 대본 대부분을 뺐습니다 ({error})") from error

    return checked, result.get("changes") or []


def verify_script(script, article, source_text, keep=lambda name, data: None):
    """팩트체크: Claude → (안 되면) Gemini. 둘 다 실패하면 FactCheckFailed (업로드 건너뜀)."""
    errors = []

    for writer in ("claude", "gemini"):
        try:
            checked, changes = factcheck_script(script, article, source_text, writer)
        except FactCheckRejected as error:
            errors.append(str(error))
            print(f"사실 검증에서 대본 대부분이 빠짐 ({writer}): {error}")
            break
        except Exception as error:
            errors.append(f"{writer}: {error}")
            print(f"사실 검증 실패 ({writer}): {error}")
            continue

        keep("factcheck.json", {"writer": writer, "changes": changes})
        print(f"사실 검증 ({writer}): {len(changes)}곳 수정")
        return checked

    keep("factcheck.json", {"failed": errors})
    raise FactCheckFailed(" / ".join(errors))


def generate_script(article, work_dir=None):
    """원문 취재 → 각도가 다른 대본 후보 여러 개(동시에) → 편집장 심사 → 팩트체크.

    중간 단계가 실패하면(사용량 한도 등) 그 단계까지 나온 결과로, 그것도 없으면 예전처럼 한 번에 쓴다.
    단계별 결과는 work_dir/research/에 남긴다.
    """
    from concurrent.futures import ThreadPoolExecutor

    research_dir = os.path.join(work_dir, "research") if work_dir else None

    def keep(name, data):
        if research_dir:
            save_json(os.path.join(research_dir, name), data)

    source_text = fetch_source_text(article)
    print(f"원문 취재: {len(source_text)}자")

    if len(source_text) < SOURCE_MIN_CHARS:
        raise SourceTooShort(f"원문 본문이 {len(source_text)}자뿐입니다 (기준 {SOURCE_MIN_CHARS}자). 대조할 원문 없이 만들지 않습니다.")

    if research_dir:
        os.makedirs(research_dir, exist_ok=True)

        with open(os.path.join(research_dir, "source.txt"), "w", encoding="utf-8") as file:
            file.write(source_text)

    # 원문에 실린 실제 사진·화면 (대본이 image 컷으로 쓴다)
    images = fetch_source_images(article, os.path.join(research_dir, "images")) if research_dir and SOURCE_IMAGES else []

    if research_dir:
        keep("images.json", images)
        print(f"원문 이미지: {len(images)}장")

    article = {**article, "source_images": images}

    angles = SCRIPT_ANGLES[: max(SCRIPT_CANDIDATES, 1)] if SCRIPT_WRITER == "claude" else []

    with ThreadPoolExecutor(max_workers=max(len(angles), 1)) as pool:
        futures = [pool.submit(write_candidate, article, source_text, angle) for angle in angles]
        candidates = []

        for future in futures:
            try:
                candidates.append(future.result())
            except Exception as error:
                print(f"대본 후보 하나를 만들지 못했습니다: {error}")

    if not candidates:
        # 대부분 Claude 사용량 한도라 Claude로 다시 시도해도 같다. 무료 Gemini로 대신 쓴다.
        print("Claude로 대본 후보를 하나도 만들지 못해 Gemini로 대신 씁니다.")
        script = write_candidate_with_gemini(article, source_text)
        keep("candidates.json", [script])
        keep("fallback.json", {"writer": GEMINI_SCRIPT_MODEL})
        script = finish_script(verify_script(script, article, source_text, keep), source_text, keep, images)
        problems = fallback_quality_problems(script)
        keep("quality.json", {"writer": GEMINI_SCRIPT_MODEL, "problems": problems})

        if problems:
            raise ScriptQualityFailed(" / ".join(problems))

        return script

    keep("candidates.json", candidates)
    print(f"대본 후보 {len(candidates)}개 작성")
    best = candidates[0]

    if len(candidates) > 1:
        try:
            verdict = judge_candidates(candidates, article, source_text)
            keep("judge.json", verdict)

            if 0 <= verdict["best"] < len(candidates):
                best = candidates[verdict["best"]]

            print(f"심사: 후보 {verdict['best']} 선택 ({verdict['reason'][:80]})")
        except Exception as error:
            print(f"심사 단계 실패, 첫 후보를 씁니다: {error}")

    return finish_script(verify_script(best, article, source_text, keep), source_text, keep, images)


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


# 모델이 강조하려고 쓰는 마크다운 굵게(**글자**, __글자__). 화면·설명란에는 별표가 그대로 보인다.
MARKDOWN_BOLD = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")


def strip_markdown(value, key=None):
    """대본 글자에서 마크다운 굵게 표시를 지운다. code 카드는 a**2, **kwargs 같은 실제 코드라서 그대로 둔다."""
    if key == "code":
        return value

    if isinstance(value, str):
        return MARKDOWN_BOLD.sub(r"\2", value).replace("**", "")

    if isinstance(value, list):
        return [strip_markdown(item) for item in value]

    if isinstance(value, dict):
        return {name: strip_markdown(item, name) for name, item in value.items()}

    return value


# "기사에 없어요", "원문엔 안 나와요"처럼 대본 밖 사정을 시청자에게 말하는 문장 (프롬프트로 막아도 가끔 나온다)
META_TALK = re.compile(r"(기사|원문|자료|본문|보도)(에|엔|에는|에선|에서는)\s*(없|안\s*나|나오지\s*않|언급(이|은)?\s*없)")


def speakable_numbers(text):
    """TTS가 어색하게 읽는 숫자 표기를 고친다: 소수점 끝의 0 ("0.30달러" → "0.3달러", "2.0배" → "2배")."""
    text = re.sub(r"(\d+\.\d*?[1-9])0+(?!\d)", r"\1", text)

    return re.sub(r"(\d+)\.0+(?!\d)", r"\1", text)


def drop_meta_talk(script):
    """대본 밖 이야기를 하는 컷·문장을 뺀다."""
    script["cuts"] = [cut for cut in script.get("cuts") or [] if not META_TALK.search(cut.get("line") or "")]

    for key in ("summary", "caution", "question"):
        if META_TALK.search(script.get(key) or ""):
            script[key] = ""

    script["tips"] = [tip for tip in script.get("tips") or [] if not META_TALK.search(tip)]

    return script


def validate_script(script):
    script = drop_meta_talk(strip_markdown(clean_text(script)))
    cuts = script.get("cuts") or []

    if not 6 <= len(cuts) <= 20:
        raise ValueError(f"컷 수가 이상합니다: {len(cuts)}")

    for cut in cuts:
        cut["line"] = speakable_numbers((cut.get("line") or "").strip())
        cut["emphasis"] = [speakable_numbers(word) for word in cut.get("emphasis") or []]

        if not spoken_line(cut):
            raise ValueError("대사가 비어 있는 컷이 있습니다.")

        # 자막에서 강조할 단어는 대사에 실제로 들어 있는 것만 남긴다.
        cut["emphasis"] = [word for word in cut.get("emphasis") or [] if word and word in spoken_line(cut)]
        cut["visual"] = drop_duplicate_label(validate_visual(cut.get("visual")), spoken_line(cut))

    # 화면 스타일은 모델이 고르지 않고 규칙으로: code 카드가 있으면 explain(다크 + 에디터), 없으면 news(크림 잡지)
    script["style"] = "explain" if any(cut["visual"].get("type") == "code" for cut in cuts) else "news"

    for index, cut in enumerate(cuts):
        heading = re.sub(r"\\n", "\n", str(cut.get("heading") or "")).strip()
        cut["heading"] = "" if index == 0 else "\n".join(line.strip() for line in heading.split("\n")[:2] if line.strip())
        cut["section"] = "" if index == 0 else str(cut.get("section") or "").strip()[:10]

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

    before, after = visual.get("before") or {}, visual.get("after") or {}

    has_content = {
        "hook": bool((visual.get("value") or "").strip()),
        "diagram": len([node for node in visual.get("nodes") or [] if (node.get("label") or "").strip()]) >= 2,
        "beforeafter": all((side.get("value") or "").strip() for side in (before, after)),
        "scale": (visual.get("count") or 0) >= 2 and bool((visual.get("value") or "").strip()),
        "quote": len((visual.get("quote") or "").strip()) >= 8,
        "scene3d": visual.get("scene") in SCENE3D_FILES and scene3d_ready(visual.get("scene")),
        "metaphor": len([room for room in visual.get("rooms") or [] if (room.get("place") or "").strip()]) >= 2,
        "number": bool(re.search(r"\d", visual.get("value") or "")),
        "compare": len(visual.get("bars") or []) >= 2,
        "flow": len(visual.get("items") or []) >= 2,
        "keywords": len(visual.get("items") or []) >= 1,
        "code": bool((visual.get("code") or "").strip()),
        "image": bool(re.fullmatch(r"img\d+", (visual.get("image") or "").strip())),
        # 질문 문구가 없어도 물음표 애니메이션만으로 장면이 성립한다.
        "question": True,
        "none": True,
    }

    if not has_content.get(kind):
        return {"type": "none"}

    if kind == "scene3d":
        return validate_scene3d_beats(visual)

    if kind == "code":
        code_lines = visual["code"].strip("\n").split("\n")
        visual["code"] = "\n".join(code_lines[:7])
        highlight = visual.get("highlight")

        # 범위 밖이거나 0이면 강조 줄 없음
        if not isinstance(highlight, int) or not 1 <= highlight <= min(len(code_lines), 7):
            visual.pop("highlight", None)

    return visual


def validate_scene3d_beats(visual):
    """scene3d 배역(beats)은 장면 이름표 파일(*_anchors.json)에 있는 대상만, 이름표는 12자 이내만 남긴다.
    이름표 파일이 있는 장면인데 쓸 수 있는 배역이 하나도 없으면, 꼬마가 그냥 돌아다니기만 하는 그림이 되므로 넣지 않는다.
    이름표 파일이 없는 장면은 예전처럼 장면만 띄운다."""
    anchors = scene3d_anchors(visual.get("scene"))

    if not anchors:
        visual.pop("beats", None)
        return visual

    beats, seen = [], set()

    for beat in visual.get("beats") or []:
        target = (beat.get("target") or "").strip()
        label = re.sub(r"\s+", " ", beat.get("label") or "").strip()

        if target in anchors and target not in seen and label and len(label) <= SCENE3D_BEAT_LABEL_MAX:
            beats.append({"target": target, "label": label})
            seen.add(target)

    if not beats:
        return {"type": "none"}

    visual["beats"] = beats[:SCENE3D_MAX_BEATS]
    # 배역 이야기가 있으면 장면 위 문구는 띄우지 않는다 (한 번에 하나만)
    visual.pop("label", None)
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


# Gemini TTS 시도 횟수와, 받아쓴 글자가 대본의 몇 % 이상이어야 끝까지 읽은 것으로 볼지
TTS_ATTEMPTS = 4
# 무료 Gemini TTS가 429(분당 한도)로 막히면 기다렸다 다시 한다 (초). 분당 한도라 1~2분이면 풀린다.
TTS_RETRY_WAITS = [30, 60, 90]
# 예비 목소리(edge-tts)로 업로드할지. 품질이 떨어져서 기본은 업로드하지 않고 다음 실행으로 미룬다.
ALLOW_FALLBACK_VOICE = os.environ.get("SHORTS_ALLOW_FALLBACK_VOICE") == "1"
# 영어 이름은 한글로 받아써져 글자 수가 줄어서 여유를 둔다 (실제로 끊긴 경우는 30% 안팎)
TTS_MIN_COVERAGE = 0.7


def speech_coverage(text, heard):
    """받아쓴 단어들의 글자 수 / 대본 글자 수. 음성이 중간에 끊겼는지 확인한다(숫자·영문 표기 차이를 감안해 대략)."""
    expected = len(_letters(text))
    got = len(_letters(" ".join(word["text"] for word in heard)))

    return got / expected if expected else 1.0


def synthesize_narration(cuts, work_dir, voice):
    """모든 컷의 대사를 한 번에 읽혀서 컷 사이가 끊기지 않게 한다.

    Gemini TTS를 먼저 쓰고, 실패하면 edge-tts로 대체한다.
    돌려주는 값: (mp3 경로, 컷별 단어 목록, 실제로 쓴 목소리). 단어마다 startMs, endMs가 있다.
    """
    path = os.path.join(work_dir, "narration.mp3")
    text = " ".join(spoken_line(cut) for cut in cuts)
    words = None

    if GEMINI_API_KEY:
        # Gemini TTS는 가끔 대본 중간에서 음성을 끊어 버린다. 받아쓴 글자가 대본보다 크게 모자라면 다시 만든다.
        for attempt in range(1, TTS_ATTEMPTS + 1):
            try:
                gemini_tts(text, path, voice)
                heard = transcribe_words(path)
                coverage = speech_coverage(text, heard)

                if coverage < TTS_MIN_COVERAGE:
                    raise RuntimeError(f"음성이 대본의 {coverage:.0%}에서 끊겼습니다")

                words = align_to_script(text, heard, audio_duration(path) * 1000)
                print(f"음성: Gemini TTS ({voice}, 대본의 {coverage:.0%} 확인)")
                break
            except Exception as error:
                print(f"Gemini TTS {attempt}번째 실패: {error}")

                if attempt <= len(TTS_RETRY_WAITS):
                    import time

                    time.sleep(TTS_RETRY_WAITS[attempt - 1])

        if words is None:
            if not ALLOW_FALLBACK_VOICE:
                # 예비 목소리로 올리느니 이번엔 건너뛴다. 기록에 안 남으므로 다음 실행에서 같은 기사로 다시 만든다.
                raise RuntimeError("Gemini TTS를 쓰지 못해 이번 영상은 건너뜁니다 (예비 목소리 업로드 꺼짐)")

            print("Gemini TTS를 쓰지 못해 edge-tts로 대체합니다.")

    if words is None:
        # 여기까지 오면 Gemini 키가 없는 로컬 시험이거나, 예비 목소리 업로드를 켠 경우다.
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


SCENE3D_LOOP_FRAMES = 360  # video/src/Background.tsx와 같은 값 (12초 루프)


def extract_scene3d_frames(props_cuts, public_dir, run_name):
    """3D 장면 컷마다 루프 영상(투명 webm)의 앞부분을 PNG 프레임으로 풀어 둔다.

    렌더러가 webm에서 프레임을 직접 꺼내는 단계(OffthreadVideo)가 CI에서 계속 멈춰서(11/23 기본·동시 1개 모두 실패),
    필요한 프레임만 미리 이미지로 만들어 화면이 그림 파일을 읽게 한다. 장면마다 그 장면이 쓰이는 가장 긴 컷 길이만큼만."""
    needed = {}

    for cut in props_cuts:
        visual = cut["visual"]

        if visual.get("type") == "scene3d" and visual.get("scene") in SCENE3D_FILES:
            needed[visual["scene"]] = max(needed.get(visual["scene"], 0), min(cut["durationInFrames"], SCENE3D_LOOP_FRAMES))

    folders = {}

    for scene, count in needed.items():
        folder = os.path.join(public_dir, f"s3d_{scene}")
        os.makedirs(folder, exist_ok=True)

        try:
            # 기본 vp9 디코더는 투명도(알파)를 버리므로 libvpx로 푼다.
            subprocess.run(
                [ffmpeg_exe(), "-v", "error", "-y", "-c:v", "libvpx-vp9",
                 "-i", os.path.join(VIDEO_PROJECT_DIR, "public", "assets3d", SCENE3D_FILES[scene]),
                 "-frames:v", str(count), "-compression_level", "1", os.path.join(folder, "%03d.png")],
                check=True, capture_output=True, timeout=300,
            )
            frames = len([name for name in os.listdir(folder) if name.endswith(".png")])

            if frames:
                folders[scene] = (f"{run_name}/s3d_{scene}", frames)
        except Exception as error:
            # 못 풀면 예전처럼 영상에서 직접 꺼낸다
            print(f"3D 장면 프레임을 풀지 못했습니다 ({scene}): {error}")

    for cut in props_cuts:
        visual = cut["visual"]

        if visual.get("type") == "scene3d" and visual.get("scene") in folders:
            folder, frames = folders[visual["scene"]]
            cut["visual"] = {**visual, "frames": folder, "frameCount": frames}

    return props_cuts


def add_hook_visual(props_cuts, style):
    """첫 컷(훅)에 이 영상의 대표 그림을 미리 보여 준다: 원문 이미지가 있으면 그것, 없으면 첫 3D 장면(이름표 없이 전체).

    잘 되는 쇼츠는 첫 1초에 그림이 보인다. 글자만 있는 첫 화면은 넘기기 쉽다 (11/23 개선본)."""
    if style not in EDITORIAL_STYLES or not props_cuts or props_cuts[0]["visual"].get("type") not in ("hook", "none"):
        return props_cuts

    later = [cut["visual"] for cut in props_cuts[1:]]
    pick = next((visual for visual in later if visual.get("type") == "image" and visual.get("src")), None)
    pick = pick or next((visual for visual in later if visual.get("type") == "scene3d" and visual.get("scene")), None)

    if pick:
        props_cuts[0]["visual"] = {**pick, "beats": []} if pick["type"] == "scene3d" else dict(pick)

    return props_cuts


def build_props(script, narration_path, cut_words, source_label, run_name):
    """Remotion에 넘길 props를 만든다. 타이밍은 모두 프레임 단위로 계산해서 넘긴다."""
    public_dir = os.path.join(VIDEO_PROJECT_DIR, "public", run_name)
    os.makedirs(public_dir, exist_ok=True)
    shutil.copyfile(narration_path, os.path.join(public_dir, "narration.mp3"))

    total_frames = ms_to_frame(audio_duration(narration_path) * 1000 + END_PAD_MS)
    style = script_style(script)
    # 3D 꼬마 캐릭터 장면은 영상당 최대 2번 (잡지·다크 화면에서는 헤드라인 아래를 크게 채운다)
    cuts = add_scene3d_cut(script)["cuts"]

    # 컷은 그 컷의 첫 단어를 말하기 시작할 때 바뀐다.
    starts = [0] + [ms_to_frame(words[0]["startMs"]) if words else 0 for words in cut_words[1:]]
    ends = starts[1:] + [total_frames]
    # 마지막 컷 뒤에 마무리 장면을 붙인다 (자막·그래픽 없이 채널 로고)
    outro_from = total_frames
    total_frames += OUTRO_FRAMES

    props_cuts = []

    for index, (cut, words) in enumerate(zip(cuts, cut_words)):
        start, end = starts[index], max(ends[index], starts[index] + 1)
        chunks = caption_chunks(words, cut["emphasis"], caption_segments(cut))
        chunk_starts = [max(ms_to_frame(c["startMs"]) - start, 0) for c in chunks]
        chunk_ends = chunk_starts[1:] + [end - start]

        visual = cut["visual"]

        # 원문 이미지는 렌더용 폴더에 복사하고 그 경로를 넘긴다. 잡지·다크 화면에서만 그린다.
        if visual.get("type") == "image":
            image = next((item for item in script.get("images") or [] if item["id"] == visual.get("image")), None)

            if image and style in EDITORIAL_STYLES and os.path.exists(image["file"]):
                shutil.copyfile(image["file"], os.path.join(public_dir, f"{image['id']}.png"))
                visual = {**visual, "src": f"{run_name}/{image['id']}.png", "value": image.get("source") or urllib.parse.urlparse(image["url"]).netloc}
            else:
                visual = cut["visual"] = {"type": "none"}

        # 3D 장면 이야기는 이름표를 읽을 시간이 필요하다. 1.6초보다 짧은 컷이면 자막만 둔다.
        if visual.get("type") == "scene3d" and end - start < SCENE3D_MIN_FRAMES:
            visual = cut["visual"] = {"type": "none"}

        props_cuts.append(
            {
                "from": start,
                "durationInFrames": end - start,
                "visual": visual,
                "heading": cut.get("heading") or "",
                "section": cut.get("section") or "",
                "emphasis": cut.get("emphasis") or [],
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

    add_hook_visual(props_cuts, style)
    extract_scene3d_frames(props_cuts, public_dir, run_name)

    return {
        "channel": CHANNEL_NAME,
        "theme": style if style in EDITORIAL_STYLES else SHORTS_THEME,
        "style": style,
        "backdrop": pick_backdrop(script) if style == "classic" else "glow",
        "cover": script["cover"],
        "series": script.get("series") or "",
        "source": source_label,
        "audio": f"{run_name}/narration.mp3",
        "durationInFrames": total_frames,
        "outroFrom": outro_from,
        "cuts": props_cuts,
        # 마무리 로고가 뜰 때 짧은 실로폰 소리 (마지막 음이 로고 빨간 점과 맞도록)
        "sfx": pick_sfx(cuts, starts) + [{"src": "sfx/chime.wav", "from": outro_from + 5, "volume": 0.55}],
    }


def scene3d_hits(text, keywords):
    """주제어가 몇 번 나오는지. 영문·숫자는 단어 경계, 한글은 그대로, 're:'는 정규식으로 찾는다."""
    text = (text or "").lower()
    hits = 0

    for keyword in keywords:
        if keyword.startswith("re:"):
            hits += len(re.findall(keyword[3:], text))
        elif re.fullmatch(r"[a-z0-9 .\-]+", keyword):
            hits += len(re.findall(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text))
        else:
            hits += text.count(keyword)

    return hits


def desk3d_hits(text):
    return scene3d_hits(text, DESK3D_KEYWORDS)


def scene3d_ready(scene):
    """장면 루프 파일이 저장소에 있는지 (없는 장면은 고르지 않는다)."""
    root = os.path.dirname(os.path.abspath(__file__))
    return os.path.exists(os.path.join(root, VIDEO_PROJECT_DIR, "public", "assets3d", SCENE3D_FILES[scene]))


SCENE3D_MIN_FRAMES = 48  # 3D 장면 컷 최소 길이 (1.6초). 짧은 컷은 화면 쪽(fitBeats)이 들어가는 만큼만 이름표를 보여 준다
SCENE3D_MAX_BEATS = 4
SCENE3D_BEAT_LABEL_MAX = 12
SCENE3D_ROLE_SCENES = 3  # 대본 요청에 배역 목록을 넣을 장면 수 (기사 주제와 가장 맞는 순)
_SCENE3D_ANCHORS = {}


def scene3d_anchors(scene):
    """장면 이름표 파일(video/public/assets3d/*_anchors.json)의 {배역 이름: 설명}. 파일이 없으면 빈 dict.
    Blender 스크립트가 사물·꼬마의 화면 좌표를 프레임마다 내보낸 파일이다 (video/assets3d/README.md)."""
    if scene not in SCENE3D_FILES:
        return {}

    if scene not in _SCENE3D_ANCHORS:
        root = os.path.dirname(os.path.abspath(__file__))
        name = SCENE3D_FILES[scene].replace("_loop.webm", "_anchors.json")
        path = os.path.join(root, VIDEO_PROJECT_DIR, "public", "assets3d", name)

        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            _SCENE3D_ANCHORS[scene] = {key: value.get("desc", "") for key, value in (data.get("anchors") or {}).items()}
        except (OSError, ValueError):
            _SCENE3D_ANCHORS[scene] = {}

    return _SCENE3D_ANCHORS[scene]


def scene3d_roles_prompt(article):
    """대본 요청에 넣을 "3D 장면 배역" 목록. 기사 주제어와 가장 맞는 장면 몇 개만 넣어 프롬프트를 짧게 둔다."""
    text = " ".join(
        [article.get("title") or "", article.get("one_line") or ""]
        + list(article.get("key_points") or [])
        + list(article.get("topics") or [])
    )
    order = list(SCENE3D_FILES)
    scored = [(scene3d_hits(text, keywords), scene) for scene, keywords in SCENE3D_KEYWORDS.items()]
    scenes = [scene for hits, scene in sorted(scored, key=lambda item: (-item[0], order.index(item[1]))) if hits > 0]
    scenes = [scene for scene in scenes if scene not in SCENE3D_FALLBACK and scene3d_anchors(scene)][:SCENE3D_ROLE_SCENES]

    if not scenes and scene3d_anchors(SCENE3D_FALLBACK[0]):
        scenes = [SCENE3D_FALLBACK[0]]

    if not scenes:
        return ""

    lines = ["3D 장면 배역 (scene3d를 쓸 때 이 장면들 중에서 고르고, beats의 target은 아래 이름만 쓴다):"]

    for scene in scenes:
        lines.append(f"- {scene}")
        lines += [f"  - {key}: {desc}" for key, desc in scene3d_anchors(scene).items()]

    return "\n".join(lines)


def scene3d_scores(script):
    """장면마다 (점수, 제목 주제어 수, 대사 주제어 수). 점수 = 제목 × SCENE3D_COVER_WEIGHT + 대사."""
    cover = script.get("cover") or ""
    lines = " ".join(spoken_line(cut) for cut in script.get("cuts") or [])
    scores = {}

    for scene, keywords in SCENE3D_KEYWORDS.items():
        in_cover, in_lines = scene3d_hits(cover, keywords), scene3d_hits(lines, keywords)
        scores[scene] = (in_cover * SCENE3D_COVER_WEIGHT + in_lines, in_cover, in_lines)

    return scores


def pick_scene3d(script):
    """기사 주제에 맞는 3D 장면. 없으면 None.

    제목에 주제어가 있거나 대사 전체에 주제어가 2번 이상 나오는 장면 중 가장 많이 맞는 장면.
    한 번 스치듯 나온 단어로는 고르지 않는다.
    점수가 같으면 SCENE3D_FILES 순서(보안 > 법 > 비용 > 인프라 > 칩 > ... > 책상 > 출시)로, 더 구체적인 장면을 고른다.
    장면 파일이 없으면 고르지 않는다. SCENE3D_FALLBACK(AI 일반)은 다른 장면이 하나도 맞지 않을 때만 고른다.
    """
    scores = scene3d_scores(script)
    order = list(SCENE3D_FILES)
    candidates = [
        scene for scene in order
        if (scores[scene][1] >= 1 or scores[scene][2] >= 2) and scene3d_ready(scene)
    ]

    specific = [scene for scene in candidates if scene not in SCENE3D_FALLBACK]
    candidates = specific or candidates

    if not candidates:
        return None

    return max(candidates, key=lambda scene: (scores[scene][0], -order.index(scene)))


def pick_backdrop(script):
    """배경 고르기. 직접 정한 배경(SHORTS_BACKDROP)이 있으면 그대로 쓴다.
    3D 장면은 기본적으로 설명 컷(scene3d)에 쓰고, SHORTS_DESK3D=1일 때만 배경에도 깐다."""
    if SHORTS_BACKDROP != "glow" or not DESK3D_AUTO:
        return SHORTS_BACKDROP

    return pick_scene3d(script) or SHORTS_BACKDROP


SCENE3D_MAX_CUTS = 3


def add_scene3d_cut(script):
    """3D 장면 컷은 영상에 최대 SCENE3D_MAX_CUTS번 (붙어 있는 컷 연달아는 안 됨). 대본이 안 썼는데 주제가 맞는 장면이 있으면,
    훅 다음 ~ 끝에서 3번째 전의 자막만 있는 컷 중 대사가 가장 긴 컷에 그 장면을 띄운다."""
    cuts = script["cuts"]
    kept = []

    for index, cut in enumerate(cuts):
        if cut["visual"].get("type") == "scene3d":
            if len(kept) >= SCENE3D_MAX_CUTS or (kept and index - kept[-1] < 2):
                cut["visual"] = {"type": "none"}
            else:
                kept.append(index)

    if kept:
        return script

    scene = pick_scene3d(script)

    # 배역 이름표가 있는 장면은 대본이 쓴 beats(이야기)가 있어야 한다. 자동으로는 beats를 만들 수 없으니 넣지 않는다.
    if not scene or scene3d_anchors(scene):
        return script

    # 장면이 충분히 오래 보이도록, 자막만 있는 컷 중 대사가 가장 긴 컷에 띄운다.
    spots = [index for index in range(1, max(len(cuts) - 2, 1)) if cuts[index]["visual"].get("type") == "none"]

    if spots:
        best = max(spots, key=lambda index: len(spoken_line(cuts[index])))
        cuts[best]["visual"] = {"type": "scene3d", "scene": scene}

    return script


def pick_sfx(cuts, starts):
    """효과음은 꼭 필요한 순간에만: 첫 컷(훅)의 임팩트, 비유 건물이 처음 나올 때의 휙 소리.

    컷마다 소리를 넣으면 화면이 넘어갈 때마다 소리가 나서 거슬린다.
    """
    sfx = [{"src": "sfx/impact.wav", "from": 0, "volume": 0.5}]
    metaphor = next((index for index, cut in enumerate(cuts) if index > 0 and cut["visual"]["type"] == "metaphor"), None)

    if metaphor is not None:
        sfx.append({"src": "sfx/whoosh1.wav", "from": max(starts[metaphor] - 3, 0), "volume": 0.25})

    return sfx


def without_scene3d(props):
    """3D 장면 컷을 자막·헤드라인만 있는 컷으로 바꾼 props (3D 루프 때문에 렌더가 계속 멈출 때 마지막 수단)."""
    props = json.loads(json.dumps(props))

    for cut in props.get("cuts", []):
        if cut.get("visual", {}).get("type") == "scene3d":
            cut["visual"] = {"type": "none"}

    return props


def render_attempts(props):
    """렌더링 시도 순서: (설명, 추가 옵션, props).

    3D 루프(투명 webm) 프레임 추출이 가끔 멈춘다. 장면 컷이 많을수록 잦다.
    1) 그대로 2) 동시 작업 1개로 천천히 3) 3D 장면을 빼고 (업로드가 멈추지 않게)."""
    attempts = [("기본", [], props), ("동시 작업 1개", ["--concurrency=1"], props)]

    if any(cut.get("visual", {}).get("type") == "scene3d" for cut in props.get("cuts", [])):
        attempts.append(("3D 장면 빼고", [], without_scene3d(props)))

    return attempts


def render_with_remotion(props, work_dir, output_path):
    npx = shutil.which("npx")

    if not npx:
        raise RuntimeError("Node.js(npx)가 없습니다. video/ 폴더에서 npm ci를 먼저 실행하세요.")

    props_path = os.path.abspath(os.path.join(work_dir, "props.json"))
    error = ""

    for attempt, (name, extra, attempt_props) in enumerate(render_attempts(props), start=1):
        save_json(props_path, attempt_props)
        command = [
            npx, "remotion", "render", "src/index.ts", "Short",
            os.path.abspath(output_path),
            f"--props={props_path}",
            # YouTube가 다시 압축해도 글자·3D 경계가 뭉개지지 않게 원본 화질을 높게 (기본 crf 18)
            f"--crf={RENDER_CRF}",
            "--x264-preset=slow",
            # 3D 루프(OffthreadVideo) 프레임 추출이 가끔 기본 30초 delayRender 제한에 걸린다. 넉넉히 준다.
            "--timeout=120000",
            "--log=error",
            *extra,
        ]
        result = subprocess.run(
            command,
            cwd=VIDEO_PROJECT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=1800,
        )

        if result.returncode == 0:
            if attempt > 1:
                print(f"Remotion 렌더링: {attempt}번째 시도({name})로 성공")
            return output_path

        error = (result.stderr or result.stdout).strip()[-2000:]
        print(f"Remotion 렌더링 {attempt}번째 실패 ({name}): {error[-300:]}")

    raise RuntimeError(f"Remotion 렌더링 실패: {error}")


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
    style = script_style(script)
    props = {
        "channel": CHANNEL_NAME,
        "theme": style if style in EDITORIAL_STYLES else SHORTS_THEME,
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

    return youtube_safe(clean_text("\n\n".join(sections)))


# YouTube는 제목·설명란에 < > 가 있으면 업로드를 거절한다 (400 invalidDescription / invalidTitle).
def youtube_safe(text):
    return text.replace("->", "→").replace("<-", "←").replace("<", "‹").replace(">", "›")


def cut_bytes(text, limit):
    """UTF-8 바이트 기준으로 자른다. YouTube 한도는 글자 수가 아니라 바이트(설명란 5000)."""
    data = text.encode("utf-8")

    if len(data) <= limit:
        return text

    return data[:limit].decode("utf-8", errors="ignore").rstrip()


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


# 렌더링 화질 (x264 crf, 낮을수록 고화질·큰 파일). 50초 영상 기준 약 30~60MB.
RENDER_CRF = int(os.environ.get("SHORTS_RENDER_CRF", "14"))

# 한 번 실행에서 팩트체크 실패 시 시도할 기사 수
FACTCHECK_ATTEMPTS = int(os.environ.get("SHORTS_FACTCHECK_ATTEMPTS", "2"))


def next_publish_slot(history, now=None):
    """아직 아무 영상도 예약하지 않은 가장 이른 공개 시각 (KST). 슬롯을 안 쓰면 None."""
    if not PUBLISH_SLOTS:
        return None

    now = now or datetime.now(KST)
    earliest = now + timedelta(minutes=PUBLISH_LEAD_MINUTES)
    taken = {entry.get("publish_at") for entry in history if entry.get("publish_at")}

    for day in range(3):
        date = (now + timedelta(days=day)).date()

        for hour in sorted(PUBLISH_SLOTS):
            slot = datetime(date.year, date.month, date.day, hour, tzinfo=KST)

            if slot >= earliest and slot.isoformat() not in taken:
                return slot

    return None


def upload_youtube(video_path, script, article, history=(), publish_at=None):
    token = youtube_access_token()
    metadata = {
        "snippet": {
            "title": youtube_safe(script["title"])[:100],
            "description": cut_bytes(build_description(script, article, history), 5000),
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

    if publish_at and UPLOAD_PRIVACY == "public":
        # 예약 공개: 비공개로 올리고 publishAt(UTC)에 YouTube가 공개로 바꾼다.
        metadata["status"]["privacyStatus"] = "private"
        metadata["status"]["publishAt"] = publish_at.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    return youtube_upload_file(video_path, metadata, token)


def youtube_upload_file(video_path, metadata, token=None):
    """영상 파일을 YouTube에 올린다(재개 가능 업로드). 돌려주는 값: (영상 ID, 실제 공개 상태). 쇼츠·주간 영상 공통."""
    token = token or youtube_access_token()
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

    # 팩트체크에 실패한 기사는 올리지 않고 건너뛴 기록을 남긴 뒤 다음 기사로 한 번 더 시도한다.
    attempts = 1 if (args.link or args.script) else FACTCHECK_ATTEMPTS

    for attempt in range(attempts):
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
            article = pick_article_for_viewers(issues, used_links, lambda name, data: save_json(os.path.join(OUTPUT_DIR, name), data))

        if not article:
            print(f"{args.date} 기준 최근 {LOOKBACK_DAYS}일 이슈에 영상으로 만들 새 기사가 없습니다.")
            return

        if args.link and "kind" not in article:
            # 시험 실행(기사 지정)도 종류·시리즈를 매겨 실제와 같은 대본이 나오게
            rank = rank_for_viewers([article])[0][0]
            kind = rank.get("kind") if rank.get("kind") in SERIES else "wow"
            article = {**article, "kind": kind, "series": SERIES[kind], "pick_score": rank.get("score")}
            print(f"지정한 기사 종류: {SERIES[kind]} ({rank.get('score')}점)")

        print(f"선택한 기사: [{article['issue_date']}] {article['title']}")

        # 같은 날 여러 편을 만들 수 있게 기사마다 작업 폴더를 나눈다.
        slug = re.sub(r"[^0-9A-Za-z]+", "-", urllib.parse.urlsplit(article["link"]).path + urllib.parse.urlsplit(article["link"]).query)
        work_dir = os.path.join(OUTPUT_DIR, f"{article['issue_date']}_{slug.strip('-')[-24:]}")
        os.makedirs(work_dir, exist_ok=True)

        if args.script:
            script = validate_script(load_json(args.script, {}))
            break

        try:
            script = generate_script(article, work_dir)
            script["series"] = article.get("series") or ""

            if script["series"]:
                tag = re.sub(r"[^0-9A-Za-z가-힣]", "", script["series"])
                script["hashtags"] = [tag, *[t for t in script["hashtags"] if t != tag]][:6]

            break
        except ScriptQualityFailed as error:
            # 예비 대본이 부실하면 이번 실행은 올리지 않는다. 기록에 안 남기므로 다음 실행에서 같은 기사를 다시 시도한다.
            print(f"예비(Gemini) 대본 품질 미달로 이번 실행은 업로드하지 않습니다: {error}")
            notify_slack(
                f"[{CHANNEL_NAME}] Shorts 건너뜀 (Claude 사용 불가 + 예비 대본 품질 미달)\n*{article['title']}*\n{str(error)[:500]}"
            )
            return
        except FactCheckFailed as error:
            print(f"이 기사는 업로드하지 않습니다 ({error.label}): {error}")
            notify_slack(
                f"[{CHANNEL_NAME}] Shorts 건너뜀 ({error.label})\n*{article['title']}*\n{str(error)[:500]}\n원문: {article['link']}"
            )
            used_links.add(article["link"])

            # 업로드 테스트가 아닐 때만 기록: 다음 실행에서 같은 기사를 또 고르지 않게 한다.
            if not args.no_upload and not args.link:
                history.append({"date": article["issue_date"], "link": article["link"], "title": article["title"],
                                "skipped": error.reason})
                save_json(SHORTS_HISTORY_FILE, history)
    else:
        print("팩트체크를 통과한 대본이 없어 이번 실행은 업로드하지 않습니다.")
        return

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
        publish_at = next_publish_slot(history) if UPLOAD_PRIVACY == "public" else None
        video_id, privacy = upload_youtube(video_path, script, article, history, publish_at)

        if publish_at and privacy == "private":
            privacy = "scheduled"
            print(f"업로드 완료 (예약 공개 {publish_at:%m/%d %H:%M} KST): https://youtu.be/{video_id}")
        else:
            publish_at = None
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

        if privacy == "scheduled":
            headline = f"[{CHANNEL_NAME}] 새 Shorts 예약 공개 ({publish_at:%m/%d %H:%M} KST)"
        elif privacy == "public":
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
                **({"publish_at": publish_at.isoformat()} if publish_at else {}),
                # 주간 모음 영상(weekly.py)이 팩트체크를 마친 이 대본을 다시 쓴다
                "series": script.get("series") or "",
                "pick_score": article.get("pick_score"),
                "script": {
                    **{key: script[key] for key in ("title", "cover", "style", "series", "cuts", "summary") if key in script},
                    # 이미지 파일은 실행이 끝나면 사라지므로 주소만 (주간 영상에서 다시 받는다)
                    "images": [{k: v for k, v in image.items() if k != "file"} for image in script.get("images") or []],
                },
                "source_label": source_label,
            }
        )
        save_json(SHORTS_HISTORY_FILE, history)


if __name__ == "__main__":
    main()
