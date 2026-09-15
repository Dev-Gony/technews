# Personalized AI Tech News Agent 고도화 계획

## 1. 목표

현재의 Daily Tech News Bot을 단순 예약 실행형 자동화에서 사용자의 관심사와 요청에 따라 뉴스 탐색, 선별, 요약, 전달 방식을 조정하는 개인화 AI Tech News Agent로 발전시킨다.

현재 시스템은 이미 다음 기능을 가지고 있다.

- RSS / Atom / HTML 기반 기술 콘텐츠 수집
- 신규 글 판별 및 처리 이력 관리
- URL 및 제목 기준 중복 제거
- Gemini 기반 관련성, 실무 가치, 중요도 평가
- 점수에 따른 상세 요약 / 짧은 소개 / 제외 분류
- 배치 단위 AI 평가 및 요약
- Slack 자동 발송
- GitHub Actions 예약 실행

V2에서는 이 기능들을 버리지 않고 Agent가 사용할 수 있는 기능 단위로 재구성한다.

---

## 2. 현재 버전과 Agent 버전의 차이

### 현재 V1

현재 흐름은 코드에 정해진 순서대로 실행된다.

    정해진 소스 수집
    -> 신규 글 판별
    -> 고정된 관심 분야로 평가
    -> 점수에 따라 분류
    -> 요약
    -> Slack 전송

LLM이 기사 중요도를 판단하지만 전체 실행 흐름은 미리 정해져 있다.

따라서 현재 단계는 "LLM 기반 뉴스 큐레이션 자동화"로 정의한다.

### 목표 V2

Agent는 사용자의 목표와 관심사를 입력으로 받아 필요한 행동을 선택한다.

예:

    사용자: "요즘 MCP와 AI Agent 관련해서 중요한 것만 알려줘"

    Agent
    -> 현재 관심사 확인
    -> 기존 수집 소스 확인
    -> 관련 뉴스 후보 탐색
    -> 필요하면 추가 검색 수행
    -> 중복 기사 통합
    -> 사용자 기준으로 적합도 평가
    -> 중요한 기사만 원문 분석
    -> 요약 및 선정 이유 작성
    -> Slack 또는 Telegram으로 전달

핵심 차이는 "LLM을 한 단계에서 사용하는가"가 아니라 "목표를 받은 뒤 어떤 도구와 단계를 사용할지 Agent가 판단할 수 있는가"이다.

---

## 3. V2 MVP 범위

처음부터 완전 자율형 Agent를 만들지 않는다.

V2 MVP는 다음 네 가지에 집중한다.

### 3.1 사용자 관심사 외부 설정

현재 코드 안에 들어 있는 관심 분야를 별도 설정 데이터로 분리한다.

예:

```json
{
  "interests": [
    "AI Agent",
    "Agentic Workflow",
    "MCP",
    "LLM",
    "Python",
    "업무 자동화"
  ],
  "avoid_topics": [],
  "detailed_score_threshold": 11,
  "brief_score_threshold": 9,
  "language": "ko"
}
```

이 단계의 목적은 이후 Slack 또는 Telegram 명령으로 관심사를 바꿔도 main.py를 직접 수정하지 않도록 만드는 것이다.

### 3.2 대화형 관심사 관리

사용자가 채팅으로 관심사를 추가, 삭제, 조회할 수 있게 한다.

예상 명령:

    /interests
    /add MCP
    /add Cloud FinOps
    /remove SQL
    /digest AI Agent

MVP 입력 채널은 Telegram을 우선 검토한다.

이유:

- 기존 Slack Incoming Webhook은 발송용이므로 사용자 메시지를 받는 기능이 없다.
- Slack에서 메시지를 받으려면 별도의 Slack App 이벤트 처리 구조가 필요하다.
- Telegram Bot은 개인 프로젝트에서 양방향 명령 인터페이스를 작게 시작하기 쉽다.

Slack은 기존 데일리 브리핑 전달 채널로 유지할 수 있다.

최종 채널은 구현 전에 다시 결정한다.

### 3.3 개인화 평가

기사 평가 프롬프트에 하드코딩된 관심사 대신 사용자 설정 데이터를 전달한다.

평가 기준은 현재 구조를 유지한다.

- relevance: 사용자 관심사와의 관련성
- practical_value: 실무, 프로젝트, 학습 활용 가치
- significance: 기술 및 업계 중요도

기본 분류:

    11~15점 -> 상세 브리핑
    9~10점 -> 짧은 소개
    0~8점 -> 제외

단, 이후 사용자가 "이런 뉴스는 별로다" 또는 "이 주제는 더 보고 싶다"라고 피드백하면 관심사 또는 가중치를 수정할 수 있도록 확장한다.

### 3.4 요청형 Digest

예약 실행 외에 사용자가 특정 주제의 뉴스를 요청할 수 있게 한다.

예:

    /digest MCP
    /digest AI Agent
    /digest Cloud 비용 절감

MVP에서는 먼저 현재 보유한 수집 소스 안에서 관련 콘텐츠를 찾는다.

그 다음 단계에서 검색 API 또는 웹 검색 도구를 추가해 고정 RSS 목록 밖까지 탐색 범위를 확장한다.

---

## 4. 목표 아키텍처

```text
User
  |
  | 관심사 / 질문 / 피드백
  v
Interaction Layer
  - Telegram Bot
  - 이후 Slack App 지원 가능
  |
  v
Agent Controller
  - 사용자 의도 파악
  - 필요한 작업 선택
  - 사용자 설정 로드
  |
  +-----------------------------+
  |              |              |
  v              v              v
Collector      Evaluator      Summarizer
RSS / HTML     Gemini         Gemini
GeekNews       relevance      상세 요약
추후 Search    value          핵심 개념
               significance
  |              |              |
  +--------------+--------------+
                 |
                 v
           Dedup / State
           처리 이력
           사용자 관심사
           피드백 기록
                 |
                 v
             Delivery
          Slack / Telegram
```

---

## 5. Agent Tool 후보

기존 main.py의 기능을 이후 다음 Tool 단위로 나누는 것을 목표로 한다.

### collect_articles

역할:

- 등록된 RSS / HTML 소스에서 최신 글 수집

입력:

- source
- recent limit

출력:

- title
- link
- source
- published_at
- RSS content / summary

### deduplicate_articles

역할:

- URL 및 제목 기준 중복 제거
- 기존 처리 이력과 비교

### evaluate_articles

역할:

- 사용자 관심사와 기사 후보를 비교
- relevance / practical_value / significance 점수 계산

### fetch_article_content

역할:

- 상세 분석이 필요한 기사만 본문 확보

### summarize_articles

역할:

- 상세 기사 배치 요약

### create_digest

역할:

- 최종 기사 순위 및 데일리 브리핑 생성

### send_message

역할:

- Slack 또는 Telegram으로 결과 전송

### update_preferences

역할:

- 사용자 관심사 추가 / 삭제 / 조회

---

## 6. 사용자 설정 데이터

초기 MVP에서는 데이터베이스를 바로 도입하지 않는다.

개인용 Agent이므로 JSON 파일부터 시작한다.

예상 파일:

    config/user_preferences.json

예상 구조:

```json
{
  "profile_name": "default",
  "interests": [
    "AI Agent",
    "Agentic Workflow",
    "LLM",
    "RAG",
    "MCP",
    "Python",
    "데이터 분석",
    "SQL",
    "업무 자동화",
    "서버",
    "클라우드",
    "백엔드 아키텍처",
    "비용 절감",
    "성능 개선"
  ],
  "avoid_topics": [],
  "scoring": {
    "detailed_threshold": 11,
    "brief_threshold": 9
  },
  "delivery": {
    "daily_digest": true,
    "language": "ko"
  }
}
```

공개 저장소이므로 개인 식별 정보, 토큰, Webhook URL, API Key는 저장하지 않는다.

---

## 7. 상태 데이터 구분

현재 `sent_articles.json`은 처리 이력 역할을 한다.

V2에서는 상태를 목적별로 나누는 것을 검토한다.

### processed_articles

이미 평가 또는 전달한 기사

### user_preferences

사용자의 관심사 및 기준

### feedback

사용자가 뉴스 추천에 대해 남긴 피드백

예:

```json
{
  "article_id": "...",
  "feedback": "less_like_this",
  "topic": "hardware news"
}
```

MVP에서는 과도한 상태 구조를 만들지 않고 필요해질 때 분리한다.

---

## 8. 뉴스 탐색 전략

V2를 두 단계로 나눈다.

### 단계 A: 기존 소스 기반 Agent

사용 가능한 현재 자산:

- 약 30개 기술 블로그 / 기술 소스
- GeekNews
- RSS / Atom / HTML 수집기

먼저 이 데이터 안에서 사용자의 요청을 처리한다.

장점:

- 이미 검증한 수집 코드 재사용
- 비용과 복잡도 낮음
- 기존 자동화가 깨질 위험이 적음

### 단계 B: 외부 뉴스 탐색

기존 소스만으로 부족할 때 추가 검색을 수행한다.

후보:

- 공식 API
- 검색 API
- 공개 RSS
- 검색엔진 기반 결과
- 공식 기업 / 프로젝트 사이트

특정 사이트 이용약관이나 접근 제한을 우회하는 방식은 사용하지 않는다.

Agent가 무조건 검색하는 것이 아니라 현재 소스만으로 충분한지 먼저 판단하는 방향을 목표로 한다.

---

## 9. 사용자 경험 예시

### 관심사 등록

    사용자
    /add MCP

    Agent
    관심사에 MCP를 추가했습니다.
    현재 관심사: AI Agent, Agentic Workflow, MCP, Python, 업무 자동화

### 요청형 뉴스

    사용자
    /digest MCP

    Agent
    최근 수집된 콘텐츠에서 MCP 관련 후보를 찾았습니다.
    관련성 및 실무 가치를 평가한 뒤 우선순위가 높은 글을 정리합니다.

### 후속 질문

    사용자
    2번을 더 자세히 알려줘

    Agent
    해당 글의 원문을 기준으로 핵심 구조, 활용 포인트, 알아둘 개념을 추가로 설명합니다.

### 피드백

    사용자
    이런 하드웨어 뉴스는 별로 관심 없어

    Agent
    이후 추천에서 해당 유형의 우선순위를 낮추도록 관심 설정에 반영합니다.

피드백 학습은 V2 MVP 이후 단계로 둔다.

---

## 10. 단계별 구현 계획

### Phase 1. 개인화 설정 분리

목표:

- 하드코딩된 관심사를 JSON 설정으로 분리
- 기존 데일리 자동화 동작은 그대로 유지

작업:

- `config/user_preferences.example.json` 생성
- 사용자 설정 로더 구현
- 평가 프롬프트가 설정 파일을 사용하도록 변경
- 설정 파일이 없을 때 기본값 fallback

완료 기준:

- main.py의 관심 키워드를 수정하지 않고 JSON만 수정해 평가 기준 변경 가능
- 기존 GitHub Actions 데일리 브리핑 정상 동작

### Phase 2. Telegram 입력 인터페이스

목표:

- 관심사 조회, 추가, 삭제
- 특정 키워드 Digest 요청

작업:

- Telegram Bot 생성
- 명령 parser
- 관심사 JSON 변경
- 요청형 Digest 실행

완료 기준:

- `/add MCP` 후 관심사에 MCP 저장
- `/digest MCP` 요청 시 관련 기사 결과 반환

### Phase 3. Agent Controller

목표:

사용자의 자연어 요청을 해석해 필요한 Tool을 선택한다.

예:

    "오늘 AI Agent 쪽에서 중요한 것만 찾아줘"

Agent 판단:

1. 관심사 로드
2. 현재 수집 데이터 검색
3. 후보 부족 여부 판단
4. 평가
5. 필요한 기사 본문 분석
6. 요약
7. 전달

완료 기준:

- 고정 명령어가 아닌 자연어 요청 처리
- 불필요한 Tool 호출 없이 필요한 단계만 실행

### Phase 4. 외부 검색 Tool

목표:

- 고정 RSS 목록 밖의 뉴스 탐색

완료 기준:

- 기존 소스에서 충분한 결과가 없을 때만 추가 검색
- 원문 출처와 검색 출처 구분
- 중복 기사 통합

### Phase 5. 사용자 피드백 반영

목표:

- 좋아요 / 관심 없음 등의 피드백을 다음 평가에 반영

완료 기준:

- 관심 없는 주제의 점수 감소
- 선호하는 주제의 점수 증가
- 변경된 기준을 사용자가 확인 가능

---

## 11. 구현 우선순위

현재 가장 먼저 구현할 것은 Phase 1이다.

이유:

현재 관심 분야가 main.py 프롬프트 안에 직접 들어 있다.

이 상태에서 Telegram이나 Slack 입력부터 붙이면 사용자의 관심사를 저장하고 재사용할 명확한 구조가 없다.

따라서 먼저 다음 구조를 만든다.

    user_preferences.json
            |
            v
    관심사 / 점수 기준 로드
            |
            v
    기존 AI 평가 파이프라인

이 기반을 만든 뒤 대화형 입력 채널을 연결한다.

---

## 12. 포트폴리오 관점의 발전 스토리

### V1

기술 블로그를 직접 확인하는 반복 업무를 자동화했다.

### V1.5

수집되는 글이 많아지면서 단순 요약만으로는 정보 과부하가 발생했다.

Gemini 기반 중요도 평가와 배치 처리를 도입해 필요한 글만 선별하도록 개선했다.

### V2

개발자가 직접 정한 관심사가 코드에 고정되어 있다는 한계를 해결한다.

사용자가 관심사를 대화로 관리하고, Agent가 요청에 맞는 뉴스 탐색과 분석 작업을 선택하는 개인화 AI Tech News Agent로 확장한다.

이 프로젝트의 핵심은 처음부터 완성된 Agent를 만든 것이 아니라 실제 자동화를 운영하면서 발생한 문제를 단계적으로 해결하고 Agent 구조로 발전시키는 과정이다.

---

## 13. 다음 작업

다음 구현 단계는 `Phase 1. 개인화 설정 분리`이다.

첫 작업:

1. `config/user_preferences.example.json` 생성
2. main.py에 설정 로더 추가
3. 기사 선별 프롬프트에 설정된 관심사 사용
4. 점수 기준도 설정 파일에서 읽기
5. 기존 데일리 브리핑 회귀 테스트

Phase 1이 안정적으로 동작하는 것을 확인한 뒤 Telegram 입력 인터페이스를 추가한다.
