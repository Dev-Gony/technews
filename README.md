# Daily Tech News Bot

국내외 IT 기업 기술 블로그와 GeekNews를 자동으로 확인하고, 새 글을 Gemini로 평가·선별·요약한 뒤 Slack으로 전달하는 개인용 기술 뉴스 큐레이션 자동화 프로젝트입니다.

처음에는 새 글을 찾아 요약하는 RSS 자동화로 시작했지만, 운영 과정에서 정보량과 API 호출 수가 늘어나면서 현재는 다음과 같이 동작하도록 발전했습니다.

    뉴스 수집
    → 신규 글 판별
    → 중복 제거
    → AI 적합도 평가
    → 중요도별 분류
    → 중요 글 배치 요약
    → 데일리 편집
    → Slack 전달
    → 처리 이력 저장

## 프로젝트 목적

여러 기술 블로그를 매일 직접 확인하는 시간을 줄이고, 현재 학습 및 관심 분야와 관련성이 높은 글을 먼저 확인하기 위해 만들었습니다.

단순히 모든 새 글을 전달하지 않고 다음 기준으로 우선순위를 판단합니다.

- 사용자 관심 분야와의 관련성
- 실무 및 프로젝트 활용 가치
- 기술·업계 변화의 중요도

## 주요 기능

### 1. 국내외 기술 콘텐츠 자동 수집

RSS, Atom Feed 또는 HTML Parsing을 이용해 약 30개의 소스를 확인합니다.

주요 소스 예시:

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
- 무신사
- Google Developers
- Apple Developer
- GitHub Blog
- Meta Engineering
- Netflix TechBlog
- Slack Engineering
- Spotify Engineering
- Stripe
- Cloudflare
- AWS Architecture
- AWS Compute
- Uber Engineering
- GeekNews

일부 사이트는 RSS를 제공하지 않기 때문에 HTML 페이지의 게시글 링크 패턴을 분석해 수집합니다.

GeekNews는 기업 기술 블로그 외의 새로운 기술 콘텐츠를 발견하기 위한 보조 큐레이션 소스로 사용합니다.

#### GeekNews 수집 방식

GeekNews는 일반 기업 블로그와 달리 FeedBurner의 공개 Atom 피드(`https://feeds.feedburner.com/geeknews-feed`)를 사용합니다.

Atom 항목의 링크 형식 차이로 인해 GeekNews만 링크를 별도로 정규화합니다. 링크 후보는 `rel=alternate`의 `href`를 가장 먼저 사용하고, 없으면 `entry.link`, 마지막으로 `entry.id`를 fallback으로 사용합니다. 이렇게 얻은 URL도 기존 `normalize_article_url()`을 거쳐 `topic?id=` 식별자는 유지하면서 추적용 Query Parameter는 제거합니다.

`NomaDamas/k-skill`의 `geeknews-search` 구현도 동일한 공개 FeedBurner 피드를 사용하는 것을 확인했지만, 이 프로젝트에서는 해당 Skill/CLI를 런타임 의존성으로 추가하지 않았습니다. Tech News Bot 자체의 Python 수집 흐름 안에서 직접 처리해 GitHub Actions 의존성과 운영 복잡도를 늘리지 않는 방향을 선택했습니다.

### 2. 신규 글 판별 및 중복 제거

한 번 처리한 글은 `sent_articles.json`에 URL을 저장합니다.

다음 실행부터는 이미 처리한 글을 제외하고 새 글만 대상으로 합니다.

또한 같은 실행 안에서 URL과 제목을 기준으로 중복 후보를 제거합니다.

URL 정규화 시 일반적인 추적 Query Parameter는 제거하지만, GeekNews의 `?id=` 값처럼 게시글 식별에 필요한 Query Parameter는 유지합니다.

### 3. Gemini 기반 1차 뉴스 선별

수집된 글을 곧바로 모두 상세 요약하지 않습니다.

먼저 제목과 RSS 미리보기를 기반으로 Gemini가 다음 세 항목을 각각 0~5점으로 평가합니다.

- `relevance`: 현재 관심 분야와의 관련성
- `practical_value`: 실무·프로젝트·학습 활용 가치
- `significance`: 기술 및 업계 변화의 중요도

총점은 15점 만점입니다.

현재 분류 기준:

- 11~15점: 상세 브리핑 대상
- 9~10점: 제목·선정 이유·링크만 간단히 소개
- 0~8점: 우선순위가 낮아 브리핑에서 제외

고정된 기사 개수만 선택하지 않고, 그날 실제로 볼 가치가 있는 글의 수에 따라 결과 개수가 달라집니다.

### 4. 배치 처리로 Gemini API 호출 최적화

GeekNews처럼 한 번에 많은 새 글이 들어오는 경우 기사별로 Gemini를 호출하면 무료 API 한도에 빠르게 도달할 수 있습니다.

현재는 다음과 같이 배치 처리합니다.

    1차 선별
    10개 기사씩 한 번에 평가

    상세 요약
    5개 기사씩 한 번에 요약

예를 들어 새 글이 30개이고 상세 요약 대상이 10개라면:

    1차 선별 3회
    + 상세 요약 2회
    + 최종 편집 1회
    = 약 6회 Gemini 호출

이를 통해 기사마다 개별 호출하던 방식보다 API 요청 수를 크게 줄였습니다.

### 5. 관심 분야 기반 개인화

현재 우선 관심 분야는 다음과 같습니다.

- AI Agent / Agentic Workflow
- LLM / RAG / MCP
- Python
- 데이터 분석
- SQL
- 업무 자동화
- 서버 / 클라우드 / 인프라
- 백엔드 아키텍처
- 개발 생산성 / Developer Tools
- GitHub 및 소프트웨어 개발 워크플로
- 비용 절감 / 성능 개선 / 운영 효율화
- 실제 기업의 기술 적용 사례

유명 기업의 글이라는 이유만으로 우선하지 않고, 실제 활용성과 학습 가치를 함께 평가하도록 구성했습니다.

### 6. 상세 요약 및 데일리 편집

상세 브리핑 대상으로 선정된 글은 다음 형태로 정리합니다.

- 한줄 요약
- 핵심 내용
- 알아둬야 할 개념
- 추천 대상

이후 상세 요약과 참고 글을 다시 Gemini에 전달해 하루 전체를 정리합니다.

- 오늘 꼭 볼 글
- 오늘의 기술 키워드
- 오늘의 한줄 포인트
- 오늘 왜 중요한가
- 왜 이 글들을 골랐나
- 오늘 공부해볼 것

### 7. Slack 자동 전달

최종 결과는 Slack `#tech-digest` 채널로 전달됩니다.

브리핑에는 다음 정보가 함께 표시됩니다.

- 오늘 확인한 새 글 수
- 상세 브리핑 수
- 추가로 볼 만한 글 수
- 우선순위가 낮아 제외한 글 수
- 상세 글의 AI 선별 점수

메시지가 길어지면 Slack 전송 제한을 고려해 여러 메시지로 나누어 전송합니다.

새 글이 없는 날에는 Slack 메시지를 보내지 않습니다.

## 전체 동작 구조

    GitHub Actions
    매일 오전 05:57 KST
            │
            ▼
    기술 블로그 / GeekNews 수집
            │
            ▼
    sent_articles.json과 비교
            │
            ▼
    URL / 제목 중복 제거
            │
            ▼
    Gemini 1차 선별
    relevance + practical_value + significance
            │
            ├─ 0~8점  → 제외
            ├─ 9~10점 → 짧은 소개
            └─ 11~15점
                    │
                    ▼
              본문 / RSS 콘텐츠 확보
                    │
                    ▼
              Gemini 배치 상세 요약
                    │
                    ▼
              Gemini 데일리 편집
                    │
                    ▼
    Slack Tech Digest
            │
            ▼
    sent_articles.json 저장

## 기술 스택

- Python 3.12
- GitHub Actions
- Google Gemini API
- Slack Incoming Webhook
- feedparser
- BeautifulSoup4
- RSS / Atom Feed
- HTML Parsing

## GitHub Actions

워크플로 파일:

`.github/workflows/slack-test.yml`

예약 실행:

    schedule:
      - cron: "57 5 * * *"
        timezone: "Asia/Seoul"

매일 한국 시간 오전 5시 57분부터 실행됩니다.

수동 실행:

    GitHub
    → Actions
    → Daily Tech News
    → Run workflow

## GitHub Secrets

다음 Secret이 필요합니다.

- `SLACK_WEBHOOK_URL`
- `GEMINI_API_KEY`

API Key와 Slack Webhook URL은 코드에 직접 작성하지 않습니다.

## 설치 및 실행

로컬 설치:

`pip install -r requirements.txt`

실행:

`python main.py`

## 비용

현재는 가능한 한 무료 범위에서 운영하도록 구성했습니다.

- GitHub Actions
- Gemini Free Tier
- Slack Incoming Webhook

Gemini API 무료 사용량과 Rate Limit은 Google 정책에 따라 변경될 수 있습니다.

## 안정성 처리

Gemini API에서 다음 오류가 발생할 경우 자동 재시도합니다.

- 429
- 500
- 502
- 503
- 504

429 응답에서는 가능하면 API 응답의 재시도 대기 시간을 읽어 대기한 뒤 다시 요청합니다.

또한 AI 응답에서 기사 평가가 누락될 경우 모든 글을 자동 합격시키지 않고, 누락 여부를 확인하고 필요 시 같은 배치를 다시 평가합니다.

평가 또는 요약이 끝나지 않은 글은 처리 완료로 기록하지 않아 다음 실행에서 다시 확인할 수 있도록 구성했습니다.

## 현재 제한사항

- 우아한형제들 기술 블로그는 GitHub Actions 환경에서 HTTP 403이 발생해 현재 비활성화 상태입니다.
- 사이트의 RSS 주소나 HTML 구조가 변경되면 수집 코드 수정이 필요할 수 있습니다.
- 현재 관심 분야는 코드 내부에 정의되어 있으며 사용자가 Slack이나 Telegram에서 직접 변경하는 기능은 아직 없습니다.
- 현재 시스템은 정해진 워크플로 안에서 AI가 선별·요약하는 자동화 시스템이며, 도구를 자율적으로 선택하는 AI Agent 구조는 아직 구현하지 않았습니다.

## 운영 검증 계획

2026-09-14 기준 현재 버전을 약 3일간 실제 Slack에서 운영하며 다음 항목을 확인합니다.

- 매일 예약 실행이 안정적으로 동작하는지
- 새 글과 기존 글이 정확히 구분되는지
- GeekNews가 과도하게 브리핑을 차지하지 않는지
- 11점 이상 상세 브리핑의 품질과 양이 적절한지
- 9~10점 참고 글이 실제로 유용한지
- Gemini 429 및 기타 API 오류가 반복되는지
- Slack 메시지 길이와 가독성이 적절한지

운영 결과를 확인한 뒤 선별 점수와 브리핑 분량을 조정할 예정입니다.

## 다음 단계: 개인화 AI Tech News Agent

현재 자동화가 안정화된 이후에는 다음 방향으로 확장하는 것을 검토하고 있습니다.

    Slack / Telegram에서 관심 키워드 입력
            ↓
    사용자 관심사 저장
            ↓
    관련 뉴스 및 기술 콘텐츠 탐색
            ↓
    사용자별 적합도 평가
            ↓
    중요 콘텐츠 원문 분석 및 요약
            ↓
    Slack / Telegram 개인화 브리핑
            ↓
    사용자 피드백 반영

장기적으로는 기존 수집기, 중복 제거기, 적합도 평가기, 요약기, Slack 전송기를 각각 도구로 분리하고, Agent가 목표에 따라 필요한 도구를 선택하는 구조로 고도화할 수 있습니다.

현재 단계에서는 Agent라는 이름을 먼저 붙이기보다, 자동화 시스템을 며칠간 안정적으로 운영·검증하는 것을 우선합니다.

## 개발 기록

실제 구현 과정에서 발생한 오류, 원인 분석, 수정 과정은 `DEVLOG.md`에 기록하고 있습니다.
