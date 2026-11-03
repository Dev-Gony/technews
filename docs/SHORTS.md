# Daily Shorts (itgony)

GONY DAILY 이슈에서 AI 기사 1개를 골라 45초 안팎의 YouTube Shorts를 자동으로 만든다.

```text
Daily Tech News 완료
      |
      v
config/issues/YYYY-MM-DD.json
      |
      v
AI 기사 선택 (selection_score 순, 이미 만든 기사 제외)
      |
      v
Claude 대본 (claude -p, 구독 계정 사용 / 훅 → 본문 → 질문, 장면 4~6개)
      |
      v
edge-tts 음성 (장면별 mp3)
      |
      v
Remotion 인포그래픽 영상 (video/, 장면별 그래픽 + 단어 단위 자막 + 장면 전환)
      |
      v
배경음 (bgm.py가 날짜별로 직접 만든 로파이 곡, 말할 때 자동으로 작아짐, -14 LUFS)
      |
      v
YouTube 업로드 (비공개) → Slack 알림 → Studio에서 확인 후 공개
```

## 파일

| 파일 | 역할 |
|---|---|
| `shorts.py` | 파이프라인 전체 |
| `youtube_auth.py` | YouTube 로그인 후 Secrets 3개 자동 등록 (로컬, 1회) |
| `bgm.py` | 배경음 생성 |
| `video/` | Remotion 프로젝트. `npm run dev`로 Studio 미리보기 |
| `.github/workflows/shorts.yml` | Daily Tech News 성공 후 자동 실행, 수동 실행 가능 |
| `config/shorts_history.json` | 업로드한 기사 기록 (같은 기사 중복 방지) |
| `runtime/shorts/<날짜>/` | 대본, 음성, 장면 이미지, 최종 `short.mp4` (git 제외) |

## 로컬 실행

```bash
pip install -r requirements.txt
```

Claude 없이 직접 쓴 대본으로 영상만 만들기:

```bash
python shorts.py --date 2026-11-03 --script my_script.json --no-upload
```

Claude로 대본까지 만들기 (Claude Code에 로그인되어 있으면 API 키 없이 구독으로 실행):

```bash
python shorts.py --no-upload
```

Windows에서 `ZoneInfoNotFoundError`가 나면 `pip install tzdata`.

## GitHub Secrets

| 이름 | 용도 |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | 대본 생성 (Claude 구독, API 과금 없음) |
| `YOUTUBE_CLIENT_ID` | YouTube 업로드 |
| `YOUTUBE_CLIENT_SECRET` | YouTube 업로드 |
| `YOUTUBE_REFRESH_TOKEN` | YouTube 업로드 |
| `SLACK_WEBHOOK_URL` | 업로드 알림 (기존 값 재사용) |

YouTube 값이 없으면 영상만 만들고 Actions artifact(`shorts`)로 남긴다.

`CLAUDE_CODE_OAUTH_TOKEN`은 로컬에서 한 번 발급한다. Claude 구독(Pro/Max) 계정으로 로그인하면 1년짜리 토큰이 출력된다.

```bash
claude setup-token
```

하루 1번, 짧은 대본 1개라 구독 사용량에는 거의 영향이 없다.

## YouTube 업로드 준비

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 **YouTube Data API v3**를 사용 설정한다.
2. OAuth 동의 화면을 만들고, 테스트 사용자에 itgony 채널 Google 계정을 추가한다.
3. 사용자 인증 정보 → OAuth 클라이언트 ID → 유형 **데스크톱 앱**으로 만들고 **JSON 다운로드**를 누른다.
4. 로컬에서 실행한다. 다운로드 폴더의 `client_secret*.json`을 찾아 로그인한 뒤, Secrets 3개를 GitHub에 바로 등록한다.

   ```bash
   python youtube_auth.py
   ```

참고:
- OAuth 앱이 "테스트" 상태면 refresh token이 7일 뒤 만료된다. 계속 쓰려면 동의 화면을 "프로덕션"으로 게시한다.
- 검수(audit)를 받지 않은 API 프로젝트로 올린 영상은 비공개로 고정될 수 있다. 기본값도 비공개(`SHORTS_PRIVACY=private`)이고, Studio에서 확인 후 공개로 바꾸는 흐름이다.
- 업로드 시 `containsSyntheticMedia: true`(AI 합성 콘텐츠 표시)를 설정한다.

## 설정 (환경변수)

| 이름 | 기본값 |
|---|---|
| `SHORTS_CLAUDE_MODEL` | 비우면 구독 플랜 기본 모델 (`opus`, `sonnet` 등) |
| `SHORTS_VOICE` | `ko-KR-InJoonNeural` (여성: `ko-KR-SunHiNeural`) |
| `SHORTS_TTS_RATE` | `+8%` |
| `SHORTS_PRIVACY` | `private` |
| `SHORTS_BGM_VOLUME` | `0.15` (0이면 배경음 없음) |
| `SHORTS_CHANNEL_NAME` | `itgony` |

## 영상 그래픽 (Remotion)

대본을 쓸 때 Claude가 장면마다 `visual`을 하나 고르고, `video/src/Visuals.tsx`가 그린다.

| type | 화면 |
|---|---|
| `number` | 숫자 카운트업 (`value`, `label`) |
| `compare` | 막대 비교 차트 (`bars`) |
| `flow` | 단계 흐름도 (`items`) |
| `keywords` | 핵심 단어 카드 (`items`) |
| `code` | 터미널 코드 타이핑 (`code`) |
| `question` | 엔딩 질문 카드 (`label`) |
| `none` | 헤드라인만 크게 |

- 자막은 edge-tts의 단어별 시점(WordBoundary)으로 말하는 단어를 강조한다.
- 디자인 수정: `cd video && npm install && npm run dev`로 Remotion Studio를 열고 `src/` 파일을 고친다.
- Remotion은 개인·3인 이하 팀은 무료다.
- Claude Code용 Remotion 공식 스킬이 `.claude/skills/`에 들어 있다.
