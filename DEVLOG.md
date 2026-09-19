# Daily Tech News Bot 개발 일지

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

## 24. 자동 예약 실행

GitHub Actions 예약 실행을 설정했습니다.

    schedule:
      - cron: "57 5 * * *"
        timezone: "Asia/Seoul"

매일 오전 5시 57분 실행을 시작합니다.

새 글이 없는 날에는 Slack 메시지를 보내지 않습니다.

---

## 25. GeekNews를 보조 뉴스 소스로 추가

기존 기업 기술 블로그만 확인했을 때 어떤 날은 새 글이 거의 없었습니다.

기술 트렌드를 조금 더 폭넓게 발견하기 위해 GeekNews의 공식 Atom Feed를 추가했습니다.

    https://news.hada.io/rss/news

GeekNews는 기업 기술 블로그와 동일한 우선순위의 원본 소스라기보다 새로운 기술 콘텐츠를 발견하기 위한 큐레이션 소스로 사용합니다.

최근 후보는 최대 30개까지 확인하도록 설정했습니다.

이 숫자는 최종 발송 개수 제한이 아니라 AI가 판단할 수 있는 후보 범위를 정하기 위한 안전장치입니다.

---

## 26. GeekNews 30개가 1개로 합쳐지는 URL 정규화 버그

GeekNews 최신 글 30개를 정상적으로 읽었지만 로그에서 다음 결과가 나왔습니다.

    중복 제거 전 새 글 후보: 30
    중복 제거 후 새 글 후보: 1

### 원인

기존 URL 정규화 함수는 모든 Query Parameter를 제거했습니다.

GeekNews URL은 다음처럼 `id`가 게시글의 고유 식별자입니다.

    https://news.hada.io/topic?id=33667
    https://news.hada.io/topic?id=33665

하지만 기존 정규화에서는 모두 다음 주소가 됐습니다.

    https://news.hada.io/topic

### 해결

일반적인 추적 Query Parameter는 계속 제거하되 GeekNews의 `/topic?id=`는 `id` 값을 유지하도록 예외 처리했습니다.

수정 후:

    중복 제거 전 새 글 후보: 30
    중복 제거 후 새 글 후보: 30

을 확인했습니다.

---

## 27. AI 선별 결과 누락 시 모든 글이 자동 합격하는 문제

30개의 GeekNews 글을 한 번에 Gemini에게 평가하도록 했을 때 일부 기사 번호가 AI 응답에서 누락됐습니다.

초기 구현은 평가가 없는 글을 놓치지 않기 위해 안전하게 상세 분석 대상으로 포함했습니다.

그 결과 실제로는 일부 글만 평가됐는데도 30개 모두 상세 요약 대상으로 들어갔습니다.

### 문제점

    30개 수집
    ↓
    Gemini가 일부만 평가
    ↓
    평가 누락 글 자동 합격
    ↓
    30개 모두 상세 요약

이 방식은 중요한 글을 놓치지 않는 대신 선별 기능 자체를 무력화했습니다.

### 해결

- 한 번에 30개를 평가하지 않고 10개씩 3개 배치로 분리
- 각 배치에서 모든 기사 번호가 반환됐는지 검사
- 누락이 있으면 같은 배치를 한 번 더 평가
- 그래도 평가되지 않은 글은 자동 합격시키지 않고 보류 처리

---

## 28. Gemini Free Tier 429와 API 호출 최적화

GeekNews 30개를 각각 상세 요약하던 테스트에서 Gemini API가 다음 오류를 반환했습니다.

    429 RESOURCE_EXHAUSTED
    free_tier_requests
    limit: 15

기사마다 한 번씩 Gemini를 호출하면 다음과 같은 구조가 됩니다.

    1차 선별 1회
    + 기사 상세 요약 30회
    + 최종 편집 1회

무료 범위에서 안정적으로 운영하기 어려운 구조였습니다.

### 해결

AI 호출을 단계별 배치 방식으로 변경했습니다.

1차 선별:

    기사 10개 → Gemini 1회

상세 요약:

    기사 5개 → Gemini 1회

실제 30개 테스트에서는:

    1차 선별 3회
    상세 요약 2회
    최종 편집 1회
    총 약 6회 호출

으로 정상 완료했습니다.

429가 발생한 경우 고정된 짧은 Backoff만 사용하는 대신, 가능한 경우 Gemini 오류 응답에 포함된 `retry in ...s` 값을 읽어 실제 재시도 가능 시간에 맞춰 기다리도록 개선했습니다.

---

## 29. 중요도 점수에 따라 상세 / 참고 / 제외 분류

기사를 고정 개수로 자르는 대신 그날의 중요도에 따라 브리핑 양이 달라지도록 변경했습니다.

Gemini는 각 글을 다음 기준으로 0~5점씩 평가합니다.

- relevance: 사용자 관심 분야와의 관련성
- practical_value: 실무·학습·프로젝트 활용 가치
- significance: 기술·업계 변화의 중요도

총점은 15점입니다.

현재 기준:

    11~15점 → 상세 브리핑
    9~10점  → 짧은 소개
    0~8점   → 제외

30개의 GeekNews 기사로 테스트한 결과:

    상세 요약 대상: 10
    짧게 소개할 글: 5
    선별 제외: 15
    선별 평가 보류: 0

이후 상세 대상 10개를 5개씩 두 번에 나눠 요약했고 Slack 발송까지 정상 완료했습니다.

---

## 30. 3일 운영 검증 후 Agent 고도화 예정

현재 버전은 기능을 더 추가하기보다 실제 자동 실행의 안정성을 확인하는 단계로 두기로 했습니다.

약 3일간 다음 항목을 확인합니다.

- GitHub Actions 예약 실행 안정성
- 신규 글 및 처리 완료 글 구분 정확도
- GeekNews 비중이 적절한지
- 11점 이상 상세 브리핑의 양과 품질
- 9~10점 참고 글의 유용성
- Gemini 429 및 기타 API 오류 발생 여부
- Slack 메시지 길이와 가독성

운영 결과에 따라 점수 기준과 브리핑 분량을 조정합니다.

이후 다음 단계에서는 사용자가 Slack 또는 Telegram에서 관심 키워드를 입력하고, 시스템이 해당 관심사를 바탕으로 뉴스를 탐색·평가·요약하는 개인화 AI Tech News Agent 형태로 확장하는 것을 검토합니다.

현재 단계는 미리 Agent라고 부르기보다, 정해진 파이프라인 안에서 AI가 판단하는 뉴스 큐레이션 자동화 시스템으로 정의합니다.

---

## 현재 구조

    약 30개 기술 콘텐츠 소스
            │
            ▼
    RSS / Atom / HTML 수집
            │
            ▼
    신규 글 판별
            │
            ▼
    URL / 제목 중복 제거
            │
            ▼
    Gemini 1차 적합도 평가
            │
            ├─ 0~8점  → 제외
            ├─ 9~10점 → 짧은 소개
            └─ 11~15점
                    │
                    ▼
              Gemini 배치 상세 요약
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

이번 프로젝트는 단순히 API를 연결하는 것보다 실제 자동화를 운영하면서 문제를 관찰하고 수정하는 과정이 더 중요했습니다.

특히 다음 내용을 경험했습니다.

- 외부 API 연동
- RSS / Atom 처리
- HTML Parsing
- GitHub Actions 자동화
- Secret 관리
- 상태 파일 관리
- URL 정규화
- 중복 처리
- 동시 실행 문제
- 사이트별 예외 처리
- Gemini API Retry / Backoff
- API Rate Limit 대응
- AI 응답 누락 검증
- Batch Processing
- AI 기반 적합도 점수화
- AI Prompt 설계
- Hallucination 방지
- Slack Webhook 연동
- 운영 로그 기반 디버깅
- 작은 단위의 반복 테스트

처음에는 단순한 RSS 요약 봇으로 시작했지만, 현재는 여러 데이터 소스를 수집하고 AI가 사용자 관심사와 실무 가치를 기준으로 콘텐츠를 선별한 뒤 필요한 수준으로 요약하는 뉴스 큐레이션 자동화 시스템으로 발전했습니다.

---

## 2026-09-14. GeekNews Feed/Atom 링크 처리 안정화

### 문제

GeekNews를 일반 RSS 소스와 같은 방식으로 처리하면서 `entry.link`만 신뢰하고 있었습니다. GeekNews는 Atom 구조를 사용하고 링크 정보가 `links` 배열의 `rel=alternate`에 들어갈 수 있어, 피드 형식 변화에 따라 링크를 안정적으로 얻지 못할 가능성이 있었습니다.

또한 기존 설정은 `https://news.hada.io/rss/news`를 사용하고 있었습니다. 별도 구현을 조사하는 과정에서 `NomaDamas/k-skill`의 `geeknews-search`가 GeekNews 공개 FeedBurner Atom 피드(`https://feeds.feedburner.com/geeknews-feed`)를 읽기 전용 소스로 사용하는 것을 확인했습니다.

### 해결

GeekNews만 다음 순서로 링크를 찾도록 전용 fallback을 추가했습니다.

    Atom rel=alternate href
    → entry.link
    → entry.id
    → normalize_article_url()

그리고 GeekNews RSS 주소를 공개 FeedBurner 피드로 변경했습니다.

`k-skill` 자체를 프로젝트 의존성으로 추가하지는 않았습니다. 이 봇은 30여 개 소스를 주기적으로 수집하고 신규 판별, 중복 제거, Gemini 선별/요약, Slack 발송, 처리 이력 저장까지 수행하는 운영 자동화이므로, GeekNews 조회용 CLI를 중간에 추가하면 Node/npx 의존성과 실패 지점만 늘어나기 때문입니다.

### 결과

- 기존 `feedparser` 기반 공통 RSS 구조 유지
- GeekNews에만 Atom 링크 fallback 적용
- 외부 Skill/CLI 런타임 의존성 없음
- 기존 신규 글 판별 및 `sent_articles.json` 중복 방지 흐름 그대로 사용

장애 확인 시 GeekNews 항목의 `title`, `link`, `links`, `id` 순으로 확인하면 됩니다.

---

## 2026-09-19. Slack News → Action 1차 구현

### 목표

기존 Tech Digest가 기사를 선별하고 요약하는 데서 끝나지 않고, 실제로 바로 시도해볼 수 있는 실행 항목까지 제안하도록 확장했습니다.

이번 단계에서는 Telegram 기능을 건드리지 않고 Slack 데일리 브리핑만 개선했습니다.

### 구현

Gemini 상세 요약 결과에 다음 구조를 추가했습니다.

- `actionability`: 0~5점
- `action.type`: experiment / code_improvement / study / adoption_review
- `action.title`: 바로 해볼 행동
- `action.steps`: 시작 단계 최대 3개
- `action.effort`: 예상 작업량

기존 상세 요약 Gemini 호출에 함께 생성하도록 구성해 Action 기능 때문에 API 호출 횟수가 추가되지 않도록 했습니다.

### 노출 기준

모든 기사에 억지 Action을 만들지 않도록 `actionability >= 4`인 경우에만 Slack 상세 브리핑에 다음 영역을 표시합니다.

    ⚡ [직접 해볼 것]
    구체적인 실행 항목
    유형: 코드 개선 · 예상 작업량: 30~60분
    • 첫 단계
    • 두 번째 단계

개념 소개나 홍보성 내용처럼 바로 적용하기 어려운 글은 Action을 숨깁니다.

### 안전성

- 기사 본문과 사용자 관심 분야에서 직접 도출할 수 있는 Action만 생성
- 기사에 없는 제품 기능, 성능 수치, 구현 결과를 추측하지 않도록 프롬프트 제한
- 잘못된 `actionability` 값이나 비정상적인 `action` 구조가 와도 기존 요약은 정상 출력
- 향후 Feedback Learning / Trend Radar에서 재사용할 수 있도록 원본 구조화 요약 데이터도 `summary_data`로 유지

### 테스트

`tests/test_slack_actions.py`에서 다음을 검증합니다.

- Action 점수가 높은 기사에서 Action 표시
- Action 점수가 낮은 기사에서 Action 미표시
- 잘못된 Action 데이터가 들어와도 안전하게 fallback

### 다음 후보

1. Slack 피드백 수집
2. 기사/Action metadata 저장
3. Feedback Learning
4. 누적 기사 데이터를 활용한 Trend Radar

