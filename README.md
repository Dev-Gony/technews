# 📰 Daily Tech News Bot

국내외 IT 기업의 기술 블로그를 자동으로 확인하고, 새 글이 발견되면 Gemini API를 이용해 한국어로 요약한 뒤 Slack으로 매일 아침 기술 브리핑을 전달하는 자동화 프로젝트입니다.

## 🎯 프로젝트 목적

여러 기업의 기술 블로그를 매일 직접 확인하는 번거로움을 줄이고, 관심 있는 기술 정보를 한 곳에서 빠르게 확인하기 위해 만들었습니다.

단순히 새 글 링크를 전달하는 것이 아니라 다음 내용까지 정리합니다.

- 글의 핵심 내용
- 알아두면 좋은 기술 개념
- 추천 대상
- 오늘 꼭 볼 글
- 오늘의 기술 키워드
- 추가로 공부하면 좋은 내용

---

## ✨ 주요 기능

### 1. 여러 기술 블로그 자동 수집

RSS 또는 HTML 페이지를 이용해 국내외 기술 블로그의 최신 글을 확인합니다.

현재 약 29개의 기술 블로그를 모니터링합니다.

예시:

- 네이버 D2
- 네이버 플레이스
- 쿠팡
- 요기요
- 토스
- 뱅크샐러드
- 쏘카
- G마켓
- 마켓컬리
- 당근
- LINE Engineering
- 데브시스터즈
- 왓챠
- 무신사
- Google Developers
- Apple Developer
- GitHub Blog
- Meta Engineering
- Netflix TechBlog
- Google Play
- Airbnb Engineering
- Slack Engineering
- Spotify Engineering
- Stripe
- Cloudflare
- AWS Architecture
- AWS Compute
- Uber Engineering

일부 사이트는 RSS를 제공하고, 일부 사이트는 HTML 페이지를 직접 분석합니다.

---

### 2. 중복 게시글 방지

한 번 처리한 글은 `sent_articles.json`에 저장합니다.

다음 실행부터는 이미 처리한 URL을 제외하고 새 글만 처리합니다.

동작 순서:

1. 새 글 발견
2. Gemini 요약
3. Slack 전송
4. 전송 성공 시 `sent_articles.json`에 URL 저장

Slack 전송에 실패한 경우에는 해당 URL을 발송 완료로 기록하지 않습니다.

---

### 3. Gemini 기반 기술 글 요약

Google Gemini API를 사용해 기술 블로그 내용을 한국어로 쉽게 정리합니다.

개별 글은 다음 형태로 요약됩니다.

- 한줄 요약
- 핵심 내용
- 알아둬야 할 것
- 추천 대상

본문에 없는 내용을 임의로 생성하지 않도록 프롬프트에 제한 조건을 두었습니다.

---

### 4. AI 기반 데일리 브리핑

새 글이 여러 개 발견되면 개별 요약 결과를 다시 Gemini에게 전달합니다.

Gemini는 기술 뉴스레터 편집장 역할을 수행하며 다음 내용을 생성합니다.

- 오늘 꼭 볼 글
- 오늘의 기술 키워드
- 오늘의 한줄 포인트
- 오늘 왜 중요한가
- 왜 이 글들을 골랐나
- 오늘 공부해볼 것

중요도 판단에는 다음 관심 분야를 반영했습니다.

- AI Agent
- Agentic Workflow
- LLM
- RAG
- MCP
- Python
- 데이터 분석
- SQL
- 업무 자동화
- 서버 / 클라우드
- 백엔드 아키텍처
- 비용 절감
- 성능 개선
- 실제 기업 기술 적용 사례

---

### 5. Slack 브리핑

최종 결과는 Slack `#tech-digest` 채널로 전달됩니다.

예시:

    🌅 2026-09-13 오늘의 Tech Digest

    AI · 데이터 · 자동화 · 백엔드 중심 아침 기술 브리핑

    오늘 새 글: 3개

    ━━━━━━━━━━━━━━━━━━
    🔥 오늘 꼭 볼 글

    1. GitHub
    ...

    2. Cloudflare
    ...

    ━━━━━━━━━━━━━━━━━━
    💡 오늘의 편집 노트

    [오늘의 기술 키워드]
    AI Agent, Kubernetes, RAG ...

    [오늘의 한줄 포인트]
    ...

    [오늘 공부해볼 것]
    ...

새 글이 없는 날에는 Slack 메시지를 보내지 않습니다.

---

## ⚙️ 기술 스택

- Python 3.12
- GitHub Actions
- Google Gemini API
- Slack Incoming Webhook
- feedparser
- BeautifulSoup4
- RSS / Atom Feed
- HTML Parsing

---

## 🔄 전체 동작 구조

    GitHub Actions
    매일 오전 05:57 KST
            │
            ▼
    기술 블로그 확인
            │
            ▼
    RSS / HTML에서 최신 글 수집
            │
            ▼
    sent_articles.json과 비교
            │
            ├─ 기존 글 → 무시
            │
            └─ 새 글
                 │
                 ▼
            본문 수집
                 │
                 ▼
            Gemini 개별 요약
                 │
                 ▼
            Gemini 데일리 편집
                 │
                 ▼
            Slack Tech Digest
                 │
                 ▼
            sent_articles.json 저장

---

## 🚀 GitHub Actions

GitHub Actions를 이용해 서버 없이 자동 실행합니다.

워크플로 파일:

`.github/workflows/slack-test.yml`

예약 실행 설정:

    schedule:
      - cron: "57 5 * * *"
        timezone: "Asia/Seoul"

매일 한국 시간 오전 5시 57분부터 실행됩니다.

블로그 확인과 Gemini 요약 시간이 필요하기 때문에 Slack 브리핑은 보통 오전 6시 전후 도착하도록 구성했습니다.

수동 실행도 가능합니다.

    GitHub
    → Actions
    → Daily Tech News
    → Run workflow

---

## 🔐 GitHub Secrets

다음 Secret이 필요합니다.

- `SLACK_WEBHOOK_URL`
- `GEMINI_API_KEY`

경로:

    Repository
    → Settings
    → Secrets and variables
    → Actions

API Key와 Slack Webhook URL은 코드에 직접 작성하지 않습니다.

---

## 📦 설치

로컬에서 실행할 경우:

`pip install -r requirements.txt`

`requirements.txt` 내용:

    feedparser
    beautifulsoup4

---

## ▶️ 실행

`python main.py`

---

## 💰 비용

현재 프로젝트는 가능한 한 무료 범위에서 운영하도록 구성했습니다.

- GitHub Actions
- Gemini Free Tier
- Slack Incoming Webhook

Gemini API의 무료 사용량 및 제한은 Google 정책에 따라 변경될 수 있습니다.

---

## 🛡️ 안정성 처리

Gemini API에서 다음 오류가 발생할 경우 자동 재시도하도록 구현했습니다.

- 429
- 500
- 502
- 503
- 504

재시도 간격:

    1차 실패 → 3초 대기
    2차 실패 → 6초 대기
    3차 실패 → 12초 대기
    4차 실패 → 최종 실패

또한 하루에 갑자기 너무 많은 게시글이 감지되는 상황을 막기 위해 한 번 실행에서 처리할 글 수를 제한하고 있습니다.

`MAX_ARTICLES_PER_RUN = 10`

---

## ⚠️ 현재 제한사항

일부 기술 블로그는 GitHub Actions 환경의 요청을 차단합니다.

예:

    우아한형제들 기술블로그
    HTTP 403 Forbidden

현재는 해당 블로그를 비활성화해 두었습니다.

또한 사이트 구조가 변경되거나 RSS 주소가 변경될 경우 수집 코드 수정이 필요할 수 있습니다.

---

## 📚 개발 기록

프로젝트를 만들면서 발생했던 문제와 해결 과정은 `DEVLOG.md`에 별도로 정리했습니다.

---

## 📌 앞으로 개선할 기능

- 추가 기술 블로그 지원
- 우아한형제들 수집 방식 개선
- 실패 사이트 자동 감지
- 블로그별 중요도 가중치
- 뉴스 카테고리 분류
- AI / Backend / Data / Infra 별 브리핑
- 주간 Tech Digest
- 기술 키워드 트렌드 분석
