# YouTube API 심사 신청서 답변 초안

신청 페이지: https://support.google.com/youtube/contact/yt_api_form
→ **Google Cloud 프로젝트를 만든 계정(gg...)으로 로그인**한 뒤 작성하세요.
→ **자동 공개는 이미 됩니다**(2026-11-05 업로드가 공개로 올라간 것 확인). 그래서 이 신청은 **하루 6편보다 더 올리고 싶을 때만** 필요합니다.
→ 신청 종류는 **"Quota extension"(한도 증설)** 을 고릅니다(양식에 감사가 함께 묶여 있으면 그대로 진행).
   - 지금 한도(10,000)로는 하루 6편이 최대라서, GONY DAILY 기사 수(하루 5~19개)만큼 올릴 수 있게 32,000으로 요청합니다.

`[ ]` 표시만 직접 채우면 됩니다. 나머지는 그대로 복사해서 붙여넣으세요.
양식 문항 이름이 조금 다를 수 있으니, 가장 비슷한 칸에 넣으면 됩니다.

---

## 1. 연락처 / 기본 정보

| 문항 | 답변 |
|---|---|
| Name | `[본인 이름]` |
| Email | `[Google Cloud 계정 이메일]` |
| Company / Organization name | `Individual developer (itgony)` |
| Company website | `https://dev-gony.github.io/technews/` |
| Country | `South Korea` |

## 2. API 프로젝트 정보

| 문항 | 답변 |
|---|---|
| Google Cloud project ID | `project-db56ee32-1c1b-4881-b97` |
| Google Cloud project number | `[콘솔 → 대시보드 → 프로젝트 정보 카드의 "프로젝트 번호" 숫자]` |
| OAuth client ID | `[GitHub Secrets의 YOUTUBE_CLIENT_ID 값, 또는 콘솔 → 클라이언트 → itgony]` |
| Which YouTube API services do you use? | `YouTube Data API v3` |
| YouTube channel(s) the API client accesses | `https://www.youtube.com/@GONYIT-h3r` (itgony) |

## 3. API 클라이언트 설명 (가장 중요한 칸)

**What does your API client do? / Describe your use case**

```
This is a personal automation tool used only by the owner of a single YouTube channel (itgony, @GONYIT-h3r).

Every day, a scheduled GitHub Actions job reads tech news that I curate on my own site (GONY DAILY, https://dev-gony.github.io/technews/), generates a 30–45 second explainer Short about one article (script, AI voice, captions, motion graphics), and uploads it to my own channel with videos.insert.

- Only my own channel is accessed. There are no other users and no public sign-up; the OAuth consent is granted once by the channel owner.
- Scopes: youtube.upload (to upload my videos) and youtube.readonly (only to confirm that the authorized account is my channel before saving the token).
- No YouTube data is collected, stored, analyzed, or shown to anyone. The tool only stores the uploaded video ID and title in my own repository to avoid uploading the same article twice.
- Each upload sets containsSyntheticMedia=true and states in the description that the script and voice are AI-generated, with a link to the original news source.
- Volume: my news site publishes 5–19 detailed articles per day. With the default 10,000 unit quota (1,600 units per videos.insert) I can upload at most 6 Shorts per day.

I am requesting (1) the audit, so that uploads are no longer locked to private and can be published as public automatically, and (2) a daily quota of 32,000 units, so I can upload up to 20 Shorts per day (20 × 1,600 = 32,000), one per article.
```

## 3-1. 한도 증설 문항 (나오면)

| 문항 | 답변 |
|---|---|
| Current quota | `10,000` |
| Requested quota (units per day) | `32,000` |
| Why do you need more quota? | 아래 영어 문단 |

```
Each Short is uploaded with one videos.insert call (1,600 units). My news site publishes 5–19 detailed tech articles per day, and I want to publish one Short per article. 20 uploads per day require 32,000 units. Uploads are spread across the day by a scheduler, all to my own single channel. No other API methods consume meaningful quota.
```

## 4. 사용하는 API 메서드

**Which API methods / endpoints does your client call?**

```
- videos.insert (resumable upload, part=snippet,status) — upload one Short to my own channel
- channels.list (part=snippet, mine=true) — called once during the one-time OAuth setup to confirm the authorized channel
- OAuth 2.0 token endpoint — refresh the access token before each upload
```

## 5. 데이터 처리 / 정책 준수

**How do you store and use YouTube API data? / Data retention**

```
The only data kept is the video ID and title returned by videos.insert, saved in a JSON file in my private automation repository (config/shorts_history.json) to prevent duplicate uploads and to link previous videos in new descriptions. No other API data is stored. OAuth credentials are kept as encrypted GitHub Actions secrets and can be revoked at any time from my Google account.
```

**Privacy policy URL**

```
https://dev-gony.github.io/technews/privacy.html
```

**Terms of service URL** (필수가 아니면 비워도 됨)

```
https://dev-gony.github.io/technews/privacy.html
```

**Does your client display YouTube data to users?**

```
No. It only uploads videos to my own channel.
```

**Does your client allow other users to authorize their accounts?**

```
No. Only the channel owner authorizes it, once.
```

## 6. 첨부 자료 (스크린샷/영상을 요구하는 경우)

아래 화면을 캡처해서 올리면 됩니다.

1. GitHub Actions의 **Daily Shorts** 실행 기록 화면 (업로드 완료 로그가 보이게)
2. YouTube Studio의 itgony 채널 콘텐츠 목록 (자동 업로드된 Shorts)
3. Google Cloud **OAuth 동의 화면**(브랜딩) 화면
4. 개인정보처리방침 페이지 화면

## 7. 제출 후

- 보통 몇 주 걸리고, Google이 메일로 추가 질문을 보낼 수 있습니다. 질문이 오면 메일 내용을 붙여넣어 주세요. 답변을 같이 쓰겠습니다.
- 감사가 승인되면 따로 할 일은 없습니다. 이미 공개로 업로드를 요청하고 있어서 그때부터 자동 공개됩니다.
- 한도 증설이 승인되면 알려주세요. 하루 실행 횟수를 승인된 한도에 맞게 늘리겠습니다.
