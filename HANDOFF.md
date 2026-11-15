# HANDOFF — technews (GONY DAILY + itgony 쇼츠)

작성: 2026-11-11, 갱신: 2026-11-15 오후 (#97~#103 품질 검사·화면 보완까지).
새 Claude는 이 파일을 먼저 읽고, **모든 답변을 한국어로** 해 주세요 (사용자 강력 선호).

시작 전에: `git checkout main && git pull` (로컬이 오래된 브랜치에 있을 수 있음)

## 1. 프로젝트 개요

- 저장소: `Dev-Gony/technews` (공개). main은 보호됨 → 새 브랜치 + PR로만 반영.
- **GONY DAILY**: 국내외 기술 블로그·GeekNews 수집 → 중복 제거 → Gemini 점수·요약 → Slack 다이제스트 + 웹 신문(https://dev-gony.github.io/technews/)
  - 주요 파일: `main.py`, `build_newspaper.py`, `trend_radar.py`, `slack_feedback.py`, `telegram_*.py`, `preferences.py`
  - 데이터: `config/issues/YYYY-MM-DD.json`, `sent_articles.json`
- **itgony 쇼츠(@ITGONY)**: GONY DAILY 기사 1개 → 45~55초 쇼츠 → YouTube 업로드
  - `shorts.py`(파이프라인 전체), `bgm.py`(코드로 만든 배경음·효과음·차임), `youtube_auth.py`
  - 영상: `video/` (Remotion 4.0.540) — **지금 기본 화면은 `editorial/Page.tsx`·`editorial/Editorial.tsx`(크림 잡지·다크)**, 예전 화면(classic): `Short.tsx`, `Visuals.tsx`, `VisualsPro.tsx`, `Scene3DVisual.tsx`, `Background.tsx`, `Thumbnail.tsx`, `brand/Brand.tsx`, `schema.ts`, `theme.ts`
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

### 11/15 오후 (로컬 Claude 세션)
- #97 **code 카드 원문 대조**: 팩트체크 뒤 code 카드의 줄마다 원문(공백 무시)에 있는지 확인, 없는 줄이 하나라도 있으면 카드 빼기(→ 헤드라인만 컷). 주석·괄호 줄은 대조 안 함. 결과 `research/code_check.json`. Rust 1.100 기사 시험에서 `Vec::new_in(alloc)`(원문엔 인자 없이 `Vec::new_in`만), `$ cargo build`(원문에 없음) 2장을 뺌
- #98 **핵심어 카드 한 단어**: 카드 74% 높이 + `— KEYWORD` 라벨 + 큰 단어 + 강조색 밑줄. 2~3단어 카드는 그대로
- #99 **Gemini 예비 대본 품질 검사**: Gemini로 쓴 대본만. 1컷 빼고 ① 약한 헤드라인(빈 것, 또는 숫자 없이 일반 낱말 — 핵심·비결·요약·구조·분석·원인·현황·상세 등 — 이 나머지 낱말 수 이상) **2개 이상** 또는 ② 카드 없는 컷 **4개 이상**이면 업로드 안 함. Slack 알림, history 기록 안 함(다음 실행에서 같은 기사를 Claude로 재시도). 결과 `research/quality.json`. 시험: Lovable 기사 Gemini 대본 → "카드 없는 컷 6개 / 10컷"으로 건너뜀
- #100 대본의 마크다운 `**굵게**`가 화면에 별표로 보이던 문제(code 카드 제외하고 지움), 마지막 컷 예시 문구 "3시간마다" → "출근·점심·퇴근길에"
- #102 **행동 제안은 원문에 나온 행동만** (사용자 결정 11/15): 끝에서 두 번째 컷·tips는 원문의 설치법·명령어·설정·권고·주의만, 없으면 원문 사실로 의미 정리·tips 빈 배열. 심사·팩트체크도 원문 밖 조언을 감점·수정. 시험(OpenAI 로보틱스): "2027년 휴머노이드 시연 목표"(원문에 있음)로 바뀜, tips 빈 배열
- #103 화살표 있는 3~4단계 diagram 카드가 카드 밖으로 잘리던 문제 → 3단계 이상이면 촘촘한 레이아웃
- 정리: 확인용 브랜치 15개 삭제(`preview/*` 9개, `claude/editorial-styles`·`editorial-pages`·`frames-check`·`claude-script-check`·`token-check`·`handoff-1115`), 임시 워크플로 7개(Still check, TTS Samples, Pages check ×3, Frames check, Style preview) 실행 기록을 지워 목록에서 제거
- 업로드 없는 확인 실행(main, 페르마 형식화 기사): Claude 대본, news, 헤드라인 모두 내용 있음, 카드 없는 컷 2/14, 숫자 원문 대조 이상 없음

### 11/14~11/15 (클라우드 Claude 세션)
- #93 팩트체크 실패 시 업로드 건너뜀: Claude → Gemini 순서로 팩트체크, 둘 다 실패하면 안 올림(Slack 알림, history에 `skipped: factcheck`, 같은 실행에서 다음 기사 1번 더). YouTube `400 invalidDescription` 대응(제목·설명란 `< >` 치환, 설명란 5000**바이트** 자르기)
- #94 화면 스타일 추가: `news`(크림 잡지) / `explain`(남색 다크 + 코드 에디터 창). 레퍼런스: YouTube **@Solostack-1** (사용자가 직접 지정)
- **#94로 11/15 07·08·12·13시에 올라간 4편은 레퍼런스와 많이 달라서 사용자가 크게 화냄**: 4편 모두 다크, 가운데는 예전 3D 아이콘·작은 알약 그대로, 화면 절반이 빔. 첫 영상 확인을 약속하고 안 했음. 올라간 4편은 그대로 두기로 함
- #95 컷 = 잡지 페이지로 재작업: 섹션 번호(`03 — 구조`) + 큰 헤드라인 + 큰 카드 하나(숫자·전후·막대·단계·핵심어·인용·비유표·코드) + 자막. 3D 아이콘 안 씀. 대본에 컷별 `heading`·`section`. 스타일은 규칙(대본에 code 카드가 있거나 **원문에 코드가 있으면** explain, 아니면 news). Gemini 503/429 재시도
- 확인: 업로드 없이 실제 파이프라인으로 Claude 대본 2편(JEPA → news, Zig → explain) 렌더, 헤드라인에 내용 있음, 카드 없는 컷 16컷 중 3~4컷. 사용자 승인 후 업로드 재개
- 11/15 사용자가 `CLAUDE_CODE_OAUTH_TOKEN`을 다른 구독 토큰으로 교체 → 업로드 없는 실행에서 Claude 대본·심사·팩트체크 확인함

### 그 이전

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

- [ ] **11/16 새벽부터 새 화면으로 올라간 영상 프레임 확인 후 보고** (11/15 오후엔 아직 실행이 없어서 못 함. 업로드 재개 후 첫 실행은 11/16 03:47 KST) — 스타일(news/explain), Claude/Gemini(로그 "Gemini로 대신"), 헤드라인 내용, 카드 없는 컷 수, 숫자·코드 원문 대조, 깨진·넘치는 글자. 아래 "영상 프레임 확인 방법"
- [x] "써 보기" 행동 제안을 원문에 나온 행동만으로 (#102, 11/15)
- [ ] code 카드가 빠지면(#97) 그 컷은 카드 없는 컷이 됨. Rust 시험에서 카드 없는 컷 4/13. Claude 대본엔 #99 검사가 안 걸리므로 지켜보기
- [ ] Codex CLI(ChatGPT 구독)를 두 번째 예비 대본 작성자로 쓸지: 사용자 결정 전. 지금은 Gemini 대본이 #99 기준에 못 미치면 건너뜀
- [x] 핵심어 한 단어 카드(#98), code 카드 원문 대조(#97), Gemini 예비 대본 품질 검사(#99), 확인용 브랜치 삭제 — 11/15 끝

- [ ] **#85·#87·#88 적용 후 첫 영상(11/11 공개분) 확인 보고 안 함** — 카메라 움직임, 3D 이름표, 렌더 실패 여부
- [ ] 아침 슬롯(07·08시)이 비는지 확인. 11/11은 03:47 예약 실행이 08:43쯤에야 시작돼 비었음 → 필요하면 cron 더 앞당기기
- [x] 썸네일 일괄 적용 끝 (11/11): 마지막 1개 적용, 남은 3개는 비공개라 목록에서 제외하고 목록 파일 삭제
- [x] 임시 워크플로 정리 (11/15)
- [x] 문서 갱신: `docs/BRANDING.md` 채널 설명 새 슬롯, `SHORTS-GUIDE.md` 아웃트로 문구 (11/15). **YouTube Studio 채널 설명은 사용자가 직접 수정** (아직 "07시부터 3시간마다"일 수 있음)
- [x] 계정 변경 끝 (11/11): 개인 Ultra 구독 토큰으로 `CLAUDE_CODE_OAUTH_TOKEN` 갱신, 업로드 없는 테스트 실행에서 Claude 대본 생성 확인. 한도 걱정 불필요
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
- **디자인 (11/15~)**: Solostack 레퍼런스. 뉴스(신모델·연구·수치) = 크림 잡지(명조 헤드라인, 빨강 강조, 검은 테두리 카드), 설명(코드 있는 개발 기사) = 남색 다크(격자 배경, 파란 알약 라벨, 노란 강조, 에디터 창). `SHORTS_STYLE`: auto(기본)·news·explain·classic. 레퍼런스를 그대로 베끼지 않음(itgony 색·문구·아웃트로 유지). **시안은 손으로 만든 HTML이 아니라 실제 파이프라인 렌더 프레임으로 보여주기.**
- **예전 디자인(classic)**: 먹색(ink) + 골드, glow 배경만, 효과음 적게, 0.5초 넘게 멈춘 화면·하드컷 없음, 아웃트로 "AI·개발 뉴스, 출근·점심·퇴근길에". 사용자는 **시각 퀄리티 우선**. 3D 캐릭터는 짜리몽땅·귀엽게, 레퍼런스 베끼지 않음, 의미 없이 돌아다니면 안 되고 대사를 설명해야 함.
- **3D 용량**: `assets3d` 전체 150MB 이내.

## 5. 비밀값 / 환경변수 (이름만)

- GitHub Secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `GEMINI_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `SLACK_WEBHOOK_URL`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_ID`
- GitHub Variables: `SHORTS_THUMBNAIL` (0이면 썸네일 끔)
- 화면 스타일: `SHORTS_STYLE` (auto/news/explain/classic), 팩트체크 실패 시 다른 기사 시도 수 `SHORTS_FACTCHECK_ATTEMPTS`(기본 2)
- shorts.py 설정: `SHORTS_CLAUDE_MODEL`, `SHORTS_CANDIDATE_MODEL`, `SHORTS_SCRIPT_WRITER`, `SHORTS_SCRIPT_CANDIDATES`, `SHORTS_GEMINI_SCRIPT_MODEL`, `SHORTS_GEMINI_TTS_MODEL`, `SHORTS_GEMINI_VOICES`, `SHORTS_VOICE`, `SHORTS_TTS_RATE`, `SHORTS_WHISPER_MODEL`, `SHORTS_ALLOW_FALLBACK_VOICE`, `SHORTS_PRIVACY`, `SHORTS_PUBLISH_SLOTS`, `SHORTS_THEME`, `SHORTS_BACKDROP`, `SHORTS_DESK3D`, `SHORTS_RENDER_CRF`, `SHORTS_BGM_VOLUME`, `SHORTS_LOOKBACK_DAYS`, `SHORTS_CHANNEL_NAME`, `SHORTS_THUMBNAIL_BATCH_LIMIT`
- 로컬 실행은 같은 이름을 `.env`로. YouTube refresh token은 `youtube_auth.py`로 발급.

## 6. 작업 방식 (사용자 선호)

- **항상 한국어.** 직설적인 편이며, 의도를 잘못 이해하거나 **확인 안 한 결과를 보고**하거나 기사에 없는 사실이 영상에 들어가면 크게 화냄 → 직접 확인 후 보고, 못 한 건 못 했다고 말하기.
- PR: 기능마다 `feature/*` 또는 `claude/*` 브랜치, 제목·본문 한국어, base는 항상 main(쌓지 않기). 머지 전 최신 main과 합친 상태로 테스트 + `npx tsc --noEmit` + `npx remotion still`로 화면 확인, 대본·카드 로직을 바꿨으면 Daily Shorts `upload=false` 실행 후 프레임 확인. 11/15 사용자 지시로 **위 확인이 다 통과하면 PR checks 초록 확인 후 Claude가 squash 머지까지** 함.
- 수동 실행은 항상 `upload=false`. 시험 실행도 Gemini TTS 무료 한도를 씀(11/15 시험 4번째에 429 두 번) → 예약 실행 직전에 몰아서 돌리지 않기(한도는 KST 17:00 초기화)
- 설명: 짧은 결론 → 굵은 소제목 + 불릿 → 표. 쉬운 말, 구체적 숫자. 바뀐 점은 시안(이미지·영상) 먼저 보여주고 승인받기.
- 큰 작업은 별도 세션·워크트리로 병렬 진행 가능.
  - Windows: 워크트리 지우기 전 `node_modules` 정션을 먼저 `rmdir` (안 하면 본 저장소 node_modules가 지워짐)
  - Git Bash에서 `git show origin/main:path`가 깨지면 `MSYS_NO_PATHCONV=1`
- 사용자가 직접 하는 일: 토큰·비밀값 입력, 영상 삭제, YouTube Studio 설정. 요청 범위를 넘는 업로드·공개는 하지 않음.

## 7. 영상 프레임 확인 방법

- 업로드 없이 만들기: Daily Shorts 수동 실행(`upload=false`, `link=`로 기사 지정). 결과는 `shorts` 아티팩트(`short.mp4`, `script.json`, `research/`)
- 올라간 영상 확인: 실행의 `shorts` 아티팩트를 받아 `ffmpeg -i short.mp4 -vf "fps=1/2,scale=300:-1,tile=8x3" -frames:v 1 contact.png`로 2초 간격 한 장 보기
  - Windows 로컬엔 ffmpeg가 PATH에 없음. Remotion에 든 ffmpeg는 `tile` 필터가 없어서 안 됨 → `pip install imageio-ffmpeg` 후 `python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"` 경로의 ffmpeg 사용
  - 프레임 이미지는 `runtime/shorts/frames/`에 (gitignore)
  - 로컬 테스트: `pip install tzdata beautifulsoup4` 필요, 출력 깨지면 `PYTHONIOENCODING=utf-8`
- 샘플 스틸: `video/`에서 `npx remotion still src/index.ts ShortNews out.png --frame=170` (`ShortExplain`도 있음, `editorial/samples.ts`)
- 보고 전에 꼭: 스타일, 헤드라인 내용, 카드 비율, 코드·숫자가 원문에 있는지

## 8. 로컬에만 있는 것 (git에 없음)

- `runtime/` (~474MB, 테스트 렌더 결과물), `tts-samples/` (목소리 비교 샘플) — 커밋하지 않음. PC를 옮길 거면 따로 복사.
- `.env`, `.claude/settings.local.json`(로컬 권한 설정) — gitignore 대상.
- 이전 대화 기록: `C:\Users\Gony\.claude\projects\C--Users-Gony-Desktop-code-technews*` (같은 PC면 `claude --resume`).
