import os
import json
import re
import urllib.request
import urllib.parse
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
RECENT_ARTICLE_LIMIT = 10
MAX_ARTICLES_PER_RUN = 10

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
        print("발송 기록 읽기 실패:", error)
        return []


def save_sent_articles(sent_articles):
    unique_articles = list(
        dict.fromkeys(sent_articles)
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

    parsed = urllib.parse.urlsplit(url)

    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            ""
        )
    )


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

    text = unescape(text)

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


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


def get_rss_articles(blog, limit):
    feed = get_feed(blog)

    articles = []

    for entry in feed.entries[:limit]:
        title = entry.get(
            "title",
            "제목 없음"
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
                "title": title.strip(),
                "link": link,
                "pub_date": pub_date.strip(),
                "summary": summary,
                "rss_content": rss_content,
            }
        )

    return articles


def get_socar_articles(blog, limit):
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
            tag.get("href", "")
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

        title = tag.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        seen_urls.add(url)

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": url,
                "pub_date": "",
                "summary": "",
                "rss_content": "",
            }
        )

        if len(articles) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "쏘카 글 목록을 찾지 못했습니다."
        )

    return articles


def get_uber_articles(blog, limit):
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
            tag.get("href", "")
        )

        parsed = urlsplit(
            full_url
        )

        if not re.fullmatch(
            r"/us/en/blog/[^/]+/?",
            parsed.path
        ):
            continue

        if parsed.path.rstrip("/") == (
            "/us/en/blog/engineering"
        ):
            continue

        url = normalize_article_url(
            full_url
        )

        if url in seen_urls:
            continue

        title = tag.get_text(
            " ",
            strip=True
        )

        if len(title) < 5:
            continue

        seen_urls.add(url)

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": url,
                "pub_date": "",
                "summary": "",
                "rss_content": "",
            }
        )

        if len(articles) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "Uber Engineering 글 목록을 찾지 못했습니다."
        )

    return articles


def get_html_articles(blog, limit):
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
    limit=10
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


def get_content_from_rss(article):
    rss_content = article.get(
        "rss_content",
        ""
    )

    if rss_content:
        cleaned = clean_html(
            rss_content
        )

        if len(cleaned) >= 200:
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

        if len(cleaned) >= 200:
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
                str(main_content)
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

    request = urllib.request.Request(
        url,
        data=json.dumps(
            body
        ).encode("utf-8"),
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=90
    ) as response:
        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    return (
        result["candidates"][0]
        ["content"]["parts"][0]
        ["text"]
    )


def summarize_article(
    article,
    content
):
    prompt = f"""
너는 개발자를 위한 기술 블로그 요약 편집자다.

아래 글을 읽고 한국어로 간단하고 정확하게 요약한다.

회사:
{article["company"]}

제목:
{article["title"]}

게시일:
{article["pub_date"]}

본문:
{content}

다음 형식으로만 작성한다.

[한줄 요약]
글의 핵심을 한 문장으로 설명한다.

[핵심 내용]
- 중요한 내용 3개
- 각 항목은 1~2문장

[알아둬야 할 것]
이 글에서 꼭 이해해야 할 개념을
쉽게 2~3문장으로 설명한다.

[추천 대상]
누가 읽으면 좋은지 한 줄로 작성한다.

규칙:
- 본문에 없는 사실은 만들지 않는다.
- 숫자나 성능 결과를 추측하지 않는다.
- 해외 글도 한국어로 작성한다.
- 기술명은 원래 이름을 유지한다.
"""

    return call_gemini(
        prompt
    )


def create_daily_editorial(
    summarized_articles
):
    editorial_input = []

    for index, item in enumerate(
        summarized_articles,
        start=1
    ):
        article = item["article"]

        editorial_input.append(
            f"""
글 {index}

회사:
{article["company"]}

제목:
{article["title"]}

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

오늘 발견된 기술 블로그 글들의 요약이 아래에 있다.

{combined}


사용자의 우선 관심 분야는 다음과 같다.

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


중요도 판단 기준:

- 실제 실무에 적용할 수 있는가
- 새로운 기술 흐름을 이해하는 데 도움이 되는가
- AI / 데이터 / 자동화와 관련성이 높은가
- 기업이 실제 문제를 어떻게 해결했는가
- 성능, 비용, 생산성, 안정성 개선 사례가 있는가
- 학습 가치가 높은가

위 관심 분야와 직접 관련된 글에는
중요도 판단에서 가산점을 준다.

하지만 단순히 AI라는 단어가 들어갔다는 이유만으로
높게 평가하면 안 된다.

실제 내용의 깊이와 실무 활용 가능성을
함께 판단해야 한다.


다음 형식으로만 작성한다.


[오늘 꼭 볼 글 번호]

가장 읽을 가치가 높은 글을
최대 3개 선정한다.

번호만 중요도 순서대로 쉼표로 작성한다.

예:
3, 1, 5


[오늘의 기술 키워드]

오늘 글 전체에서 중요하게 등장한
기술 키워드 또는 개념을
3~5개 선정한다.

쉼표로 작성한다.

예:
AI Agent, Kubernetes, RAG, Observability


[오늘의 한줄 포인트]

오늘 기술 글 전체를 관통하는 흐름을
한국어 한 문장으로 작성한다.

너무 추상적으로 쓰지 말고
개발자가 기억할 만한 내용으로 작성한다.


[오늘 왜 중요한가]

오늘 올라온 글들을 종합했을 때
개발자 또는 데이터/AI 학습자가
왜 관심을 가져야 하는지
2~3문장으로 설명한다.


[왜 이 3개를 골랐나]

선정한 각 글에 대해 다음 형식으로 작성한다.

1번 글:
선정 이유 한 문장

2번 글:
선정 이유 한 문장

3번 글:
선정 이유 한 문장

실제 선정된 글 번호에 맞춰 작성한다.


[오늘 공부해볼 것]

오늘 글들을 바탕으로
사용자가 20~30분 정도 추가로 공부하면 좋은
주제 1~3개를 추천한다.

각 주제마다 왜 공부하면 좋은지도
짧게 작성한다.


규칙:

- 제공된 글 요약에 없는 사실을 만들지 않는다.
- 특정 회사가 유명하다는 이유만으로 우선하지 않는다.
- 사용자의 관심 분야와 관련성이 높아도
  내용이 얕으면 과도하게 높게 평가하지 않는다.
- 기술적으로 깊이가 있어도
  실무 활용도가 낮으면 그 점도 고려한다.
- 홍보성 글보다 실제 기술 문제 해결 사례를 우선한다.
- 실제 수치나 결과가 있다면 중요하게 고려한다.
- 모든 결과는 한국어로 작성한다.
"""
    return call_gemini(
        prompt
    )


def parse_top_indices(editorial):
    match = re.search(
        r"\[오늘 꼭 볼 글 번호\]\s*([0-9,\s]+)",
        editorial
    )

    if not match:
        return []

    values = []

    for raw in match.group(1).split(","):
        raw = raw.strip()

        if raw.isdigit():
            values.append(
                int(raw)
            )

    return values[:3]


def split_slack_messages(
    text,
    limit=3500
):
    messages = []

    while len(text) > limit:
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
        messages.append(text)

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
            .decode("utf-8")
        )

    if result != "ok":
        raise RuntimeError(
            f"Slack 전송 실패: {result}"
        )


def build_digest(
    summarized_articles,
    editorial,
    top_indices,
    failed_blogs
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
    f"오늘 새 글: *{len(summarized_articles)}개*",
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

        article = item["article"]

        parts.extend(
            [
                f"*{position}. {article['company']}*",
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
                "📚 *나머지 새 글*",
                "",
            ]
        )

        for item in remaining:
            article = item["article"]

            one_line = item[
                "summary"
            ]

            one_line_match = re.search(
                r"\[한줄 요약\]\s*(.+?)(?:\n|$)",
                one_line,
                re.S
            )

            if one_line_match:
                one_line = (
                    one_line_match
                    .group(1)
                    .strip()
                )
            else:
                one_line = (
                    one_line
                    .replace("\n", " ")
                    [:180]
                )

            parts.extend(
                [
                    f"• *{article['company']}* — {article['title']}",
                    f"  {one_line}",
                    f"  🔗 {article['link']}",
                    "",
                ]
            )

    parts.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "💡 *오늘의 편집 노트*",
            "",
            editorial,
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

    return "\n".join(parts)


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
        len(enabled_blogs)
    )

    print(
        "기존 발송 기록:",
        len(sent_articles)
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

            articles = get_recent_articles(
                blog,
                RECENT_ARTICLE_LIMIT
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
                len(new_articles)
            )

            new_articles.reverse()

            candidate_articles.extend(
                new_articles
            )

        except Exception as error:
            print(
                "[오류]",
                blog["name"],
                repr(error)
            )

            failed_blogs.append(
                blog["name"]
            )

    print()
    print(
        "전체 새 글 후보:",
        len(candidate_articles)
    )

    if not candidate_articles:
        print(
            "새 글이 없습니다."
        )

        return

    candidate_articles = (
        candidate_articles[
            :MAX_ARTICLES_PER_RUN
        ]
    )

    summarized_articles = []

    for article in candidate_articles:
        print()
        print(
            "요약 처리:",
            article["company"],
            "-",
            article["title"]
        )

        try:
            content = get_article_content(
                article
            )

            if not content:
                print(
                    "본문 없음 - 건너뜀"
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
                repr(error)
            )

    if not summarized_articles:
        print(
            "Slack으로 보낼 요약이 없습니다."
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
            repr(error)
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
        failed_blogs
    )

    messages = split_slack_messages(
        digest
    )

    for index, message in enumerate(
        messages,
        start=1
    ):
        print(
            f"Slack 발송 {index}/{len(messages)}"
        )

        send_slack_text(
            message
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
        "발송 글:",
        len(summarized_articles)
    )


if __name__ == "__main__":
    main()
