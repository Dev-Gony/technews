# itgony 쇼츠 자동 제작 전체 가이드

> GONY DAILY(매일 아침 테크 신문) 기사로 YouTube Shorts를 **하루 6편, 사람 손 없이, 비용 0원**으로 만들어 올리는 시스템의 모든 것.
> 기준일: 2026-11-08 · 레포: `Dev-Gony/technews` (공개 저장소)

---

## 목차

1. [한눈에 보기](#1-한눈에-보기)
2. [전체 흐름](#2-전체-흐름)
3. [단계별 상세](#3-단계별-상세)
4. [대본 작성 규칙 (Claude에게 주는 지시)](#4-대본-작성-규칙-claude에게-주는-지시)
5. [화면 디자인 사양](#5-화면-디자인-사양)
6. [소리: 내레이션·배경음·효과음](#6-소리-내레이션배경음효과음)
7. [업로드와 영상 설명란](#7-업로드와-영상-설명란)
8. [돈이 안 나가는 이유 (비용 0원 구조)](#8-돈이-안-나가는-이유-비용-0원-구조)
9. [한도와 제약](#9-한도와-제약)
10. [처음 한 번 해야 하는 설정](#10-처음-한-번-해야-하는-설정)
11. [수동 실행·테스트 방법](#11-수동-실행테스트-방법)
12. [설정값 (환경변수)](#12-설정값-환경변수)
13. [파일 구조](#13-파일-구조)
14. [겪었던 문제와 해결](#14-겪었던-문제와-해결)
15. [앞으로 할 것](#15-앞으로-할-것)

---

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 채널 | YouTube **itgony** (@ITGONY) |
| 원재료 | GONY DAILY 기사 (https://dev-gony.github.io/technews/) |
| 편수 | 하루 6편, 07·08·12·13·17·18시 KST 공개 (YouTube 예약 공개) |
| 길이 | 30~50초 (짧게보다 **정확하고 이해하기 쉽게**가 우선) |
| 대본 | Claude (구독 계정, `claude -p`): 후보는 Sonnet, 심사·팩트체크는 Opus. Claude가 막히면 Gemini가 대신 씀 |
| 목소리 | Gemini TTS 여성 목소리 **Leda** 고정 (끝까지 실패하면 그 회차는 **업로드하지 않고 건너뜀**) |
| 자막 시점 | faster-whisper로 받아 적어서 단어별 시점 계산 |
| 편집 | Remotion (React로 영상 만드는 도구) |
| 배경음·효과음 | 코드로 직접 만든 음원 (저작권 걱정 없음) |
| 업로드 | YouTube Data API v3, **공개**로 바로 올라감 + 맞춤 썸네일 자동 적용 |
| 실행 장소 | GitHub Actions (공개 저장소라 무료) |
| 비용 | **0원** |
| 사람이 하는 일 | 없음 (가끔 영상 품질 확인, 코드 개선 PR 머지) |

---

## 2. 전체 흐름

```text
[매일 05:57 KST] Daily Tech News 워크플로 (main.py)
   여러 기술 블로그 + GeekNews 수집 → 중복 제거 → Gemini(무료)로 평가·요약
   → config/issues/YYYY-MM-DD.json 저장 → GONY DAILY 웹 신문 발행
        |
        v
[03:47·04:47·08:47·09:47·13:47·14:47 KST] Daily Shorts 워크플로 (shorts.py) — 실행 1번 = 영상 1편
        |
        |  ① 기사 고르기 ─ 오늘 주요 기사 → 오늘 상세 기사 → 최근 3일 남은 기사
        |                  (이미 만든 기사는 최신 main의 config/shorts_history.json으로 제외)
        v
        ② 대본 쓰기 ─ 원문 취재 → 후보 3개(Sonnet) → 심사(Opus) → 팩트체크(Opus) → JSON 대본 (컷 10~15개)
        |              (Claude가 사용량 한도로 막히면 무료 Gemini가 대신 씀)
        v
        ③ 목소리 ─ Gemini TTS(Leda)로 대본 전체를 한 번에 읽기
        |          (중간에 끊기면 다시 만들고, 한도에 걸리면 기다렸다 재시도. 끝까지 안 되면 이번 회차는 건너뜀)
        v
        ④ 자막 시점 ─ faster-whisper로 받아 적기 → 대본 어절에 글자 단위로 맞추기
        v
        ⑤ 영상 렌더링 ─ Remotion: 배경 + 컷별 그래픽 + 팝업 자막 + 상단 제목 + 효과음 + 마무리 로고
        v
        ⑥ 배경음 ─ bgm.py로 곡 생성 → 말할 때 자동으로 작아지게(덕킹) → -14 LUFS + 리미터(-1.5dB)
        v
        ⑦ 자동 검수 ─ 해상도·fps·길이·소리·음량·무음·깨진 글자 확인. 실패하면 업로드 보류 + Slack 알림
        v
        ⑧ 업로드 ─ YouTube API (공개, AI 합성 콘텐츠 표시, 과학기술 카테고리) → 썸네일 적용
        v
        ⑨ 마무리 ─ 업로드 기록을 최신 main 기록과 합쳐 커밋 + Slack 알림 + 영상 파일 14일 보관
```

한 편 만드는 데 GitHub Actions에서 **약 8~10분** 걸린다.

---

## 3. 단계별 상세

### 0) 원재료: GONY DAILY 이슈 만들기 (`main.py`)

- 워크플로: `.github/workflows/slack-test.yml` (이름: *Daily Tech News*), 매일 **05:57 KST**.
- 여러 기술 블로그 RSS와 GeekNews를 모아 중복을 지우고, **Gemini `gemini-3.1-flash-lite`(무료 등급)**로 기사 가치를 평가하고 요약한다.
- 결과는 `config/issues/YYYY-MM-DD.json`에 저장되고, `pages.yml`이 웹 신문을 발행한다.
- 기사마다 쇼츠에 쓰는 정보: `title`, `one_line`(한 줄 요약), `key_points`(핵심 포인트), `topics`, `recommended_for`, `company`(출처), `link`, `selection_score`, `editorial_rank`.
- 이슈는 `top_stories`(주요 기사)와 `more_detailed`(상세 기사)로 나뉜다.

### 1) 실행 시점 (`.github/workflows/shorts.yml`)

- 하루 6번 cron: 03:47, 04:47, 08:47, 09:47, 13:47, 14:47 (`timezone: "Asia/Seoul"`).
- **공개 시각은 따로 정한다:** 출근(07·08시), 점심(12·13시), 퇴근(17·18시). 영상은 약 3시간 앞서 만들어 비공개로 올리고
  YouTube 예약 공개(`publishAt`)로 정확한 시각에 공개한다. `shorts.py`의 `next_publish_slot`이 아직 비어 있는 가장 이른 시각을 고르고,
  기록(`publish_at`)에 남겨 다음 실행이 같은 시각을 쓰지 않게 한다. 바꾸려면 `SHORTS_PUBLISH_SLOTS`(예: `7,8,12,13,17,18`, 비우면 즉시 공개).
- **왜 정각이 아니라 47분인가:** GitHub 예약 실행은 정각에 몰려서 몇 시간씩 늦게 시작되곤 했다(22시 실행이 새벽 1~5시에 시작). 정각을 피하고 3시간 여유를 둔다.
- **왜 6번인가:** YouTube API 하루 한도가 10,000유닛이고 업로드 1번에 1,600유닛이라 6편이 최대.
- **한도 초기화:** 미국 태평양 시간 자정(**한국 17:00**). 업로드(03:47~14:47)가 모두 같은 한도 날에 들어가 하루 6편 그대로다.
- `concurrency: tech-news-bot`: 뉴스 수집 등 다른 작업과 겹치지 않게 줄 세운다.
- 실행 환경: Ubuntu, Python 3.12, Node.js 22, Claude Code CLI(`npm install -g @anthropic-ai/claude-code`), Remotion용 Chrome(`remotion browser ensure`), Whisper 모델 캐시.
- 제한 시간 45분.
- **체크아웃 직후 `config/shorts_history.json`만 최신 main으로 맞춘다.** 실행이 줄 서 있다가 시작되면 체크아웃은 "예약된 시점"의 코드라서, 바로 앞 실행이 올린 영상 기록이 빠져 있다. 그대로 두면 같은 기사로 또 만들어 중복 업로드된다(실제로 겪음).

### 2) 기사 고르기 (`pick_article`)

1. 오늘부터 거꾸로 **최근 3일** 이슈 파일을 읽는다 (`SHORTS_LOOKBACK_DAYS`).
2. `key_points`가 있는 기사만 후보로 쓴다 (단신은 정보가 부족해서 제외).
3. `config/shorts_history.json`에 있는 링크(이미 만든 기사)는 뺀다. (위에서 최신 main 기록으로 맞춘 파일)
4. 남은 후보를 이 순서로 정렬해 1개를 고른다.
   1. **최신 날짜 먼저**: 오늘 기사를 다 쓰기 전에는 전날 기사로 넘어가지 않는다.
   2. 같은 날이면 **주요 기사(top_stories) → 상세 기사**
   3. 그 안에서 **AI 관련 기사 우선** (제목·요약·토픽에 ai, llm, claude, agent, 에이전트 등이 있으면)
   4. **선정 점수 높은 순** → 편집 순위 순
5. 고를 기사가 없으면 아무것도 하지 않고 끝난다.

### 3) 대본 쓰기 (`generate_script` → `claude_json`)

영상 하나에 Claude를 **5번** 부르는 다단계 방식. 사용량 대부분인 후보 3개는 가벼운 **Sonnet**, 심사·팩트체크는 **Opus**. 단계별 결과는 작업 폴더 `research/`에 남는다(Actions 결과물에도 포함).

| 단계 | 하는 일 | 함수 |
|---|---|---|
| ① 원문 취재 | 기사 링크 본문을 가져온다. GeekNews는 `#topic_contents`의 자세한 정리 + 원본 글(SNS 제외). 최대 14,000자 | `fetch_source_text` |
| ② 후보 3개 (동시에, Sonnet) | 각도별 대본: 원리·구조 / 숫자·결과 / 실무 적용 | `write_candidate` |
| ③ 편집장 심사 (Opus) | 훅·정확도(2배)·이해도·그래픽·지속력 점수로 1개 선택 | `judge_candidates` |
| ④ 팩트체크 (Opus) | 모든 문장·숫자·그래픽 값을 원문과 대조, 근거 없으면 고치거나 삭제 | `factcheck_script` |

- 심사·팩트체크가 실패하면 그때까지의 결과로 진행한다.
- **후보가 하나도 안 나오면**(대부분 Claude 구독 사용량 한도) Claude로 다시 해도 같으므로 **무료 Gemini `gemini-3.1-flash-lite`로 대본 1개**를 쓴다. 이때 `research/fallback.json`에 기록한다. 쇼츠 대본은 사람이 쓰는 Claude 대화와 같은 구독 한도를 나눠 쓰기 때문에 둔 예비 경로다.
- 설정: `SHORTS_CANDIDATE_MODEL`(후보, 기본 `sonnet`), `SHORTS_CLAUDE_MODEL`(심사·검증, 기본 `opus`), `SHORTS_SCRIPT_CANDIDATES`(기본 3, 1이면 심사 생략), `SHORTS_SCRIPT_WRITER=gemini`(예비 경로 바로 시험)
- 시험 결과(Revolut): 심사가 "원문에 없는 인과"가 있는 후보를 감점, 팩트체크가 "약 2,000명", "월 최대 1만 달러" 같은 조건을 살리고 근거 없는 "GPU 운영 부담" 문장을 삭제

- 명령: `claude -p --output-format json --tools "" --system-prompt <규칙> --json-schema <형식>`
  - `--tools ""`: 파일 읽기·인터넷 검색 같은 도구를 전부 끄고 **글만 쓰게** 한다.
  - `--json-schema`: 정해진 JSON 형식으로만 답하게 강제한다 → 결과는 `structured_output`.
- 입력: 기사 제목, 한 줄 요약, 핵심 포인트, 키워드, 추천 대상, 출처.
- 출력 형식:

```json
{
  "title": "유튜브 제목 (40자 이내)",
  "cover": "화면 맨 위 고정 제목 (2줄, 줄당 10자)",
  "summary": "설명란 요약",
  "tips": ["바로 써먹는 법"],
  "caution": "주의점 (없으면 빈 문자열)",
  "hashtags": ["해시태그"],
  "cuts": [
    {
      "line": "토큰당 비용이 / 10분의 1로 / 줄었대요.",
      "emphasis": ["10분의"],
      "visual": { "type": "number", "value": "1/10", "label": "토큰당 비용" }
    }
  ]
}
```

- `line`의 ` / `는 **화면 자막을 끊을 위치**. 의미가 붙은 말이 떨어지지 않게 대본 단계에서 정한다.
- 받은 대본은 `validate_script`가 점검한다.
  - 컷이 6~20개인지, 대사가 비었는지 확인
  - 강조 단어는 대사에 실제로 있는 것만 남김
  - 그릴 재료가 없는 그래픽은 `none`(자막만)으로 바꿈
  - `=`, `vs`처럼 글자 없는 키워드 카드는 뺌
  - 화면 문구가 자막과 같은 문장이면 지움 (같은 말이 두 번 안 보이게)

### 4) 목소리 (`synthesize_narration` → `gemini_tts`)

- 모델 `gemini-3.1-flash-tts-preview`, 목소리 **Leda (여성) 고정**.
- **대본 전체를 한 번에** 읽힌다. 컷마다 따로 읽히면 컷 사이가 뚝뚝 끊기기 때문이다.
- 말투 지시: "유튜브 쇼츠 내레이터처럼… 빠르고 텐션 높게, 문장 끝을 늘이지 말고 툭툭 끊어서"
- 결과는 PCM(24kHz)으로 오고, ffmpeg로 mp3로 바꾼다.
- **음성 끊김 검사:** Gemini TTS는 가끔 대본 중간에서 음성을 끊어 버린다. 만든 음성을 Whisper로 받아 적어 **대본 글자의 70% 미만**이면 끊긴 것으로 보고 다시 만든다. (영어 이름이 한글로 받아써져 글자 수가 줄기 때문에 여유를 둔 값. 실제로 끊긴 경우는 30% 안팎)
- **한도 대기:** 무료 등급은 분당 요청 한도(429)가 있다. 실패하면 **30초 → 60초 → 90초** 기다렸다가 다시 한다(최대 4번). 분당 한도라 1~2분이면 풀린다.
- **끝까지 실패하면 업로드하지 않고 건너뛴다.** 예비 목소리(edge-tts)는 품질이 떨어지고 채널 목소리가 섞이므로 기본으로 쓰지 않는다. 기록에 남지 않으니 다음 실행에서 같은 기사로 다시 만든다.
  - `SHORTS_ALLOW_FALLBACK_VOICE=1`로 켜면 예전처럼 edge-tts 여성 `ko-KR-SunHiNeural`(속도 +22%)로 대신 만들어 올린다.
  - `GEMINI_API_KEY`가 없는 로컬 시험에서는 바로 edge-tts로 만든다.

### 5) 자막 시점 맞추기 (`transcribe_words` → `align_to_script`)

- Gemini TTS는 "몇 초에 어떤 단어를 말했는지"를 알려주지 않는다.
- 그래서 **faster-whisper `small` 모델**(CPU, int8)로 만든 음성을 다시 받아 적어 단어별 시점을 얻는다.
- 받아 적은 글자는 대본과 조금 다를 수 있어서(띄어쓰기, 숫자 표기), **글자 단위로 대본 어절에 맞춘다**(`difflib`). 화면에는 항상 **대본 원문**이 나온다.
- 컷은 그 컷의 첫 단어를 말하기 시작하는 순간 바뀐다.
- 자막 조각(`caption_chunks`): 대본의 ` / ` 표시대로 묶고, 표시가 없으면 1~2어절(8자 이하)씩 묶는다.

### 6) 영상 렌더링 (`build_props` → `render_with_remotion`)

- `video/` 폴더의 Remotion 프로젝트, 컴포지션 `Short` (1080×1920, 30fps).
- shorts.py가 컷별 시작 프레임, 자막 조각 시점, 그래픽, 효과음 목록을 `props.json`으로 넘긴다.
- 명령: `npx remotion render src/index.ts Short <출력> --props=props.json`
- 마지막 대사 뒤 0.6초 여유 + **마무리 장면 42프레임(1.4초)**: "IT." 로고 + 채널명 + "AI·개발 뉴스, 출근·점심·퇴근길에" + 실로폰 효과음. 마지막 자막에서 뚝 끊기지 않게 한다.
- 화면 구성은 [5. 화면 디자인 사양](#5-화면-디자인-사양) 참고.

### 7) 배경음 (`add_bgm`)

- `bgm.py`가 **영상 길이에 맞춰 곡을 직접 생성**한다 (로파이: 7화음 패드 + 베이스 + 킥 + 하이햇).
- 같은 기사(seed)는 항상 같은 곡, 기사가 바뀌면 화음 진행과 템포가 바뀐다.
- ffmpeg 처리:
  - 배경음 크기 0.15
  - **사이드체인 덕킹**: 내레이션이 나오면 배경음이 자동으로 작아짐
  - **loudnorm -14 LUFS**: 휴대폰 스피커에서도 잘 들리는 쇼츠 표준 음량
  - **리미터 -1.5dB**: loudnorm만으로는 순간 최대 음량이 0dB 가까이 튀어서(실제 -0.1dB 측정) 한 번 더 눌러준다

### 7-1) 업로드 전 자동 검수 (`probe_video` → `find_video_problems`)

ffmpeg 한 번으로 영상을 읽고 아래를 확인한다. **하나라도 실패하면 업로드하지 않고** Slack으로 이유를 알린다. 기록에 남기지 않으므로 다음 실행에서 같은 기사로 다시 만든다. 결과는 작업 폴더의 `qa.json`에 저장.

| 항목 | 통과 기준 |
|---|---|
| 해상도 | 1080×1920 |
| fps | 30 |
| 길이 | 15~75초 |
| 소리 | 소리 트랙 있음 |
| 최대 음량 | -0.5dB 이하 (찢어짐 방지) |
| 평균 음량 | -35dB 이상 (안 들리는 영상 방지) |
| 무음 | 2.5초 넘는 무음 구간 없음 (음성 끊김 감지) |
| 글자 | 제목·설명란·자막에 깨진 글자(�)나 보이지 않는 문자 없음 |

### 8) 업로드 (`upload_youtube`)

- YouTube Data API v3 `videos.insert`, 이어 올리기(resumable) 방식.
- 설정값:
  - 공개 상태 `public` (실제로 공개로 올라가는 것 확인함)
  - 카테고리 `28` (과학기술), 언어 `ko`
  - `selfDeclaredMadeForKids: false` (아동용 아님)
  - `containsSyntheticMedia: true` (AI 합성 콘텐츠 표시, YouTube 정책)
- 설명란 구성은 [7. 업로드와 영상 설명란](#7-업로드와-영상-설명란) 참고.
- **썸네일 (`render_thumbnail` → `set_youtube_thumbnail`):** 업로드 직후 Remotion `Thumbnail` 컴포지션으로 1080×1920 PNG를 만들어 `thumbnails.set`으로 적용한다.
  - 구성: cover 제목 + 대표 그래픽 하나 (우선순위 diagram → metaphor → beforeafter → scale → number → compare → flow → keywords, 없으면 제목만)
  - 채널에 **맞춤 썸네일 권한(전화번호 인증)**이 있어야 한다. 없으면 403. itgony는 2026-11-07 인증 완료.
  - 썸네일 업로드는 하루 횟수 제한(대략 10개 안팎)이 있다. 예전 영상 일괄 적용(`--thumbnail-batch`)은 한 번에 5개까지만 하고 새 영상 몫을 남긴다.
  - 끄려면 저장소 Variables에 `SHORTS_THUMBNAIL=0`.

### 9) 마무리

- `config/shorts_history.json`에 `{날짜, 링크, 제목, video_id, voice}`를 추가하고 main 브랜치에 커밋한다. 다음 실행에서 같은 기사를 다시 만들지 않는다.
  - **기록 합치기:** 그사이 다른 실행이 기록을 올렸으면 충돌로 실패하는 대신, 최신 main 기록에 내 기록 중 없는 항목(`video_id` 기준)만 덧붙여 커밋한다. push가 실패하면 다시 받아와 합치기를 최대 3번 반복한다.
  - 다른 브랜치에서 시험 실행한 결과는 main에 커밋하지 않는다.
  - 업로드하지 않은 시험 영상은 기록에 남기지 않는다.
- Slack으로 "새 Shorts 공개 업로드 + 제목 + 영상 링크 + Studio 링크 + 원문"을 알린다.
- `short.mp4`와 `script.json`을 Actions artifact(`shorts`)로 14일 보관한다.

---

## 4. 대본 작성 규칙 (Claude에게 주는 지시)

`shorts.py`의 `SCRIPT_SYSTEM_PROMPT` 요약.

### 목표
**확실한 정보를 정확하고, 깔끔하고, 이해하기 쉽게.** 길이를 줄이는 것보다 다 보고 나서 "아, 이거구나" 하고 정확히 이해하는 게 우선이다. 시작은 강하게, 설명은 친절하게.

### 말투
- 현업 시니어가 후배한테 뼈 때리듯 말하는 **시니컬한 구어체** ("~죠", "~거든요", "근데", "솔직히")
- 발표체("~했습니다")와 두루뭉술한 말("좋아집니다", "혁신적입니다") 금지
- **한 컷 = 한 호흡 = 사실 하나**, 25자 이내. 사실이 두 개면 컷을 나눈다.
- 컷 10~15개, 30~50초
- 전문 용어는 처음 나올 때 쉽게 풀기 (예: "리드타임, 그러니까 개발 시작부터 배포까지 걸리는 시간")
- 숫자는 "무엇의" 숫자인지 같이 말하기 ("70% 개선" → "리드타임이 70% 줄었다")
- 숫자는 소리 내어 읽기 자연스럽게: 소수점 끝 0 금지 ("0.30달러" → "0.3달러")

### 구조
1. **훅 (첫 3초):** 인사·채널 소개 금지. 기사 주제와 이어지는 개발자의 아픔으로 시작 (예: "AI 청구서, 또 폭탄이죠?")
2. **답:** 이 기사가 내놓은 답이나 가장 센 결과, 이어서 **짧은 연결** 한 컷(10자 안팎, 예: "빠르게 볼게요."). 시청자에게 뭘 하라고 시키거나("끝까지 보세요") 내용을 미리 늘어놓지 않는다.
3. **공간·역할 비유:** 복잡한 구조를 건물·사무실·주방 같은 공간과 역할로 설명 (예: "배달 끊고 자기 주방을 차린 셈"). 영상 하나에 비유 하나만, 끝까지 일관되게. 사실을 왜곡하면 비유 대신 흐름도·비교 그래프로.
4. **수치:** 기사에 있는 숫자와 동작 방식을 구체적으로. 변화는 "처음엔 A, 지금은 B"처럼 전후 숫자로
5. **행동:** 시청자가 이번 주에 할 행동 한 마디 (예: "청구서 보기 전에 토큰 단가부터 뽑아보세요")
6. **다음 영상 잇기:** 짧은 한 줄, 매번 다르게 (예: "이런 소식, 매일 올려요.")

### 제목·설명란
- **제목:** 실제 검색어(회사명·제품명·기술명)를 앞에 + 핵심 결과. 예: "Revolut 자체 호스팅 GLM, AI 비용 90% 절감"
- **cover(화면 제목):** 기사에서 가장 센 구체적 결과(숫자 포함). 첫 장면 훅이자 썸네일
- **question:** 이 영상이 답하는 질문 한 줄 → 설명란 첫 줄

### 사실 규칙 (가장 중요)
- 숫자, 회사명, 결과, 동작 방식은 **주어진 기사에 있는 것만**
- 예시에 나온 수치를 그대로 가져오지 않기
- 기사에 없는 효과("생산성 향상", "보안 강화" 등) 덧붙이지 않기
- 조건이 붙은 내용은 조건까지 같이 말하기
- 기사에 없는 내용은 그냥 넘어간다. "기사엔 안 나와요" 같은 대본 밖 사정을 말하지 않는다

### 그래픽 고르기 (`visual.type`)
같은 종류를 3번 연속 쓰지 않는다. **움직이는 그림 그래픽(diagram·beforeafter·scale·quote)은 영상마다 2개 이상, 종류별로 한 번씩** 쓴다 (시청자가 넘기지 않고 보게 만드는 장치).

| type | 화면 | 쓰는 때 |
|---|---|---|
| `hook` | (그리지 않음) 첫 컷은 cover 제목이 화면 가운데에 크게 나옴 | 첫 컷 전용 |
| `metaphor` | 아이소메트릭 사물 2~3개를 가로로 나란히 + "비유 / 실제 기술". 사물 12종: server, gpu, cloud, database, robot, person, laptop, document, coins, truck, lock, building | 비유를 꺼낼 때 (구조가 바뀌면 한 번 더) |
| `diagram` | 구조도: 사물 2~4개를 화살표로 잇고, 화살표가 그려진 뒤 일감이 흐르고, 카메라가 핵심 마디(`focus`)로 밀고 들어감 | 동작 방식·요청 흐름·구성 |
| `beforeafter` | 전후 비교: 왼쪽 before / 오른쪽 after, 각각 제목·값·사물 | 기사에 바뀌기 전·후 값이 **둘 다** 있을 때만 |
| `scale` | 규모: 같은 사물을 격자로 최대 60개 깔고 큰 숫자 표시 | 숫자를 체감시킬 때 (60 넘으면 상징 개수 + 실제 숫자는 글자로) |
| `quote` | 원문 인용 카드, 핵심 구절은 `**강조**` | 원문 핵심 문장 그대로 (지어낸 문장 금지) |
| `number` | 숫자 카운트업 + 설명 | 인상적인 숫자 하나 |
| `compare` | 막대 비교 그래프 | 기사에 실제 수치가 2개 이상일 때 |
| `flow` | 단계 흐름도 (2~4단계, 명사구) | 과정·원리 |
| `keywords` | 핵심 단어 카드 2~3개 | 개념 정리 |
| `code` | 한 글자씩 타이핑되는 터미널 | 기사와 관련된 명령어·코드 |
| `question` | 맥박 뛰는 물음표 + 질문 | 시청자에게 질문 |
| `none` | 그래픽 없이 자막만 크게 | 쉬어가는 컷 |

---

## 5. 화면 디자인 사양

### 레이아웃 (1080×1920)

| 위치 (y) | 요소 |
|---|---|
| 150 | 채널명 `itgony`(왼쪽) + 출처(오른쪽), 회색 |
| 208 | 얇은 회색 진행 막대 |
| 560 → 250 | **제목(cover)**: 첫 컷 동안 화면 가운데에 크게(훅) → 첫 컷이 끝나면 상단(250)으로 줄어들어 고정. 명조, 숫자 어절은 골드 |
| 470~1070 | 컷별 그래픽 |
| 1110 | 팝업 자막 (그래픽이 없는 컷은 화면 가운데 760에 크게) |

양옆 여백 80px. 위아래는 YouTube 쇼츠 UI(제목, 버튼)에 가리지 않는 영역만 쓴다.

### 테마 (채널 브랜드색에 맞춤)

기본은 **먹색(ink)**. `SHORTS_THEME=paper`로 바꾸면 종이색이 된다.

| 역할 | 먹색 (ink, 기본) | 종이색 (paper) |
|---|---|---|
| 배경 | `#11110F` 따뜻한 먹색 | `#F7F4EA` 종이색 |
| 글자 | `#F7F4EA` | `#11110F` |
| 빨강 (문제·핵심, 한 가지로 통일) | `#EF4B3C` | `#D4382C` |
| 골드 (숫자) | **`#FFC24B`** | `#B07A12` |
| 자막 테두리·그림자 | 없음 | 없음 |

**원칙 (AI 티 줄이기):** 강조색은 역할별로 하나씩만(빨강 = 문제·핵심, 골드 = 숫자). 글자 발광·네온 빛·테두리·그림자 같은 장식은 쓰지 않는다. 글자는 가운데 정렬.

- 배경(`SHORTS_BACKDROP=glow`, 기본): 고정 바탕 + **비네트** + **장면마다 자리를 옮기는 빛**. 컷이 바뀌면 빛이 다음 위치로 부드럽게 이동하고, 숫자 장면(number·scale·beforeafter·compare)에서는 빨강에서 골드로 색이 섞인다. 천천히 흔들리는 움직임이 더해진다. (움직이는 줄무늬는 거슬려서 없앰)
  - `SHORTS_BACKDROP=type`: 위 빛 + 장면 핵심어를 크게 깐 옅은 윤곽 글자.
- 글꼴: Noto Sans KR 500/700/900 (Google Fonts). 코드 화면은 Consolas/DejaVu Sans Mono, 한글은 Noto로 대체(서버에서 □로 깨지는 것 방지).

### 움직임

- **컷 전환:** 화면이 살짝 확대됐다가 자리 잡는 펀치인 + 좌우로 천천히 흐름. 컷끼리 살짝 겹쳐서 그래픽이 **교차 페이드**로 넘어간다(빈 화면이 번쩍이지 않게).
- **마무리:** 화면이 바탕색으로 덮이고 "IT" + 빨간 점 "." 로고가 튀어나온 뒤 채널명과 "AI·개발 뉴스, 매일 3시간마다"가 올라온다.
- **첫 컷:** 흰 섬광이 짧게 번쩍 + 제목이 쾅 찍힘. 첫 컷이 끝나면 제목이 위로 줄어듦.
- **자막:** 0.7배 → 1.05배 → 1배로 튀어나옴. 강조 단어는 색이 바뀜 (숫자가 있으면 골드, 아니면 빨강).
- **3D 그림:** 바닥 판이 위에서 떨어져 내려앉고 사물이 톡 튀어나옴. 사물 사이로 일감(골드 점)이 오감. 첫 번째(핵심)만 빨강.
- **숫자:** 고정폭 숫자로 카운트업 (올라가는 동안 좌우로 떨리지 않음). 큰 숫자는 화면 폭에 맞게 자동으로 줄어든다.

### 채널 꾸미기 (같은 브랜드)
`video/src/brand/Brand.tsx`로 만든다. 자세한 건 `docs/BRANDING.md`.
- 프로필 800×800 (종이색 / 먹색 두 가지)
- 배너 2560×1440 (모든 기기에서 보이는 가운데 1546×423 안에만 글씨)
- 워터마크 150×150 (쇼츠에는 안 보이고 일반 영상에만 표시)

---

## 6. 소리: 내레이션·배경음·효과음

| 소리 | 만드는 곳 | 크기 | 비고 |
|---|---|---|---|
| 내레이션 | Gemini TTS (Leda) | 기준 | 끝까지 실패하면 그 회차 건너뜀 |
| 배경음 | `bgm.py` 코드 생성 | 0.15 | 말할 때 자동으로 작아짐 |
| 효과음 "쾅" | `bgm.py` (`impact.wav`) | 0.5 | **첫 장면에만** |
| 효과음 "휙" | `bgm.py` (`whoosh1.wav`) | 0.25 | **3D 건물이 처음 나올 때만** |
| 효과음 "딩-딩-딩-띵" | `bgm.py` (`chime.wav`, 실로폰 C6·E6·G6→C7, 약 1초) | 0.55 | **마무리 로고에서만** |
| 최종 음량 | ffmpeg loudnorm | -14 LUFS | 쇼츠 표준 음량 |

> 예전에는 컷이 바뀔 때마다 효과음이 나서(영상당 15~20번) 거슬렸다. 지금은 본편에서 **최대 2번** + 마무리 차임 1번만 난다. (PR #61, #69)

---

## 7. 업로드와 영상 설명란

설명란은 `build_description`이 자동으로 만든다.

```text
{이 영상이 답하는 질문}       ← 검색 결과·미리보기에 보이는 첫 줄

{요약 1~2문장}

✅ 바로 써먹는 법
- {tip 1}
- {tip 2}

⚠️ 주의
{주의점}                      ← 없으면 생략

🔗 원문
{기사 링크}

📺 지난 영상
- {최근 영상 제목}: https://youtu.be/...   ← 최근 3개

이 영상의 대본과 음성은 AI로 생성되었습니다.

#shorts #해시태그1 #해시태그2 ...
```

- 제목: 대본의 `title` (100자 제한, 검색어 앞쪽)
- 제목·설명란의 깨진 글자·보이지 않는 문자는 자동으로 지운다
- 태그: 대본의 `hashtags`

---

## 8. 돈이 안 나가는 이유 (비용 0원 구조)

| 단계 | 쓰는 것 | 왜 무료인가 | 한도를 넘으면? |
|---|---|---|---|
| 실행 서버 | **GitHub Actions** | 공개(Public) 저장소는 표준 러너 사용 시간이 무료 | 해당 없음 (공개 저장소 무제한) |
| 뉴스 요약 | **Gemini `gemini-3.1-flash-lite`** | Google AI Studio 무료 등급 API 키 (결제 수단 미연결) | 요금이 아니라 **요청 실패**로 끝남 |
| 대본 | **Claude (`claude -p`)** | API 키가 아니라 **이미 내고 있는 Claude 구독**으로 실행 (`CLAUDE_CODE_OAUTH_TOKEN`, `claude setup-token`으로 발급한 1년짜리 토큰) | 구독 사용량 한도 안에서만 동작. 추가 과금 없음. 한도에 걸리면 **무료 Gemini로 대본**을 씀 |
| 목소리 | **Gemini TTS** | 같은 무료 등급 키 | 기다렸다 재시도, 그래도 안 되면 **그 회차 건너뜀** |
| 예비 목소리 | **edge-tts** | Microsoft Edge "소리 내어 읽기" 음성, 무료. 로컬 시험용 (업로드에는 기본으로 안 씀) | — |
| 자막 시점 | **faster-whisper** | 오픈소스, GitHub Actions 서버에서 직접 실행 | — |
| 영상 편집 | **Remotion** | 개인·3인 이하 회사는 무료 라이선스 | — |
| 글꼴 | **Noto Sans/Serif KR** | Google Fonts, 오픈 폰트 라이선스(OFL) | — |
| 배경음·효과음 | **bgm.py** | 코드로 직접 만든 소리라 음원 구매·저작권(Content ID) 문제 없음 | — |
| 영상 합성 | **ffmpeg** (imageio-ffmpeg) | 오픈소스 | — |
| 업로드 | **YouTube Data API v3** | 하루 10,000유닛 무료 할당량. Google Cloud에 **결제 계정을 연결하지 않음** | 요금이 아니라 **quotaExceeded 실패** (다음 날 재시도) |
| 웹 신문 | **GitHub Pages** | 공개 저장소 무료 호스팅 | — |
| 알림 | **Slack Incoming Webhook** | 무료 | — |

**핵심 원칙**
1. **결제 수단을 어디에도 연결하지 않는다.** (Google Cloud, Google AI Studio) → 한도를 넘어도 청구가 아니라 실패로 끝난다.
2. **유료 API 키 대신 이미 내는 구독을 쓴다.** (Claude Pro/Max → `claude -p`) Anthropic API 키(`ANTHROPIC_API_KEY`)는 쓰지 않는다. 쓰면 사용량만큼 과금된다.
3. **외부 음원·이미지를 쓰지 않는다.** 소리·그래픽은 전부 코드로 만든다.
4. **품질을 낮춰서라도 올리기보다, 건너뛰고 다음 실행에서 다시 한다.** 기록에 남기지 않으면 같은 기사가 다음 실행에서 자동으로 다시 잡힌다. (대본은 Claude → Gemini 예비 경로가 있지만, 목소리는 채널 정체성이라 대체하지 않음)

> ⚠️ 주의: Google Cloud 프로젝트나 AI Studio에 결제 계정을 연결하면 무료 한도를 넘는 순간부터 과금될 수 있다. 연결하지 말 것.

---

## 9. 한도와 제약

| 항목 | 한도 | 대응 |
|---|---|---|
| YouTube 업로드 | 하루 10,000유닛 ÷ 1,600 = **6편** | 3시간 간격 6번. 더 늘리려면 할당량 증가 신청(무료, 초안: `youtube-audit-answers.md`) |
| 할당량 초기화 | 미국 태평양 자정 = **한국 17:00** | 이 시점을 걸쳐 고르게 실행 |
| 할당량 우회 | Cloud 프로젝트 여러 개로 나눠 쓰기는 **정책 위반** | 하지 않음 (레포를 늘려도 한도는 그대로) |
| Gemini 무료 등급 (TTS) | 분당·일일 요청 수 제한 (429) | 30·60·90초 기다렸다 재시도, 그래도 안 되면 건너뜀 |
| Claude 구독 | 플랜별 사용량 한도 (사람이 쓰는 대화와 공유) | 후보는 Sonnet으로 아끼고, 막히면 Gemini가 대본 작성 |
| GitHub Actions | 실행 1번 45분 제한, 대기열 지연 있을 수 있음 | 한 편 8~10분 (TTS 대기 시 최대 3분 더) |
| 썸네일 업로드 | 하루 횟수 제한 (대략 10개 안팎), 채널 전화번호 인증 필요 | 새 영상 우선, 일괄 적용은 한 번에 5개 |

---

## 10. 처음 한 번 해야 하는 설정

### GitHub Secrets (저장소 → Settings → Secrets and variables → Actions)

| 이름 | 용도 | 만드는 법 |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | 대본 (구독) | 로컬에서 `claude setup-token` → 출력된 `sk-ant-oat...` 토큰 |
| `GEMINI_API_KEY` | 뉴스 요약 + 목소리 | Google AI Studio에서 무료 API 키 발급 (결제 연결 X) |
| `YOUTUBE_CLIENT_ID` | 업로드 | 아래 YouTube 설정 |
| `YOUTUBE_CLIENT_SECRET` | 업로드 | 아래 YouTube 설정 |
| `YOUTUBE_REFRESH_TOKEN` | 업로드 | 아래 YouTube 설정 |
| `SLACK_WEBHOOK_URL` | 알림 | Slack Incoming Webhook |

### YouTube 업로드 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성 → **YouTube Data API v3** 사용 설정 (결제 계정 연결 안 함).
2. OAuth 동의 화면 생성 → 가능하면 **프로덕션으로 게시**. (테스트 상태로 두면 refresh token이 7일 뒤 만료될 수 있으니, 업로드가 갑자기 인증 오류로 실패하면 `youtube_auth.py`를 다시 실행)
3. 사용자 인증 정보 → OAuth 클라이언트 ID → 유형 **데스크톱 앱** → JSON 다운로드.
4. 로컬에서 실행:

```bash
python youtube_auth.py
```

   - 다운로드 폴더의 `client_secret*.json`을 찾아 브라우저 로그인을 띄운다.
   - **itgony 채널이 있는 Google 계정**(브랜드 채널이면 채널 선택)으로 허용한다.
   - 연결된 이메일과 채널 이름을 보여주고 확인(y)하면 Secrets 3개를 `gh`로 바로 등록한다.
5. 개인정보처리방침 URL: https://dev-gony.github.io/technews/privacy.html

---

## 11. 수동 실행·테스트 방법

### GitHub Actions에서 (실제 환경과 똑같이, 업로드 없이)

```bash
gh workflow run shorts.yml --ref <브랜치> -f upload=false
```

추가 입력:

| 입력 | 뜻 | 예 |
|---|---|---|
| `date` | 이슈 날짜 | `2026-11-04` |
| `upload` | YouTube에 올릴지 | `false` |
| `link` | 이 기사로 만들기 (이미 만든 기사도 가능) | `https://news.hada.io/topic?id=36534` |
| `theme` | 배경 테마 | `ink` / `paper` |
| `script` | Claude 대신 이 대본 파일 사용 | `tests/fixtures/revolut_script.json` |
| `writer` | 대본 작성자 (`gemini`면 예비 경로 시험) | `gemini` |
| `thumbnail_only` | 영상은 안 만들고, `script` 대본으로 만든 썸네일만 이 영상 ID에 적용 | `abc123XYZ` |
| `thumbnail_batch` | 이미 올린 영상들에 썸네일 일괄 적용 (`[{video_id, title, script}]` 파일) | `runtime/thumbs.json` |

결과 영상 받기:

```bash
gh run download <run-id> -n shorts -D runtime/test
```

> 예약 실행은 main에서만 돌고, 다른 브랜치 시험 결과는 기록(history)에 남지 않는다.

### 로컬에서

```bash
pip install -r requirements.txt
cd video && npm ci && cd ..
python shorts.py --no-upload
```

- `--date`, `--link`, `--script`, `--thumbnail-only`, `--thumbnail-batch` 옵션은 Actions 입력과 같다.
- 로컬에 `GEMINI_API_KEY`가 없으면 edge-tts 목소리로 만들어진다. (실제와 같은 목소리로 보려면 Actions에서 시험)
- Windows: `PYTHONIOENCODING=utf-8`, `pip install tzdata` 필요.
- 디자인 미리보기: `cd video && npm run dev` (Remotion Studio)

### 테스트

```bash
python -m unittest tests.test_shorts tests.test_cards tests.test_bgm
cd video && npx tsc --noEmit
```

---

## 12. 설정값 (환경변수)

| 이름 | 기본값 | 설명 |
|---|---|---|
| `SHORTS_CLAUDE_MODEL` | `opus` | 심사·팩트체크 모델 (비우면 구독 플랜 기본) |
| `SHORTS_CANDIDATE_MODEL` | `sonnet` | 대본 후보 3개 작성 모델 |
| `SHORTS_SCRIPT_WRITER` | `claude` | `gemini`면 Claude 없이 예비 경로로 바로 작성 (시험용) |
| `SHORTS_GEMINI_SCRIPT_MODEL` | `gemini-3.1-flash-lite` | Claude가 막혔을 때 대본 쓰는 모델 |
| `SHORTS_SCRIPT_CANDIDATES` | `3` | 대본 후보 수 (1이면 심사 생략) |
| `SHORTS_GEMINI_TTS_MODEL` | `gemini-3.1-flash-tts-preview` | TTS 모델 |
| `SHORTS_GEMINI_VOICES` | `Leda` | 쉼표로 여러 개 넣으면 영상마다 번갈아 사용 |
| `SHORTS_ALLOW_FALLBACK_VOICE` | (꺼짐) | `1`이면 Gemini TTS 실패 시 edge-tts 목소리로 만들어 업로드 |
| `SHORTS_VOICE` | `ko-KR-SunHiNeural` | 예비 음성 (edge-tts) |
| `SHORTS_TTS_RATE` | `+22%` | 예비 음성 속도 |
| `SHORTS_WHISPER_MODEL` | `small` | 자막 시점용 Whisper 모델 |
| `SHORTS_THEME` | `ink` | 배경 테마 `ink` / `paper` |
| `SHORTS_BACKDROP` | `glow` | 배경 `glow`(장면마다 옮겨 가는 빛) / `type`(빛 + 핵심어 윤곽 글자) |
| `SHORTS_THUMBNAIL` | (켜짐) | `0`이면 썸네일 적용 안 함 (저장소 Variables) |
| `SHORTS_THUMBNAIL_BATCH_LIMIT` | `5` | 일괄 적용 한 번에 넣을 최대 개수 |
| `SHORTS_BGM_VOLUME` | `0.15` | 배경음 크기 (0이면 없음) |
| `SHORTS_LOOKBACK_DAYS` | `3` | 기사 고를 최근 이슈 일수 |
| `SHORTS_PRIVACY` | `public` | 업로드 공개 상태 |
| `SHORTS_CHANNEL_NAME` | `itgony` | 화면 왼쪽 위 채널명 |

---

## 13. 파일 구조

| 경로 | 역할 |
|---|---|
| `main.py` | GONY DAILY 뉴스 수집·요약 (원재료) |
| `config/issues/YYYY-MM-DD.json` | 날짜별 이슈 (쇼츠 원재료) |
| `shorts.py` | 쇼츠 파이프라인 전체 (기사 선택 → 대본 → 음성 → 렌더링 → 업로드) |
| `bgm.py` | 배경음·효과음 생성 |
| `youtube_auth.py` | YouTube 로그인 + Secrets 자동 등록 (로컬, 1회) |
| `config/shorts_history.json` | 업로드한 영상 기록 (중복 방지) |
| `.github/workflows/shorts.yml` | 하루 6번 예약 실행 + 수동 실행 |
| `video/src/Root.tsx` | Remotion 컴포지션 등록 (Short, Cards, 채널 꾸미기) |
| `video/src/Short.tsx` | 쇼츠 화면 (컷, 상단 제목, 진행 막대, 출처, 마무리 로고) |
| `video/src/Visuals.tsx` | 기본 컷 그래픽 (number, compare, flow, keywords, code, question 등) |
| `video/src/VisualsPro.tsx` | 움직이는 그림 그래픽 (diagram, beforeafter, scale, quote) |
| `video/src/visualKit.tsx` | 그래픽 공용 부품 |
| `video/src/Isometric.tsx` | 아이소메트릭 사물 12종 |
| `video/src/Thumbnail.tsx` | 썸네일 (cover + 대표 그래픽) |
| `video/src/Captions.tsx` | 팝업 자막 |
| `video/src/Background.tsx` | 배경 (장면마다 옮겨 가는 빛) |
| `video/src/theme.ts` | 테마 색 (ink/paper), 글꼴, 레이아웃 |
| `video/src/schema.ts` | props 형식 (shorts.py와 같은 구조) |
| `video/src/brand/Brand.tsx` | 프로필·배너·워터마크 |
| `.claude/skills/` | Remotion 공식 Claude Code 스킬 |
| `tests/test_shorts.py` | 쇼츠 테스트 |
| `tests/fixtures/revolut_script.json` | 시험용 고정 대본 |
| `runtime/shorts/<날짜>_<기사>/` | 작업 폴더: 대본, `research/`(원문·후보·심사·팩트체크), 음성, props, `qa.json`, `thumbnail.png`, 최종 `short.mp4` (git 제외) |
| `docs/SHORTS.md` | 기술 문서 (짧은 버전) |
| `docs/BRANDING.md` | 채널 꾸미기 |

---

## 14. 겪었던 문제와 해결

| 문제 | 원인 | 해결 |
|---|---|---|
| Claude API 키를 쓰면 돈이 나감 | API는 사용량 과금 | 구독 계정 토큰(`claude setup-token`) + `claude -p`로 변경 |
| 토큰을 붙여넣으면 인증 실패 | 터미널 줄바꿈·공백이 섞임 | `normalize_oauth_token`이 토큰 조각만 이어 붙임 |
| 업로드 시 `youtubeSignupRequired` | 허용한 Google 계정에 채널이 없었음 | 채널 계정으로 다시 로그인 (`youtube_auth.py`가 채널 확인) |
| 코드 화면 한글이 □로 깨짐 | 리눅스 고정폭 글꼴에 한글 없음 | 글꼴 목록 끝에 Noto Sans KR 추가 |
| 자막이 "엔지니어 한 / 명당"처럼 어색하게 끊김 | 기계적으로 2어절씩 자름 | 대본 단계에서 ` / `로 끊을 위치 지정 |
| 국어책 읽는 말투 | 발표체 대본 + 기본 TTS | 구어체 규칙 + Gemini TTS 말투 지시 |
| 영상이 정적임 | 장면이 길고 그래픽이 단순 | 컷 편집, 펀치인, 그래픽 9종, 3D 비유 |
| 배경이 칙칙하고 브랜드와 따로 놂 | 남색·파란 빛 배경 | 먹색·빨강·골드 브랜드 테마 |
| 배경 줄무늬가 거슬림 | 줄이 위로 흘러감 | 줄무늬 제거, 비네트로 대체 |
| 화면 넘어갈 때 소리가 너무 잦음 | 컷마다 효과음 | 영상당 최대 2번 (PR #61) |
| 남성 목소리는 집중이 안 됨 | 4개 목소리 번갈아 사용 | 여성 Leda 고정 (PR #61) |
| 강조가 여기저기라 핵심이 안 보임, AI 티 | 빨강 6곳·발광·테두리 | 역할별 강조색 하나, 장식 제거 (PR #62) |
| 핵심 훅 문구가 약함 | 상단 작은 제목 | 첫 장면에 제목을 크게 → 위로 줄어듦 (PR #62) |
| 3D 비유가 추상적 | 판만 쌓임 | 아이소메트릭 사물 12종 (PR #62) |
| 대본에 깨진 글자(�) | 모델 출력 | `clean_text`로 자동 제거 |
| 최대 음량 -0.1dB (찢어짐 직전) | loudnorm 한 번 | 리미터 추가 + 업로드 전 자동 검수 |
| 하루 한 편만 만듦 | 하루 1번 실행 | 6번 실행 + 오늘 기사 우선 선택 |
| 그래픽이 단조로워 넘김 | 숫자·키워드 카드 위주 | 구조도·전후 비교·규모·인용 그래픽 추가, 영상마다 2개 이상 (PR #67) |
| 컷 넘어갈 때 빈 화면이 번쩍 | 앞 그래픽이 사라진 뒤 다음 그래픽 등장 | 컷을 겹쳐 교차 페이드 (PR #67) |
| 마지막 자막에서 영상이 뚝 끊김 | 대사 끝 = 영상 끝 | "IT." 마무리 로고 + 실로폰 차임 (PR #69) |
| "0.30달러"처럼 어색하게 읽힘 | 소수점 끝 0 | 대본 규칙 + 끝 0 자동 제거 (PR #67) |
| "기사엔 안 나와요" 같은 말이 대본에 들어감 | 대본이 빠진 정보를 굳이 언급 | 대본 밖 사정 언급 금지 규칙 (PR #67) |
| 대본 때문에 Claude 대화 한도가 금방 참 | 대본 5번 호출 모두 Opus | 후보 3개는 Sonnet, 막히면 Gemini (PR #70) |
| 음성이 대본 중간에서 끊긴 채 업로드 | Gemini TTS가 가끔 중간에 멈춤 | Whisper로 받아 적어 70% 미만이면 다시 만듦 (PR #70) |
| 한도(429)에 걸려 SunHi 목소리 영상이 섞임 | 바로 edge-tts로 대체 | 30·60·90초 기다렸다 재시도, 그래도 안 되면 업로드 안 함 |
| 같은 기사가 두 번 업로드됨 | 줄 서 있던 실행이 앞 실행의 기록 없이 시작 + 기록 push 충돌 | 시작 시 최신 main 기록 받기 + push 때 기록 합치기 |

---

## 15. 앞으로 할 것

- [x] PR #61 머지 (효과음 줄이기 + 목소리 고정)
- [x] PR #62 머지 (새 디자인)
- [x] 맞춤 썸네일 자동 적용 (PR #64, #65)
- [ ] 주간 성과 리포트 (조회수 TOP 5 + 형식 분석, 영상 2주 쌓인 뒤)
- [ ] 먹색/종이색 번갈아 올려 시청 지속률 비교 (선택)
- [ ] 인스타그램: 카드뉴스 하루 2편 + 릴스 3편 (계정 생성 대기 중, 카드 생성기는 `cards.py`로 완성)
- [ ] 스레드: 카드뉴스와 함께 게시
- [ ] 틱톡: 앱 심사(2~6주) 후
- [ ] YouTube 할당량 증가 신청 (선택, 무료)
