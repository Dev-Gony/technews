import os
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from html import unescape
from urllib.parse import urljoin, urlsplit
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
from bs4 import BeautifulSoup


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.1-flash-lite"

SENT_ARTICLES_FILE = "sent_articles.json"

MAX_CONTENT_LENGTH = 12000

DEFAULT_RECENT_ARTICLE_LIMIT = 10
GEEKNEWS_RECENT_ARTICLE_LIMIT = 30

PREFILTER_TEXT_LENGTH = 800
PREFILTER_SCORE_THRESHOLD = 9

INITIALIZE_ONLY = False


BLOGS = [
    {
        "name": "네이버 D2",
        "enabled": True,
        "type": "rss",
        "rss": "https://d2.naver.com/d2.atom",
    },
    {
        "name": "네이버 플레이스",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/naver-place-dev",
    },
    {
        "name": "쿠팡",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/coupang-engineering",
    },
    {
        "name": "우아한형제들",
        "enabled": False,
        "type": "html",
        "url": "https://techblog.woowahan.com/",
        "html_type": "woowahan",
    },
    {
        "name": "요기요",
        "enabled": True,
        "type": "rss",
        "rss": "https://techblog.yogiyo.co.kr/feed",
    },
    {
        "name": "토스",
        "enabled": True,
        "type": "rss",
        "rss": "https://toss.tech/rss.xml",
    },
    {
        "name": "뱅크샐러드",
        "enabled": True,
        "type": "rss",
        "rss": "https://blog.banksalad.com/rss.xml",
    },
    {
        "name": "쏘카",
        "enabled": True,
        "type": "html",
        "url": "https://tech.socar.kr/posts",
        "html_type": "socar",
    },
    {
        "name": "직방",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/zigbang",
    },
    {
        "name": "G마켓",
        "enabled": True,
        "type": "rss",
        "rss": "https://dev.gmarket.com/rss",
    },
    {
        "name": "마켓컬리",
        "enabled": True,
        "type": "rss",
        "rss": "https://helloworld.kurly.com/rss.xml",
    },
    {
        "name": "당근",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/daangn",
    },
    {
        "name": "LINE Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://engineering.linecorp.com/ko/feed/index.html",
    },
    {
        "name": "데브시스터즈",
        "enabled": True,
        "type": "rss",
        "rss": "https://tech.devsisters.com/rss.xml",
    },
    {
        "name": "왓챠",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/watcha",
    },
    {
        "name": "무신사",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/musinsa-tech",
    },

    {
        "name": "Google Developers",
        "enabled": True,
        "type": "rss",
        "rss": "https://developers.googleblog.com/feeds/posts/default/",
    },
    {
        "name": "Apple Developer",
        "enabled": True,
        "type": "rss",
        "rss": "https://developer.apple.com/news/rss/news.rss",
    },
    {
        "name": "GitHub Blog",
        "enabled": True,
        "type": "rss",
        "rss": "https://github.blog/feed/",
    },
    {
        "name": "Meta Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://engineering.fb.com/feed/",
    },
    {
        "name": "Netflix TechBlog",
        "enabled": True,
        "type": "rss",
        "rss": "https://netflixtechblog.com/feed",
    },
    {
        "name": "Google Play",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/googleplaydev",
    },
    {
        "name": "Airbnb Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/airbnb-engineering",
    },
    {
        "name": "Slack Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://slack.engineering/feed/",
    },
    {
        "name": "Spotify Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://engineering.atspotify.com/feed/",
    },
    {
        "name": "Stripe",
        "enabled": True,
        "type": "rss",
        "rss": "https://stripe.com/blog/feed.rss",
    },
    {
        "name": "Cloudflare",
        "enabled": True,
        "type": "rss",
        "rss": "https://blog.cloudflare.com/rss/",
    },
    {
        "name": "AWS Architecture",
        "enabled": True,
        "type": "rss",
        "rss": "https://aws.amazon.com/blogs/architecture/feed/",
    },
    {
        "name": "AWS Compute",
        "enabled": True,
        "type": "rss",
        "rss": "https://aws.amazon.com/blogs/compute/feed/",
    },
    {
        "name": "Uber Engineering",
        "enabled": True,
        "type": "html",
        "url": "https://www.uber.com/us/en/blog/engineering/",
        "html_type": "uber",
    },
    {
        "name": "GeekNews",
        "enabled": True,
        "type": "rss",
        "rss": "https://news.hada.io/rss/news",
        "recent_limit": GEEKNEWS_RECENT_ARTICLE_LIMIT,
        "source_kind": "curation",
    },
]


def load_sent_articles():
    if not os.path.exists(SENT_ARTICLES_FILE):
        return []

    try:
        with open(
            SENT_ARTICLES_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception as error:
        print(
            "발송 기록 읽기 실패:",
            error
        )

        return []


def save_sent_articles(sent_articles):
    unique_articles = list(
        dict.fromkeys(
            sent_articles
        )
    )

    with open(
        SENT_ARTICLES_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            unique_articles,
            file,
            ensure_ascii=False,
            indent=2
        )


def normalize_article_url(url):
    if not url:
        return ""

    parsed = urllib.parse.urlsplit(
        url
    )

    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            ""
        )
    )


def normalize_title_for_dedupe(title):
    if not title:
        return ""

    normalized = unescape(
        title
    ).lower()

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    )

    normalized = re.sub(
        r"[^0-9a-z가-힣 ]",
        "",
        normalized
    )

    return normalized.strip()


def clean_html(html_text):
    if not html_text:
        return ""

    soup = BeautifulSoup(
        html_text,
        "html.parser"
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "form",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator="\n"
    )

    text = unescape(
        text
    )

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            lines.append(
                line
            )

    return "\n".join(
        lines
    )


def clean_slack_text(text):
    if not text:
        return ""

    text = unescape(
        text
    )

    text = text.replace(
        "\\-",
        "•"
    )
    text = text.replace(
        "\\*",
        "*"
    )
    text = text.replace(
        "\\_",
        "_"
    )
    text = text.replace(
        "\\.",
        "."
    )
    text = text.replace(
        "\\(",
        "("
    )
    text = text.replace(
        "\\)",
        ")"
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"*\1*",
        text
    )

    text = re.sub(
        r"(?m)^-\s+",
        "• ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def download_html(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language": (
                "ko-KR,ko;q=0.9,"
                "en-US;q=0.8,en;q=0.7"
            ),
            "Cache-Control": "no-cache",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="ignore"
        )


def get_feed(blog):
    print(
        f"RSS 요청: {blog['rss']}"
    )

    feed = feedparser.parse(
        blog["rss"],
        agent=(
            "Mozilla/5.0 "
            "(compatible; TechNewsBot/1.0)"
        )
    )

    if not feed.entries:
        raise RuntimeError(
            "RSS에서 게시글을 찾지 못했습니다."
        )

    if getattr(
        feed,
        "bozo",
        False
    ):
        print(
            "RSS 경고:",
            getattr(
                feed,
                "bozo_exception",
                "알 수 없는 RSS 오류"
            )
        )

    return feed


def get_rss_articles(
    blog,
    limit
):
    feed = get_feed(
        blog
    )

    articles = []

    for entry in feed.entries[:limit]:
        title = unescape(
            entry.get(
                "title",
                "제목 없음"
            ).strip()
        )

        link = normalize_article_url(
            entry.get(
                "link",
                ""
            )
        )

        pub_date = (
            entry.get("published")
            or entry.get("updated")
            or ""
        )

        summary = entry.get(
            "summary",
            ""
        )

        rss_content = ""

        if "content" in entry:
            try:
                contents = entry.get(
                    "content",
                    []
                )

                if contents:
                    rss_content = (
                        contents[0]
                        .get(
                            "value",
                            ""
                        )
                    )

            except Exception as error:
                print(
                    "RSS 본문 추출 실패:",
                    error
                )

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": link,
                "pub_date": pub_date.strip(),
                "summary": summary,
                "rss_content": rss_content,
                "source_kind": blog.get(
                    "source_kind",
                    "direct"
                ),
            }
        )

    return articles


def get_socar_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    soup = BeautifulSoup(
        download_html(
            blog["url"]
        ),
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        full_url = urljoin(
            blog["url"],
            tag.get(
                "href",
                ""
            )
        )

        parsed = urlsplit(
            full_url
        )

        if not re.fullmatch(
            r"/dev/\d{4}/\d{2}/\d{2}/[^/]+/?",
            parsed.path
        ):
            continue

        url = normalize_article_url(
            full_url
        )

        if url in seen_urls:
            continue

        title = unescape(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if not title:
            continue

        seen_urls.add(
            url
        )

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": url,
                "pub_date": "",
                "summary": "",
                "rss_content": "",
                "source_kind": blog.get(
                    "source_kind",
                    "direct"
                ),
            }
        )

        if len(
            articles
        ) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "쏘카 글 목록을 찾지 못했습니다."
        )

    return articles


def get_uber_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    soup = BeautifulSoup(
        download_html(
            blog["url"]
        ),
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        full_url = urljoin(
            blog["url"],
            tag.get(
                "href",
                ""
            )
        )

        parsed = urlsplit(
            full_url
        )

        if not re.fullmatch(
            r"/us/en/blog/[^/]+/?",
            parsed.path
        ):
            continue

        if parsed.path.rstrip(
            "/"
        ) == (
            "/us/en/blog/engineering"
        ):
            continue

        url = normalize_article_url(
            full_url
        )

        if url in seen_urls:
            continue

        title = unescape(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if len(
            title
        ) < 5:
            continue

        seen_urls.add(
            url
        )

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": url,
                "pub_date": "",
                "summary": "",
                "rss_content": "",
                "source_kind": blog.get(
                    "source_kind",
                    "direct"
                ),
            }
        )

        if len(
            articles
        ) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "Uber Engineering 글 목록을 찾지 못했습니다."
        )

    return articles


def get_html_articles(
    blog,
    limit
):
    html_type = blog.get(
        "html_type"
    )

    if html_type == "socar":
        return get_socar_articles(
            blog,
            limit
        )

    if html_type == "uber":
        return get_uber_articles(
            blog,
            limit
        )

    raise RuntimeError(
        f"지원하지 않는 HTML 방식: {html_type}"
    )


def get_recent_articles(
    blog,
    limit=DEFAULT_RECENT_ARTICLE_LIMIT
):
    if blog["type"] == "rss":
        return get_rss_articles(
            blog,
            limit
        )

    if blog["type"] == "html":
        return get_html_articles(
            blog,
            limit
        )

    raise RuntimeError(
        "알 수 없는 수집 방식입니다."
    )


def deduplicate_candidate_articles(
    articles
):
    deduplicated = []
    url_positions = {}
    title_positions = {}

    for article in articles:
        url_key = normalize_article_url(
            article.get(
                "link",
                ""
            )
        )

        title_key = normalize_title_for_dedupe(
            article.get(
                "title",
                ""
            )
        )

        duplicate_position = None

        if (
            url_key
            and url_key in url_positions
        ):
            duplicate_position = (
                url_positions[url_key]
            )

        elif (
            title_key
            and title_key in title_positions
        ):
            duplicate_position = (
                title_positions[title_key]
            )

        if duplicate_position is None:
            position = len(
                deduplicated
            )

            deduplicated.append(
                article
            )

            if url_key:
                url_positions[
                    url_key
                ] = position

            if title_key:
                title_positions[
                    title_key
                ] = position

            continue

        existing = deduplicated[
            duplicate_position
        ]

        existing_kind = existing.get(
            "source_kind",
            "direct"
        )

        new_kind = article.get(
            "source_kind",
            "direct"
        )

        if (
            existing_kind == "curation"
            and new_kind == "direct"
        ):
            deduplicated[
                duplicate_position
            ] = article

            if url_key:
                url_positions[
                    url_key
                ] = duplicate_position

            if title_key:
                title_positions[
                    title_key
                ] = duplicate_position

    return deduplicated


def get_prefilter_text(
    article
):
    rss_content = clean_html(
        article.get(
            "rss_content",
            ""
        )
    )

    summary = clean_html(
        article.get(
            "summary",
            ""
        )
    )

    text = rss_content or summary

    return text[
        :PREFILTER_TEXT_LENGTH
    ]


def extract_json_text(text):
    if not text:
        return ""

    text = text.strip()

    fenced_match = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.S | re.I
    )

    if fenced_match:
        text = fenced_match.group(
            1
        ).strip()

    first_bracket = text.find(
        "["
    )

    last_bracket = text.rfind(
        "]"
    )

    if (
        first_bracket >= 0
        and last_bracket > first_bracket
    ):
        return text[
            first_bracket:
            last_bracket + 1
        ]

    return text


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY가 없습니다."
        )

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
        f"?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    data = json.dumps(
        body
    ).encode(
        "utf-8"
    )

    max_attempts = 4

    for attempt in range(
        1,
        max_attempts + 1
    ):
        print(
            f"Gemini 요청 시도 "
            f"{attempt}/{max_attempts}"
        )

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type":
                    "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=90
            ) as response:
                result = json.loads(
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
                )

            text = (
                result["candidates"][0]
                ["content"]["parts"][0]
                ["text"]
            )

            print(
                "Gemini 요청 성공"
            )

            return text

        except urllib.error.HTTPError as error:
            status_code = error.code

            try:
                error_body = (
                    error
                    .read()
                    .decode(
                        "utf-8",
                        errors="ignore"
                    )
                )

            except Exception:
                error_body = ""

            print(
                "Gemini HTTP 오류:",
                status_code
            )

            print(
                error_body[:1000]
            )

            retryable_codes = {
                429,
                500,
                502,
                503,
                504,
            }

            if (
                status_code
                not in retryable_codes
            ):
                raise

            if attempt >= max_attempts:
                raise

            wait_seconds = (
                3 * (2 ** (attempt - 1))
            )

            print(
                f"{wait_seconds}초 후 다시 시도"
            )

            time.sleep(
                wait_seconds
            )

        except (
            TimeoutError,
            urllib.error.URLError
        ) as error:
            print(
                "Gemini 네트워크 오류:",
                repr(error)
            )

            if attempt >= max_attempts:
                raise

            wait_seconds = (
                3 * (2 ** (attempt - 1))
            )

            print(
                f"{wait_seconds}초 후 다시 시도"
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        "Gemini 요청이 모두 실패했습니다."
    )


def select_relevant_articles(
    candidate_articles
):
    if not candidate_articles:
        return [], []

    article_inputs = []

    for index, article in enumerate(
        candidate_articles,
        start=1
    ):
        preview = get_prefilter_text(
            article
        )

        article_inputs.append(
            f"""
기사 번호: {index}
출처: {article["company"]}
출처 유형: {article.get("source_kind", "direct")}
제목: {article["title"]}
게시일: {article["pub_date"]}
RSS 미리보기:
{preview if preview else "(미리보기 없음)"}
"""
        )

    combined = "\n".join(
        article_inputs
    )

    prompt = f"""
너는 개발자와 IT 실무자를 위한 기술 뉴스 편집자다.

아래는 오늘 새로 발견된 기술 콘텐츠 후보들이다.

아직 각 글의 전체 본문을 읽기 전이다.
제목과 RSS 미리보기만 보고
상세 본문을 읽을 가치가 있는 글을 선별해야 한다.

사용자의 우선 관심 분야:

1. AI Agent / Agentic Workflow
2. LLM / RAG / MCP
3. Python
4. 데이터 분석
5. SQL
6. 업무 자동화
7. 서버 / 클라우드 / 인프라
8. 백엔드 아키텍처
9. 실제 기업의 기술 적용 사례
10. 비용 절감 / 성능 개선 / 운영 효율화
11. 개발 생산성 / Developer Tools
12. GitHub 및 소프트웨어 개발 워크플로

판단 기준은 세 가지다.

relevance:
사용자의 관심 분야 및 현재 학습/개발 방향과 얼마나 관련 있는지
0~5점

practical_value:
실무, 프로젝트, 학습에 실제로 활용할 가치가 얼마나 있는지
0~5점

significance:
새로운 기술 변화, 중요한 발표, 보안 이슈,
업계 변화 또는 알아둘 가치가 얼마나 큰지
0~5점

total_score는 세 점수의 합계다.

기본적으로 total_score가
{PREFILTER_SCORE_THRESHOLD}점 이상이면 selected를 true로 한다.

하지만 다음과 같은 경우에는
점수가 조금 낮더라도 selected를 true로 할 수 있다.

- 개발자가 알아야 할 큰 보안 사고
- 주요 플랫폼이나 개발도구의 중요한 변경
- AI 또는 소프트웨어 산업의 큰 변화
- 널리 사용되는 기술의 중대한 장애나 정책 변화

반대로 다음 글은 제외하는 쪽으로 판단한다.

- 단순 홍보성 콘텐츠
- 기술적 내용이 거의 없는 기업 소식
- 제목만 자극적이고 실질 내용이 약한 글
- 사용자의 관심 분야와 거의 무관하고 업계 중요도도 낮은 글
- 동일하거나 사실상 같은 주제의 반복 콘텐츠

직접 구독 중인 기업 기술블로그는
사용자가 의도적으로 선택한 출처라는 점을 약간 고려할 수 있다.

GeekNews는 새로운 콘텐츠를 발견하기 위한 큐레이션 출처다.
GeekNews라는 이유만으로 점수를 높이거나 낮추지 않는다.

중요:
선정 개수를 미리 정하지 않는다.

볼 가치가 있는 글이 2개면 2개만 선택하고,
볼 가치가 있는 글이 12개면 12개 모두 선택한다.

결과는 반드시 JSON 배열만 반환한다.

다른 설명이나 Markdown 코드블록은 출력하지 않는다.

각 요소 형식:

{{
  "index": 1,
  "relevance": 0,
  "practical_value": 0,
  "significance": 0,
  "total_score": 0,
  "selected": true,
  "reason": "선정 또는 제외 이유를 한국어 한 문장으로 작성"
}}

후보 목록:

{combined}
"""

    result = call_gemini(
        prompt
    )

    json_text = extract_json_text(
        result
    )

    parsed = json.loads(
        json_text
    )

    if not isinstance(
        parsed,
        list
    ):
        raise ValueError(
            "기사 선별 결과가 JSON 배열이 아닙니다."
        )

    decisions = {}

    for item in parsed:
        if not isinstance(
            item,
            dict
        ):
            continue

        try:
            index = int(
                item.get(
                    "index"
                )
            )

        except (
            TypeError,
            ValueError
        ):
            continue

        if (
            index < 1
            or index > len(
                candidate_articles
            )
        ):
            continue

        decisions[
            index
        ] = item

    selected_articles = []
    excluded_articles = []

    for index, article in enumerate(
        candidate_articles,
        start=1
    ):
        decision = decisions.get(
            index
        )

        if decision is None:
            article[
                "selection_score"
            ] = None

            article[
                "selection_reason"
            ] = (
                "Gemini 선별 결과에 해당 번호가 없어 "
                "안전하게 상세 분석 대상으로 포함"
            )

            selected_articles.append(
                article
            )

            continue

        try:
            total_score = int(
                decision.get(
                    "total_score",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):
            total_score = 0

        selected = decision.get(
            "selected",
            False
        )

        if isinstance(
            selected,
            str
        ):
            selected = (
                selected
                .strip()
                .lower()
                == "true"
            )

        article[
            "selection_score"
        ] = total_score

        article[
            "selection_reason"
        ] = str(
            decision.get(
                "reason",
                ""
            )
        ).strip()

        if selected:
            selected_articles.append(
                article
            )

        else:
            excluded_articles.append(
                article
            )

    return (
        selected_articles,
        excluded_articles
    )


def get_content_from_rss(article):
    rss_content = article.get(
        "rss_content",
        ""
    )

    if rss_content:
        cleaned = clean_html(
            rss_content
        )

        if len(
            cleaned
        ) >= 200:
            return cleaned[
                :MAX_CONTENT_LENGTH
            ]

    summary = article.get(
        "summary",
        ""
    )

    if summary:
        cleaned = clean_html(
            summary
        )

        if len(
            cleaned
        ) >= 200:
            return cleaned[
                :MAX_CONTENT_LENGTH
            ]

    return ""


def download_article_page(article):
    try:
        html = download_html(
            article["link"]
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        main_content = (
            soup.find("article")
            or soup.find("main")
        )

        if main_content:
            content = clean_html(
                str(
                    main_content
                )
            )

        else:
            content = clean_html(
                html
            )

        return content[
            :MAX_CONTENT_LENGTH
        ]

    except Exception as error:
        print(
            "본문 페이지 가져오기 실패:",
            error
        )

        return ""


def get_article_content(article):
    content = get_content_from_rss(
        article
    )

    if content:
        return content

    return download_article_page(
        article
    )


def summarize_article(
    article,
    content
):
    selection_score = article.get(
        "selection_score"
    )

    selection_reason = article.get(
        "selection_reason",
        ""
    )

    prompt = f"""
너는 개발자를 위한 기술 블로그 요약 편집자다.

아래 글을 읽고 한국어로 간단하고 정확하게 요약한다.

출처:
{article["company"]}

제목:
{article["title"]}

게시일:
{article["pub_date"]}

1차 선별 점수:
{selection_score}

1차 선별 이유:
{selection_reason}

본문:
{content}

다음 형식을 반드시 사용한다.

[한줄 요약]
핵심을 한 문장으로 설명한다.

[핵심 내용]
• 중요한 내용 3개
• 각 항목은 1~2문장
• Markdown의 ** 문법은 사용하지 않는다.

[알아둬야 할 것]
• 핵심 개념 1~3개를 쉽게 설명한다.
• 불필요하게 길게 쓰지 않는다.

[추천 대상]
누가 읽으면 좋은지 한 줄로 작성한다.

규칙:
- 본문에 없는 사실은 만들지 않는다.
- 숫자나 결과를 추측하지 않는다.
- 해외 글도 한국어로 작성한다.
- 기술명은 원래 이름을 유지한다.
- Slack에서 읽기 쉽게 작성한다.
- *, **, -, # 같은 Markdown 장식을 남발하지 않는다.
- 목록은 반드시 • 기호를 사용한다.
"""

    result = call_gemini(
        prompt
    )

    return clean_slack_text(
        result
    )


def create_daily_editorial(
    summarized_articles
):
    editorial_input = []

    for index, item in enumerate(
        summarized_articles,
        start=1
    ):
        article = item[
            "article"
        ]

        editorial_input.append(
            f"""
글 {index}

출처:
{article["company"]}

제목:
{article["title"]}

1차 선별 점수:
{article.get("selection_score")}

1차 선별 이유:
{article.get("selection_reason", "")}

요약:
{item["summary"]}
"""
        )

    combined = "\n".join(
        editorial_input
    )

    prompt = f"""
너는 개발자와 IT 실무자를 위한
아침 기술 뉴스레터의 편집장이다.

오늘 선별된 기술 글들의 요약이 아래에 있다.

{combined}


사용자의 우선 관심 분야:

1. AI Agent / Agentic Workflow
2. LLM / RAG / MCP
3. Python
4. 데이터 분석
5. SQL
6. 업무 자동화
7. 서버 / 클라우드 / 인프라
8. 백엔드 아키텍처
9. 실제 기업의 기술 적용 사례
10. 비용 절감 / 성능 개선 / 운영 효율화
11. 개발 생산성 / Developer Tools
12. GitHub 및 소프트웨어 개발 워크플로


중요도 판단 기준:

• 실제 실무에 적용할 수 있는가
• 새로운 기술 흐름을 이해하는 데 도움이 되는가
• AI / 데이터 / 자동화와 관련성이 높은가
• 기업이 실제 문제를 어떻게 해결했는가
• 성능, 비용, 생산성, 안정성 개선 사례가 있는가
• 학습 가치가 높은가
• 개발 생태계에서 중요도가 높은 변화인가

AI라는 단어가 포함됐다는 이유만으로
무조건 높은 점수를 주면 안 된다.

내용의 깊이와 실제 활용 가능성을 함께 판단한다.


다음 형식으로 작성한다.


[오늘 꼭 볼 글 번호]

오늘 선별된 글 중에서도
가장 우선해서 읽을 가치가 높은 글을
최대 3개 선정한다.

번호만 중요도 순서대로 쉼표로 작성한다.

예:
3, 1, 5


[오늘의 기술 키워드]

기술 키워드 또는 개념을
3~5개 쉼표로 작성한다.


[오늘의 한줄 포인트]

오늘 기술 글 전체를 관통하는 흐름을
한국어 한 문장으로 작성한다.


[오늘 왜 중요한가]

오늘 글들을 종합했을 때
개발자 또는 AI/데이터 학습자가
왜 관심을 가져야 하는지
2~3문장으로 설명한다.


[왜 이 글들을 골랐나]

오늘 꼭 볼 글로 선정한 각각의 글에 대해
왜 우선해서 읽을 가치가 있는지
한 문장씩 작성한다.

글이 1개면 1개만,
글이 2개면 2개만,
글이 3개 이상이면 최대 3개만 작성한다.


[오늘 공부해볼 것]

오늘 글을 바탕으로
20~30분 정도 추가 공부하면 좋은
주제 1~3개를 추천한다.

각 주제마다 이유도 짧게 작성한다.


규칙:

- 제공된 요약에 없는 사실을 만들지 않는다.
- 회사 인지도만으로 우선순위를 정하지 않는다.
- 홍보성 글보다 실제 기술 문제 해결 사례를 우선한다.
- 실제 수치나 운영 결과가 있다면 중요하게 고려한다.
- Slack에서 읽기 쉽게 작성한다.
- 목록은 • 기호를 사용한다.
- ** 같은 Markdown 강조 문법은 사용하지 않는다.
"""

    result = call_gemini(
        prompt
    )

    return clean_slack_text(
        result
    )


def parse_top_indices(editorial):
    match = re.search(
        r"\[오늘 꼭 볼 글 번호\]\s*([0-9,\s]+)",
        editorial
    )

    if not match:
        return []

    values = []

    for raw in match.group(
        1
    ).split(","):
        raw = raw.strip()

        if raw.isdigit():
            values.append(
                int(raw)
            )

    return values[:3]


def remove_internal_editorial_sections(
    editorial
):
    cleaned_editorial = re.sub(
        r"\[오늘 꼭 볼 글 번호\]\s*.*?(?=\n\[|\Z)",
        "",
        editorial,
        flags=re.S
    ).strip()

    cleaned_editorial = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned_editorial
    )

    return cleaned_editorial


def split_slack_messages(
    text,
    limit=3500
):
    messages = []

    while len(
        text
    ) > limit:
        split_at = text.rfind(
            "\n",
            0,
            limit
        )

        if split_at <= 0:
            split_at = limit

        messages.append(
            text[:split_at]
        )

        text = text[
            split_at:
        ].lstrip()

    if text:
        messages.append(
            text
        )

    return messages


def send_slack_text(text):
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL이 없습니다."
        )

    data = json.dumps(
        {
            "text": text
        }
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        result = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    if result != "ok":
        raise RuntimeError(
            f"Slack 전송 실패: {result}"
        )


def build_digest(
    summarized_articles,
    editorial,
    top_indices,
    failed_blogs,
    candidate_count,
    excluded_count
):
    now = datetime.now(
        ZoneInfo(
            "Asia/Seoul"
        )
    )

    date_text = now.strftime(
        "%Y-%m-%d"
    )

    parts = [
        f"🌅 *{date_text} 오늘의 Tech Digest*",
        "",
        "AI · 데이터 · 자동화 · 백엔드 중심 아침 기술 브리핑",
        "",
        f"오늘 확인한 새 글: *{candidate_count}개*",
        f"AI 선별 후 읽을 글: *{len(summarized_articles)}개*",
        f"선별 제외: *{excluded_count}개*",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "🔥 *오늘 꼭 볼 글*",
        "",
    ]

    top_set = set(
        top_indices
    )

    for position, index in enumerate(
        top_indices,
        start=1
    ):
        if (
            index < 1
            or index > len(
                summarized_articles
            )
        ):
            continue

        item = summarized_articles[
            index - 1
        ]

        article = item[
            "article"
        ]

        score = article.get(
            "selection_score"
        )

        score_text = ""

        if score is not None:
            score_text = (
                f" · 선별점수 {score}/15"
            )

        parts.extend(
            [
                f"*{position}. {article['company']}*{score_text}",
                f"*{article['title']}*",
                "",
                item["summary"],
                "",
                f"🔗 {article['link']}",
                "",
            ]
        )

    remaining = []

    for index, item in enumerate(
        summarized_articles,
        start=1
    ):
        if index in top_set:
            continue

        remaining.append(
            item
        )

    if remaining:
        parts.extend(
            [
                "━━━━━━━━━━━━━━━━━━",
                "📚 *그 외 읽을 가치가 있는 글*",
                "",
            ]
        )

        for item in remaining:
            article = item[
                "article"
            ]

            one_line = item[
                "summary"
            ]

            match = re.search(
                r"\[한줄 요약\]\s*(.+?)(?:\n|$)",
                one_line,
                re.S
            )

            if match:
                one_line = (
                    match
                    .group(1)
                    .strip()
                )

            else:
                one_line = (
                    one_line
                    .replace(
                        "\n",
                        " "
                    )
                    [:180]
                )

            score = article.get(
                "selection_score"
            )

            score_text = ""

            if score is not None:
                score_text = (
                    f" [{score}/15]"
                )

            parts.extend(
                [
                    f"• *{article['company']}*{score_text} — {article['title']}",
                    f"  {one_line}",
                    f"  🔗 {article['link']}",
                    "",
                ]
            )

    cleaned_editorial = (
        remove_internal_editorial_sections(
            editorial
        )
    )

    parts.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "💡 *오늘의 편집 노트*",
            "",
            cleaned_editorial,
        ]
    )

    if failed_blogs:
        parts.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━",
                "⚠️ *수집 실패*",
                ", ".join(
                    failed_blogs
                ),
            ]
        )

    return clean_slack_text(
        "\n".join(
            parts
        )
    )


def main():
    sent_articles = load_sent_articles()

    enabled_blogs = [
        blog
        for blog in BLOGS
        if blog.get(
            "enabled",
            True
        )
    ]

    candidate_articles = []
    failed_blogs = []

    print(
        "================================"
    )

    print(
        "Tech News Bot 시작"
    )

    print(
        "활성 블로그:",
        len(
            enabled_blogs
        )
    )

    print(
        "기존 발송 기록:",
        len(
            sent_articles
        )
    )

    print(
        "================================"
    )

    for blog in enabled_blogs:
        try:
            print()
            print(
                "=" * 60
            )

            print(
                "확인 중:",
                blog["name"]
            )

            recent_limit = blog.get(
                "recent_limit",
                DEFAULT_RECENT_ARTICLE_LIMIT
            )

            print(
                "최근 확인 범위:",
                recent_limit
            )

            articles = get_recent_articles(
                blog,
                recent_limit
            )

            new_articles = [
                article
                for article in articles
                if article["link"]
                and article["link"]
                not in sent_articles
            ]

            print(
                "새 글 수:",
                len(
                    new_articles
                )
            )

            new_articles.reverse()

            candidate_articles.extend(
                new_articles
            )

        except Exception as error:
            print(
                "[오류]",
                blog["name"],
                repr(
                    error
                )
            )

            failed_blogs.append(
                blog["name"]
            )

    print()
    print(
        "중복 제거 전 새 글 후보:",
        len(
            candidate_articles
        )
    )

    candidate_articles = (
        deduplicate_candidate_articles(
            candidate_articles
        )
    )

    print(
        "중복 제거 후 새 글 후보:",
        len(
            candidate_articles
        )
    )

    if not candidate_articles:
        print(
            "새 글이 없습니다."
        )

        return

    print()
    print(
        "Gemini 1차 기사 선별 시작"
    )

    try:
        (
            selected_articles,
            excluded_articles
        ) = select_relevant_articles(
            candidate_articles
        )

        print(
            "1차 선별 완료"
        )

        print(
            "상세 분석 대상:",
            len(
                selected_articles
            )
        )

        print(
            "선별 제외:",
            len(
                excluded_articles
            )
        )

    except Exception as error:
        print(
            "1차 기사 선별 실패:",
            repr(
                error
            )
        )

        print(
            "중요한 글 누락 방지를 위해 "
            "모든 후보를 상세 분석합니다."
        )

        selected_articles = (
            candidate_articles
        )

        excluded_articles = []

        for article in (
            selected_articles
        ):
            article[
                "selection_score"
            ] = None

            article[
                "selection_reason"
            ] = (
                "1차 선별 실패로 안전하게 상세 분석 대상에 포함"
            )

    if not selected_articles:
        print(
            "오늘은 선별 기준을 통과한 글이 없습니다."
        )

        for article in excluded_articles:
            if article.get(
                "link"
            ):
                sent_articles.append(
                    article["link"]
                )

        save_sent_articles(
            sent_articles
        )

        return

    print()
    print(
        "상세 요약 시작"
    )

    summarized_articles = []

    for article in selected_articles:
        print()
        print(
            "요약 처리:",
            article["company"],
            "-",
            article["title"]
        )

        if (
            article.get(
                "selection_score"
            )
            is not None
        ):
            print(
                "선별 점수:",
                article[
                    "selection_score"
                ],
                "/15"
            )

            print(
                "선별 이유:",
                article.get(
                    "selection_reason",
                    ""
                )
            )

        try:
            content = get_article_content(
                article
            )

            if not content:
                print(
                    "본문 없음 - 이번 실행에서는 건너뜀"
                )

                continue

            summary = summarize_article(
                article,
                content
            )

            summarized_articles.append(
                {
                    "article": article,
                    "summary": summary,
                }
            )

        except Exception as error:
            print(
                "요약 실패:",
                repr(
                    error
                )
            )

    if not summarized_articles:
        print(
            "Slack으로 보낼 요약이 없습니다."
        )

        for article in excluded_articles:
            if article.get(
                "link"
            ):
                sent_articles.append(
                    article["link"]
                )

        save_sent_articles(
            sent_articles
        )

        return

    print()
    print(
        "오늘의 편집 브리핑 생성"
    )

    try:
        editorial = create_daily_editorial(
            summarized_articles
        )

    except Exception as error:
        print(
            "편집 브리핑 생성 실패:",
            repr(
                error
            )
        )

        editorial = (
            "[오늘의 기술 키워드]\n"
            "편집 요약 생성 실패\n\n"
            "[오늘의 한줄 포인트]\n"
            "개별 글 요약은 정상적으로 생성되었습니다."
        )

    top_indices = parse_top_indices(
        editorial
    )

    if not top_indices:
        top_indices = list(
            range(
                1,
                min(
                    3,
                    len(
                        summarized_articles
                    )
                ) + 1
            )
        )

    digest = build_digest(
        summarized_articles,
        editorial,
        top_indices,
        failed_blogs,
        candidate_count=len(
            candidate_articles
        ),
        excluded_count=len(
            excluded_articles
        )
    )

    messages = split_slack_messages(
        digest
    )

    for index, message in enumerate(
        messages,
        start=1
    ):
        print(
            f"Slack 발송 "
            f"{index}/{len(messages)}"
        )

        send_slack_text(
            message
        )

    for article in excluded_articles:
        if article.get(
            "link"
        ):
            sent_articles.append(
                article["link"]
            )

    for item in summarized_articles:
        sent_articles.append(
            item["article"]["link"]
        )

    save_sent_articles(
        sent_articles
    )

    print(
        "브리핑 발송 완료"
    )

    print(
        "전체 후보:",
        len(
            candidate_articles
        )
    )

    print(
        "선별 제외:",
        len(
            excluded_articles
        )
    )

    print(
        "발송 글:",
        len(
            summarized_articles
        )
    )


if __name__ == "__main__":
    main()
