# Slack Feedback MVP

## 목적

Slack Tech Digest의 상위 추천 기사에 사용자가 남긴 반응을 기사별 피드백 데이터로 저장한다.

이번 단계의 목표는 추천 품질을 바로 자동 조정하는 것이 아니라, 다음 단계의 Feedback Learning이 사용할 수 있는 신뢰 가능한 피드백 데이터를 쌓는 것이다.

## 사용자 경험

Daily Tech Digest는 기존 형식을 그대로 유지한다.

상위 추천 기사에는 별도의 피드백 카드가 추가된다.

    🧭 추천 피드백
    기사 제목
    출처 · 점수

    한줄 요약

    이 추천이 어땠는지 반응으로 알려주세요.
    👍 도움됨  👎 별로  🔥 이런 거 더  🙈 이 주제 줄이기

사용자는 Slack reaction으로 평가한다.

## Reaction 의미

- 👍 (`+1`) → helpful
- 👎 (`-1`) → not_helpful
- 🔥 (`fire`) → more_like_this
- 🙈 (`see_no_evil`) → less_like_this

## 동작 구조

    Daily Tech News
    → Slack Bot API로 상위 기사 피드백 카드 전송
    → message ts / channel / article metadata 저장
    → config/slack_feedback_state.json

    Slack Feedback Sync
    → reactions.get
    → 반응 개수 읽기
    → config/slack_feedback.json 업데이트

## 필요한 GitHub Secrets

기존:

- `SLACK_WEBHOOK_URL`
- `GEMINI_API_KEY`

추가:

- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`

Bot Token이 없으면 기존 Incoming Webhook 전송 방식으로 fallback한다. 이 경우 피드백 카드는 생성하지 않는다.

## Slack App 권한

Bot Token에는 최소한 다음 권한이 필요하다.

- `chat:write`
- `reactions:read`

Bot은 대상 채널에 참여해 있어야 한다.

## 상태 파일

### config/slack_feedback_state.json

최근 상위 추천 기사와 Slack message timestamp를 저장한다.

### config/slack_feedback.json

기사 URL을 key로 하여 누적 피드백 snapshot을 저장한다.

예:

    {
      "articles": {
        "https://example.com/article": {
          "article": {
            "title": "...",
            "company": "...",
            "topics": ["MCP", "RAG"]
          },
          "feedback": {
            "helpful": 2,
            "not_helpful": 0,
            "more_like_this": 1,
            "less_like_this": 0
          }
        }
      }
    }

## GitHub Actions

`.github/workflows/slack-feedback.yml`

- 2시간마다 Slack reactions를 동기화
- 수동 실행 지원
- 피드백 변화가 있을 때만 저장소에 commit

## 다음 단계

Feedback Learning에서는 이 데이터를 사용자 선호 가중치로 변환한다.

예:

    more_like_this
    → 해당 topic / content type 가중치 상승

    less_like_this
    → 해당 topic 가중치 하락

이 가중치는 Gemini 1차 선별 프롬프트와 최종 추천 순위에 반영한다.
