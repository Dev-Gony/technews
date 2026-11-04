# Daily Shorts (itgony)

GONY DAILY 기사로 30~45초 YouTube Shorts를 자동으로 만든다.
하루 6번(07·10·13·16·19·22시 KST) 실행되고, 실행마다 최근 3일 이슈에서 아직 안 만든 기사 1개로 1편을 만든다. AI 기사를 먼저, 다 쓰면 점수 높은 다른 기술 기사를 고른다.

```text
하루 3번 예약 실행
      |
      v
config/issues/ 최근 3일
      |
      v
기사 선택 (AI 기사 우선 → 점수 → 최신 이슈, 이미 만든 기사 제외)
      |
      v
Claude 대본 (claude -p, 구독 계정 사용 / 훅 → 본문 → 질문, 장면 4~6개)
      |
      v
Gemini TTS 음성 (Leda·Puck·Zephyr·Fenrir 번갈아, 대본 전체를 한 번에, 실패하면 edge-tts) + Whisper로 단어 시점 맞추기
      |
      v
Remotion 컷 편집 영상 (video/, 1.5~3초마다 컷, 1~2어절 팝업 자막, 컷별 그래픽, 효과음)
      |
      v
배경음 (bgm.py가 날짜별로 직접 만든 로파이 곡, 말할 때 자동으로 작아짐, -14 LUFS)
      |
      v
YouTube 업로드 (공개 요청. API 심사 전에는 YouTube가 비공개로 잠금) → Slack 알림
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
| `GEMINI_API_KEY` | 음성 (Gemini TTS 무료 등급, 기존 값 재사용) |
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
| `SHORTS_GEMINI_VOICES` | `Leda,Puck,Zephyr,Fenrir` (영상마다 차례로 사용) |
| `SHORTS_LOOKBACK_DAYS` | `3` (기사를 고를 최근 이슈 일수) |
| `SHORTS_GEMINI_TTS_MODEL` | `gemini-3.1-flash-tts-preview` |
| `SHORTS_WHISPER_MODEL` | `small` |
| `SHORTS_VOICE` | 대체 음성 `ko-KR-HyunsuMultilingualNeural` |
| `SHORTS_TTS_RATE` | 대체 음성 속도 `+22%` |
| `SHORTS_PRIVACY` | `public` |
| `SHORTS_BGM_VOLUME` | `0.15` (0이면 배경음 없음) |
| `SHORTS_CHANNEL_NAME` | `itgony` |

## 영상 그래픽 (Remotion)

대본은 12~16컷의 짧은 구어체 대사로 쓴다. 컷마다 Claude가 `visual`을 하나 고르고, `video/src/Visuals.tsx`가 그린다.

| type | 화면 |
|---|---|
| `hook` | 첫 컷. 대형 문구가 쾅 내려찍힘 (`value`) |
| `number` | 숫자 카운트업 (`value`, `label`) |
| `compare` | 막대 비교 차트 (`bars`) |
| `flow` | 단계 흐름도 (`items`) |
| `keywords` | 핵심 단어 카드 (`items`) |
| `code` | 터미널 코드 타이핑 (`code`) |
| `question` | 엔딩 질문 카드 (`label`) |
| `none` | 그래픽 없이 자막만 크게 |

- 자막은 대본의 ` / ` 표시대로 의미 단위(1~3어절)로 튀어나오고, `emphasis` 단어는 노란색이다.
- 화면 맨 위에는 대본의 `cover` 제목이 영상 내내 고정된다. Shorts는 썸네일을 직접 지정할 수 없어서, 어느 장면이 잡혀도 제목이 보이게 한 것이다.
- 더보기란에는 요약, 바로 써먹는 법(`tips`), 주의(`caution`), 원문, 지난 영상 링크가 들어간다.
- 효과음(컷 전환 슉, 숫자 쿵, 카드 뽁)은 `bgm.py`가 코드로 만든다.
- 디자인 수정: `cd video && npm install && npm run dev`로 Remotion Studio를 열고 `src/` 파일을 고친다.
- Remotion은 개인·3인 이하 팀은 무료다.
- Claude Code용 Remotion 공식 스킬이 `.claude/skills/`에 들어 있다.

## 자동 공개 (YouTube API 심사)

2020년 7월 이후 만든 Google Cloud 프로젝트는 YouTube의 심사(audit)를 통과하기 전까지 API로 올린 영상이 **비공개로 잠긴다**.
업로드는 이미 공개로 요청하고 있으므로, 심사만 통과하면 코드 수정 없이 바로 자동 공개된다.

- 신청: [YouTube API Services Audit and Quota Extension Form](https://support.google.com/youtube/contact/yt_api_form)
- 필요한 것: Google Cloud 프로젝트 번호, 앱 설명(개인 채널 자동 업로드), 개인정보처리방침 URL(`https://dev-gony.github.io/technews/privacy.html`)
- 심사 전에는 Slack 알림의 Studio 링크에서 공개로 바꾸면 된다.
