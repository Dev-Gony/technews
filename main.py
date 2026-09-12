import os
import json
import re
import urllib.request
import urllib.parse
from html import unescape
from urllib.parse import urljoin, urlsplit

import feedparser
from bs4 import BeautifulSoup


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.1-flash-lite"

SENT_ARTICLES_FILE = "sent_articles.json"

MAX_CONTENT_LENGTH = 12000
RECENT_ARTICLE_LIMIT = 10

# 새로운 블로그를 추가했기 때문에
# 현재 글들을 먼저 "기준점"으로 등록한다.
#
# 최초 1회 실행 후 반드시 False로 변경한다.
INITIALIZE_ONLY = False


BLOGS = [

    # =====================================================
    # 국내
    # =====================================================

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

    # GitHub Actions 환경에서 현재 HTTP 403 발생.
    # 나중에 별도 수집 방식으로 해결 예정.
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


    # =====================================================
    # 해외 - 기존
    # =====================================================

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


    # =====================================================
    # 해외 - 신규 추가
    # =====================================================

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


# =========================================================
# 발송 기록
# =========================================================


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


# =========================================================
# URL
# =========================================================


def normalize_article_url(url):
    if not url:
        return ""

    parsed = urllib.parse.urlsplit(url)

    normalized = urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            ""
        )
    )

    return normalized.rstrip("/")


# =========================================================
# HTML 정리
# =========================================================


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


# =========================================================
# HTTP
# =========================================================


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


# =========================================================
# RSS
# =========================================================


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
        title = entry.get(
            "title",
            "제목 없음"
        )

        link = entry.get(
            "link",
            ""
        )

        normalized_url = normalize_article_url(
            link
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
                "link": normalized_url,
                "pub_date": pub_date.strip(),
                "summary": summary,
                "rss_content": rss_content,
            }
        )

    return articles


# =========================================================
# HTML - 쏘카
# =========================================================


def get_socar_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    html = download_html(
        blog["url"]
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        href = tag.get(
            "href",
            ""
        )

        full_url = urljoin(
            blog["url"],
            href
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
            }
        )

        if len(articles) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "쏘카 글 목록을 찾지 못했습니다."
        )

    return articles


# =========================================================
# HTML - 우아한형제들
# 현재 비활성화
# =========================================================


def get_woowahan_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    html = download_html(
        blog["url"]
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        href = tag.get(
            "href",
            ""
        )

        full_url = urljoin(
            blog["url"],
            href
        )

        parsed = urlsplit(
            full_url
        )

        if not re.fullmatch(
            r"/\d+/?",
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
            }
        )

        if len(articles) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "우아한형제들 글 목록을 찾지 못했습니다."
        )

    return articles


# =========================================================
# HTML - Uber
# =========================================================


def get_uber_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    html = download_html(
        blog["url"]
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        href = tag.get(
            "href",
            ""
        )

        full_url = urljoin(
            blog["url"],
            href
        )

        parsed = urlsplit(
            full_url
        )

        # Uber Engineering의 개별 글은
        # /us/en/blog/글-slug/
        # 형태로 제공된다.
        if not re.fullmatch(
            r"/us/en/blog/[^/]+/?",
            parsed.path
        ):
            continue

        # 목록 페이지 자체 등 제외
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
            }
        )

        if len(articles) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "Uber Engineering 글 목록을 찾지 못했습니다."
        )

    return articles


# =========================================================
# HTML 라우터
# =========================================================


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

    if html_type == "woowahan":
        return get_woowahan_articles(
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


# =========================================================
# 최근 글 가져오기
# =========================================================


def get_recent_articles(
    blog,
    limit=10
):
    source_type = blog.get(
        "type"
    )

    if source_type == "rss":
        return get_rss_articles(
            blog,
            limit
        )

    if source_type == "html":
        return get_html_articles(
            blog,
            limit
        )

    raise RuntimeError(
        f"알 수 없는 수집 방식: {source_type}"
    )


# =========================================================
# 본문
# =========================================================


def get_content_from_rss(
    article
):
    rss_content = article.get(
        "rss_content",
        ""
    )

    if rss_content:
        cleaned = clean_html(
            rss_content
        )

        if len(cleaned) >= 200:
            print(
                "RSS 안의 본문을 사용합니다."
            )

            return cleaned[
                :MAX_CONTENT_LENGTH
            ]

    summary = article.get(
        "summary",
        ""
    )

    if summary:
        cleaned_summary = clean_html(
            summary
        )

        if len(cleaned_summary) >= 200:
            print(
                "RSS 요약문을 사용합니다."
            )

            return cleaned_summary[
                :MAX_CONTENT_LENGTH
            ]

    return ""


def download_article_page(
    article
):
    url = article["link"]

    if not url:
        return ""

    print(
        "원문 페이지에서 본문을 가져옵니다."
    )

    try:
        html = download_html(
            url
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


def get_article_content(
    article
):
    rss_content = get_content_from_rss(
        article
    )

    if rss_content:
        return rss_content

    page_content = download_article_page(
        article
    )

    if page_content:
        return page_content

    print(
        "본문을 충분히 가져오지 못했습니다."
    )

    return ""


# =========================================================
# Gemini
# =========================================================


def summarize_with_gemini(
    article,
    content
):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY가 없습니다."
        )

    if not content:
        raise RuntimeError(
            "요약할 본문이 없습니다."
        )

    prompt = f"""
너는 개발자를 위한 기술 블로그 브리핑 편집자다.

아래 글을 읽고 한국어로 정리한다.

해외 글이라도 결과는 한국어로 작성한다.

회사:
{article["company"]}

제목:
{article["title"]}

게시일:
{article["pub_date"]}

본문:
{content}


다음 형식을 반드시 사용한다.


[한눈에 보기]

이 글이 무엇에 관한 것인지
2~3문장으로 쉽게 설명한다.


[왜 이 글을 썼나]

작성자가 어떤 문제나 필요 때문에
이 주제를 다루었는지 설명한다.


[핵심 내용]

핵심을 3~5개로 정리한다.

단순한 키워드 나열이 아니라
왜 중요한지도 설명한다.


[사용한 기술 / 방법]

실제 본문에 등장하는 기술,
프레임워크, 라이브러리,
인프라, 아키텍처 또는 방법을 정리한다.


[결과]

본문에 실제 결과가 있다면 정리한다.

수치가 없으면 수치를 만들어내지 않는다.


[알아둬야 할 것]

이 글을 이해하기 위해 알아두면 좋은
개념이나 배경지식을 쉽게 설명한다.


[추가로 공부하면 좋은 것]

연결해서 공부하면 좋은 기술 또는
개념을 2~4개 추천한다.

왜 공부하면 좋은지도 간단히 설명한다.


[난이도]

초급 / 중급 / 고급 중 하나


[추천 대상]

어떤 개발자나 학습자에게
도움이 될지 한 줄로 설명한다.


규칙:

- 반드시 제공된 본문에 근거한다.
- 본문에 없는 사실을 만들지 않는다.
- 숫자나 성능 결과를 추측하지 않는다.
- 제목만 보고 내용을 추측하지 않는다.
- 어려운 기술 용어는 쉽게 설명한다.
- 주요 기술명과 제품명은 원래 이름을 유지한다.
- 광고, 메뉴, 푸터 등 관련 없는 문구는 무시한다.
- 원문 URL을 요약 내용에 반복하지 않는다.
"""

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

    request = urllib.request.Request(
        url,
        data=data,
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

    try:
        return (
            result["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        )

    except (
        KeyError,
        IndexError
    ):
        print(
            "Gemini 응답:",
            result
        )

        raise RuntimeError(
            "Gemini 응답을 해석하지 못했습니다."
        )


# =========================================================
# Slack
# =========================================================


def send_to_slack(
    article,
    summary
):
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL이 없습니다."
        )

    message_text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "📰 *새 기술 블로그 글*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🏢 *{article['company']}*\n\n"

        f"📌 *{article['title']}*\n\n"

        f"{summary}\n\n"

        f"📅 *게시일*\n"
        f"{article['pub_date'] or '미확인'}\n\n"

        f"🔗 *원문*\n"
        f"{article['link']}"
    )

    message = {
        "text": message_text
    }

    data = json.dumps(
        message
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


# =========================================================
# 초기화
# =========================================================


def initialize_blog_articles(
    new_articles,
    sent_articles
):
    print(
        "초기화 모드입니다."
    )

    added_count = 0

    for article in new_articles:
        article_url = (
            article["link"]
        )

        if (
            article_url
            and article_url
            not in sent_articles
        ):
            sent_articles.append(
                article_url
            )

            added_count += 1

    save_sent_articles(
        sent_articles
    )

    print(
        "기준점으로 등록한 글 수:",
        added_count
    )

    print(
        "Slack 전송은 하지 않습니다."
    )

    return 0


# =========================================================
# 블로그 처리
# =========================================================


def process_blog(
    blog,
    sent_articles
):
    print()

    print(
        "=" * 60
    )

    print(
        f"확인 중: {blog['name']}"
    )

    print(
        "수집 방식:",
        blog["type"]
    )

    articles = get_recent_articles(
        blog,
        limit=RECENT_ARTICLE_LIMIT
    )

    print(
        "확인한 글 수:",
        len(articles)
    )

    new_articles = []

    for article in articles:
        article_url = (
            article["link"]
        )

        if not article_url:
            continue

        if (
            article_url
            not in sent_articles
        ):
            new_articles.append(
                article
            )

    print(
        "새 글 수:",
        len(new_articles)
    )

    if not new_articles:
        print(
            "새 글이 없습니다."
        )

        return 0

    if INITIALIZE_ONLY:
        return initialize_blog_articles(
            new_articles,
            sent_articles
        )

    # RSS는 대부분 최신글부터 제공한다.
    # Slack에는 오래된 새 글부터 보낸다.
    new_articles.reverse()

    sent_count = 0

    for article in new_articles:
        print()

        print(
            "-" * 40
        )

        print(
            "처리할 글:",
            article["title"]
        )

        print(
            "URL:",
            article["link"]
        )

        content = get_article_content(
            article
        )

        print(
            "최종 본문 길이:",
            len(content)
        )

        if not content:
            print(
                "본문이 없어 건너뜁니다."
            )

            continue

        print(
            "Gemini 요약 요청"
        )

        try:
            summary = summarize_with_gemini(
                article,
                content
            )

        except Exception as error:
            print(
                "Gemini 요약 실패:",
                repr(error)
            )

            continue

        print(
            "Gemini 요약 완료"
        )

        try:
            send_to_slack(
                article,
                summary
            )

        except Exception as error:
            print(
                "Slack 전송 실패:",
                repr(error)
            )

            continue

        print(
            "Slack 전송 완료"
        )

        # Slack 발송에 성공한 경우에만
        # 이미 보낸 글로 기록한다.
        sent_articles.append(
            article["link"]
        )

        save_sent_articles(
            sent_articles
        )

        print(
            "발송 기록 저장 완료"
        )

        sent_count += 1

    return sent_count


# =========================================================
# main
# =========================================================


def main():
    sent_articles = (
        load_sent_articles()
    )

    enabled_blogs = [
        blog
        for blog in BLOGS
        if blog.get(
            "enabled",
            True
        )
    ]

    disabled_blogs = [
        blog["name"]
        for blog in BLOGS
        if not blog.get(
            "enabled",
            True
        )
    ]

    print(
        "================================"
    )

    print(
        "Tech News Bot 시작"
    )

    print(
        "전체 등록:",
        len(BLOGS)
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
        "초기화 모드:",
        INITIALIZE_ONLY
    )

    if disabled_blogs:
        print(
            "비활성:",
            ", ".join(
                disabled_blogs
            )
        )

    print(
        "================================"
    )

    success_count = 0
    sent_count_total = 0
    error_count = 0

    failed_blogs = []

    for blog in enabled_blogs:
        try:
            sent_count = (
                process_blog(
                    blog,
                    sent_articles
                )
            )

            success_count += 1

            sent_count_total += (
                sent_count
            )

        except Exception as error:
            error_count += 1

            failed_blogs.append(
                blog["name"]
            )

            print()

            print(
                f"[오류] {blog['name']}"
            )

            print(
                repr(error)
            )

            print(
                "이 블로그는 건너뛰고 "
                "다음 블로그를 확인합니다."
            )

    print()

    print(
        "================================"
    )

    print(
        "모든 블로그 확인 완료"
    )

    print(
        "정상 확인:",
        success_count
    )

    print(
        "실제 Slack 발송 글:",
        sent_count_total
    )

    print(
        "오류:",
        error_count
    )

    print(
        "현재 발송 기록:",
        len(sent_articles)
    )

    if failed_blogs:
        print(
            "실패 블로그:",
            ", ".join(
                failed_blogs
            )
        )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()
