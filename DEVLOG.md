# 🛠 Daily Tech News Bot 개발 일지

Daily Tech News Bot을 개발하면서 발생한 문제와 원인, 해결 방법을 기록한 문서입니다.

단순한 완성 결과보다 자동화 시스템을 실제로 운영 가능한 형태로 만들기까지의 시행착오를 남기는 것을 목적으로 합니다.

---

## 1. n8n 대신 GitHub Actions 선택

### 문제

처음에는 n8n을 이용해 다음 자동화를 만들려고 했습니다.

    기술 블로그
    → RSS
    → AI 요약
    → Slack

그러나 n8n Cloud는 장기적으로 유료 사용이 필요할 수 있었습니다.

개인 프로젝트였기 때문에 가능한 한 고정 비용 없이 운영하고 싶었습니다.

### 해결

다음 구조로 변경했습니다.

    GitHub Actions
    +
    Python
    +
    Gemini API
    +
    Slack Incoming Webhook

GitHub Actions를 서버처럼 활용하면서 별도의 VPS나 클라우드 서버를 유지하지 않아도 되도록 구성했습니다.

---

## 2. Slack Incoming Webhook 연결

Slack App을 생성하고 Incoming Webhook을 활성화했습니다.

전송 채널:

`#tech-digest`

GitHub Secret에 다음 값을 저장했습니다.

`SLACK_WEBHOOK_URL`

Python에서 Webhook URL을 직접 코드에 작성하지 않고 환경 변수로 읽도록 구성했습니다.

---

## 3. GitHub Actions에서 Slack 테스트 성공

최초 목표는 아주 단순했습니다.

    GitHub Actions 실행
    → Python 실행
    → Slack 테스트 메시지

이 단계가 성공한 뒤 RSS와 Gemini 기능을 하나씩 추가했습니다.

한 번에 전체 자동화를 구현하지 않고 작은 단위로 테스트하면서 확장했습니다.

---

## 4. GitHub Actions Node 버전 경고

초기 Workflow에서 다음 Action을 사용했습니다.

    actions/checkout@v4
    actions/setup-python@v5

GitHub에서 Node 관련 경고가 발생했습니다.

### 해결

다음 버전으로 변경했습니다.

    actions/checkout@v7
    actions/setup-python@v7

---

## 5. GitHub Actions에서 git push 실패

`sent_articles.json`을 자동 업데이트하기 위해 GitHub Actions가 repository에 commit/push 하도록 구현했습니다.

하지만 다음 오류가 발생했습니다.

    ! [rejected] main -> main (fetch first)
    error: failed to push some refs

또한 Workflow의 write permission 문제도 있었습니다.

### 해결

Workflow에 다음 권한을 추가했습니다.

    permissions:
      contents: write

Repository의 Actions Workflow Permission도 Read and write로 변경했습니다.

또한 push 전에 다음 명령을 수행하도록 변경했습니다.

    git pull --rebase origin main
    git push origin main

---

## 6. Slack 메시지가 중복 발송되는 문제

동시에 실행된 두 GitHub Actions가 같은 `sent_articles.json`을 읽었습니다.

두 실행 모두 동일한 글을 "아직 보내지 않은 새 글"로 판단하면서 Slack 메시지가 중복 발송됐습니다.

### 해결

GitHub Actions에 concurrency를 추가했습니다.

    concurrency:
      group: tech-news-bot
      cancel-in-progress: false

이후 동일 Workflow가 동시에 실행되지 않도록 했습니다.

---

## 7. 새 글 중복 방지 구현

한 번 보낸 글을 계속 다시 보내는 문제가 있었습니다.

### 해결

`sent_articles.json`을 만들었습니다.

예:

    [
      "https://example.com/article1",
      "https://example.com/article2"
    ]

Slack 발송 성공 후 URL을 저장합니다.

다음 실행에서는 저장된 URL을 제외합니다.

---

## 8. Medium URL Query Parameter 문제

Medium RSS에서 URL이 다음처럼 제공됐습니다.

    https://medium.com/...?...source=rss...

동일한 글인데도 Query Parameter가 달라지면 다른 URL로 판단할 가능성이 있었습니다.

### 해결

URL 정규화 함수를 추가했습니다.

    https://medium.com/article?source=rss
    ↓
    https://medium.com/article

이를 통해 같은 글을 하나의 URL로 인식하도록 했습니다.

---

## 9. Medium 원문 접근 시 403 Forbidden

네이버 플레이스와 당근 등의 Medium 글을 Python에서 직접 요청했을 때 다음 오류가 발생했습니다.

    HTTP Error 403: Forbidden

처음에는 Gemini에게 본문 없이 요약을 요청하는 fallback을 고려했습니다.

그러나 이 경우 Gemini가 제목만 보고 내용을 추측할 위험이 있었습니다.

### 해결

본문이 없는 경우에는 요약하지 않는 것으로 정책을 변경했습니다.

그리고 Medium RSS 안의 `entry.content`를 우선 사용했습니다.

처리 순서:

    RSS 전체 본문
    ↓
    RSS summary
    ↓
    원문 HTML
    ↓
    모두 실패하면 요약하지 않음

---

## 10. 쿠팡 RSS XML Parsing 오류

쿠팡 Medium RSS에서 다음 오류가 발생했습니다.

    not well-formed (invalid token)

기존에는 Python 기본 XML Parser를 사용했습니다.

XML 문법이 조금만 깨져 있어도 전체 parsing이 실패했습니다.

### 해결

`feedparser`를 도입했습니다.

`feedparser`

feedparser는 RSS가 일부 잘못되어 있어도 가능한 데이터를 복구해서 읽을 수 있었습니다.

실제로 다음 경고가 발생했지만:

    RSS 경고:
    not well-formed

최신 게시글 10개는 정상적으로 가져올 수 있었습니다.

---

## 11. 초기 실행 시 과거 게시글 폭탄 문제

기술 블로그를 새로 추가했을 때 최근 게시글 10개가 모두 새 글로 판단됐습니다.

이 상태로 Slack을 실행하면 많은 과거 글이 한꺼번에 전송될 수 있었습니다.

### 해결

초기화 모드를 만들었습니다.

`INITIALIZE_ONLY = True`

초기화 모드에서는:

    최근 게시글 조회
    → sent_articles.json에 저장
    → Gemini 호출 안 함
    → Slack 발송 안 함

초기화 이후:

`INITIALIZE_ONLY = False`

로 변경했습니다.

---

## 12. 초기 4개 블로그 검증

다음 네 블로그부터 테스트했습니다.

- G마켓
- 네이버 플레이스
- 쿠팡
- 당근

초기화 결과:

    기존 기록 4
    → 최근 10개씩 기준점 저장
    → 총 40개

이후 일반 모드에서:

    새 글 수: 0
    Slack 발송: 0

을 확인했습니다.

---

## 13. 기술 블로그를 21개로 확대

수집 대상을 늘린 뒤 21개 중 3개가 실패했습니다.

- 우아한형제들
- 쏘카
- 마켓컬리

### 마켓컬리

기존 주소 대신 다음 주소를 사용하면서 정상화되었습니다.

`https://helloworld.kurly.com/rss.xml`

---

## 14. 쏘카 RSS 실패

쏘카 RSS 주소에서 게시글을 읽지 못했습니다.

### 해결

RSS 대신 HTML 페이지를 직접 분석했습니다.

`https://tech.socar.kr/posts`

개별 게시글 URL 패턴:

`/dev/YYYY/MM/DD/article-name`

BeautifulSoup을 이용해 해당 링크만 추출했습니다.

결과:

    HTML 수집 성공
    최근 게시글 10개 정상 확인

---

## 15. 우아한형제들 HTTP 403

우아한형제들 기술 블로그를 GitHub Actions에서 요청하면 다음 오류가 발생했습니다.

    HTTP 403 Forbidden

브라우저에서는 정상 접속되지만 GitHub Actions 환경의 요청은 차단되는 것으로 보였습니다.

### 현재 처리

해당 소스를 비활성화했습니다.

`"enabled": False`

전체 자동화가 한 사이트 때문에 실패하지 않도록 했습니다.

추후 별도의 수집 방법을 검토할 예정입니다.

---

## 16. 기술 블로그 29개까지 확대

추가로 다음 블로그를 포함했습니다.

- Google Play
- Airbnb Engineering
- Slack Engineering
- Spotify Engineering
- Stripe
- Cloudflare
- AWS Architecture
- AWS Compute
- Uber Engineering

최종 테스트 결과:

    활성 블로그: 29
    정상 확인: 29
    오류: 0

---

## 17. Uber Engineering HTML 수집

Uber Engineering은 HTML 방식으로 처리했습니다.

목록 페이지:

`https://www.uber.com/us/en/blog/engineering/`

게시글 링크 패턴을 분석해 최신 글을 가져오도록 구성했습니다.

---

## 18. Gemini API 503 오류

개별 글 요약은 정상적으로 생성됐지만 마지막 데일리 편집 과정에서 다음 오류가 발생했습니다.

    503 ServiceUnavailable

Slack 결과에는 다음 fallback 문구가 표시되었습니다.

    편집 요약 생성 실패

처음에는 Gemini 무료 API 사용 한도가 8회 정도라고 생각했지만, AI Studio 화면의 `총 API 요청 수 8`은 한도가 아니라 실제 사용량이었습니다.

### 해결

Gemini 요청에 재시도 기능을 추가했습니다.

재시도 대상:

- 429
- 500
- 502
- 503
- 504

Backoff:

    3초
    6초
    12초

최대 4번까지 요청합니다.

---

## 19. Slack Markdown 표현 문제

처음 Slack 결과에서 복사된 텍스트에는 다음과 같은 문자가 보였습니다.

    \-
    \*\*
    &quot;

실제 Slack UI에서는 대부분 정상 렌더링됐지만 일부 HTML Entity가 남아 있었습니다.

### 해결

Python `html.unescape()`를 사용했습니다.

`unescape(title)`

또한 Gemini에게 Markdown을 과도하게 사용하지 않고 불릿은 다음 기호를 사용하도록 프롬프트를 수정했습니다.

`•`

---

## 20. 단순 요약에서 AI 아침 브리핑으로 발전

초기에는 새 글마다 Slack 메시지를 각각 보냈습니다.

    글 A → Slack
    글 B → Slack
    글 C → Slack

하지만 게시글이 많아지면 Slack 알림이 과도해질 수 있었습니다.

### 개선

개별 글을 먼저 요약한 뒤 모든 요약을 다시 Gemini에게 전달합니다.

    글 A ─┐
    글 B ─┼→ Gemini 편집장
    글 C ─┘

Gemini가 다음을 생성합니다.

- 오늘 꼭 볼 글
- 오늘의 기술 키워드
- 오늘의 한줄 포인트
- 오늘 왜 중요한가
- 왜 이 글들을 골랐나
- 오늘 공부해볼 것

결과적으로 단순한 RSS 알림이 아니라 개인화된 기술 뉴스레터 형태가 되었습니다.

---

## 21. 사용자 관심 분야를 브리핑에 반영

"오늘 꼭 볼 글" 선정 기준에 개인 관심 분야를 추가했습니다.

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
- 백엔드
- 비용 절감
- 성능 개선

단순히 유명 기업의 글을 우선하는 것이 아니라 학습 가치와 실무 활용성을 중심으로 선정하도록 했습니다.

---

## 22. 내부 정보가 Slack에 노출되는 문제

Gemini 편집 결과에 다음 값이 포함되었습니다.

    [오늘 꼭 볼 글 번호]

    1, 3, 2

이 값은 프로그램이 Top 글을 선택하기 위한 내부 데이터였지만 Slack에도 그대로 표시되었습니다.

### 해결

Top 글 선정에는 계속 사용하지만 최종 Slack 메시지를 만들 때 해당 섹션을 정규식으로 제거했습니다.

동작 구조:

    Gemini 결과
    ↓
    Top 번호 Parsing
    ↓
    Slack 출력에서는 해당 섹션 제거

---

## 23. 실수로 sent_articles.json 덮어쓰기

GitHub Web Editor를 사용하던 중 Workflow YAML 코드를 실수로 `sent_articles.json` 파일에 붙여넣고 Commit했습니다.

`sent_articles.json`에는 이미 처리한 게시글 URL이 저장되어 있기 때문에 그대로 두면 중복 판단 로직이 정상적으로 작동하지 않는 상황이었습니다.

### 해결

GitHub의 File History에서 실수하기 직전 버전을 찾아 복구했습니다.

이 경험을 통해 상태 파일 수정 전 파일명을 반드시 확인해야 한다는 점을 배웠습니다.

---

## 24. 최종 자동 실행

GitHub Actions 예약 실행을 설정했습니다.

    schedule:
      - cron: "57 5 * * *"
        timezone: "Asia/Seoul"

매일 오전 5시 57분 실행을 시작합니다.

목표 흐름:

    05:57
    GitHub Actions
    ↓
    RSS / HTML 확인
    ↓
    Gemini 요약
    ↓
    약 06:00 전후
    ↓
    Slack Tech Digest

새 글이 없는 날에는 Slack 메시지를 보내지 않습니다.

---

## 최종 구조

    29개 기술 블로그
            │
            ▼
    RSS / HTML 수집
            │
            ▼
    새 글 판별
            │
            ▼
    Gemini 개별 요약
            │
            ▼
    Gemini 편집장
            │
            ▼
    개인화 Tech Digest
            │
            ▼
    Slack
            │
            ▼
    sent_articles.json

---

## 이번 프로젝트에서 배운 점

이번 프로젝트는 단순히 API를 연결하는 것보다 실제 자동화를 안정적으로 운영하는 과정이 더 중요했습니다.

특히 다음 내용을 경험했습니다.

- 외부 API 연동
- RSS / Atom 처리
- HTML Parsing
- GitHub Actions 자동화
- Secret 관리
- API 장애 대응
- Retry / Backoff
- 상태 관리
- 중복 처리
- 동시 실행 문제
- 사이트별 예외 처리
- AI Prompt 설계
- AI Hallucination 방지
- Slack Webhook 연동
- 운영용 로그 확인
- 자동화 시스템의 단계적 테스트

처음에는 단순한 RSS 요약 봇으로 시작했지만, 결과적으로는 여러 데이터 소스를 수집하고 AI가 정보를 정리한 뒤 사용자 관심사에 따라 우선순위를 결정하는 자동화 시스템으로 발전했습니다.
