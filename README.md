# 📰 Daily Tech News Bot

국내외 IT 기업의 기술 블로그를 자동으로 확인하고,  
새 글이 발견되면 Gemini API를 이용해 한국어로 요약한 뒤  
Slack으로 매일 아침 기술 브리핑을 전달하는 자동화 프로젝트입니다.

## 🎯 프로젝트 목적

여러 기업의 기술 블로그를 매일 직접 확인하는 번거로움을 줄이고,
관심 있는 기술 정보를 한 곳에서 빠르게 확인하기 위해 만들었습니다.

단순히 새 글 링크를 전달하는 것이 아니라,

- 글의 핵심 내용
- 알아두면 좋은 기술 개념
- 추천 대상
- 오늘 꼭 볼 글
- 오늘의 기술 키워드
- 추가로 공부하면 좋은 내용

까지 AI가 정리해서 Slack으로 전달합니다.

---

## ✨ 주요 기능

### 1. 여러 기술 블로그 자동 수집

RSS 또는 HTML 페이지를 이용해
국내외 기술 블로그의 최신 글을 확인합니다.

현재 약 29개의 기술 블로그를 모니터링합니다.

예시:

- 네이버 D2
- 네이버 플레이스
- 쿠팡
- 요기요
- 토스
- 뱅크샐러드
- 쏘카
- G마켓
- 마켓컬리
- 당근
- LINE Engineering
- 데브시스터즈
- 무신사
- Google Developers
- GitHub Blog
- Meta Engineering
- Netflix TechBlog
- Airbnb Engineering
- Slack Engineering
- Spotify Engineering
- Stripe
- Cloudflare
- AWS
- Uber Engineering

일부 사이트는 RSS를 제공하고,
일부 사이트는 HTML 페이지를 직접 분석합니다.

---

## 2. 중복 게시글 방지

한 번 처리한 글은 `sent_articles.json`에 저장합니다.

다음 실행부터는 이미 처리한 URL을 제외하고
새 글만 처리합니다.

```text
새 글 발견
↓
Gemini 요약
↓
Slack 전송 성공
↓
sent_articles.json에 URL 저장
