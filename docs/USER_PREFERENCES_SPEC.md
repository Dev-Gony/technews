# User Preferences Specification

## 목적

Tech News Bot의 관심 분야와 선별 기준을 코드에서 분리해 사용자 설정으로 관리한다.

현재 `main.py`에는 관심 키워드와 점수 기준이 프롬프트 안에 하드코딩되어 있다. V2에서는 이를 설정 파일로 분리해 향후 Telegram 명령이나 다른 인터페이스에서 코드 수정 없이 변경할 수 있도록 한다.

## 이번 단계 범위

이번 단계에서는 다음만 구현한다.

- 사용자 관심 키워드 외부 설정 파일로 분리
- 상세 브리핑 기준 점수 외부 설정
- 짧은 소개 기준 점수 외부 설정
- 언어 설정 외부화
- 설정 파일이 없거나 잘못된 경우 안전한 기본값 사용

이번 단계에서는 다음은 구현하지 않는다.

- Telegram Bot
- 자연어 명령 해석
- 사용자별 다중 프로필
- 외부 웹 검색
- 피드백 기반 자동 학습

## 설정 파일

기본 경로:

`config/user_preferences.json`

예시 파일:

`config/user_preferences.example.json`

예상 구조:

    {
      "profile_name": "default",
      "interests": [
        "AI Agent",
        "MCP",
        "Python"
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

## 동작 규칙

### interests

Gemini 1차 선별 프롬프트의 사용자 우선 관심 분야로 사용한다.

관심사는 문자열 배열로 관리한다.

### avoid_topics

사용자가 우선순위를 낮추고 싶은 주제를 기록한다.

첫 구현에서는 프롬프트에 참고 정보로 전달한다. 강제 제외 규칙으로 사용하지 않는다.

### scoring.detailed_threshold

이 점수 이상인 기사는 상세 요약 대상으로 분류한다.

기본값은 11이다.

### scoring.brief_threshold

이 점수 이상이고 `detailed_threshold` 미만인 기사는 짧은 소개 대상으로 분류한다.

기본값은 9이다.

### delivery.language

요약 및 편집 언어를 지정한다.

첫 구현은 `ko`만 실제 지원한다.

## 안전한 기본값

설정 파일을 찾지 못하거나 JSON 파싱에 실패해도 자동화 전체가 중단되지 않아야 한다.

이 경우 코드 내부 기본값을 사용한다.

기본 관심 분야:

- AI Agent
- Agentic Workflow
- LLM
- RAG
- MCP
- Python
- 데이터 분석
- SQL
- 업무 자동화
- 서버
- 클라우드
- 백엔드 아키텍처
- 비용 절감
- 성능 개선
- 개발 생산성
- Developer Tools
- GitHub 및 소프트웨어 개발 워크플로

기본 점수:

- 상세 브리핑: 11점 이상
- 짧은 소개: 9점 이상

## 완료 조건

다음 조건을 모두 만족하면 이번 기능을 완료한 것으로 본다.

1. `main.py`에서 사용자 관심 분야를 직접 하드코딩하지 않는다.
2. `config/user_preferences.json` 값을 변경하면 다음 실행부터 선별 프롬프트에 반영된다.
3. 점수 기준도 설정 파일에서 읽는다.
4. 설정 파일 오류가 발생해도 기본값으로 계속 실행된다.
5. 기존 RSS 수집, Gemini 평가, Slack 발송 흐름은 깨지지 않는다.

## 검증 방법

1. 기본 설정으로 수동 Workflow 실행
2. Actions 로그에서 로드한 프로필과 관심사 개수 확인
3. 관심사 하나를 테스트 값으로 변경
4. 다시 수동 실행해 Gemini 선별 프롬프트에 변경된 설정이 사용되는지 확인
5. 설정 파일을 임시로 잘못된 JSON으로 만들어 기본값 fallback 로그 확인
6. 정상 설정으로 복구

## 다음 단계

이 기능이 `develop`에 병합되면 다음 기능 브랜치에서 Telegram 인터페이스를 구현한다.

예상 브랜치:

`feature/telegram-interface`

Telegram에서는 이후 다음 명령을 목표로 한다.

    /interests
    /add MCP
    /remove SQL
    /digest AI Agent

이 단계부터 사용자가 코드나 JSON을 직접 수정하지 않고 관심사를 변경할 수 있게 한다.
