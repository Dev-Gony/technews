# TechNews 고도화 사례 보고서

> 목적: 단순 RSS 요약 자동화에서 개인화 Developer Intelligence 서비스로 발전시키는 과정의 선택, 이유, 구현, 결과, 학습 내용을 기록한다.
>
> 이 문서는 최종적으로 PDF 포트폴리오/프로젝트 회고 보고서의 원본으로 사용한다.

---

## 0. 문서 작성 원칙

각 고도화 단계는 다음 형식으로 기록한다.

1. 문제
2. 고려한 선택지
3. 최종 선택
4. 선택 이유
5. 구현
6. 결과
7. 진행하면서 배운 점
8. 다음 단계 판단

단순히 "무엇을 만들었는가"보다 "왜 그렇게 만들었는가"를 남기는 것을 우선한다.

---

# 1. 시작점: RSS 기술 뉴스 자동화

## 문제

관심 있는 기술 블로그와 개발자 콘텐츠가 여러 사이트에 흩어져 있어 매일 직접 확인해야 했다.

처음 목표는 복잡한 AI Agent보다 다음 문제를 해결하는 것이었다.

- 여러 기술 블로그를 자동 수집
- 이미 본 글 제외
- 관심 있는 글만 선별
- 핵심 내용을 요약
- Slack으로 정기 전달

## 선택

초기 구조는 정해진 파이프라인 기반의 자동화로 시작했다.

    RSS / Atom / HTML
        ↓
    신규 글 탐지
        ↓
    중복 제거
        ↓
    Gemini 평가
        ↓
    상세 / 짧은 소개 / 제외
        ↓
    Slack Digest

## 선택 이유

처음부터 자율 Agent 구조로 만들 경우 도구 선택, 상태 관리, 재시도, 메모리 등 해결해야 할 문제가 급격히 늘어난다.

반면 이 프로젝트의 첫 번째 검증 포인트는 "기술 뉴스 추천 자체가 실제로 유용한가"였기 때문에, 동작이 예측 가능한 파이프라인이 더 적합했다.

## 배운 점

AI를 넣었다고 바로 Agent가 되는 것은 아니다.

먼저 반복 가능한 자동화 파이프라인을 안정화하고, AI가 판단해야 할 지점을 명확히 나누는 것이 중요했다.

---

# 2. 기사 수집에서 기사 선별로

## 문제

모든 새 기사를 요약하면 비용과 읽을 양이 동시에 증가했다.

"수집"보다 "무엇을 읽지 않을 것인가"가 더 중요한 문제가 되었다.

## 선택

Gemini가 다음 3가지 기준을 각각 0~5점으로 평가하도록 만들었다.

- relevance
- practical_value
- significance

총점에 따라:

- 높은 점수 → 상세 요약
- 중간 점수 → 짧은 소개
- 낮은 점수 → 제외

## 선택 이유

단일 yes/no 분류보다 점수를 분리하면 왜 해당 기사가 선택되었는지 설명하기 쉽다.

또한 사용자 관심도만 사용하면 중요한 보안 사고나 플랫폼 변화가 누락될 수 있기 때문에 significance를 별도 축으로 두었다.

## 배운 점

추천 시스템은 "좋아할 것"만 찾으면 안 된다.

사용자 취향과 별개로 반드시 알아야 할 정보가 존재하므로, 개인화와 중요도를 분리해서 생각해야 했다.

---

# 3. 관심사 외부화와 개인화 기반

## 문제

관심사가 코드에 박혀 있으면 사용자의 관심 변화에 따라 코드를 수정해야 했다.

## 선택

관심사와 점수 기준을 설정 파일로 분리했다.

## 선택 이유

추천 로직과 사용자 설정을 분리하면:

- 코드 변경 없이 관심사 조정 가능
- 이후 피드백 학습 연결 가능
- 사용자별 설정으로 확장 가능

## 배운 점

개인화 기능을 만들기 전에 먼저 "개인 설정"이 코드와 분리되어 있어야 한다.

---

# 4. Telegram 확장 후 Slack 중심으로 방향 수정

## 문제

Telegram에서 관심사 변경, 온디맨드 digest, follow-up 질문 기능까지 확장했지만 Slack과 Telegram을 동시에 고도화하면 UI와 상태 관리 기능을 두 번 구현해야 했다.

## 고려한 선택지

### 선택지 A
Slack과 Telegram을 동일하게 계속 확장

### 선택지 B
Telegram을 제거하고 Slack만 유지

### 선택지 C
Telegram은 유지하되 신규 핵심 기능은 Slack 중심으로 개발

## 최종 선택

선택지 C.

    Slack = 주 인터페이스
    Telegram = 기존 기능 유지 / 추후 확장

## 선택 이유

News → Action, Feedback Learning, Trend Radar는 개인 메신저보다 업무/개발 환경인 Slack과 더 자연스럽게 연결된다.

기존 Telegram 기능을 삭제할 이유는 없지만, 두 채널을 동시에 발전시키는 것은 개발 비용 대비 효과가 낮았다.

## 배운 점

기능을 더 많이 지원하는 것이 항상 제품을 더 좋게 만드는 것은 아니다.

핵심 사용 경로를 하나 정하고 그 경로에서 경험을 깊게 만드는 것이 중요했다.

---

# 5. News → Action

## 문제

기존 뉴스 요약은 읽고 끝났다.

사용자 입장에서는 "그래서 내가 무엇을 해보면 되는가?"라는 다음 행동이 남아 있었다.

## 선택

상세 요약 시 다음 정보를 함께 생성하도록 했다.

- actionability: 0~5
- action type
- action title
- steps
- effort

actionability가 높은 기사만 Slack에 Action을 노출했다.

## 선택 이유

모든 기사에 Action을 강제로 만들면 의미 없는 "공부해보세요" 형태의 문장이 늘어날 가능성이 높았다.

따라서 실제로 적용 가치가 높은 기사에만 Action을 만들었다.

또한 별도 Gemini 호출을 추가하지 않고 기존 상세 요약 호출에 포함시켜 비용과 지연을 늘리지 않았다.

## 배운 점

LLM 기능은 생성량을 늘리는 것보다 "언제 생성하지 않을 것인가"를 설계하는 것이 중요했다.

---

# 6. Slack Feedback 수집

## 문제

관심 키워드만으로는 사용자가 실제 어떤 추천을 좋아했는지 알 수 없었다.

## 고려한 선택지

### Interactive Button
UX는 좋지만 별도의 이벤트 서버와 request verification이 필요하다.

### Slack Reaction
기존 Slack 환경 안에서 쉽게 사용할 수 있고 주기적 polling으로 수집 가능하다.

## 최종 선택

1차 MVP는 Slack Reaction.

- 👍 도움됨
- 👎 별로
- 🔥 이런 거 더
- 🙈 이 주제 줄이기

## 선택 이유

현재 프로젝트는 GitHub Actions 중심으로 운영되고 있다.

Reaction 방식은 새로운 상시 서버를 추가하지 않고도 기존 인프라를 유지하면서 피드백 데이터를 쌓을 수 있다.

## 배운 점

좋은 아키텍처는 가장 최신 기술을 사용하는 구조가 아니라 현재 제품 단계와 운영 비용에 맞는 구조다.

---

# 7. Feedback Learning

## 문제

피드백을 저장만 하면 개인화가 아니다.

다음 추천 결과가 실제로 변해야 했다.

## 선택

반응별 가중치를 다르게 주었다.

- 👍 +0.25
- 👎 -0.25
- 🔥 +0.75
- 🙈 -0.75

기사 topic과 신규 기사 title/preview가 실제 매칭될 때 relevance를 최대 ±1 보정한다.

significance는 변경하지 않는다.

## 선택 이유

피드백 하나 때문에 추천 결과가 크게 흔들리는 것을 막기 위해 약한 보조 신호로 사용했다.

또한 사용자가 특정 주제를 싫어하더라도 중요한 보안/플랫폼 변화까지 숨겨지면 안 되므로 significance는 개인화 대상에서 제외했다.

## 배운 점

개인화는 강할수록 좋은 것이 아니다.

초기 피드백 데이터가 적을 때는 보수적으로 반영하고, 중요 정보 보호 장치를 별도로 두는 것이 안전하다.

---

# 8. Trend Radar

## 문제

기사 단위 추천만으로는 기술 변화의 방향을 보기 어렵다.

여러 기사에서 같은 주제가 반복되는 현상을 "하나의 흐름"으로 보여줄 필요가 있었다.

## 선택

상세 기사 metadata를 누적하고:

    최근 7일
    vs
    이전 7일

topic 빈도 변화를 비교한다.

실제 증가한 topic만 Rising Topic으로 선정하고, 관련 기사 내용을 Gemini가 다시 묶어 흐름을 해석한다.

## 선택 이유

LLM에게 단순히 "요즘 뭐가 유행인지 말해줘"라고 하면 근거 없는 트렌드가 만들어질 수 있다.

먼저 실제 수집 데이터로 후보 trend를 계산하고, LLM은 해석에만 사용하도록 역할을 분리했다.

## 배운 점

LLM은 데이터 계산보다 의미 해석에 사용할 때 더 안정적이다.

정량 조건과 생성형 해석을 분리하면 hallucination을 줄일 수 있다.

---

# 9. Newspaper Web으로 확장

## 문제

Slack은 전달에는 강하지만 콘텐츠가 시간순으로 흘러가고 장기 아카이브와 탐색에는 약하다.

현재 TechNews에는 이미 다음 내용이 생겼다.

- 기사 선별
- 상세 요약
- News → Action
- Feedback Learning
- Trend Radar

하지만 이 정보들이 Slack 메시지 안에만 존재하면 제품의 전체 가치를 한눈에 보여주기 어렵다.

## 고려한 선택지

### A. Slack 메시지를 계속 고도화

장점:
- 구현 비용이 가장 작음
- 기존 사용자 경험 유지

단점:
- 정보량이 늘수록 가독성 저하
- 과거 issue 탐색이 어려움
- 포트폴리오 시각적 전달력이 낮음

### B. React/Next.js 기반 полноцен한 웹 애플리케이션부터 제작

장점:
- 확장성 높음
- 검색/필터/사용자 계정 추가에 유리

단점:
- 현재 검증 단계에서 프론트엔드 복잡도가 지나치게 커질 수 있음
- 기존 데이터 파이프라인보다 UI 개발이 중심이 될 위험

### C. 정적 Daily Newspaper Web을 먼저 제작

장점:
- 현재 GitHub Actions 구조와 잘 맞음
- 서버 운영 없이 시작 가능
- 매일 issue를 파일 형태로 보존 가능
- 추후 Next.js 등으로 마이그레이션 가능

## 최종 선택

1차는 **정적 Newspaper Web**으로 진행한다.

역할을 다음과 같이 분리한다.

    Slack
    = 알림 / 빠른 소비 / 피드백

    Newspaper Web
    = 읽기 / 탐색 / 아카이브 / 시각적 경험

## 선택 이유

현재 단계에서 가장 중요한 것은 새로운 백엔드 기능 추가가 아니라 이미 만들어진 지능형 기능을 사용자가 잘 볼 수 있는 형태로 재구성하는 것이다.

정적 사이트는 기존 GitHub Actions 기반 운영 방식과 가장 자연스럽게 연결된다.

## 1차 목표 UI

- Masthead / 날짜 / Issue Number
- Top Stories
- Action Desk
- Trend Radar
- More News
- Sources
- Daily Archive

디자인 방향은 사용자가 제시한 신문 레이아웃의 특징을 참고하되 그대로 복제하지 않고 TechNews 고유 스타일로 재구성한다.

## 저작권 관련 선택

웹에는 원문 전체를 재게시하지 않는다.

다음만 제공한다.

- 원문 제목
- 출처
- 자체 생성 요약
- 자체 분석
- Action
- 원문 링크

---

# 10. 현재 진행 단계

현재 브랜치:

    feature/newspaper-web

다음 구현 순서:

1. Daily Issue 데이터 모델
2. 정적 HTML generator
3. Newspaper CSS
4. Archive 생성
5. GitHub Pages 배포 workflow
6. Slack에 "오늘 신문 읽기" 링크 연결
7. 모바일 가독성 개선
8. 실제 운영 후 UI 조정

---

# 11. 최종 PDF 구성 예정

최종 PDF는 다음 구조로 정리한다.

1. 프로젝트 배경
2. 초기 문제 정의
3. 전체 아키텍처 변화
4. 단계별 고도화 과정
5. 주요 기술적 선택과 Trade-off
6. 실패/제약/운영 이슈
7. LLM 사용 방식의 변화
8. 개인화 설계
9. Trend Radar 설계
10. Newspaper Web 전환
11. 최종 시스템 아키텍처
12. 결과 화면
13. 테스트 및 운영 전략
14. 배운 점
15. 이후 개선 방향

최종 문서는 단순 개발일지가 아니라 "문제를 발견하고 제품/기술 의사결정을 반복한 과정"이 보이는 사례 보고서로 만든다.

---

# 12. Newspaper Web 1차 구현: 데이터와 표현 분리

## 문제

Slack Digest 문자열을 그대로 HTML로 변환하면 구현은 빠르지만 웹 UI가 Slack 메시지 포맷에 종속된다.

이 경우 다음 문제가 생긴다.

- Slack 문구를 바꾸면 웹 파싱도 깨질 수 있음
- Action, topic, score를 다시 정규식으로 추출해야 함
- Archive/Search 기능 확장 시 구조화 데이터가 부족함
- 웹과 Slack 중 하나가 다른 표현을 원할 때 수정 범위가 커짐

## 고려한 선택지

### A. Slack Digest 문자열 재사용

장점:
- 구현량이 가장 작음

단점:
- presentation 문자열을 다시 parsing해야 함
- 데이터 손실 가능성
- 장기 운영에 취약

### B. 기존 article_history.json만 사용

장점:
- 이미 구조화된 데이터 존재

단점:
- 하루 단위 편집 결과와 Top Story 순위가 없음
- brief article과 editorial note가 보존되지 않음
- 당시 발행 상태를 그대로 재현하기 어려움

### C. Daily Issue를 별도 JSON 계약으로 저장

장점:
- 한 번 발행한 신문을 동일하게 재현 가능
- Slack/Web UI가 같은 원천 데이터를 공유할 수 있음
- 향후 검색, RSS, API, 모바일 UI로 확장 가능

## 최종 선택

C를 선택했다.

매일 다음 경로에 발행 데이터를 저장한다.

    config/issues/YYYY-MM-DD.json

Daily Issue에는 다음 정보가 포함된다.

- issue number / issue date
- 발행 통계
- Top Stories
- 기타 상세 기사
- brief 기사
- editor's note
- topic
- News → Action
- 원문 URL

## 선택 이유

UI는 바뀔 가능성이 높지만 발행 데이터는 장기 자산이다.

따라서 데이터 모델을 Slack과 Web보다 먼저 독립시키는 것이 장기 운영에 유리하다고 판단했다.

## 배운 점

"화면을 만드는 것"과 "발행 데이터를 정의하는 것"은 다른 문제다.

운영 서비스에서는 presentation 문자열보다 재현 가능한 structured data를 먼저 확보하는 것이 중요했다.

---

# 13. 프론트엔드 선택: 정적 생성 vs 서버형 웹

## 문제

Newspaper UI를 실제 서비스로 운영하려면 배포 구조가 필요하다.

## 고려한 선택지

### Next.js + Vercel

장점:
- 동적 라우팅
- 검색/로그인/API 확장 용이

단점:
- 현재 단계에서는 런타임과 프론트엔드 의존성이 증가
- 기존 Python/GitHub Actions 파이프라인과 별도 운영 구조가 생김

### Python Static Site Generator + GitHub Pages

장점:
- 기존 Python 코드와 바로 연결
- 서버가 필요 없음
- 날짜별 Issue를 파일로 영구 보존 가능
- 장애 지점과 비용이 적음

단점:
- 서버 검색, 로그인, 사용자별 페이지에는 한계

## 최종 선택

1차 운영 버전은 Python Static Site Generator + GitHub Pages.

## 선택 이유

현재 필요한 기능은:

- 오늘 발행본
- Action Desk
- Trend Radar
- Archive
- 원문 이동

으로 모두 정적 HTML에서 해결 가능하다.

사용자 계정과 서버 검색은 아직 검증되지 않은 요구사항이므로, 미리 복잡성을 추가하지 않기로 했다.

## 구현

    Daily Tech News
        ↓
    config/issues/YYYY-MM-DD.json
        ↓
    Git commit to main
        ↓
    Pages workflow trigger
        ↓
    build_newspaper.py
        ↓
    public/
        ├─ index.html
        ├─ archive/index.html
        ├─ issues/YYYY-MM-DD/index.html
        └─ assets/styles.css
        ↓
    GitHub Pages

## 디자인 선택

사용자가 제공한 신문 레이아웃에서 다음 원칙을 참고했다.

- 검정 배경 + 밝은 종이 면
- 큰 Masthead
- Serif 중심 기사 제목
- 작은 section label
- 얇은 rule line
- 2단 Top Story
- 명확한 Issue/Date 표기

원본 디자인을 그대로 복제하지 않고 TechNews용 정보 구조와 반응형 레이아웃으로 재구성했다.

## 모바일 대응

신문형 2단 레이아웃은 작은 화면에서 그대로 유지하면 읽기 어렵다.

따라서 모바일에서는:

- Top Story 1단
- Action 1단
- Editorial 1단
- Navigation horizontal scroll

로 전환한다.

## 첫 발행 데이터가 없을 때의 선택

가짜 샘플 뉴스를 배포하지 않는다.

Issue가 하나도 없으면:

    첫 발행을 준비하고 있습니다.

화면을 표시한다.

실제 Daily 실행으로 데이터가 생성된 뒤 자동으로 첫 신문이 발행된다.

## 배운 점

운영 서비스의 초기 화면에서는 "보기 좋은 가짜 데이터"보다 실제 시스템 상태를 정확히 보여주는 것이 중요하다.

또한 정적 사이트는 단순한 기술이지만 데이터 생성 주기가 하루 단위인 서비스에는 오히려 적절한 선택이 될 수 있다.

---

# 14. 현재 Newspaper Web 1차 구조

현재 구현 범위:

- Daily Issue JSON 저장
- Latest Issue 홈
- 날짜별 Issue 페이지
- Archive
- Top Stories
- News → Action Desk
- Trend Radar 데이터 표시
- Editor's Note
- More News
- 원문 링크
- 반응형 디자인
- GitHub Pages 자동 배포
- HTML escaping 테스트
- 빈 데이터 fallback

다음 운영 검증 항목:

- 실제 기사 제목 길이에 따른 레이아웃 변화
- Action 길이와 카드 높이
- 모바일 가독성
- Issue 파일 증가 시 build 시간
- Trend Radar 정보 밀도
- Slack에서 Web으로 이동하는 비율
- 원문 클릭 동선

---

# 15. Slack의 역할 재정의: 읽는 화면에서 배달 채널로

## 문제

Newspaper Web이 생긴 뒤에도 Slack에 모든 정보를 길게 제공하면 웹과 Slack의 역할이 중복된다.

두 채널이 같은 역할을 하면 사용자는 어디에서 읽어야 하는지 애매해지고, 같은 콘텐츠를 두 번 유지해야 한다.

## 선택

Slack은 다음 역할에 집중한다.

- 오늘 발행 알림
- 핵심 기사 요약
- 빠른 피드백
- 오늘 Newspaper로 이동하는 진입점

웹은 다음 역할을 담당한다.

- 전체 읽기
- Action 확인
- Trend 탐색
- Archive
- 날짜별 발행본 보존

## 구현

Daily Slack Digest에 해당 날짜의 Newspaper Issue 링크를 추가했다.

    https://dev-gony.github.io/technews/issues/YYYY-MM-DD/

페이지가 먼저 생성되어야 하는 구조가 아니라, Daily 실행에서 Issue JSON을 만든 뒤 runtime state를 main에 commit하고 Pages workflow가 자동 배포하는 구조다.

Slack 메시지는 발행 URL을 미리 알려주며, Pages 배포가 끝나면 같은 URL에서 당일 신문을 읽을 수 있다.

## 선택 이유

Slack을 별도의 완성형 콘텐츠 화면으로 계속 확장하면 메시지가 길어지고, 웹 UI와 중복 구현이 늘어난다.

배달 채널과 읽기 채널을 분리하면 각 인터페이스의 강점을 살릴 수 있다.

## 배운 점

멀티채널 서비스에서 중요한 것은 모든 채널에 같은 기능을 넣는 것이 아니라 각 채널의 역할을 명확히 정하는 것이다.

---

# 16. 첫 실운영 발행 실패와 테스트 보강

## 발생한 문제

첫 Newspaper Web 실데이터 발행을 위해 Daily Tech News workflow를 수동 트리거했으나 상세 요약 단계에서 실행이 중단됐다.

오류:

    ValueError: Invalid format specifier ...

원인은 `build_detail_prompt()`의 f-string 안에 포함된 Action JSON 예시의 중첩 중괄호였다.

Python f-string에서는 실제 중괄호를 출력하려면 `{{`와 `}}`로 escape해야 한다.

기존 outer JSON object는 escape되어 있었지만 새로 추가된 nested `action` object는 일반 `{` / `}`를 사용하고 있었다.

## 왜 기존 테스트에서 발견되지 않았나

News → Action 기능 개발 당시 테스트는 다음을 검증했다.

- actionability가 높을 때 Slack Action 출력
- 낮을 때 미출력
- 잘못된 Action 데이터 fallback

하지만 실제 Gemini 상세 prompt를 **끝까지 문자열로 렌더링하는 테스트**는 없었다.

즉 데이터 formatting 함수는 테스트했지만 prompt construction 경로는 테스트하지 못했다.

## 수정

nested Action JSON 예시의 중괄호를 f-string literal 형식으로 escape했다.

추가로 다음 회귀 테스트를 만들었다.

    build_detail_prompt(...)
    → 실제 prompt 생성
    → nested action JSON 포함 확인

## 배운 점

LLM 기반 애플리케이션에서는 prompt도 코드다.

프롬프트를 단순 문자열 리소스로 취급하면 syntax/formatting 오류가 실제 API 호출 직전까지 숨어 있을 수 있다.

특히 f-string, JSON example, Markdown example이 섞이는 prompt는 다음을 테스트해야 한다.

- prompt 함수가 실제 입력으로 정상 렌더링되는가
- placeholder가 의도대로 치환되는가
- JSON 예시가 깨지지 않는가

또한 Unit Test가 모두 통과해도 운영 경로 전체가 검증된 것은 아니다.

이번 사례를 통해 **unit test → production workflow smoke test**의 두 단계 검증이 필요하다는 것을 확인했다.

---

# 17. GitHub Actions 간 자동 배포 연결 문제

## 발생한 문제

Daily Tech News가 성공적으로 `config/issues/YYYY-MM-DD.json`을 생성하고 main에 commit했지만 Newspaper Pages workflow가 자동으로 실행되지 않았다.

## 원인

Daily workflow가 사용하는 기본 `GITHUB_TOKEN`으로 push된 commit은 보안상 다른 GitHub Actions workflow의 `push` trigger를 연쇄 실행하지 않는다.

즉 다음 구조는 의도대로 동작하지 않았다.

    Daily Tech News
    → GITHUB_TOKEN으로 main commit
    → push event
    → Pages workflow

## 고려한 선택지

### A. PAT를 사용해 commit

장점:
- 일반 사용자 push처럼 다른 workflow trigger 가능

단점:
- 별도 Personal Access Token 관리 필요
- 권한 범위와 secret 관리 부담 증가

### B. Daily workflow 안에서 Pages까지 직접 배포

장점:
- 단일 workflow로 확실하게 실행

단점:
- 뉴스 수집/Slack 발송과 웹 배포 책임이 한 workflow에 결합
- 배포만 다시 실행하기 어려움

### C. Pages workflow를 `workflow_run`으로 연결

장점:
- PAT 추가 필요 없음
- Daily workflow와 Pages workflow의 책임 분리 유지
- Daily 성공 후 독립적으로 웹 배포 가능

## 최종 선택

C를 선택했다.

Pages workflow는 다음 이벤트에서 실행된다.

- main의 웹 코드 직접 변경
- 수동 실행
- `Daily Tech News` workflow 성공 완료

Daily workflow가 실패하면 Pages 배포는 실행하지 않는다.

## 첫 Pages 배포에서 발견한 추가 문제

`actions/configure-pages`에서 Pages 사이트를 자동 생성하려 했으나 GitHub App integration 권한으로 repository Pages를 최초 활성화할 수 없어 다음 오류가 발생했다.

    Resource not accessible by integration

사이트 build 자체는 성공했다.

## 대응

workflow에서는 Pages 최초 생성 책임을 제거하고, 이미 활성화된 Pages 설정을 사용하는 구조로 변경했다.

저장소에서 최초 1회:

    Settings
    → Pages
    → Build and deployment
    → Source: GitHub Actions

설정이 필요하다.

이후 배포는 자동으로 수행된다.

## 배운 점

CI/CD 설계에서는 코드뿐 아니라 플랫폼의 trigger 규칙과 token 권한 모델을 이해해야 한다.

같은 GitHub Actions 안에서도:

- 어떤 token으로 commit했는지
- 어떤 event가 새 workflow를 발생시키는지
- repository administration 권한이 필요한 작업인지

에 따라 자동화가 달라진다.

운영 자동화에서는 기능 흐름뿐 아니라 **event chain 자체를 smoke test**해야 한다.

---

# 18. 첫 실데이터 발행과 Pages 공개 성공

## 첫 발행 결과

2026-09-19 첫 실데이터 Newspaper Issue를 실제 운영 파이프라인으로 생성했다.

수집/선별 결과:

- 신규 후보 기사: 20개
- 상세 기사: 9개
- 짧은 소개: 2개
- 제외: 9개
- 평가 보류: 0개
- Top Story: 3개

첫 발행 파일:

    config/issues/2026-09-19.json

## News → Action 검증

첫 호의 Top Story 중 actionability가 높은 기사에는 실제 Action이 생성됐다.

예를 들어 Agent-Native 기사에는:

- Actionability: 5
- 유형: experiment
- 예상 작업량: 30~60분
- 프로젝트 생성 → action 정의 → UI/Agent 동작 검증

순서의 실행 단계가 생성됐다.

이를 통해 News → Action이 단순 문구 추가가 아니라 실제 발행 데이터 구조 안에서 정상 동작하는 것을 확인했다.

## Pages 최초 공개

GitHub Pages를 Repository Settings에서 최초 1회 활성화한 뒤 실패한 Pages workflow를 재실행했다.

검증 결과:

- static newspaper build 성공
- Pages configuration 성공
- artifact upload 성공
- deploy 성공
- GitHub Pages deployment status: success

공개 URL:

    https://dev-gony.github.io/technews/

## 첫 운영 검증에서 얻은 결과

이번 단계에서 Unit Test만으로는 발견하지 못했던 두 가지 운영 이슈를 실제 smoke test에서 발견했다.

1. f-string 내부 nested JSON prompt escaping 오류
2. GITHUB_TOKEN commit이 다음 workflow를 push event로 연쇄 실행하지 않는 GitHub Actions 제약

둘 다 실제 운영 흐름을 태우지 않았다면 놓칠 수 있는 문제였다.

## 배운 점

"배포 가능한 코드"와 "실제로 운영되는 서비스" 사이에는 차이가 있다.

실제 서비스 검증에서는 다음을 모두 확인해야 했다.

- 외부 API 호출
- Secrets 주입
- LLM prompt runtime rendering
- 상태 파일 생성
- repository commit
- workflow event chain
- Pages 권한
- artifact upload
- production deployment

이번 첫 발행을 통해 TechNews는 단순 개발 단계에서 실제 운영 가능한 Newspaper 서비스 단계로 넘어갔다.

