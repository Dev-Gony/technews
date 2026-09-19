# TechNews

여러 기술 블로그와 GeekNews를 매일 확인하고,  
새 글을 선별·요약해 Slack으로 전달하는 개인용 기술 뉴스 자동화 프로젝트입니다.

단순 RSS 알림이 아니라 **수집 → 중복 제거 → 가치 평가 → 요약 → 전달 → 피드백 데이터 저장**까지 하나의 반복 가능한 파이프라인으로 구성했습니다.

## Problem

기술 블로그를 여러 곳 구독하면 읽을 글은 많아지지만 실제로 중요한 글을 고르는 시간이 더 많이 듭니다.

이 프로젝트에서는 다음 문제를 줄이는 것을 목표로 했습니다.

- 여러 기술 블로그를 직접 확인해야 하는 반복 작업
- 이미 본 글과 새 글을 매번 구분해야 하는 문제
- 관심 분야와 관계없는 글까지 모두 읽게 되는 문제
- 기사마다 LLM을 호출할 때 생기는 API 요청 증가
- 요약 결과를 실제로 읽었는지, 도움이 됐는지 다시 반영하기 어려운 문제

## Pipeline

```text
GitHub Actions
      |
      v
RSS / Atom / HTML Collection
      |
      v
New Article Detection
      |
      v
URL / Title Deduplication
      |
      v
Gemini Relevance Scoring
      |
      +--> detailed briefing
      +--> short mention
      `--> excluded
      |
      v
Batch Summarization
      |
      v
Daily Editorial
      |
      v
Slack Digest
      |
      +--> feedback cards
      `--> article history
```

## What Is Implemented

### Multi-source collection

국내외 기업 기술 블로그와 GeekNews를 포함한 여러 소스를 수집합니다.

- RSS / Atom 지원 사이트는 feed 기반으로 처리
- RSS가 없는 일부 사이트는 HTML 구조를 이용해 최근 글 탐색
- 사이트별 최근 확인 범위를 제한해 불필요한 요청 감소

### New article detection and deduplication

- 처리한 URL을 상태 파일에 저장
- URL 정규화
- 같은 실행 안에서 URL / 제목 기준 중복 제거
- 평가나 요약에 실패한 글은 완료 처리하지 않아 다음 실행에서 다시 확인

### Gemini-based filtering

모든 기사를 바로 상세 요약하지 않습니다.

먼저 다음 기준으로 기사를 평가합니다.

- 관심 분야와의 관련성
- 실무 / 프로젝트 활용 가치
- 기술 및 업계 변화의 중요도

평가 결과에 따라 상세 브리핑, 짧은 소개, 제외 대상으로 분리합니다.

### Batch processing

API 호출 수를 줄이기 위해 기사별 개별 호출 대신 배치 단위 평가와 요약을 사용합니다.

이 구조는 새 글이 많은 날에도 요청 수가 기사 개수에 그대로 비례해 증가하지 않도록 하기 위한 선택입니다.

### Slack delivery

최종 브리핑은 Slack으로 전달합니다.

- 상세 요약
- 참고할 글
- 오늘의 기술 키워드
- 주요 포인트
- 실패한 소스 정보
- 메시지 길이에 따른 분할 전송

새 글이 없으면 메시지를 보내지 않습니다.

### Feedback and history

현재 코드에는 다음 확장을 위한 기반도 포함되어 있습니다.

- 기사별 Slack 피드백 카드
- 기사 이력 저장
- Trend Radar용 히스토리 축적

현재 단계에서는 이 데이터를 쌓고 있으며, 이후 추천 기준과 기술 흐름 감지에 연결하는 방향으로 확장하고 있습니다.

## Reliability

운영 자동화를 만들면서 다음 부분을 별도로 처리했습니다.

- Gemini 429 / 5xx 오류 재시도
- 평가 결과 누락 검증
- 일부 소스 실패 시 전체 실행 중단 방지
- 처리 완료 / 미완료 기사 분리
- GitHub Actions 중복 실행 방지
- 런타임 상태 파일 자동 저장

## Automation

GitHub Actions에서 매일 실행합니다.

```yaml
schedule:
  - cron: "57 5 * * *"
    timezone: "Asia/Seoul"
```

워크플로는 다음 런타임 상태를 저장합니다.

- 처리된 기사
- Slack 피드백 상태
- 기사 히스토리

## Tech Stack

- Python 3.12
- Google Gemini API
- Slack
- GitHub Actions
- feedparser
- BeautifulSoup4
- RSS / Atom / HTML parsing

## Run Locally

Install:

```bash
pip install -r requirements.txt
```

Required environment variables:

```env
GEMINI_API_KEY=...
SLACK_WEBHOOK_URL=...
```

Slack 피드백 기능을 사용할 경우 Bot Token과 Channel ID 설정이 추가로 필요합니다.

Run:

```bash
python main.py
```

## Current Status

현재 구현된 핵심 흐름은 실제 예약 실행 가능한 상태입니다.

현재 집중하고 있는 개선 방향:

- Slack 피드백을 다음 기사 선별 기준에 반영
- 여러 기사에서 반복되는 기술 주제를 묶는 Trend Radar
- 뉴스를 읽고 끝내지 않고 실제 프로젝트에 적용할 Action으로 변환
- 관심사 설정을 코드 밖으로 분리해 개인화 강화

## Notes

이 프로젝트는 현재 **자율적으로 도구를 선택하는 범용 AI Agent**보다, 명확한 입력과 출력이 있는 운영형 자동화 시스템에 가깝습니다.

먼저 반복 실행 안정성과 실제 사용 가치를 검증한 뒤 Agent 구조를 확장하는 방향으로 개발하고 있습니다.
