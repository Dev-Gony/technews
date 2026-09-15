# Telegram Preference Interface

## 목적

Tech News Bot의 관심사를 Telegram 명령으로 조회하고 변경할 수 있도록 한다.

이번 단계는 뉴스 검색이나 대화형 질의까지 확장하지 않는다. 먼저 사용자 설정을 안전하게 관리하는 입력 인터페이스를 만든다.

## 지원 명령

`/interests`

현재 관심사와 점수 기준을 확인한다.

`/add 키워드`

새 관심사를 추가한다.

예:

    /add FinOps

`/remove 키워드`

기존 관심사를 삭제한다.

예:

    /remove SQL

`/chatid`

현재 Telegram chat id를 확인한다.

`/help`

지원 명령을 확인한다.

## 설정 파일 연결

Telegram 명령은 다음 파일을 변경한다.

`config/user_preferences.json`

예를 들어 Telegram에서:

    /add FinOps

를 실행하면 다음 실행부터 Tech News Bot의 Gemini 선별 프롬프트에 `FinOps`가 관심사로 포함된다.

## 필요한 환경 변수

`TELEGRAM_BOT_TOKEN`

BotFather에서 발급받은 Telegram Bot Token이다.

`TELEGRAM_ALLOWED_CHAT_ID`

설정 변경을 허용할 개인 Telegram chat id다.

보안을 위해 허용된 chat id와 다른 요청은 무시한다.

## 최초 설정 순서

1. Telegram에서 BotFather를 연다.
2. `/newbot` 명령으로 Bot을 생성한다.
3. 발급받은 Bot Token을 `TELEGRAM_BOT_TOKEN`으로 설정한다.
4. 아직 `TELEGRAM_ALLOWED_CHAT_ID`는 비워둔다.
5. `python telegram_bot.py`를 실행한다.
6. Telegram에서 Bot에게 `/chatid`를 보낸다.
7. 응답으로 받은 숫자를 `TELEGRAM_ALLOWED_CHAT_ID`에 설정한다.
8. Bot을 다시 실행한다.
9. `/interests`, `/add`, `/remove`를 테스트한다.

## 실행

    python telegram_bot.py

프로세스는 Telegram Long Polling 방식으로 계속 실행된다.

현재 단계에서는 별도 서버 배포를 포함하지 않는다. 로컬 또는 서버에서 프로세스를 실행할 수 있는 인터페이스까지만 구현한다.

GitHub Actions를 이용한 Telegram 상시 처리 또는 별도 무료 호스팅 배포는 다음 단계에서 결정한다.

## 보안 정책

- Bot Token은 코드에 저장하지 않는다.
- `TELEGRAM_BOT_TOKEN`은 환경 변수 또는 GitHub Secret으로 관리한다.
- 설정 변경 명령은 `TELEGRAM_ALLOWED_CHAT_ID`와 일치하는 사용자만 실행할 수 있다.
- 허용되지 않은 chat id의 요청은 무시한다.
- `config/user_preferences.json`에는 API Key나 개인 인증정보를 저장하지 않는다.

## 오류 처리

Telegram API 연결이 실패하면 5초 후 다시 연결을 시도한다.

설정 파일 저장은 임시 파일을 먼저 작성한 뒤 `os.replace`로 교체해 중간 저장 실패 위험을 줄인다.

## 테스트

Telegram API를 실제 호출하지 않고 명령 처리 로직을 테스트한다.

    python -m unittest tests.test_telegram_bot

주요 테스트 항목:

- `/add` 관심사 추가
- 대소문자 차이에 따른 중복 방지
- `/remove` 관심사 삭제
- `/interests` 조회
- 알 수 없는 명령 처리
- Bot username이 붙은 명령 파싱

## 이번 단계에서 하지 않는 것

- 자연어 명령 해석
- `/digest AI Agent` 같은 즉시 뉴스 검색
- Telegram으로 뉴스 브리핑 발송
- 사용자별 다중 프로필
- 피드백 학습
- 웹 검색 Tool 호출

## 다음 단계

다음 단계에서는 Telegram 프로세스를 어디서 지속 실행할지 결정한다.

후보:

1. GitHub Actions 주기 실행
2. 무료 또는 저비용 서버
3. Cloud Run 등 서버리스 환경

배포 방식을 결정한 뒤 `/digest 키워드` 요청을 추가하고, 기존 뉴스 수집 및 평가 기능을 Agent Tool 형태로 연결한다.
