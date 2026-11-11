# HANDOFF — technews (GONY DAILY + itgony 쇼츠)

작성: 2026-11-11, 다른 Claude 계정으로 작업을 넘기기 위해 정리함.
새 Claude는 이 파일을 먼저 읽고, **모든 답변을 한국어로** 해 주세요 (사용자 강력 선호).

시작 전에: `git checkout main && git pull` (로컬이 오래된 브랜치에 있을 수 있음)

## 1. 프로젝트 개요

- 저장소: `Dev-Gony/technews` (공개). main은 보호됨 → 새 브랜치 + PR로만 반영.
- **GONY DAILY**: 국내외 기술 블로그·GeekNews 수집 → 중복 제거 → Gemini 점수·요약 → Slack 다이제스트 + 웹 신문(https://dev-gony.github.io/technews/)
  - 주요 파일: `main.py`, `build_newspaper.py`, `trend_radar.py`, `slack_feedback.py`, `telegram_*.py`, `preferences.py`
  - 데이터: `config/issues/YYYY-MM-DD.json`, `sent_articles.json`
- **itgony 쇼츠(@ITGONY)**: GONY DAILY 기사 1개 → 30~50초 쇼츠 → YouTube 업로드
  - `shorts.py`(파이프라인 전체), `bgm.py`(코드로 만든 배경음·효과음·차임), `youtube_auth.py`
  - 영상: `video/` (Remotion 4.0.540) — `Short.tsx`, `Visuals.tsx`, `VisualsPro.tsx`, `Scene3DVisual.tsx`, `Background.tsx`, `Thumbnail.tsx`, `brand/Brand.tsx`, `schema.ts`, `theme.ts`
  - 3D 소재: Blender 스크립트 `video/assets3d/scripts/`, 결과물 `video/public/assets3d/` (`*_world.png`, `*_world_loop.webm`, `*_anchors.json`)
  - 테스트: `tests/test_shorts.py`
  - 가이드: **`docs/SHORTS-GUIDE.md`(가장 최신)**, `docs/SHORTS.md`(요약), `docs/BRANDING.md`(채널 꾸미기)
- 쇼츠 흐름: 기사 고르기 → 원문 취재 → 대본 후보 3개(Sonnet) → 심사·팩트체크(Opus) → Gemini TTS(Leda) → faster-whisper 단어 시점 → Remotion 렌더 → bgm/loudnorm/alimiter → ffmpeg 검수 → YouTube 업로드(비공개 + `publishAt` 예약 공개) → 썸네일 → `config/shorts_history.json`

### GitHub Actions (KST)

| 워크플로 | 시각 / 계기 | 하는 일 |
|---|---|---|
| `shorts.yml` | 03:47, 04:47, 08:47, 09:47, 13:47, 14:47 | 쇼츠 제작·예약 업로드 (제한 45분) |
| `slack-test.yml` | 05:57 | 뉴스 수집·발행 |
| `pages.yml` | 뉴스 실행 뒤 | 웹 신문 배포 |
| `slack-feedback.yml` | 2시간마다 :17 | Slack 반응 동기화 |
| `telegram-poll.yml` | 5분마다 | 텔레그램 선호도 수집 |
| `trend-radar.yml` | 월 08:00 | 주간 트렌드 레이더 |
| `tests.yml` | PR마다 | 단위 테스트 |

`shorts.yml` 수동 실행 입력값: date, upload, link, theme, script, thumbnail_only, thumbnail_batch, writer

## 2. 지금까지 한 작업 (모두 main에 머지됨)

- #59 채널 브랜딩 / #60~#63 연출 기본기(훅, 여성 목소리 고정, 아이소메트릭 디자인, QA 게이트, 리미터, 검색용 제목)
- #64·#65·#73·#74 썸네일 자동 적용 + 기존 영상 일괄 적용
- #66 대본 단계화: 원문 취재 → 각도 3개 → 편집자 심사 → 팩트체크
- #67~#69 새 그래픽 4종, glow 배경, 아웃트로 "IT." 로고 + 실로폰 차임
- #70 Claude 사용량 절감(후보는 Sonnet, 막히면 Gemini 대본), TTS 끊김 재생성
- #71·#72 중복 업로드 방지(history 병합), TTS 끝까지 실패 시 업로드 건너뜀
- #75~#79 Blender 3D → 배경이 아니라 **설명 컷**(`scene3d`)으로 사용
- #80~#83·#86 3D 장면 25개 (~36MB, 한도 150MB): desk, vault, coins, server, lab, data, web, repo, launch, law, chip, phone, deploy, media, search, invest, terminal, chat, voice, robot, ai, lang, work, game, math
- #84 공개 슬롯 07·08·12·13·17·18시 (cron은 ~3시간 앞 :47에 만들고 YouTube 예약 공개)
- #85 카메라 계속 움직임, scene3d 영상당 최대 2번, `--crf=14 --x264-preset=slow`
- #87 3D 스토리 연출: 장면마다 배역 좌표(`*_anchors.json`), 대본 단계에서 배역 2~4개 → 카메라가 대사 순서대로 밀고 들어가며 링+이름표
- #88 렌더 멈춤 대비: `--timeout=120000`, 실패 시 1번 재시도

## 3. 남은 할 일

- [ ] **#85·#87·#88 적용 후 첫 영상(11/11 공개분) 확인 보고 안 함** — 카메라 움직임, 3D 이름표, 렌더 실패 여부
- [ ] 아침 슬롯(07·08시)이 비는지 확인. 11/11은 03:47 예약 실행이 08:43쯤에야 시작돼 비었음 → 필요하면 cron 더 앞당기기
- [ ] 썸네일 일괄 적용: `config/thumbnail_backfill.json`에 4개 남음. 11/11 20:28쯤 수동 실행 결과 미확인.
      매일 돌리던 예약 작업은 이전 계정 세션 전용이라 사라짐 → 직접 실행 후 적용된 ID는 새 브랜치 + PR로 목록에서 제거
      `gh workflow run shorts.yml --ref main -f upload=false -f thumbnail_batch=config/thumbnail_backfill.json`
- [ ] 임시 워크플로 "Still check (temporary)", "TTS Samples (temporary)" 정리 (사용자에게 아직 말 안 함)
- [ ] 문서 갱신: `docs/BRANDING.md` 채널 설명("07시부터 3시간마다" → 새 슬롯), `SHORTS-GUIDE.md` 1장의 "공개로 바로 올라감" → 예약 공개. YouTube Studio 설명은 사용자가 직접 수정
- [ ] **(사용자) 계정 변경 시 `claude setup-token`으로 새 토큰 발급 → GitHub Secret `CLAUDE_CODE_OAUTH_TOKEN` 갱신.** 안 하면 대본이 Gemini 대체 경로로만 만들어짐
- [ ] (사용자, 선택) YouTube API 할당량 증가 신청 — 초안 `youtube-audit-answers.md`. 하루 6편보다 늘릴 때만 필요
- 보류/아이디어: 인스타(카드뉴스+릴스, `cards.py` 완성)·스레드·틱톡(인스타 계정 정지 반복 → YouTube 품질 우선), 주간 성과 리포트, ink/paper 테마 A/B, 3D 후보(우주·바이오·에너지)
- 두 번째 채널(쇼핑/드라마 쇼츠, 다른 YouTube 계정): 아직 없음. 답을 기다리는 질문 3개 — 수익화(쿠팡 파트너스 vs YouTube 쇼핑), 상품 분야, 새 저장소 여부. 관련 작업은 `C:\shorts`(그쪽 HANDOFF.md 참고)
- 장기 계획 문서: `docs/AGENT_V2_PLAN.md`, `docs/EVOLUTION_REPORT.md` (최근 미사용)

## 4. 중요한 결정사항

- **비용 0원**: Google Cloud·AI Studio에 결제 수단 연결 안 함(한도 초과 = 실패). `ANTHROPIC_API_KEY` 사용 안 함 — Claude는 구독 OAuth 토큰으로 `claude -p` 실행(대화 사용량과 5시간 한도 공유). 음원·그래픽은 코드로 생성.
- **모델**: 후보 Sonnet(`SHORTS_CANDIDATE_MODEL`), 심사·팩트체크 Opus(`SHORTS_CLAUDE_MODEL`), Claude 한도 시 Gemini `gemini-3.1-flash-lite`.
- **TTS**: Gemini `gemini-3.1-flash-tts-preview`, 여성 목소리 **Leda 고정**(남성 목소리 싫어함). 실패 시 30·60·90초 재시도, 끝까지 안 되면 **업로드 안 함**(edge-tts 예비 목소리로 올라간 영상을 사용자가 삭제한 적 있음). 대본 70% 미만이면 재생성(`TTS_MIN_COVERAGE`).
- **원칙**: 품질 낮은 영상은 올리지 않고 건너뜀. 이미 올린 영상은 바꾸지 않고 새 영상부터 적용.
- **하루 6편**: 10,000유닛 ÷ 업로드 1,600 = 6. 할당량은 KST 17:00 초기화. Cloud 프로젝트 쪼개서 한도 늘리기는 정책 위반이라 안 함.
- **디자인**: 먹색(ink) + 골드, glow 배경만, 효과음 적게, 0.5초 넘게 멈춘 화면·하드컷 없음, 아웃트로 "AI·개발 뉴스, 출근·점심·퇴근길에". 사용자는 **시각 퀄리티 우선**. 3D 캐릭터는 짜리몽땅·귀엽게, 레퍼런스 베끼지 않음, 의미 없이 돌아다니면 안 되고 대사를 설명해야 함.
- **3D 용량**: `assets3d` 전체 150MB 이내.

## 5. 비밀값 / 환경변수 (이름만)

- GitHub Secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `GEMINI_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `SLACK_WEBHOOK_URL`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_ID`
- GitHub Variables: `SHORTS_THUMBNAIL` (0이면 썸네일 끔)
- shorts.py 설정: `SHORTS_CLAUDE_MODEL`, `SHORTS_CANDIDATE_MODEL`, `SHORTS_SCRIPT_WRITER`, `SHORTS_SCRIPT_CANDIDATES`, `SHORTS_GEMINI_SCRIPT_MODEL`, `SHORTS_GEMINI_TTS_MODEL`, `SHORTS_GEMINI_VOICES`, `SHORTS_VOICE`, `SHORTS_TTS_RATE`, `SHORTS_WHISPER_MODEL`, `SHORTS_ALLOW_FALLBACK_VOICE`, `SHORTS_PRIVACY`, `SHORTS_PUBLISH_SLOTS`, `SHORTS_THEME`, `SHORTS_BACKDROP`, `SHORTS_DESK3D`, `SHORTS_RENDER_CRF`, `SHORTS_BGM_VOLUME`, `SHORTS_LOOKBACK_DAYS`, `SHORTS_CHANNEL_NAME`, `SHORTS_THUMBNAIL_BATCH_LIMIT`
- 로컬 실행은 같은 이름을 `.env`로. YouTube refresh token은 `youtube_auth.py`로 발급.

## 6. 작업 방식 (사용자 선호)

- **항상 한국어.** 직설적인 편이며, 의도를 잘못 이해하거나 **확인 안 한 결과를 보고**하거나 기사에 없는 사실이 영상에 들어가면 크게 화냄 → 직접 확인 후 보고, 못 한 건 못 했다고 말하기.
- PR: 기능마다 `feature/*` 또는 `claude/*` 브랜치, 제목·본문 한국어, base는 항상 main(쌓지 않기). 머지 전 최신 main과 합친 상태로 테스트 + `npx tsc --noEmit` + `npx remotion still`로 화면 확인. 이전 계정에서는 Claude가 머지까지 맡았음 — **새 계정에서는 머지 전에 한 번 확인받기.**
- 설명: 짧은 결론 → 굵은 소제목 + 불릿 → 표. 쉬운 말, 구체적 숫자. 바뀐 점은 시안(이미지·영상) 먼저 보여주고 승인받기.
- 큰 작업은 별도 세션·워크트리로 병렬 진행 가능.
  - Windows: 워크트리 지우기 전 `node_modules` 정션을 먼저 `rmdir` (안 하면 본 저장소 node_modules가 지워짐)
  - Git Bash에서 `git show origin/main:path`가 깨지면 `MSYS_NO_PATHCONV=1`
- 사용자가 직접 하는 일: 토큰·비밀값 입력, 영상 삭제, YouTube Studio 설정. 요청 범위를 넘는 업로드·공개는 하지 않음.

## 7. 로컬에만 있는 것 (git에 없음)

- `runtime/` (~474MB, 테스트 렌더 결과물), `tts-samples/` (목소리 비교 샘플) — 커밋하지 않음. PC를 옮길 거면 따로 복사.
- `.env`, `.claude/settings.local.json`(로컬 권한 설정) — gitignore 대상.
- 이전 대화 기록: `C:\Users\Gony\.claude\projects\C--Users-Gony-Desktop-code-technews*` (같은 PC면 `claude --resume`).
