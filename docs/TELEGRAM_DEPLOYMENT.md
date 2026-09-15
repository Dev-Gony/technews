# Telegram Deployment

## 선택한 방식

첫 배포 방식은 GitHub Actions 기반 5분 주기 polling으로 한다.

이 방식은 실시간 응답은 아니지만 현재 개인용 MVP에는 다음 장점이 있다.

- 별도 서버 비용이 없다.
- 기존 GitHub Actions 운영 방식과 일관된다.
- Telegram Bot Token과 허용 Chat ID를 GitHub Secrets로 관리할 수 있다.
- 관심사 변경 내역을 `config/user_preferences.json`에 그대로 남길 수 있다.
- 배포 구조를 단순하게 유지한 채 다음 단계인 `/digest` 기능을 먼저 검증할 수 있다.

## 왜 장기 실행 서버를 바로 쓰지 않는가

Telegram Bot API는 Long Polling과 Webhook 두 방식을 지원한다.

현재 코드는 Long Polling을 지원하지만 무료 호스팅의 장기 실행 조건과 영속 저장소를 함께 고려하면 구조가 복잡해진다.

GitHub Actions 예약 실행은 최소 5분 간격이므로 실시간 대화형 Bot에는 적합하지 않지만, 개인용 MVP의 관심사 설정 기능을 검증하기에는 충분하다.

이번 단계에서는 GitHub Actions가 5분마다 새 Telegram 명령을 한 번 확인하고 종료하도록 구성한다.

실시간성이 중요해지는 시점에는 Webhook 기반 서비스로 전환한다.

## 동작 구조

    Telegram 사용자
        ↓
    /interests, /add, /remove
        ↓
    Telegram Bot API
        ↓
    GitHub Actions
    최대 5분 주기 실행
        ↓
    telegram_sync.py
        ↓
    config/user_preferences.json 수정
        ↓
    변경 내용 commit / push

## 필요한 GitHub Secrets

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_CHAT_ID`

Bot Token은 저장소에 직접 기록하지 않는다.

## 상태 파일

마지막으로 처리한 Telegram update 위치는 다음 파일에 저장한다.

`config/telegram_state.json`

이 파일에는 Bot Token이나 Chat ID를 저장하지 않는다.

예시:

    {
      "offset": null
    }

Workflow가 Telegram 명령을 처리하면 offset을 갱신하고 사용자 설정 변경과 함께 commit한다.

## Workflow

파일:

`.github/workflows/telegram-poll.yml`

실행 방식:

- 수동 실행: `workflow_dispatch`
- 자동 실행: 5분 간격

GitHub Actions 예약 실행은 기본 브랜치의 Workflow만 자동 실행된다.

따라서 이 기능은 `develop` 검증 후 release PR을 통해 `main`에 병합된 뒤 자동 polling이 시작된다.

## 첫 설정 순서

1. Telegram BotFather에서 Bot 생성
2. `TELEGRAM_BOT_TOKEN`을 GitHub Actions Secret에 등록
3. Chat ID를 확인
4. `TELEGRAM_ALLOWED_CHAT_ID`를 GitHub Actions Secret에 등록
5. Workflow 수동 실행으로 `/interests` 테스트
6. `/add 테스트키워드` 입력
7. 다음 polling 실행 후 `config/user_preferences.json` 변경 확인
8. `/remove 테스트키워드`로 원복

## 현재 제한

- 응답까지 최대 약 5분 걸릴 수 있다.
- GitHub Actions 스케줄은 정확한 실시간 실행을 보장하지 않는다.
- 자연어 명령은 지원하지 않는다.
- `/digest` 즉시 뉴스 검색은 아직 지원하지 않는다.

## 다음 단계

이 배포 방식이 안정적으로 동작하면 다음 기능을 구현한다.

`feature/telegram-digest`

목표:

- `/digest MCP`
- `/digest AI Agent`
- 입력 키워드 기반 후보 뉴스 탐색
- 중요도 평가
- 요약
- Telegram 응답

실시간 대화성이 중요해지는 시점에는 Webhook 기반 서비스로 전환한다.
