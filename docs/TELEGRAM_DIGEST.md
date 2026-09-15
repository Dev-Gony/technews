# Telegram On-demand Digest

## 목적

Telegram에서 사용자가 원하는 기술 주제를 직접 요청하고, 기존 Tech News Bot의 수집·AI 평가·요약 기능을 즉시 실행한다.

예시:

```text
/digest MCP
/digest AI Agent
/digest Python automation
```

## 동작 흐름

```text
Telegram /digest 요청
→ 기존 등록 기술 소스에서 최근 글 수집
→ URL/제목 중복 제거
→ 요청 키워드 기반 1차 후보 압축
→ Gemini가 요청 관련성·실무 가치·중요도 평가
→ 상위 최대 3개 선택
→ 본문/RSS 내용 확보
→ Gemini 요약
→ Telegram 응답
```

## 현재 범위

이번 버전은 기존에 등록된 기업 기술 블로그 및 GeekNews 소스를 재사용한다.

외부 웹 전체 검색은 아직 하지 않는다.

따라서 `/digest`는 "웹 검색 Agent"가 아니라 "등록 기술 소스를 도구처럼 호출하는 온디맨드 뉴스 Agent" 단계다.

## 비용 및 API 호출

요청 한 번에 기본적으로 Gemini를 최대 2회 호출한다.

1. 후보 기사 순위 평가
2. 최종 선정 기사 요약

기존 일일 브리핑보다 호출 수를 작게 유지해 무료 API 한도에서 테스트하기 쉽게 구성한다.

## 후보 선택

각 활성 소스에서 최근 글을 최대 5개 확인한다.

먼저 제목과 RSS 미리보기에서 요청 키워드를 기준으로 후보를 압축하고, 최대 25개만 Gemini 평가 대상으로 전달한다.

직접 키워드 매치가 전혀 없으면 최근 글 후보를 대상으로 Gemini가 관련성을 판단한다.

## Gemini 평가 기준

각 후보는 다음 3개 기준으로 0~5점 평가한다.

- `query_relevance`: 사용자가 요청한 주제와의 직접 관련성
- `practical_value`: 프로젝트·학습·실무 활용 가치
- `significance`: 기술적 중요도

요청 관련성이 3점 미만인 글은 최종 결과에서 제외한다.

최종 결과는 최대 3개다.

## Telegram 응답

각 글은 다음 정보를 포함한다.

- 제목
- 출처
- AI 평가 점수
- 핵심 한 문장
- 왜 중요한지
- 가져갈 실무/학습 포인트
- 원문 링크

Telegram 메시지 길이 제한을 고려해 최종 응답은 3,900자 이하로 제한한다.

## 필요한 Secrets

GitHub Actions에는 다음 Secret이 필요하다.

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_CHAT_ID`
- `GEMINI_API_KEY`

기존 일일 Tech News Bot에서 사용하던 `GEMINI_API_KEY`를 그대로 재사용한다.

## 테스트 방법

release 후 Telegram에서 다음 메시지를 보낸다.

```text
/digest MCP
```

GitHub Actions의 `Telegram Preference Poll`이 실행되면 먼저 다음 안내 메시지가 온다.

```text
'MCP' 관련 기술 뉴스를 찾고 있어요. 잠시만 기다려주세요.
```

수집과 AI 평가가 끝나면 최대 3개의 추천 글이 Telegram으로 전달된다.

## 현재 제한

- 기존 등록 소스 안에서만 찾는다.
- GitHub Actions polling 주기에 따라 응답 시작까지 지연될 수 있다.
- 다수 소스의 RSS/HTML 수집 시간 때문에 일반 설정 명령보다 처리 시간이 길다.
- 외부 사이트 장애 또는 Gemini API 한도에 따라 일부 요청이 실패할 수 있다.

## 다음 단계

이 기능이 안정화되면 다음 순서로 확장한다.

1. 자연어 요청 지원
   - `오늘 MCP 쪽 뭐 볼 만한 거 있어?`
2. 외부 검색 Tool 추가
3. 후속 질문 지원
   - `2번 더 자세히`
4. 사용자 피드백 저장
   - 관심 있음 / 별로임
5. Webhook 기반 실시간 Telegram Agent 전환
