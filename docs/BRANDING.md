# itgony 채널 꾸미기

이미지는 Remotion `video/src/brand/Brand.tsx`에서 만든다. 다시 뽑을 때(`video/` 폴더에서):

```bash
npx remotion still src/index.ts ProfilePaper ../runtime/brand/ProfilePaper.png --image-format=png
npx remotion still src/index.ts ProfileInk ../runtime/brand/ProfileInk.png --image-format=png
npx remotion still src/index.ts Banner ../runtime/brand/Banner.png --image-format=png
npx remotion still src/index.ts Watermark ../runtime/brand/Watermark.png --image-format=png
```

| 파일 | 크기 | 쓰는 곳 |
| --- | --- | --- |
| ProfilePaper.png / ProfileInk.png | 800x800 | 유튜브·인스타·스레드 프로필 사진 (둘 중 하나) |
| Banner.png | 2560x1440 | 유튜브 배너 (가운데 1546x423만 모든 기기에 보임) |
| Watermark.png | 150x150 | 유튜브 영상 워터마크 (구독 버튼) |

## 유튜브

YouTube Studio → **맞춤설정**

- **브랜딩 탭:** 사진 = 프로필, 배너 이미지 = Banner.png, 동영상 워터마크 = Watermark.png (표시 시간: 전체 동영상)
- **기본 정보 탭:** 아래 설명·링크 붙여넣기

채널 설명:

```
오늘 꼭 알아야 할 테크 뉴스를 1분으로 요약합니다.

📰 매일 6편 · 07시부터 3시간마다 업로드
▪ AI, 개발, 빅테크, 보안 소식을 쉽게
▪ 뉴스마다 "바로 해볼 행동"까지 정리
▪ 원문 링크는 영상 설명에 있어요

모든 영상은 GONY DAILY(매일 아침 테크 신문)의 기사를 바탕으로
AI가 대본·음성·편집을 만들고 사람이 운영합니다.

🗞 GONY DAILY: https://dev-gony.github.io/technews/
```

링크: `GONY DAILY` → https://dev-gony.github.io/technews/

채널 키워드(설정 → 채널 → 기본 정보):

```
테크뉴스 IT뉴스 AI뉴스 개발자 개발뉴스 인공지능 ChatGPT Claude 빅테크 쇼츠 1분뉴스 GONYDAILY
```

## 인스타그램 (계정 만든 뒤)

- 이름: `itgony | 1분 테크 뉴스` (검색에 걸리게 이름 칸에 키워드)
- 프로필 사진: 유튜브와 같은 것
- 바이오 (150자 이내):

```
오늘 꼭 알아야 할 테크 뉴스 📰
▪ 매일 카드뉴스 + 1분 릴스
▪ AI·개발·빅테크를 쉽게, 써먹는 법까지
💾 저장해두고 필요할 때 꺼내 보세요
```

- 링크: https://dev-gony.github.io/technews/

## 스레드

인스타 계정으로 로그인하면 프로필 사진·이름을 가져온다. 바이오만 짧게:

```
매일 테크 뉴스 한 줄 요약 📰 AI·개발·빅테크 · 카드뉴스는 인스타 @itgony
```
